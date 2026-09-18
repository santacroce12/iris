"""Normalización de eventos: cada marca y cada API los nombra distinto."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Tipos crudos vistos en las cámaras reales y en la documentación ISAPI.
NORMALIZED_TYPES: dict[str, str] = {
    "linedetection": "line_crossing",
    "fielddetection": "intrusion",
    "regionentrance": "region_entrance",
    "regionexiting": "region_exiting",
    "loitering": "loitering",
    "group": "people_gathering",
    "rapidmove": "fast_moving",
    "unattendedbaggage": "unattended_baggage",
    "attendedbaggage": "object_removal",
    "parking": "parking",
    "vmd": "motion",
    "shelteralarm": "tamper",
    "tamperdetection": "tamper",
    "scenechangedetection": "scene_change",
    "defocus": "defocus",
    "audioexception": "audio_exception",
    "facesnap": "face_capture",
    "facedetection": "face_capture",
    "anpr": "anpr",
    "vehicledetection": "anpr",
    "mixedtargetdetection": "mixed_target",
    "peoplecounting": "people_counting",
    "aiopenplatform": "ai_rule",
    "aiop_video": "ai_rule",
    "aiop_polling_snap": "ai_rule",
    "heopcustomevent": "ai_rule",
    "io": "io",
    "diskfull": "disk_full",
    "diskerror": "disk_error",
    "illaccess": "illegal_access",
    "nicbroken": "nic_broken",
    "ipconflict": "ip_conflict",
}

# La cámara manda esto cada ~10 s aunque no pase nada: es latido, no evento.
HEARTBEAT_TYPES = {"videoloss"}


def normalize_type(raw_type: str) -> str:
    return NORMALIZED_TYPES.get(raw_type.strip().lower(), raw_type.strip().lower())


def is_heartbeat(raw_type: str, state: str | None) -> bool:
    return raw_type.strip().lower() in HEARTBEAT_TYPES and state != "active"


@dataclass
class ParsedAlert:
    """Un mensaje del alertStream ya interpretado, todavía sin agrupar."""

    raw_type: str
    type: str
    state: str | None
    channel: int | None
    occurred_at: datetime
    rule_ref: str | None = None
    target_type: str | None = None
    bbox: dict[str, Any] | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    pictures: list[tuple[str, bytes]] = field(default_factory=list)  # (mime, contenido)

    @property
    def is_active(self) -> bool:
        # Varias cámaras no mandan eventState: si falta, se asume que el evento ocurrió.
        return self.state in (None, "active")

    def episode_key(self) -> tuple[str, int | None, str | None]:
        """Eventos con la misma clave y juntos en el tiempo son el mismo episodio."""
        return (self.type, self.channel, self.rule_ref)
