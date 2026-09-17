"""Verificación RTSP real: DESCRIBE autenticado y lectura del SDP (RFC 2326 / RFC 7616)."""

import asyncio
import base64
import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import quote

from app.drivers.errors import AuthenticationFailed, CameraUnreachable, DriverError, NotSupported


@dataclass(frozen=True)
class RtspTarget:
    host: str
    port: int
    username: str
    password: str
    timeout_s: float = 8.0


@dataclass
class RtspDescription:
    status: int
    latency_ms: float
    media: list[dict[str, str]] = field(default_factory=list)
    server: str | None = None


def public_url(target: RtspTarget, path: str) -> str:
    return f"rtsp://{target.host}:{target.port}{path}"


def credential_url(target: RtspTarget, path: str) -> str:
    user = quote(target.username, safe="")
    password = quote(target.password, safe="")
    return f"rtsp://{user}:{password}@{target.host}:{target.port}{path}"


def _parse_challenge(header: str) -> tuple[str, dict[str, str]]:
    scheme, _, rest = header.partition(" ")
    params = dict(re.findall(r'(\w+)="?([^",]*)"?', rest))
    return scheme.lower(), params


def authorization_header(
    challenge: str, method: str, uri: str, username: str, password: str
) -> str:
    scheme, params = _parse_challenge(challenge)
    if scheme == "basic":
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {token}"
    realm, nonce = params.get("realm", ""), params.get("nonce", "")
    algorithm = params.get("algorithm", "MD5").upper()
    hasher = hashlib.sha256 if algorithm == "SHA-256" else hashlib.md5

    def h(value: str) -> str:
        return hasher(value.encode()).hexdigest()

    ha1 = h(f"{username}:{realm}:{password}")
    ha2 = h(f"{method}:{uri}")
    header = f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}"'
    if "auth" in params.get("qop", "").split(","):
        cnonce, nc = secrets.token_hex(8), "00000001"
        response = h(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        header += f', qop=auth, nc={nc}, cnonce="{cnonce}"'
    else:
        response = h(f"{ha1}:{nonce}:{ha2}")
    header += f', response="{response}", algorithm={algorithm}'
    if "opaque" in params:
        header += f', opaque="{params["opaque"]}"'
    return header


def parse_sdp(sdp: str) -> list[dict[str, str]]:
    media: list[dict[str, str]] = []
    for line in sdp.splitlines():
        if line.startswith("m="):
            media.append({"type": line[2:].split(" ")[0]})
        elif line.startswith("a=rtpmap:") and media:
            encoding = line.split(" ", 1)[1] if " " in line else ""
            media[-1].setdefault("codec", encoding.split("/")[0])
    return media


async def _exchange(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, request: str
) -> tuple[int, dict[str, str], str]:
    writer.write(request.encode())
    await writer.drain()
    status_line = (await reader.readline()).decode(errors="replace").strip()
    if not status_line.startswith("RTSP/"):
        raise DriverError(f"Respuesta RTSP inválida: {status_line[:80]!r}")
    status = int(status_line.split(" ")[1])
    headers: dict[str, str] = {}
    while line := (await reader.readline()).decode(errors="replace").strip():
        key, _, value = line.partition(":")
        # WWW-Authenticate puede repetirse (Digest y Basic): se prefiere Digest.
        key = key.strip().lower()
        if key == "www-authenticate" and key in headers and "digest" in headers[key].lower():
            continue
        headers[key] = value.strip()
    length = int(headers.get("content-length", "0"))
    body = (await reader.readexactly(length)).decode(errors="replace") if length else ""
    return status, headers, body


async def describe(target: RtspTarget, path: str) -> RtspDescription:
    uri = public_url(target, path)
    started = time.perf_counter()
    try:
        async with asyncio.timeout(target.timeout_s):
            reader, writer = await asyncio.open_connection(target.host, target.port)
            try:
                base = f"DESCRIBE {uri} RTSP/1.0\r\nAccept: application/sdp\r\n"
                status, headers, body = await _exchange(reader, writer, f"{base}CSeq: 1\r\n\r\n")
                if status == 401 and "www-authenticate" in headers:
                    auth = authorization_header(
                        headers["www-authenticate"],
                        "DESCRIBE",
                        uri,
                        target.username,
                        target.password,
                    )
                    request = f"{base}CSeq: 2\r\nAuthorization: {auth}\r\n\r\n"
                    status, headers, body = await _exchange(reader, writer, request)
            finally:
                writer.close()
    except TimeoutError as exc:
        raise CameraUnreachable(f"RTSP timeout en {target.host}:{target.port}") from exc
    except (OSError, asyncio.IncompleteReadError) as exc:
        raise CameraUnreachable(f"RTSP sin conexión: {exc}") from exc

    latency = (time.perf_counter() - started) * 1000
    if status == 401:
        raise AuthenticationFailed("RTSP rechazó las credenciales", http_status=status)
    if status == 404:
        raise NotSupported(f"RTSP: no existe {path}", http_status=status)
    if status >= 400:
        raise DriverError(f"RTSP DESCRIBE → {status}", http_status=status)
    return RtspDescription(
        status=status, latency_ms=latency, media=parse_sdp(body), server=headers.get("server")
    )
