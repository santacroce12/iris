"""Modelos normalizados que devuelven todos los drivers, independientes del protocolo."""

from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import StreamType


@dataclass
class DeviceInfo:
    vendor: str | None = None
    model: str | None = None
    serial: str | None = None
    firmware: str | None = None
    mac: str | None = None
    name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamProfile:
    token: str
    name: str | None
    stream_type: StreamType
    channel: int
    codec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    bitrate_kbps: int | None = None
    rtsp_path: str | None = None  # ruta relativa, sin host ni credenciales


@dataclass
class Snapshot:
    content: bytes
    mime: str


@dataclass
class ProbeResult:
    ok: bool
    latency_ms: float | None
    error_code: str | None = None
    message: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
