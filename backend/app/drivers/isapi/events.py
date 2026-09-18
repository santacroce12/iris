"""Lectura del alertStream de Hikvision.

El stream es multipart: cada evento llega como una o más partes (XML o JSON, y a veces
una o más imágenes JPEG del objetivo detectado).
"""

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

from app.domain.events import ParsedAlert, normalize_type
from app.drivers.isapi import xml
from app.drivers.isapi.client import IsapiClient

ALERT_STREAM = "/ISAPI/Event/notification/alertStream"
_MAX_BUFFER = 8 * 1024 * 1024  # corta mensajes corruptos en vez de crecer sin límite


class MultipartBuffer:
    """Acumula bytes del stream y va entregando partes completas."""

    def __init__(self) -> None:
        self._buffer = b""

    def feed(self, chunk: bytes) -> Iterator[tuple[dict[str, str], bytes]]:
        self._buffer += chunk
        if len(self._buffer) > _MAX_BUFFER:
            self._buffer = self._buffer[-_MAX_BUFFER // 2 :]
        while True:
            part = self._take_part()
            if part is None:
                return
            yield part

    def _take_part(self) -> tuple[dict[str, str], bytes] | None:
        start = self._buffer.find(b"--")
        if start < 0:
            return None
        head_end = self._buffer.find(b"\r\n\r\n", start)
        separator = 4
        if head_end < 0:
            head_end = self._buffer.find(b"\n\n", start)
            separator = 2
            if head_end < 0:
                return None

        raw_head = self._buffer[start:head_end].decode("utf-8", "replace")
        headers = {}
        for line in raw_head.splitlines()[1:]:  # la primera línea es el boundary
            key, _, value = line.partition(":")
            if value:
                headers[key.strip().lower()] = value.strip()

        body_start = head_end + separator
        length = headers.get("content-length")
        if length and length.isdigit():
            body_end = body_start + int(length)
            if len(self._buffer) < body_end:
                return None  # falta cuerpo, esperar más datos
        else:
            # Sin Content-Length: el cuerpo termina donde empieza el próximo boundary.
            body_end = self._buffer.find(b"\r\n--", body_start)
            if body_end < 0:
                return None
        body = self._buffer[body_start:body_end]
        self._buffer = self._buffer[body_end:]
        return headers, body


def _parse_xml_alert(content: bytes) -> ParsedAlert:
    root = xml.parse(content)
    raw_type = xml.text(root, "eventType") or "unknown"
    region = xml.find(root, "DetectionRegionList", "DetectionRegionEntry")
    rule_ref = xml.text(region, "regionID") if region is not None else None
    return ParsedAlert(
        raw_type=raw_type,
        type=normalize_type(raw_type),
        state=xml.text(root, "eventState"),
        channel=xml.to_int(xml.text(root, "channelID") or xml.text(root, "dynChannelID")),
        occurred_at=_parse_time(xml.text(root, "dateTime")),
        rule_ref=rule_ref,
        target_type=xml.text(root, "detectionTarget") or xml.text(root, "targetType"),
        payload=xml.to_dict(root),
    )


def _parse_json_alert(content: bytes) -> ParsedAlert:
    data: dict[str, Any] = json.loads(content)
    raw_type = str(data.get("eventType") or data.get("type") or "unknown")
    return ParsedAlert(
        raw_type=raw_type,
        type=normalize_type(raw_type),
        state=data.get("eventState"),
        channel=data.get("channelID") or data.get("channel"),
        occurred_at=_parse_time(data.get("dateTime")),
        rule_ref=str(data["ruleID"]) if data.get("ruleID") is not None else None,
        target_type=data.get("targetType"),
        payload=data,
    )


def _parse_time(value: str | None) -> datetime:
    """La hora la pone la cámara y puede venir en otra zona horaria: se normaliza a UTC."""
    if value:
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def parse_part(headers: dict[str, str], body: bytes) -> ParsedAlert | tuple[str, bytes] | None:
    """Devuelve el evento, o una imagen (mime, bytes), o None si la parte no sirve."""
    content_type = headers.get("content-type", "").lower()
    if content_type.startswith("image/"):
        return content_type.split(";")[0], body
    body = body.strip()
    if not body:
        return None
    if "json" in content_type or body.startswith(b"{"):
        return _parse_json_alert(body)
    if "xml" in content_type or body.startswith(b"<"):
        return _parse_xml_alert(body)
    return None


async def read_alert_stream(
    client: IsapiClient, picture_grace_s: float = 0.4
) -> AsyncIterator[ParsedAlert]:
    """Mantiene abierto el alertStream y entrega eventos con sus imágenes adjuntas.

    Las fotos llegan como partes separadas justo después del XML del evento, así que al
    recibir un evento se espera `picture_grace_s` por si viene una imagen antes de entregarlo.
    """
    buffer = MultipartBuffer()
    pending: ParsedAlert | None = None
    async with client.stream(ALERT_STREAM) as response:
        # La lectura corre en su propia tarea: esperar con timeout sobre el stream
        # directamente cancelaría la lectura en curso y cortaría la conexión.
        cola: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)

        async def leer() -> None:
            try:
                async for chunk in response.aiter_bytes():
                    await cola.put(chunk)
            finally:
                await cola.put(None)

        lector = asyncio.create_task(leer(), name="alertStream-reader")
        try:
            while True:
                try:
                    timeout = picture_grace_s if pending is not None else None
                    chunk = await asyncio.wait_for(cola.get(), timeout)
                except TimeoutError:
                    # Nada más llegó: el evento pendiente ya está completo.
                    if pending is not None:
                        yield pending
                        pending = None
                    continue
                if chunk is None:
                    break
                for headers, body in buffer.feed(chunk):
                    parsed = parse_part(headers, body)
                    if parsed is None:
                        continue
                    if isinstance(parsed, tuple):
                        if pending is not None:
                            pending.pictures.append(parsed)
                        continue
                    if pending is not None:
                        yield pending
                    pending = parsed
        finally:
            lector.cancel()
    if pending is not None:
        yield pending
