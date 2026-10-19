"""Funciones comunes por ISAPI: estado, hora, OSD, imagen, movimiento y reinicio.

Son las que el anteproyecto compara contra ONVIF. Cada una se escribe con el mismo criterio
que las reglas: leer, modificar solo lo pedido y devolver lo que la cámara tiene después.
"""

import re
from typing import Any
from xml.etree.ElementTree import Element

from app.drivers.errors import NotSupported
from app.drivers.isapi import xml
from app.drivers.isapi.client import IsapiClient
from app.drivers.models import (
    DeviceTime,
    ImageSettings,
    MotionDetection,
    OsdSettings,
    SystemStatus,
)

STATUS = "/ISAPI/System/status"
TIME = "/ISAPI/System/time"
NTP = "/ISAPI/System/time/ntpServers"
REBOOT = "/ISAPI/System/reboot"


def _overlays(channel: int) -> str:
    return f"/ISAPI/System/Video/inputs/channels/{channel}/overlays"


def _image(channel: int) -> str:
    return f"/ISAPI/Image/channels/{channel}/color"


def _motion(channel: int) -> str:
    return f"/ISAPI/System/Video/inputs/channels/{channel}/motionDetection"


def _bool(valor: str | None) -> bool | None:
    return None if valor is None else valor == "true"


def _replace(raw: str, tag: str, value: str) -> str:
    """Cambia un campo sin tocar el resto del documento que devolvió la cámara.

    El valor se escapa, porque lo escribe el usuario: un `&` sin escapar arma un documento
    mal formado. Y el reemplazo va por función, no por cadena, para que una `` dentro del
    texto no se lea como referencia a un grupo.
    """
    patron = re.compile(rf"<{tag}>[^<]*</{tag}>")
    if not patron.search(raw):
        raise NotSupported(f"La cámara no expone el campo {tag}")
    escapado = xml.escapar(value)
    return patron.sub(lambda _: f"<{tag}>{escapado}</{tag}>", raw, count=1)


# --- estado --------------------------------------------------------------------------------


def _a_float(valor: str | None) -> float | None:
    """La memoria viene con decimales ("412.35"), no como entero."""
    try:
        return float(valor) if valor else None
    except ValueError:
        return None


def parse_status(root: Element) -> SystemStatus:
    memoria = xml.find(root, "MemoryList", "Memory")
    uso = _a_float(xml.text(memoria, "memoryUsage")) if memoria is not None else None
    disponible = _a_float(xml.text(memoria, "memoryAvailable")) if memoria is not None else None
    porcentaje = None
    if uso is not None and disponible:
        porcentaje = round(uso * 100 / (uso + disponible))
    return SystemStatus(
        uptime_s=xml.to_int(xml.text(root, "deviceUpTime")),
        cpu_percent=xml.to_int(xml.text(root, "CPUList", "CPU", "cpuUtilization")),
        memory_percent=porcentaje,
        raw=xml.to_dict(root),
    )


async def get_status(client: IsapiClient) -> SystemStatus:
    return parse_status((await client.get(STATUS)).xml())


# --- hora ----------------------------------------------------------------------------------


def parse_time(root: Element, ntp: Element | None = None) -> DeviceTime:
    servidor = None
    if ntp is not None:
        servidor = xml.text(ntp, "NTPServer", "hostName") or xml.text(ntp, "NTPServer", "ipAddress")
    return DeviceTime(
        local_time=xml.text(root, "localTime"),
        timezone=xml.text(root, "timeZone"),
        mode=xml.text(root, "timeMode"),
        ntp_server=servidor,
        raw=xml.to_dict(root),
    )


async def get_time(client: IsapiClient) -> DeviceTime:
    respuesta = await client.get(TIME)
    try:
        ntp = (await client.get(NTP)).xml()
    except NotSupported:
        ntp = None
    return parse_time(respuesta.xml(), ntp)


async def set_time(client: IsapiClient, *, local_time: str) -> DeviceTime:
    """Pone la hora en modo manual. `local_time` va con el huso de la cámara."""
    original = (await client.get(TIME)).content.decode()
    nuevo = _replace(_replace(original, "timeMode", "manual"), "localTime", local_time)
    await client.put(TIME, nuevo.encode())
    return await get_time(client)


# --- OSD -----------------------------------------------------------------------------------


def parse_osd(root: Element) -> OsdSettings:
    lineas = [
        texto
        for entrada in xml.find_all(root, "TextOverlay")
        if (texto := xml.text(entrada, "displayText"))
    ]
    return OsdSettings(
        show_name=_bool(xml.text(root, "channelNameOverlay", "enabled")),
        show_date=_bool(xml.text(root, "DateTimeOverlay", "enabled")),
        name=xml.text(root, "channelNameOverlay", "name"),
        date_format=xml.text(root, "DateTimeOverlay", "dateStyle"),
        lines=lineas,
        raw=xml.to_dict(root),
    )


async def get_osd(client: IsapiClient, channel: int = 1) -> OsdSettings:
    return parse_osd((await client.get(_overlays(channel))).xml())


async def set_osd(
    client: IsapiClient,
    channel: int = 1,
    *,
    show_name: bool | None = None,
    show_date: bool | None = None,
    name: str | None = None,
) -> OsdSettings:
    original = (await client.get(_overlays(channel))).content.decode()
    nuevo = original
    if show_name is not None:
        nuevo = re.sub(
            r"(<channelNameOverlay[^>]*>.*?)<enabled>\w+</enabled>",
            rf"\1<enabled>{'true' if show_name else 'false'}</enabled>",
            nuevo,
            count=1,
            flags=re.S,
        )
    if show_date is not None:
        nuevo = re.sub(
            r"(<DateTimeOverlay[^>]*>.*?)<enabled>\w+</enabled>",
            rf"\1<enabled>{'true' if show_date else 'false'}</enabled>",
            nuevo,
            count=1,
            flags=re.S,
        )
    if name is not None:
        nuevo = _replace(nuevo, "name", name[:32])
    await client.put(_overlays(channel), nuevo.encode())
    return await get_osd(client, channel)


# --- imagen --------------------------------------------------------------------------------

_IMAGEN = {
    "brightness": "brightnessLevel",
    "contrast": "contrastLevel",
    "saturation": "saturationLevel",
    "sharpness": "sharpnessLevel",
}


def parse_image(root: Element) -> ImageSettings:
    valores = {campo: xml.to_int(xml.text(root, tag)) for campo, tag in _IMAGEN.items()}
    return ImageSettings(**valores, raw=xml.to_dict(root))


async def get_image(client: IsapiClient, channel: int = 1) -> ImageSettings:
    return parse_image((await client.get(_image(channel))).xml())


async def set_image(client: IsapiClient, channel: int = 1, **valores: int | None) -> ImageSettings:
    original = (await client.get(_image(channel))).content.decode()
    nuevo = original
    for campo, tag in _IMAGEN.items():
        valor = valores.get(campo)
        if valor is not None:
            nuevo = _replace(nuevo, tag, str(max(0, min(100, valor))))
    await client.put(_image(channel), nuevo.encode())
    return await get_image(client, channel)


# --- detección de movimiento ---------------------------------------------------------------


def parse_motion(root: Element) -> MotionDetection:
    grid = xml.find(root, "MotionDetectionLayout", "sensitivityLevel")
    return MotionDetection(
        enabled=_bool(xml.text(root, "enabled")),
        sensitivity=xml.to_int(grid.text if grid is not None else None)
        or xml.to_int(xml.text(root, "MotionDetectionLayout", "sensitivityLevel")),
        raw=xml.to_dict(root),
    )


async def get_motion(client: IsapiClient, channel: int = 1) -> MotionDetection:
    return parse_motion((await client.get(_motion(channel))).xml())


async def set_motion(
    client: IsapiClient,
    channel: int = 1,
    *,
    enabled: bool | None = None,
    sensitivity: int | None = None,
) -> MotionDetection:
    original = (await client.get(_motion(channel))).content.decode()
    nuevo = original
    if enabled is not None:
        nuevo = _replace(nuevo, "enabled", "true" if enabled else "false")
    if sensitivity is not None:
        nuevo = _replace(nuevo, "sensitivityLevel", str(max(0, min(100, sensitivity))))
    await client.put(_motion(channel), nuevo.encode())
    return await get_motion(client, channel)


# --- reinicio ------------------------------------------------------------------------------


async def reboot(client: IsapiClient) -> dict[str, Any]:
    """Reinicia la cámara. Se llama solo con confirmación explícita del usuario."""
    respuesta = await client.put(REBOOT, b"")
    return {"status": respuesta.status}
