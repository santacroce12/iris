import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from app.drivers.errors import (
    AuthenticationFailed,
    CameraUnreachable,
    DriverError,
    InvalidResponse,
    NotSupported,
)
from app.drivers.isapi import xml


@dataclass(frozen=True)
class IsapiTarget:
    host: str
    port: int
    username: str
    password: str
    use_https: bool = False
    verify_tls: bool = False
    timeout_s: float = 8.0

    @property
    def base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass(frozen=True)
class IsapiResponse:
    status: int
    content_type: str
    content: bytes
    latency_ms: float

    @property
    def is_xml(self) -> bool:
        return "xml" in self.content_type or self.content.lstrip().startswith(b"<")

    def xml(self):
        return xml.parse(self.content)

    def json(self):
        import json

        try:
            return json.loads(self.content)
        except ValueError as exc:
            raise InvalidResponse(f"JSON inválido: {exc}") from exc


def _isapi_error_detail(response: httpx.Response) -> str:
    """Hikvision devuelve <ResponseStatus> con subStatusCode (p. ej. notSupport, badXmlContent)."""
    try:
        root = xml.parse(response.content)
        return xml.text(root, "subStatusCode") or xml.text(root, "statusString") or ""
    except DriverError:
        return response.text[:200]


class IsapiClient:
    """Cliente HTTP Digest para ISAPI. Un cliente por cámara; usar como context manager."""

    def __init__(self, target: IsapiTarget) -> None:
        self.target = target
        self._http = httpx.AsyncClient(
            base_url=target.base_url,
            auth=httpx.DigestAuth(target.username, target.password),
            verify=target.verify_tls,
            timeout=httpx.Timeout(target.timeout_s),
            follow_redirects=True,
        )

    async def __aenter__(self) -> "IsapiClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        content: bytes | str | None = None,
        content_type: str = "application/xml",
        params: dict[str, str] | None = None,
    ) -> IsapiResponse:
        headers = {"Content-Type": content_type} if content is not None else None
        started = time.perf_counter()
        try:
            response = await self._http.request(
                method, path, content=content, params=params, headers=headers
            )
        except httpx.TimeoutException as exc:
            raise CameraUnreachable(f"Timeout en {method} {path}") from exc
        except httpx.HTTPError as exc:
            raise CameraUnreachable(f"No se pudo conectar: {exc}") from exc
        latency = (time.perf_counter() - started) * 1000
        self._raise_for_status(response, method, path)
        return IsapiResponse(
            status=response.status_code,
            content_type=response.headers.get("content-type", ""),
            content=response.content,
            latency_ms=latency,
        )

    async def get(self, path: str, **kwargs) -> IsapiResponse:
        return await self.request("GET", path, **kwargs)

    async def put(self, path: str, content: bytes | str, **kwargs) -> IsapiResponse:
        return await self.request("PUT", path, content=content, **kwargs)

    async def post(self, path: str, content: bytes | str, **kwargs) -> IsapiResponse:
        return await self.request("POST", path, content=content, **kwargs)

    @asynccontextmanager
    async def stream(self, path: str) -> AsyncIterator[httpx.Response]:
        """Conexión larga (alertStream). Sin timeout de lectura: la cámara manda heartbeats."""
        timeout = httpx.Timeout(self.target.timeout_s, read=None)
        try:
            async with self._http.stream("GET", path, timeout=timeout) as response:
                if response.status_code >= 400:
                    await response.aread()
                    self._raise_for_status(response, "GET", path)
                yield response
        except httpx.TimeoutException as exc:
            raise CameraUnreachable(f"Timeout abriendo {path}") from exc
        except httpx.TransportError as exc:
            raise CameraUnreachable(f"Stream interrumpido: {exc}") from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response, method: str, path: str) -> None:
        status = response.status_code
        if status < 400:
            return
        detail = _isapi_error_detail(response)
        message = f"{method} {path} → HTTP {status} {detail}".strip()
        # Hikvision responde 403 + subStatusCode=notSupport para funciones inexistentes:
        # hay que mirar el cuerpo antes de asumir un problema de credenciales.
        if status in (404, 405, 501) or detail.lower() in ("notsupport", "invalid operation"):
            raise NotSupported(message, http_status=status)
        if status in (401, 403):
            raise AuthenticationFailed(message, http_status=status)
        raise DriverError(message, http_status=status)
