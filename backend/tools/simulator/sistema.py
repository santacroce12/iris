"""Las funciones comunes de la cámara simulada: estado, hora, OSD, imagen y movimiento.

Cada perfil expone un subconjunto distinto, que es lo que hace interesante a la matriz: la
cámara básica no tiene ajustes de imagen ni OSD, igual que en la realidad.
"""

import re
from datetime import UTC, datetime, timedelta

HUSO = timedelta(hours=8)  # la PTZ real reporta en +08:00


def status_xml(uptime_s: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<DeviceStatus version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
        "<currentDeviceTime>"
        f"{(datetime.now(UTC) + HUSO).strftime('%Y-%m-%dT%H:%M:%S+08:00')}"
        "</currentDeviceTime>"
        f"<deviceUpTime>{uptime_s}</deviceUpTime>"
        "<CPUList><CPU><cpuDescription>CPU1</cpuDescription>"
        "<cpuUtilization>17</cpuUtilization></CPU></CPUList>"
        "<MemoryList><Memory><memoryDescription>DDR</memoryDescription>"
        "<memoryUsage>412.35</memoryUsage><memoryAvailable>611.65</memoryAvailable>"
        "</Memory></MemoryList></DeviceStatus>"
    )


def time_xml(modo: str = "NTP", hora: str | None = None) -> str:
    momento = hora or (datetime.now(UTC) + HUSO).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Time version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
        f"<timeMode>{modo}</timeMode><localTime>{momento}</localTime>"
        "<timeZone>CST-8:00:00</timeZone></Time>"
    )


NTP_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<NTPServerList version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
    "<NTPServer><id>1</id><addressingFormatType>hostname</addressingFormatType>"
    "<hostName>time.windows.com</hostName><portNo>123</portNo>"
    "<synchronizeInterval>1440</synchronizeInterval></NTPServer></NTPServerList>"
)

OSD_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<VideoOverlay version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
    "<normalizedScreenSize><normalizedScreenWidth>704</normalizedScreenWidth>"
    "<normalizedScreenHeight>576</normalizedScreenHeight></normalizedScreenSize>"
    '<TextOverlayList size="4"><TextOverlay><id>1</id><enabled>true</enabled>'
    "<positionX>16</positionX><positionY>492</positionY>"
    "<displayText>Camara simulada</displayText></TextOverlay></TextOverlayList>"
    "<DateTimeOverlay><enabled>true</enabled><positionX>16</positionX>"
    "<positionY>16</positionY><dateStyle>MM-DD-YYYY</dateStyle>"
    "<timeStyle>24hour</timeStyle><displayWeek>false</displayWeek></DateTimeOverlay>"
    "<channelNameOverlay><enabled>true</enabled><positionX>512</positionX>"
    "<positionY>64</positionY><name>Entrada</name></channelNameOverlay>"
    "</VideoOverlay>"
)

IMAGEN_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Color version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
    "<brightnessLevel>50</brightnessLevel><contrastLevel>50</contrastLevel>"
    "<saturationLevel>50</saturationLevel><sharpnessLevel>50</sharpnessLevel></Color>"
)

MOVIMIENTO_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<MotionDetection version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
    "<enabled>false</enabled><enableHighlight>true</enableHighlight>"
    "<samplingInterval>2</samplingInterval><startTriggerTime>500</startTriggerTime>"
    "<endTriggerTime>500</endTriggerTime><regionType>grid</regionType>"
    "<Grid><rowGranularity>18</rowGranularity><columnGranularity>22</columnGranularity></Grid>"
    "<MotionDetectionLayout><sensitivityLevel>20</sensitivityLevel>"
    "<layout><gridMap>000000</gridMap></layout></MotionDetectionLayout>"
    "</MotionDetection>"
)


class Sistema:
    """Guarda en memoria lo que se le escribe, como haría la cámara."""

    def __init__(self, *, con_osd: bool = True, con_imagen: bool = True) -> None:
        self.arranque = datetime.now(UTC)
        self.osd = OSD_XML if con_osd else None
        self.imagen = IMAGEN_XML if con_imagen else None
        self.movimiento = MOVIMIENTO_XML
        self.hora: str | None = None
        self.modo_hora = "NTP"
        self.reinicios = 0

    @property
    def uptime_s(self) -> int:
        return int((datetime.now(UTC) - self.arranque).total_seconds())

    def leer_hora(self) -> str:
        return time_xml(self.modo_hora, self.hora)

    def escribir_hora(self, contenido: str) -> None:
        modo = re.search(r"<timeMode>(\w+)</timeMode>", contenido)
        momento = re.search(r"<localTime>([^<]+)</localTime>", contenido)
        if modo:
            self.modo_hora = modo.group(1)
        if momento:
            self.hora = momento.group(1)

    def reiniciar(self) -> None:
        self.reinicios += 1
        self.arranque = datetime.now(UTC)
