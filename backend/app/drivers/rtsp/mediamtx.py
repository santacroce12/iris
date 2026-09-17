"""Publicación de cámaras en MediaMTX vía su API v3.

El navegador solo recibe URLs sin credenciales.
"""

from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.drivers.errors import CameraUnreachable, DriverError


@dataclass(frozen=True)
class LiveUrls:
    path: str
    webrtc: str  # página/endpoint WHEP
    whep: str
    hls: str


class MediaMtx:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def urls(self, path: str) -> LiveUrls:
        webrtc = f"{self.settings.mediamtx_webrtc_url}/{path}"
        return LiveUrls(
            path=path,
            webrtc=webrtc,
            whep=f"{webrtc}/whep",
            hls=f"{self.settings.mediamtx_hls_url}/{path}/index.m3u8",
        )

    async def publish(self, path: str, source_url: str) -> LiveUrls:
        config = {"source": source_url, "sourceOnDemand": True, "rtspTransport": "tcp"}
        async with httpx.AsyncClient(base_url=self.settings.mediamtx_api_url, timeout=5) as api:
            try:
                response = await api.post(f"/v3/config/paths/replace/{path}", json=config)
            except httpx.HTTPError as exc:
                raise CameraUnreachable(f"MediaMTX no responde: {exc}") from exc
        if response.status_code >= 400:
            raise DriverError(f"MediaMTX rechazó la ruta {path}: {response.text[:200]}")
        return self.urls(path)

    async def remove(self, path: str) -> None:
        async with httpx.AsyncClient(base_url=self.settings.mediamtx_api_url, timeout=5) as api:
            try:
                await api.delete(f"/v3/config/paths/delete/{path}")
            except httpx.HTTPError:
                pass  # si MediaMTX no está, no hay ruta que borrar
