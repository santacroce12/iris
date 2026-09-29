"""Perfiles de cámara simulada.

Las respuestas de analítica y capacidades son grabaciones reales (las fixtures de los tests).
La identidad (serie, MAC, IP) es inventada a propósito, para que nunca se confunda una cámara
simulada con una de verdad en los informes.
"""

from dataclasses import dataclass, field
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures/hikvision"


@dataclass(frozen=True)
class Profile:
    key: str
    model: str
    firmware: str
    serial: str
    mac: str
    family: str  # smart | aiop | none
    fixtures: Path
    # recurso ISAPI -> archivo de fixture
    static: dict[str, str] = field(default_factory=dict)
    # tipos de evento que este modelo puede emitir
    events: tuple[str, ...] = ()

    def read(self, nombre: str) -> bytes:
        return (self.fixtures / nombre).read_bytes()


PTZ = Profile(
    key="ptz",
    model="DS-2DF8A836IX-AEL",
    firmware="V5.6.0 build 190320",
    serial="SIMULADA-DS2DF8A836IX-0001",
    mac="02:00:00:00:00:01",
    family="smart",
    fixtures=FIXTURES / "DS-2DF8A836IX-AEL/V5.6.0",
    static={
        "/ISAPI/System/capabilities": "smartCapabilities.xml",
        "/ISAPI/Smart/capabilities": "smartCapabilities.xml",
        "/ISAPI/Streaming/channels/1/metadata/capabilities": "metadataCapabilities.xml",
    },
    events=("linedetection", "fielddetection", "VMD", "regionEntrance", "regionExiting"),
)

DOMO = Profile(
    key="domo",
    model="iDS-2CD7146G2-IZS",
    firmware="V5.9.24 build 260702",
    serial="SIMULADA-IDS2CD7146G2-0001",
    mac="02:00:00:00:00:02",
    family="aiop",
    fixtures=FIXTURES / "iDS-2CD7146G2-IZS/V5.9.24",
    static={
        "/ISAPI/System/capabilities": "smartCapabilities.xml",
        "/ISAPI/Event/notification/subscribeEventCap": "subscribeEventCap.xml",
        "/ISAPI/Event/capabilities": "eventCapabilities.xml",
        "/ISAPI/Intelligent/AIOpenPlatform": "aiopInfo.json",
        "/ISAPI/Intelligent/AIOpenPlatform/capabilities": "aiopCapabilities.json",
        "/ISAPI/Intelligent/AIOpenPlatform/videoTask": "aiopVideoTask.json",
        "/ISAPI/Intelligent/AIOpenPlatform/videoTask/capabilities": (
            "aiopVideoTaskCapabilities.json"
        ),
        "/ISAPI/Intelligent/AIOpenPlatform/algorithmModel/engines": "aiopAlgorithmEngines.json",
        "/ISAPI/Intelligent/AIOpenPlatform/algorithmModel/management": "aiopAlgorithmModels.json",
        "/ISAPI/Intelligent/AIOpenPlatform/AIRuleConfig/channels/1/capabilities": (
            "aiopRuleCapabilities.json"
        ),
    },
    events=("VMD", "soundclassificationdetection", "AIOP_Video"),
)

BASICA = Profile(
    key="basica",
    model="DS-2CD1023G2-I",
    firmware="V5.8.4",
    serial="SIMULADA-DS2CD1023G2-0001",
    mac="02:00:00:00:00:03",
    family="none",
    fixtures=FIXTURES / "DS-2CD1023G2-I/V5.8.4",
    static={
        "/ISAPI/Streaming/channels": "streamingChannels.xml",
        "/ISAPI/Event/triggersCap": "eventTriggersCap.xml",
    },
    events=("VMD",),
)

PROFILES = {p.key: p for p in (PTZ, DOMO, BASICA)}
