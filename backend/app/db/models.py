"""Modelo de datos. Los enums se guardan como texto para que agregar valores no requiera migrar."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.domain.enums import CameraStatus, NetworkMode


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _camera_fk(nullable: bool = False, ondelete: str = "CASCADE") -> Mapped[Any]:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete=ondelete),
        nullable=nullable,
        index=True,
    )


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(120))
    host: Mapped[str] = mapped_column(String(255))
    http_port: Mapped[int] = mapped_column(Integer, default=80)
    use_https: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_tls: Mapped[bool] = mapped_column(Boolean, default=False)
    rtsp_port: Mapped[int] = mapped_column(Integer, default=554)
    onvif_port: Mapped[int] = mapped_column(Integer, default=80)
    channel: Mapped[int] = mapped_column(Integer, default=1)

    username: Mapped[str] = mapped_column(String(120))
    secret_enc: Mapped[str] = mapped_column(Text)
    # Hikvision usa un usuario ONVIF distinto al de la web; si es null se reutiliza el principal.
    onvif_username: Mapped[str | None] = mapped_column(String(120))
    onvif_secret_enc: Mapped[str | None] = mapped_column(Text)

    vendor: Mapped[str | None] = mapped_column(String(60))
    model: Mapped[str | None] = mapped_column(String(120))
    serial: Mapped[str | None] = mapped_column(String(120))
    firmware: Mapped[str | None] = mapped_column(String(120))
    mac: Mapped[str | None] = mapped_column(String(32))
    vca_mode: Mapped[str | None] = mapped_column(String(60))

    network_mode: Mapped[str] = mapped_column(String(10), default=NetworkMode.LAN)
    status: Mapped[str] = mapped_column(String(20), default=CameraStatus.UNKNOWN)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profiles: Mapped[list["VideoProfile"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan", passive_deletes=True
    )


class CapabilityCheck(Base):
    __tablename__ = "capability_checks"
    __table_args__ = (UniqueConstraint("camera_id", "capability_code", "protocol"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    camera_id: Mapped[uuid.UUID] = _camera_fk()
    capability_code: Mapped[str] = mapped_column(String(80))
    protocol: Mapped[str] = mapped_column(String(10))
    level: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(10))
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VideoProfile(Base):
    __tablename__ = "video_profiles"
    __table_args__ = (UniqueConstraint("camera_id", "protocol", "token"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    camera_id: Mapped[uuid.UUID] = _camera_fk()
    protocol: Mapped[str] = mapped_column(String(10))
    token: Mapped[str] = mapped_column(String(120))
    name: Mapped[str | None] = mapped_column(String(120))
    stream_type: Mapped[str] = mapped_column(String(10))
    codec: Mapped[str | None] = mapped_column(String(30))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer)
    rtsp_path: Mapped[str | None] = mapped_column(String(255))
    mediamtx_path: Mapped[str | None] = mapped_column(String(120))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    camera: Mapped[Camera] = relationship(back_populates="profiles")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_camera_occurred", "camera_id", "occurred_at"),
        Index("ix_events_type_occurred", "type", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE")
    )
    protocol: Mapped[str] = mapped_column(String(10))
    raw_type: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(60))
    state: Mapped[str | None] = mapped_column(String(20))
    channel: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    rule_ref: Mapped[str | None] = mapped_column(String(60))
    target_type: Mapped[str | None] = mapped_column(String(30))
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    media: Mapped[list["EventMedia"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", passive_deletes=True
    )


class EventMedia(Base):
    __tablename__ = "event_media"

    id: Mapped[uuid.UUID] = _uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))  # full | target | plate
    path: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(60))
    bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    event: Mapped[Event] = relationship(back_populates="media")


class AnalyticRule(Base):
    __tablename__ = "analytic_rules"
    __table_args__ = (
        UniqueConstraint("camera_id", "protocol", "rule_type", "channel", "external_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    camera_id: Mapped[uuid.UUID] = _camera_fk()
    protocol: Mapped[str] = mapped_column(String(10))
    rule_type: Mapped[str] = mapped_column(String(20))  # line | field | entrance | exiting
    external_id: Mapped[str] = mapped_column(String(30))
    channel: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # coordenadas 0..1
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    linkage: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConfigBackup(Base):
    __tablename__ = "config_backups"

    id: Mapped[uuid.UUID] = _uuid_pk()
    camera_id: Mapped[uuid.UUID] = _camera_fk()
    resource: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(60), default="application/xml")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OperationLog(Base):
    __tablename__ = "operation_logs"
    __table_args__ = (Index("ix_operation_logs_camera_created", "camera_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="SET NULL")
    )
    capability_code: Mapped[str] = mapped_column(String(80))
    protocol: Mapped[str] = mapped_column(String(10))
    operation: Mapped[str] = mapped_column(String(120))
    http_status: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    error_code: Mapped[str | None] = mapped_column(String(60))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
