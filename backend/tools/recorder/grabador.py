"""Graba las respuestas reales de una cámara para poder trabajar después sin ella.

El acceso al hardware es el recurso escaso del trabajo: cuando lo tenés, conviene llevarse
todo. Cada respuesta queda guardada como fixture, y el índice registra qué contestó cada
endpoint, con cuánta latencia y con qué subStatusCode.

Lo que no responde también se guarda: un `403 notSupport` es evidencia.
"""

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.drivers.errors import DriverError
from app.drivers.isapi.client import IsapiClient, IsapiTarget
from app.drivers.isapi.events import ALERT_STREAM, MultipartBuffer, parse_part
from tools.recorder.catalogo import Punto, catalogo

# Se reemplazan antes de guardar: las fixtures se versionan en el repositorio.
_SENSIBLE = (
    (re.compile(rb"(<serialNumber[^>]*>)[^<]+(</serialNumber>)"), rb"\1SERIE-OCULTA\2"),
    (re.compile(rb"(<macAddress>)[^<]+(</macAddress>)"), rb"\g<1>00:00:00:00:00:00\2"),
    (re.compile(rb"(<ipAddress>)\d+\.\d+\.\d+\.\d+(</ipAddress>)"), rb"\g<1>10.0.0.10\2"),
    (re.compile(rb"(<ipv4Address>)\d+\.\d+\.\d+\.\d+(</ipv4Address>)"), rb"\g<1>10.0.0.10\2"),
    (re.compile(rb'("serialNumber":\s*")[^"]+(")'), rb"\1SERIE-OCULTA\2"),
    (re.compile(rb"(<userName>)[^<]*(</userName>)"), rb"\1usuario\2"),
    (re.compile(rb"(<password>)[^<]*(</password>)"), rb"\1oculta\2"),
)


def sanitizar(contenido: bytes) -> bytes:
    for patron, reemplazo in _SENSIBLE:
        contenido = patron.sub(reemplazo, contenido)
    return contenido


@dataclass
class Registro:
    nombre: str
    ruta: str
    grupo: str
    status: int | None
    ok: bool
    latencia_ms: float
    archivo: str | None = None
    bytes: int | None = None
    error: str | None = None
    sub_status: str | None = None


@dataclass
class Resumen:
    modelo: str
    firmware: str
    grabado_en: str
    destino: str
    registros: list[Registro] = field(default_factory=list)

    @property
    def respondieron(self) -> int:
        return sum(1 for r in self.registros if r.ok)


def _sub_status(contenido: bytes) -> str | None:
    m = re.search(rb"<subStatusCode>([^<]*)<", contenido) or re.search(
        rb'"subStatusCode":\s*"([^"]*)"', contenido
    )
    return m.group(1).decode() if m else None


def _nombre_archivo(punto: Punto, contenido: bytes) -> str:
    extension = "json" if punto.json or contenido.lstrip().startswith(b"{") else "xml"
    return f"{punto.nombre}.{extension}"


class Grabador:
    def __init__(self, client: IsapiClient, destino: Path, canal: int = 1) -> None:
        self.client = client
        self.destino = destino
        self.canal = canal

    async def _pedir(self, punto: Punto) -> tuple[Registro, bytes | None]:
        ruta = f"{punto.ruta}?format=json" if punto.json else punto.ruta
        inicio = time.perf_counter()
        try:
            respuesta = await self.client.get(ruta)
        except DriverError as exc:
            return (
                Registro(
                    nombre=punto.nombre,
                    ruta=ruta,
                    grupo=punto.grupo,
                    status=exc.http_status,
                    ok=False,
                    latencia_ms=round((time.perf_counter() - inicio) * 1000, 1),
                    error=exc.code,
                    sub_status=str(exc.message).split()[-1] if exc.message else None,
                ),
                None,
            )
        return (
            Registro(
                nombre=punto.nombre,
                ruta=ruta,
                grupo=punto.grupo,
                status=respuesta.status,
                ok=True,
                latencia_ms=round(respuesta.latency_ms, 1),
                bytes=len(respuesta.content),
                sub_status=_sub_status(respuesta.content),
            ),
            respuesta.content,
        )

    async def identificar(self) -> tuple[str, str]:
        info = (await self.client.get("/ISAPI/System/deviceInfo")).xml()
        from app.drivers.isapi import xml

        modelo = xml.text(info, "model") or "modelo-desconocido"
        firmware = (xml.text(info, "firmwareVersion") or "sin-firmware").split()[0]
        return modelo.strip(), firmware.strip()

    async def puntos_de_la_tarea_de_ia(self) -> list[Punto]:
        """Las reglas del domo viven dentro de una tarea cuyo id hay que averiguar."""
        base = "/ISAPI/Intelligent/AIOpenPlatform"
        try:
            tareas = json.loads((await self.client.get(f"{base}/videoTask?format=json")).content)
        except (DriverError, ValueError):
            return []
        extra = []
        for tarea in tareas.get("Tasks") or []:
            tid = tarea.get("taskID")
            if not tid:
                continue
            ruta = f"{base}/AIRuleConfig/task/{tid}/channels/{self.canal}"
            extra += [
                Punto("aiopRuleConfig", ruta, "IA", json=True),
                Punto("aiopRuleTrigger", f"{ruta}/trigger", "IA", json=True),
            ]
        return extra

    async def barrer(self, resumen: Resumen) -> None:
        puntos = catalogo(self.canal) + await self.puntos_de_la_tarea_de_ia()
        for punto in puntos:
            registro, contenido = await self._pedir(punto)
            if contenido is not None:
                archivo = self.destino / _nombre_archivo(punto, contenido)
                archivo.write_bytes(sanitizar(contenido))
                registro.archivo = archivo.name
            resumen.registros.append(registro)
            marca = "ok " if registro.ok else "no "
            detalle = registro.sub_status or registro.error or ""
            print(f"  {marca}{punto.nombre:<32} {registro.latencia_ms:>7.1f} ms  {detalle}")

    async def snapshot(self, resumen: Resumen) -> None:
        ruta = f"/ISAPI/Streaming/channels/{self.canal}01/picture"
        inicio = time.perf_counter()
        try:
            respuesta = await self.client.get(ruta)
        except DriverError as exc:
            resumen.registros.append(
                Registro("snapshot", ruta, "video", exc.http_status, False, 0, error=exc.code)
            )
            return
        archivo = self.destino / "snapshot.jpg"
        archivo.write_bytes(respuesta.content)
        resumen.registros.append(
            Registro(
                "snapshot",
                ruta,
                "video",
                respuesta.status,
                True,
                round((time.perf_counter() - inicio) * 1000, 1),
                archivo.name,
                len(respuesta.content),
            )
        )
        print(f"  ok snapshot                         {len(respuesta.content)} bytes")

    async def alert_stream(self, resumen: Resumen, segundos: int, maximo: int = 6) -> None:
        """Guarda una muestra del flujo de eventos tal como lo manda la cámara."""
        import asyncio

        print(f"  escuchando eventos {segundos} s...")
        buffer = MultipartBuffer()
        guardados = 0
        vistos: dict[str, int] = {}
        limite = asyncio.get_running_loop().time() + segundos
        try:
            async with self.client.stream(ALERT_STREAM) as respuesta:
                cola: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)

                async def leer() -> None:
                    try:
                        async for trozo in respuesta.aiter_bytes():
                            await cola.put(trozo)
                    finally:
                        await cola.put(None)

                lector = asyncio.create_task(leer())
                try:
                    while asyncio.get_running_loop().time() < limite:
                        try:
                            trozo = await asyncio.wait_for(cola.get(), timeout=2)
                        except TimeoutError:
                            continue
                        if trozo is None:
                            break
                        for cabeceras, cuerpo in buffer.feed(trozo):
                            parsed = parse_part(cabeceras, cuerpo)
                            if parsed is None or isinstance(parsed, tuple):
                                continue
                            vistos[parsed.raw_type] = vistos.get(parsed.raw_type, 0) + 1
                            if guardados < maximo:
                                nombre = f"alertStream_{parsed.raw_type}_{vistos[parsed.raw_type]}"
                                (self.destino / f"{nombre}.xml").write_bytes(
                                    sanitizar(cuerpo.strip())
                                )
                                guardados += 1
                finally:
                    lector.cancel()
        except DriverError as exc:
            resumen.registros.append(
                Registro("alertStream", ALERT_STREAM, "eventos", None, False, 0, error=exc.code)
            )
            print(f"  no alertStream: {exc.message}")
            return
        resumen.registros.append(
            Registro(
                "alertStream",
                ALERT_STREAM,
                "eventos",
                200,
                True,
                segundos * 1000,
                bytes=guardados,
                sub_status=", ".join(f"{k}×{v}" for k, v in vistos.items()) or "sin eventos",
            )
        )
        print(f"  ok eventos: {vistos or 'ninguno'}")


async def grabar(
    target: IsapiTarget, raiz: Path, canal: int = 1, segundos_eventos: int = 30
) -> Resumen:
    async with IsapiClient(target) as client:
        grabador = Grabador(client, raiz, canal)
        modelo, firmware = await grabador.identificar()
        destino = raiz / modelo / firmware
        destino.mkdir(parents=True, exist_ok=True)
        grabador.destino = destino

        resumen = Resumen(
            modelo=modelo,
            firmware=firmware,
            grabado_en=datetime.now(UTC).isoformat(timespec="seconds"),
            destino=str(destino),
        )
        print(f"\n{modelo} · {firmware}\n  guardando en {destino}\n")
        await grabador.barrer(resumen)
        await grabador.snapshot(resumen)
        if segundos_eventos > 0:
            await grabador.alert_stream(resumen, segundos_eventos)

        indice = destino / "indice.json"
        datos: dict[str, Any] = asdict(resumen)
        datos["respondieron"] = resumen.respondieron
        datos["total"] = len(resumen.registros)
        indice.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        return resumen
