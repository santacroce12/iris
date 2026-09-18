import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CameraStatus, NetworkMode, StreamType


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
