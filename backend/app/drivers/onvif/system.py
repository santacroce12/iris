"""Las mismas funciones comunes, pero por ONVIF: es la comparación que pide el anteproyecto.

Diferencias de fondo con ISAPI, que después se ven en la matriz:
- La hora ONVIF viene siempre en UTC y separada en campos, no como texto.
- La imagen se ajusta por el servicio Imaging, con rangos que declara la cámara (no 0..100).
- El OSD es opcional en Media2 y muchas cámaras no lo exponen aunque lo tengan en su web.
- La detección de movimiento no es una función ONVIF: se ve como regla de analítica o como
  evento suscribible, así que la comparación honesta es "parcial", no "soportada".
"""

from typing import Any

from app.drivers.errors import NotSupported
from app.drivers.models import DeviceTime, ImageSettings, MotionDetection, OsdSettings
from app.drivers.onvif.session import OnvifSession


def _numero(valor: Any) -> int | None:
    return None if valor is None else int(valor)


def _a_cien(valor: Any, minimo: float, maximo: float) -> int | None:
    """ONVIF declara su propio rango por cámara; se normaliza a 0..100 para poder comparar."""
    if valor is None or maximo <= minimo:
        return None
    return round((float(valor) - minimo) * 100 / (maximo - minimo))


async def get_time(session: OnvifSession) -> DeviceTime:
    devicemgmt = await session.call(session.camera.create_devicemgmt_service())
    hora = await session.call(devicemgmt.GetSystemDateAndTime())
    utc = getattr(hora, "UTCDateTime", None)
    texto = None
    if utc is not None:
        f, h = utc.Date, utc.Time
        texto = (
            f"{f.Year:04d}-{f.Month:02d}-{f.Day:02d}T{h.Hour:02d}:{h.Minute:02d}:{h.Second:02d}Z"
        )
    return DeviceTime(
        local_time=texto,
        timezone=getattr(getattr(hora, "TimeZone", None), "TZ", None),
        mode=str(getattr(hora, "DateTimeType", "")).lower() or None,
        raw={"daylight_savings": getattr(hora, "DaylightSavings", None)},
    )


async def set_time(session: OnvifSession, *, utc: dict[str, int]) -> DeviceTime:
    """ONVIF pide la hora en UTC y desarmada en campos, a diferencia de ISAPI."""
    devicemgmt = await session.call(session.camera.create_devicemgmt_service())
    await session.call(
        devicemgmt.SetSystemDateAndTime(
            {
                "DateTimeType": "Manual",
                "DaylightSavings": False,
                "UTCDateTime": {
                    "Date": {"Year": utc["year"], "Month": utc["month"], "Day": utc["day"]},
                    "Time": {
                        "Hour": utc["hour"],
                        "Minute": utc["minute"],
                        "Second": utc["second"],
                    },
                },
            }
        )
    )
    return await get_time(session)


async def get_image(session: OnvifSession) -> ImageSettings:
    imaging = await session.call(session.camera.create_imaging_service())
    token = await _video_source(session)
    ajustes = await session.call(imaging.GetImagingSettings({"VideoSourceToken": token}))
    opciones = await session.call(imaging.GetOptions({"VideoSourceToken": token}))

    def rango(nombre: str) -> tuple[float, float]:
        opcion = getattr(opciones, nombre, None)
        if opcion is None:
            return (0.0, 100.0)
        return (float(opcion.Min), float(opcion.Max))

    return ImageSettings(
        brightness=_a_cien(getattr(ajustes, "Brightness", None), *rango("Brightness")),
        contrast=_a_cien(getattr(ajustes, "Contrast", None), *rango("Contrast")),
        saturation=_a_cien(getattr(ajustes, "ColorSaturation", None), *rango("ColorSaturation")),
        sharpness=_a_cien(getattr(ajustes, "Sharpness", None), *rango("Sharpness")),
        raw={"video_source": token},
    )


async def get_osd(session: OnvifSession) -> OsdSettings:
    """`GetOSDs` pide el token de la *configuración* de video, no el del origen físico:
    son dos campos distintos del mismo perfil (`VideoSourceConfiguration.token` contra
    `.SourceToken`). Verificado contra hardware real: pasar el segundo donde va el primero
    responde `The requested configuration does not exist`, no un error de credenciales."""
    media = await session.call(session.camera.create_media_service())
    if not hasattr(media, "GetOSDs"):
        raise NotSupported("El servicio Media de esta cámara no expone OSD")
    perfiles = await session.call(media.GetProfiles())
    if not perfiles:
        raise NotSupported("La cámara no declara perfiles de video")
    token = perfiles[0].VideoSourceConfiguration.token
    osds = await session.call(media.GetOSDs({"ConfigurationToken": token}))
    lineas = []
    muestra_fecha = None
    for osd in osds or []:
        texto = getattr(getattr(osd, "TextString", None), "PlainText", None)
        if texto:
            lineas.append(texto)
        tipo = getattr(getattr(osd, "TextString", None), "Type", None)
        if tipo == "DateAndTime":
            muestra_fecha = True
    return OsdSettings(show_date=muestra_fecha, lines=lineas, raw={"cantidad": len(osds or [])})


async def get_motion(session: OnvifSession) -> MotionDetection:
    """ONVIF no tiene "detección de movimiento": se infiere de los eventos que publica."""
    events = await session.call(session.camera.create_events_service())
    propiedades = await session.call(events.GetEventProperties())
    topicos = str(getattr(propiedades, "TopicSet", ""))
    if "Motion" not in topicos and "MotionAlarm" not in topicos:
        raise NotSupported("La cámara no publica eventos de movimiento por ONVIF")
    # Se puede saber que existe, pero no leer ni cambiar su sensibilidad.
    return MotionDetection(enabled=None, sensitivity=None, raw={"fuente": "GetEventProperties"})


async def reboot(session: OnvifSession) -> dict[str, Any]:
    devicemgmt = await session.call(session.camera.create_devicemgmt_service())
    mensaje = await session.call(devicemgmt.SystemReboot())
    return {"message": str(mensaje)}


async def _video_source(session: OnvifSession) -> str:
    media = await session.call(session.camera.create_media_service())
    perfiles = await session.call(media.GetProfiles())
    if not perfiles:
        raise NotSupported("La cámara no declara perfiles de video")
    return perfiles[0].VideoSourceConfiguration.SourceToken
