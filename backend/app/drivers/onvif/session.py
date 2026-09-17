import asyncio
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiohttp
from onvif import ONVIFCamera
from onvif.exceptions import ONVIFAuthError, ONVIFError, ONVIFTimeoutError

from app.drivers.errors import AuthenticationFailed, CameraUnreachable, DriverError, NotSupported


@dataclass(frozen=True)
class OnvifTarget:
    host: str
    port: int
    username: str
    password: str
    timeout_s: float = 8.0
    # Reescribe las URLs anunciadas por la cámara al host/puerto configurado (NAT / port-forward).
    nat_override: bool = False


_AUTH_HINTS = ("notauthorized", "not authorized", "unauthorized", "authority failure")


def translate_error(exc: BaseException) -> DriverError:
    message = str(exc)
    lowered = message.lower()
    if isinstance(exc, ONVIFAuthError) or any(h in lowered for h in _AUTH_HINTS):
        return AuthenticationFailed(f"ONVIF: {message}")
    if isinstance(exc, ONVIFTimeoutError | asyncio.TimeoutError | TimeoutError):
        return CameraUnreachable(f"ONVIF timeout: {message}")
    if isinstance(exc, aiohttp.ClientError | OSError):
        return CameraUnreachable(f"ONVIF sin conexión: {message}")
    if "actionnotsupported" in lowered or "not supported" in lowered:
        return NotSupported(f"ONVIF: {message}")
    if isinstance(exc, ONVIFError):
        return DriverError(f"ONVIF: {message}")
    return DriverError(f"ONVIF inesperado: {exc!r}")


class OnvifSession:
    def __init__(self, target: OnvifTarget) -> None:
        self.target = target
        self.camera = ONVIFCamera(
            target.host,
            target.port,
            target.username,
            target.password,
            adjust_time=True,
            nat_override=target.nat_override,
        )

    async def call[T](self, awaitable: Awaitable[T]) -> T:
        try:
            return await asyncio.wait_for(awaitable, timeout=self.target.timeout_s)
        except DriverError:
            raise
        except Exception as exc:  # zeep/aiohttp lanzan una variedad amplia de errores
            raise translate_error(exc) from exc


@asynccontextmanager
async def onvif_session(target: OnvifTarget) -> AsyncIterator[OnvifSession]:
    session = OnvifSession(target)
    try:
        await session.call(session.camera.update_xaddrs())
        yield session
    finally:
        await session.camera.close()
