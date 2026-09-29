"""Funciones comunes de la cámara, leídas y escritas por el protocolo que se elija.

El mismo recurso por ISAPI y por ONVIF: eso es lo que permite comparar el propietario contra
el estándar sin escribir dos pantallas distintas.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    DeviceTimeOut,
    FunctionsOut,
    ImageOut,
    ImagePatch,
    MotionOut,
    MotionPatch,
    OsdOut,
    OsdPatch,
    SystemStatusOut,
)
from app.core.db import get_session
from app.db.models import Camera
from app.domain.enums import Protocol
from app.drivers.errors import DriverError, NotSupported
from app.drivers.isapi import system as isapi_system
from app.drivers.onvif import system as onvif_system
from app.drivers.onvif.session import onvif_session
from app.services import cameras as camera_service
from app.services import detection, targets
from app.services.capabilities import record_outcome
from app.services.operations import run_operation

router = APIRouter(prefix="/api/cameras", tags=["funciones"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def _camera(camera_id: uuid.UUID, session: Session) -> Camera:
    return await camera_service.get_camera(session, camera_id)


CameraDep = Annotated[Camera, Depends(_camera)]
ProtocolQuery = Annotated[Protocol, Query(description="isapi u onvif")]


@router.post("/{camera_id}/capabilities/detect", status_code=202)
async def detect_capabilities(camera: CameraDep, session: Session) -> dict[str, str]:
    """Recorre el catálogo entero y deja la matriz de esta cámara al día."""
    await detection.detect(session, camera)
    return {"status": "listo"}


@router.get("/{camera_id}/functions", response_model=FunctionsOut)
async def read_functions(
    camera: CameraDep, session: Session, protocol: ProtocolQuery = Protocol.ISAPI
) -> FunctionsOut:
    resultado = FunctionsOut(protocol=protocol.value)
    if protocol is Protocol.ISAPI:
        async with targets.isapi_client(camera) as client:
            lecturas = {
                "status": isapi_system.get_status(client),
                "time": isapi_system.get_time(client),
                "osd": isapi_system.get_osd(client, camera.channel),
                "image": isapi_system.get_image(client, camera.channel),
                "motion": isapi_system.get_motion(client, camera.channel),
            }
            await _recolectar(session, camera, protocol, lecturas, resultado)
        return resultado

    async with onvif_session(targets.onvif_target(camera)) as onvif:
        lecturas = {
            "time": onvif_system.get_time(onvif),
            "osd": onvif_system.get_osd(onvif),
            "image": onvif_system.get_image(onvif),
            "motion": onvif_system.get_motion(onvif),
        }
        await _recolectar(session, camera, protocol, lecturas, resultado)
    return resultado


_CAPACIDAD = {
    "status": "system.status",
    "time": "system.time",
    "osd": "video.osd",
    "image": "video.image",
    "motion": "events.motion",
}
_SALIDA = {
    "status": SystemStatusOut,
    "time": DeviceTimeOut,
    "osd": OsdOut,
    "image": ImageOut,
    "motion": MotionOut,
}


async def _recolectar(
    session: AsyncSession,
    camera: Camera,
    protocol: Protocol,
    lecturas: dict[str, Any],
    salida: FunctionsOut,
) -> None:
    """Cada lectura deja evidencia en la matriz, sirva o falle."""
    for campo, llamada in lecturas.items():
        outcome = await run_operation(
            session,
            camera_id=camera.id,
            capability=_CAPACIDAD[campo],
            protocol=protocol,
            operation=f"leer {campo} por {protocol.value}",
            call=llamada,
        )
        await record_outcome(session, camera.id, _CAPACIDAD[campo], protocol, outcome)
        if outcome.ok and outcome.value is not None:
            modelo = _SALIDA[campo]
            datos = {k: v for k, v in vars(outcome.value).items() if k != "raw"}
            setattr(salida, campo, modelo(**datos))
        elif outcome.error is not None:
            salida.errors[campo] = outcome.error.message
    await session.commit()


@router.patch("/{camera_id}/functions/osd", response_model=OsdOut)
async def update_osd(camera: CameraDep, payload: OsdPatch, session: Session) -> OsdOut:
    async with targets.isapi_client(camera) as client:
        resultado = await isapi_system.set_osd(
            client,
            camera.channel,
            show_name=payload.show_name,
            show_date=payload.show_date,
            name=payload.name,
        )
    await session.commit()
    return OsdOut(**{k: v for k, v in vars(resultado).items() if k != "raw"})


@router.patch("/{camera_id}/functions/image", response_model=ImageOut)
async def update_image(camera: CameraDep, payload: ImagePatch, session: Session) -> ImageOut:
    async with targets.isapi_client(camera) as client:
        resultado = await isapi_system.set_image(
            client, camera.channel, **payload.model_dump(exclude_unset=True)
        )
    await session.commit()
    return ImageOut(**{k: v for k, v in vars(resultado).items() if k != "raw"})


@router.patch("/{camera_id}/functions/motion", response_model=MotionOut)
async def update_motion(camera: CameraDep, payload: MotionPatch, session: Session) -> MotionOut:
    async with targets.isapi_client(camera) as client:
        resultado = await isapi_system.set_motion(
            client, camera.channel, enabled=payload.enabled, sensitivity=payload.sensitivity
        )
    await session.commit()
    return MotionOut(**{k: v for k, v in vars(resultado).items() if k != "raw"})


@router.post("/{camera_id}/functions/time/sync", response_model=DeviceTimeOut)
async def sync_time(
    camera: CameraDep, session: Session, protocol: ProtocolQuery = Protocol.ISAPI
) -> DeviceTimeOut:
    """Pone la cámara en hora. Por ISAPI va como texto local; por ONVIF, en UTC desarmada."""
    from datetime import UTC, datetime

    ahora = datetime.now(UTC)
    if protocol is Protocol.ISAPI:
        async with targets.isapi_client(camera) as client:
            resultado = await isapi_system.set_time(
                client, local_time=ahora.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            )
    else:
        async with onvif_session(targets.onvif_target(camera)) as onvif:
            resultado = await onvif_system.set_time(
                onvif,
                utc={
                    "year": ahora.year,
                    "month": ahora.month,
                    "day": ahora.day,
                    "hour": ahora.hour,
                    "minute": ahora.minute,
                    "second": ahora.second,
                },
            )
    await session.commit()
    return DeviceTimeOut(**{k: v for k, v in vars(resultado).items() if k != "raw"})


@router.post("/{camera_id}/functions/reboot")
async def reboot_camera(
    camera: CameraDep,
    session: Session,
    confirm: Annotated[bool, Query(description="Tiene que venir en true")] = False,
    protocol: ProtocolQuery = Protocol.ISAPI,
) -> dict[str, Any]:
    """Reinicia la cámara. Corta el video varios minutos, así que exige confirmación."""
    if not confirm:
        raise NotSupported("El reinicio necesita confirmación explícita (confirm=true)")
    try:
        if protocol is Protocol.ISAPI:
            async with targets.isapi_client(camera) as client:
                resultado = await isapi_system.reboot(client)
        else:
            async with onvif_session(targets.onvif_target(camera)) as onvif:
                resultado = await onvif_system.reboot(onvif)
    except DriverError:
        await session.commit()
        raise
    await session.commit()
    return resultado
