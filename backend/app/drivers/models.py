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


@dataclass
class DeviceTime:
    """Hora de la cámara. Los eventos vienen con su hora, así que importa que esté bien."""

    local_time: str | None = None  # como la reporta la cámara, con su huso
    timezone: str | None = None
    mode: str | None = None  # manual | ntp
    ntp_server: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OsdSettings:
    """Texto sobrepuesto en la imagen."""

    show_name: bool | None = None
    show_date: bool | None = None
    name: str | None = None
    date_format: str | None = None
    lines: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageSettings:
    """Ajustes de imagen, normalizados a 0..100."""

    brightness: int | None = None
    contrast: int | None = None
    saturation: int | None = None
    sharpness: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MotionDetection:
    enabled: bool | None = None
    sensitivity: int | None = None  # 0..100
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStatus:
    uptime_s: int | None = None
    cpu_percent: int | None = None
    memory_percent: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)
