"""Catálogo de funciones que la matriz compara entre protocolos."""

from dataclasses import dataclass

from app.domain.enums import Protocol

ISAPI, ONVIF, RTSP = Protocol.ISAPI, Protocol.ONVIF, Protocol.RTSP


@dataclass(frozen=True)
class CapabilityDef:
    code: str
    group: str
    label: str
    protocols: tuple[Protocol, ...]  # protocolos por los que tiene sentido intentarla


CATALOG: tuple[CapabilityDef, ...] = (
    CapabilityDef("device.info", "Dispositivo", "Información del dispositivo", (ISAPI, ONVIF)),
    CapabilityDef("media.profiles", "Video", "Perfiles de video", (ISAPI, ONVIF)),
    CapabilityDef("media.live", "Video", "Video en vivo", (RTSP,)),
    CapabilityDef("media.snapshot", "Video", "Snapshot", (ISAPI, ONVIF)),
)

BY_CODE = {c.code: c for c in CATALOG}
