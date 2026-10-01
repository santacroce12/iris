import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CameraStatus, NetworkMode, StreamType
from app.domain.rules import Rule, RuleKindInfo, RuleSet, RuleUpdate


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    http_port: int = Field(80, ge=1, le=65535)
    use_https: bool = False
    verify_tls: bool = False
    rtsp_port: int = Field(554, ge=1, le=65535)
    onvif_port: int = Field(80, ge=1, le=65535)
    channel: int = Field(1, ge=1)
    username: str = Field(min_length=1, max_length=120)
    onvif_username: str | None = None
    network_mode: NetworkMode = NetworkMode.LAN


class CameraCreate(CameraBase):
    password: str = Field(min_length=1)
    onvif_password: str | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    http_port: int | None = Field(None, ge=1, le=65535)
    use_https: bool | None = None
    verify_tls: bool | None = None
    rtsp_port: int | None = Field(None, ge=1, le=65535)
    onvif_port: int | None = Field(None, ge=1, le=65535)
    channel: int | None = Field(None, ge=1)
    username: str | None = None
    password: str | None = None
    onvif_username: str | None = None
    onvif_password: str | None = None
    network_mode: NetworkMode | None = None


class CameraOut(CameraBase):
    """Nunca incluye contraseñas."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor: str | None
    model: str | None
    serial: str | None
    firmware: str | None
    mac: str | None
    vca_mode: str | None
    status: CameraStatus
    last_seen_at: datetime | None
    listen_events: bool
    created_at: datetime


class ProtocolCheck(BaseModel):
    ok: bool
    latency_ms: float
    error_code: str | None = None
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ConnectionReportOut(BaseModel):
    status: CameraStatus
    isapi: ProtocolCheck
    onvif: ProtocolCheck
    rtsp: ProtocolCheck


class VideoProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    protocol: str
    token: str
    name: str | None
    stream_type: StreamType
    codec: str | None
    width: int | None
    height: int | None
    fps: float | None
    bitrate_kbps: int | None
    rtsp_path: str | None


class LiveOut(BaseModel):
    path: str
    webrtc: str
    whep: str
    hls: str
    codec: str | None = None
    # Por qué se está viendo otro stream del pedido, o por qué no se va a ver nada.
    note: str | None = None


class CapabilityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    capability_code: str
    protocol: str
    level: str
    source: str
    evidence: dict[str, Any] | None
    latency_ms: float | None
    checked_at: datetime


class OperationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    capability_code: str
    protocol: str
    operation: str
    http_status: int | None
    success: bool
    latency_ms: float | None
    error_code: str | None
    detail: dict[str, Any] | None
    created_at: datetime


class EventMediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    mime: str
    bytes: int


class EventOut(BaseModel):
    """Un evento es un episodio: duró de occurred_at a ended_at con `hits` avisos."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    camera_id: uuid.UUID
    protocol: str
    raw_type: str
    type: str
    state: str | None
    channel: int | None
    occurred_at: datetime
    ended_at: datetime | None
    received_at: datetime
    hits: int
    rule_ref: str | None
    target_type: str | None
    payload: dict[str, Any] | None
    media: list[EventMediaOut] = Field(default_factory=list)


class ListenerState(BaseModel):
    camera_id: uuid.UUID
    status: str
    connected_since: datetime | None
    alerts_received: int
    episodes_saved: int
    open_episodes: int
    last_error: str | None


class RuleOut(BaseModel):
    """Una regla vista desde la plataforma: coordenadas 0..1 con origen arriba a la izquierda."""

    kind: str
    external_id: str
    name: str | None
    points: list[tuple[float, float]]
    enabled: bool
    configured: bool
    sensitivity: int | None
    direction: str | None
    target: list[str]
    extra: dict[str, Any]

    @classmethod
    def desde(cls, regla: Rule) -> "RuleOut":
        return cls(
            kind=regla.kind.value,
            external_id=regla.external_id,
            name=regla.name,
            points=regla.points,
            enabled=regla.enabled,
            configured=regla.configured,
            sensitivity=regla.sensitivity,
            direction=regla.direction,
            target=regla.target,
            extra=regla.extra,
        )


class RuleKindOut(BaseModel):
    """Lo que la cámara permite para un tipo de regla."""

    kind: str
    max_rules: int
    enabled: bool
    min_points: int
    max_points: int
    targets: list[str]
    directions: list[str]
    toggle_per_rule: bool

    @classmethod
    def desde(cls, info: RuleKindInfo) -> "RuleKindOut":
        return cls(**{**info.__dict__, "kind": info.kind.value})


class RuleSetOut(BaseModel):
    family: str
    kinds: list[RuleKindOut]
    rules: list[RuleOut]
    note: str | None

    @classmethod
    def desde(cls, conjunto: RuleSet) -> "RuleSetOut":
        return cls(
            family=conjunto.family.value,
            kinds=[RuleKindOut.desde(k) for k in conjunto.kinds],
            rules=[RuleOut.desde(r) for r in conjunto.rules],
            note=conjunto.note,
        )


class RulePatch(BaseModel):
    """Solo se escribe lo que viene; el resto de la regla queda como está en la cámara."""

    points: list[tuple[float, float]] | None = None
    enabled: bool | None = None
    sensitivity: int | None = Field(default=None, ge=1, le=100)
    direction: str | None = None
    target: list[str] | None = None
    name: str | None = Field(default=None, max_length=32)

    def a_update(self) -> RuleUpdate:
        return RuleUpdate(**self.model_dump(exclude_unset=True))


class ConfigBackupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource: str
    content_type: str
    created_at: datetime
    restored_at: datetime | None


class MatrixCellOut(BaseModel):
    camera_id: uuid.UUID
    protocol: str
    level: str
    source: str | None
    latency_ms: float | None
    checked_at: datetime | None
    evidence: dict[str, Any] | None


class MatrixRowOut(BaseModel):
    """Una función del catálogo, con una celda por cámara y protocolo."""

    code: str
    group: str
    label: str
    protocols: list[str]
    cells: list[MatrixCellOut]


class MatrixCameraOut(BaseModel):
    id: uuid.UUID
    name: str
    model: str | None
    host: str


class MatrixOut(BaseModel):
    cameras: list[MatrixCameraOut]
    rows: list[MatrixRowOut]


class DeviceTimeOut(BaseModel):
    local_time: str | None
    timezone: str | None
    mode: str | None
    ntp_server: str | None


class OsdOut(BaseModel):
    show_name: bool | None
    show_date: bool | None
    name: str | None
    date_format: str | None
    lines: list[str]


class ImageOut(BaseModel):
    brightness: int | None
    contrast: int | None
    saturation: int | None
    sharpness: int | None


class MotionOut(BaseModel):
    enabled: bool | None
    sensitivity: int | None


class SystemStatusOut(BaseModel):
    uptime_s: int | None
    cpu_percent: int | None
    memory_percent: int | None


class FunctionsOut(BaseModel):
    """Las funciones comunes leídas por un protocolo, para poder compararlas lado a lado."""

    protocol: str
    status: SystemStatusOut | None = None
    time: DeviceTimeOut | None = None
    osd: OsdOut | None = None
    image: ImageOut | None = None
    motion: MotionOut | None = None
    errors: dict[str, str] = Field(default_factory=dict)


class OsdPatch(BaseModel):
    show_name: bool | None = None
    show_date: bool | None = None
    name: str | None = Field(default=None, max_length=32)


class ImagePatch(BaseModel):
    brightness: int | None = Field(default=None, ge=0, le=100)
    contrast: int | None = Field(default=None, ge=0, le=100)
    saturation: int | None = Field(default=None, ge=0, le=100)
    sharpness: int | None = Field(default=None, ge=0, le=100)


class MotionPatch(BaseModel):
    enabled: bool | None = None
    sensitivity: int | None = Field(default=None, ge=0, le=100)


class RecordingOut(BaseModel):
    """Estado de la grabación continua de una cámara y los segmentos que ya quedaron."""

    path: str
    recording: bool
    segments: list[dict[str, Any]] = Field(default_factory=list)
