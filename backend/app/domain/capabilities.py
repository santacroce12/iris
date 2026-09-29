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
    CapabilityDef("analytics.rules", "Analítica", "Reglas de analítica", (ISAPI, ONVIF)),
    # Funciones comunes: son las que el anteproyecto compara entre el protocolo propietario
    # y el estándar. Cada una se intenta por los dos y la matriz muestra el resultado.
    CapabilityDef("system.status", "Sistema", "Estado y salud", (ISAPI, ONVIF)),
    CapabilityDef("system.time", "Sistema", "Hora del dispositivo", (ISAPI, ONVIF)),
    CapabilityDef("system.reboot", "Sistema", "Reinicio", (ISAPI, ONVIF)),
    CapabilityDef("video.osd", "Imagen", "Texto sobre la imagen (OSD)", (ISAPI, ONVIF)),
    CapabilityDef("video.image", "Imagen", "Ajustes de imagen", (ISAPI, ONVIF)),
    CapabilityDef("events.motion", "Eventos", "Detección de movimiento", (ISAPI, ONVIF)),
)

BY_CODE = {c.code: c for c in CATALOG}
