"""Motor de capacidades: qué declara la cámara y qué contesta de verdad, por cada protocolo.

Es el corazón de la comparación de la tesis. Para cada función del catálogo:
- **Declarada**: aparece en el documento de capacidades de la cámara (ISAPI) o en la lista de
  servicios (ONVIF). Es lo que el fabricante dice.
- **Verificada**: se llamó a la función y respondió. Es lo único que se puede afirmar.

Las funciones destructivas (reinicio) no se prueban: quedan como declaradas, y la matriz lo
aclara. Decir "soportada" sin haberla llamado sería exactamente lo que este trabajo critica.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera
from app.domain.capabilities import CATALOG
from app.domain.enums import CapabilitySource, Protocol, SupportLevel
from app.drivers.errors import DriverError
from app.drivers.isapi import device as isapi_device
from app.drivers.isapi import system as isapi_system
from app.drivers.isapi.client import IsapiClient
from app.drivers.onvif import device as onvif_device
from app.drivers.onvif import system as onvif_system
from app.drivers.onvif.session import OnvifSession, onvif_session
from app.services import targets
from app.services.capabilities import record_check, record_outcome
from app.services.operations import run_operation

# Marcas en /ISAPI/System/capabilities que indican que la cámara declara la función.
DECLARADAS_ISAPI = {
    "system.status": ("isSupportSystemStatus",),
    "system.time": ("isSupportNTP", "isSupportTimeCfg"),
    "system.reboot": ("isSupportReboot",),
    "video.osd": ("isSupportOSD", "isSupportTextOverlay"),
    "video.image": ("isSupportImageCfg", "isSupportColorCfg"),
    "events.motion": ("isSupportMotionDetection",),
    "analytics.rules": ("isSupportSmart", "SmartCap"),
    "media.snapshot": ("isSupportPictureCapture",),
}

# Servicio ONVIF que tiene que estar para que la función sea posible.
DECLARADAS_ONVIF = {
    "system.status": "device",
    "system.time": "device",
    "system.reboot": "device",
    "video.osd": "media",
    "video.image": "imaging",
    "events.motion": "events",
    "analytics.rules": "analytics",
    "device.info": "device",
    "media.profiles": "media",
    "media.snapshot": "media",
}

# Funciones que no se prueban porque tienen efecto sobre el servicio.
NO_SE_PRUEBAN = {"system.reboot"}


@dataclass
class Sonda:
    code: str
    protocol: Protocol
    operation: str
    call: Callable[[], Awaitable[Any]]


def sondas_isapi(client: IsapiClient, channel: int) -> list[Sonda]:
    """Pública: el corredor de experimentos (Fase 5) reusa las mismas sondas N veces."""
    return [
        Sonda(
            "device.info",
            Protocol.ISAPI,
            "GET /ISAPI/System/deviceInfo",
            lambda: isapi_device.get_device_info(client),
        ),
        Sonda(
            "media.profiles",
            Protocol.ISAPI,
            "GET /ISAPI/Streaming/channels",
            lambda: isapi_device.get_stream_profiles(client),
        ),
        Sonda(
            "media.snapshot",
            Protocol.ISAPI,
            f"GET /ISAPI/Streaming/channels/{channel}01/picture",
            lambda: isapi_device.get_snapshot(client, channel, 1),
        ),
        Sonda(
            "system.status",
            Protocol.ISAPI,
            f"GET {isapi_system.STATUS}",
            lambda: isapi_system.get_status(client),
        ),
        Sonda(
            "system.time",
            Protocol.ISAPI,
            f"GET {isapi_system.TIME}",
            lambda: isapi_system.get_time(client),
        ),
        Sonda(
            "video.osd",
            Protocol.ISAPI,
            "GET /ISAPI/System/Video/inputs/channels/_/overlays",
            lambda: isapi_system.get_osd(client, channel),
        ),
        Sonda(
            "video.image",
            Protocol.ISAPI,
            "GET /ISAPI/Image/channels/_/color",
            lambda: isapi_system.get_image(client, channel),
        ),
        Sonda(
            "events.motion",
            Protocol.ISAPI,
            "GET /ISAPI/System/Video/inputs/channels/_/motionDetection",
            lambda: isapi_system.get_motion(client, channel),
        ),
    ]


def sondas_onvif(session: OnvifSession) -> list[Sonda]:
    """Pública por el mismo motivo que `sondas_isapi`."""
    return [
        Sonda(
            "device.info",
            Protocol.ONVIF,
            "GetDeviceInformation",
            lambda: onvif_device.get_device_info(session),
        ),
        Sonda(
            "media.profiles",
            Protocol.ONVIF,
            "GetProfiles",
            lambda: onvif_device.get_stream_profiles(session),
        ),
        Sonda(
            "system.time",
            Protocol.ONVIF,
            "GetSystemDateAndTime",
            lambda: onvif_system.get_time(session),
        ),
        Sonda("video.osd", Protocol.ONVIF, "GetOSDs", lambda: onvif_system.get_osd(session)),
        Sonda(
            "video.image",
            Protocol.ONVIF,
            "GetImagingSettings",
            lambda: onvif_system.get_image(session),
        ),
        Sonda(
            "events.motion",
            Protocol.ONVIF,
            "GetEventProperties",
            lambda: onvif_system.get_motion(session),
        ),
    ]


def _declara(crudo: str, marca: str) -> bool | None:
    """Qué dice el documento de capacidades sobre una marca.

    Devuelve True si la declara, False si la **niega explícitamente**, y None si ni la menciona.
    Distinguir los tres casos importa: el documento mezcla banderas booleanas
    (`<isSupportSmart>false</isSupportSmart>`) con bloques cuya sola presencia es la declaración
    (`<SmartCap>...</SmartCap>`). Buscar solo si la etiqueta aparece da por soportado justo lo
    que la cámara está negando.
    """
    if f"<{marca}>true<" in crudo:
        return True
    if f"<{marca}>false<" in crudo:
        return False
    if f"<{marca}>" in crudo or f"<{marca} " in crudo:
        return True  # bloque, no bandera: que exista ya es la declaración
    return None


async def _declaradas_isapi(session: AsyncSession, camera: Camera, client: IsapiClient) -> None:
    """Lo que la cámara dice soportar, antes de probar nada."""
    try:
        crudo = (await client.get("/ISAPI/System/capabilities")).content.decode("utf-8", "replace")
    except DriverError:
        return
    for code, marcas in DECLARADAS_ISAPI.items():
        dichos = [_declara(crudo, m) for m in marcas]
        if any(d is True for d in dichos):
            nivel, nota = SupportLevel.SUPPORTED, None
        elif any(d is False for d in dichos):
            # La cámara la niega. No es prueba —se vio un equipo que niega el parking y lo
            # soporta por otro árbol (§7.3.7 de la tesis)— pero es su declaración, y decir
            # lo contrario sería inventarle soporte.
            nivel, nota = SupportLevel.UNSUPPORTED, "La cámara la declara como no soportada"
        elif code in NO_SE_PRUEBAN:
            continue  # no pisar la nota de "no se prueba" con una conclusión que no se tiene
        else:
            # Que una marca no aparezca en el documento de capacidades NO prueba que la
            # función no exista: solo una llamada que responda "notSupport" lo prueba.
            nivel, nota = SupportLevel.UNVERIFIED, "La cámara no lo declara; hay que probarlo"
        await record_check(
            session,
            camera_id=camera.id,
            code=code,
            protocol=Protocol.ISAPI,
            level=nivel,
            source=CapabilitySource.DECLARED,
            evidence={
                "marcas": list(marcas),
                "declarado": dict(zip(marcas, dichos, strict=True)),
                **({"nota": nota} if nota else {}),
            },
        )


async def _declaradas_onvif(session: AsyncSession, camera: Camera, onvif: OnvifSession) -> None:
    servicios = await onvif_device.get_services(onvif)
    nombres = " ".join(s["namespace"] for s in servicios).lower()
    for code, servicio in DECLARADAS_ONVIF.items():
        presente = servicio in nombres
        await record_check(
            session,
            camera_id=camera.id,
            code=code,
            protocol=Protocol.ONVIF,
            level=SupportLevel.SUPPORTED if presente else SupportLevel.UNSUPPORTED,
            source=CapabilitySource.DECLARED,
            evidence={
                "servicio": servicio,
                "servicios": [s["namespace"] for s in servicios],
                # GetServices sí es concluyente: sin el servicio, por ONVIF no hay manera.
                "nota": None if presente else f"La cámara no publica el servicio {servicio}",
            },
        )


async def correr(
    session: AsyncSession,
    camera: Camera,
    sondas: list[Sonda],
    *,
    repeticiones: int = 1,
    experiment_id: uuid.UUID | None = None,
) -> None:
    """Ejecuta cada sonda `repeticiones` veces. Con `experiment_id` cada corrida queda
    marcada en `operation_logs`, que es como el corredor de experimentos (Fase 5) junta
    la tasa de éxito y las latencias sin tocar el resto del motor de capacidades."""
    for sonda in sondas:
        for _ in range(repeticiones):
            outcome = await run_operation(
                session,
                camera_id=camera.id,
                capability=sonda.code,
                protocol=sonda.protocol,
                operation=sonda.operation,
                call=sonda.call(),
                experiment_id=experiment_id,
            )
            await record_outcome(session, camera.id, sonda.code, sonda.protocol, outcome)


async def _marcar_no_probadas(session: AsyncSession, camera: Camera) -> None:
    for code in NO_SE_PRUEBAN:
        definicion = next((c for c in CATALOG if c.code == code), None)
        if definicion is None:
            continue
        for protocolo in definicion.protocols:
            await record_check(
                session,
                camera_id=camera.id,
                code=code,
                protocol=protocolo,
                level=SupportLevel.UNVERIFIED,
                source=CapabilitySource.DECLARED,
                evidence={"motivo": "No se prueba automáticamente: interrumpe el servicio"},
            )


async def detect(session: AsyncSession, camera: Camera) -> None:
    """Llena la matriz de esta cámara: declaradas y verificadas, por los dos protocolos."""
    await _marcar_no_probadas(session, camera)

    async def por_isapi() -> None:
        async with targets.isapi_client(camera) as client:
            await _declaradas_isapi(session, camera, client)
            await correr(session, camera, sondas_isapi(client, camera.channel))

    async def por_onvif() -> None:
        try:
            async with onvif_session(targets.onvif_target(camera)) as onvif:
                await _declaradas_onvif(session, camera, onvif)
                await correr(session, camera, sondas_onvif(onvif))
        except DriverError as exc:
            # Sin ONVIF no se puede afirmar nada: queda "sin verificar", no "no soportada".
            for definicion in CATALOG:
                if Protocol.ONVIF not in definicion.protocols:
                    continue
                await record_check(
                    session,
                    camera_id=camera.id,
                    code=definicion.code,
                    protocol=Protocol.ONVIF,
                    level=SupportLevel.UNVERIFIED,
                    source=CapabilitySource.VERIFIED,
                    evidence={"error": exc.code, "message": str(exc.message)[:200]},
                )

    # En serie y no en paralelo: comparten la misma sesión de base de datos.
    try:
        await por_isapi()
    except DriverError:
        pass
    await por_onvif()
    await session.commit()
