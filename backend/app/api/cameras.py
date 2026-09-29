import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    CameraCreate,
    CameraOut,
    CameraUpdate,
    CapabilityCheckOut,
    ConnectionReportOut,
    LiveOut,
    OperationLogOut,
    ProtocolCheck,
    RecordingOut,
    VideoProfileOut,
)
from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import encrypt
from app.db.models import Camera, CapabilityCheck, OperationLog
from app.domain.enums import CameraStatus, StreamType
from app.drivers.rtsp.mediamtx import MediaMtx
from app.services import cameras as service

router = APIRouter(prefix="/api/cameras", tags=["cámaras"])

# Campos que cambian cómo se llega a la cámara (a diferencia de, por ejemplo, el nombre).
CONNECTION_FIELDS = {
    "host",
    "http_port",
    "use_https",
    "verify_tls",
    "rtsp_port",
    "onvif_port",
    "channel",
    "username",
    "network_mode",
}
Session = Annotated[AsyncSession, Depends(get_session)]


async def _camera(camera_id: uuid.UUID, session: Session) -> Camera:
    return await service.get_camera(session, camera_id)


CameraDep = Annotated[Camera, Depends(_camera)]


@router.get("", response_model=list[CameraOut])
async def list_cameras(session: Session) -> list[Camera]:
    return list(await session.scalars(select(Camera).order_by(Camera.name)))


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(payload: CameraCreate, session: Session) -> Camera:
    data = payload.model_dump(exclude={"password", "onvif_password"})
    camera = Camera(**data, secret_enc=encrypt(payload.password))
    if payload.onvif_password:
        camera.onvif_secret_enc = encrypt(payload.onvif_password)
    session.add(camera)
    await session.commit()
    return camera


@router.get("/{camera_id}", response_model=CameraOut)
async def read_camera(camera: CameraDep) -> Camera:
    return camera


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(payload: CameraUpdate, camera: CameraDep, session: Session) -> Camera:
    data = payload.model_dump(exclude_unset=True)
    connection_changed = False

    # Contraseñas vacías o ausentes = conservar las guardadas (el navegador nunca las conoce).
    if password := data.pop("password", None):
        camera.secret_enc = encrypt(password)
        connection_changed = True
    if onvif_password := data.pop("onvif_password", None):
        camera.onvif_secret_enc = encrypt(onvif_password)
        connection_changed = True
    if "onvif_username" in data:
        onvif_username = (data.pop("onvif_username") or "").strip() or None
        if onvif_username != camera.onvif_username:
            connection_changed = True
        camera.onvif_username = onvif_username
        if onvif_username is None:
            camera.onvif_secret_enc = None  # sin usuario ONVIF propio se usa el principal

    for key, value in data.items():
        if value is None:
            continue  # el resto de los campos son obligatorios: null no significa "borrar"
        if key in CONNECTION_FIELDS and getattr(camera, key) != value:
            connection_changed = True
        setattr(camera, key, value)

    if connection_changed:
        # Lo verificado ya no describe a esta configuración: hay que volver a probar.
        camera.status = CameraStatus.UNKNOWN
        mediamtx = MediaMtx(get_settings())
        for stream_type in StreamType:
            await mediamtx.remove(service.mediamtx_path(camera, stream_type))
    await session.commit()
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera: CameraDep, session: Session) -> None:
    mediamtx = MediaMtx(get_settings())
    for stream_type in StreamType:
        await mediamtx.remove(service.mediamtx_path(camera, stream_type))
    await session.delete(camera)
    await session.commit()


@router.post("/{camera_id}/connection-test", response_model=ConnectionReportOut)
async def connection_test(camera: CameraDep, session: Session) -> ConnectionReportOut:
    report = await service.test_connection(session, camera)

    def check(data: dict[str, Any]) -> ProtocolCheck:
        base = {k: data[k] for k in ("ok", "latency_ms", "error_code", "message")}
        details = {k: v for k, v in data.items() if k not in base}
        return ProtocolCheck(**base, details=details)

    return ConnectionReportOut(
        status=report.status,
        isapi=check(report.isapi),
        onvif=check(report.onvif),
        rtsp=check(report.rtsp),
    )


@router.get("/{camera_id}/profiles", response_model=list[VideoProfileOut])
async def get_profiles(camera: CameraDep, session: Session):
    return await service.list_profiles(session, camera.id)


@router.post("/{camera_id}/profiles/refresh", response_model=list[VideoProfileOut])
async def refresh_profiles(camera: CameraDep, session: Session):
    return await service.refresh_profiles(session, camera)


@router.get(
    "/{camera_id}/snapshot",
    responses={200: {"content": {"image/jpeg": {}}}},
    response_class=Response,
)
async def get_snapshot(camera: CameraDep, session: Session) -> Response:
    outcome = await service.snapshot(session, camera)
    if not outcome.ok or outcome.value is None:
        assert outcome.error is not None
        raise outcome.error
    return Response(
        outcome.value.content, media_type=outcome.value.mime, headers={"Cache-Control": "no-store"}
    )


@router.post("/{camera_id}/live", response_model=LiveOut)
async def start_live(
    camera: CameraDep, session: Session, stream: StreamType = StreamType.MAIN
) -> LiveOut:
    urls = await service.publish_live(session, camera, stream)
    return LiveOut(path=urls.path, webrtc=urls.webrtc, whep=urls.whep, hls=urls.hls)


@router.post("/{camera_id}/recording", response_model=RecordingOut)
async def set_recording(
    camera: CameraDep,
    session: Session,
    enabled: bool = True,
    stream: StreamType = StreamType.MAIN,
) -> RecordingOut:
    """Graba en disco lo que ve la cámara, para tener evidencia de las pruebas."""
    urls = await service.set_recording(session, camera, enabled, stream)
    return RecordingOut(
        path=urls.path,
        recording=enabled,
        segments=await service.list_recordings(camera, stream),
    )


@router.get("/{camera_id}/recording", response_model=RecordingOut)
async def get_recording(camera: CameraDep, stream: StreamType = StreamType.MAIN) -> RecordingOut:
    return RecordingOut(
        path=service.mediamtx_path(camera, stream),
        recording=await service.recording_state(camera, stream),
        segments=await service.list_recordings(camera, stream),
    )


@router.get("/{camera_id}/capabilities", response_model=list[CapabilityCheckOut])
async def get_capabilities(camera: CameraDep, session: Session):
    result = await session.scalars(
        select(CapabilityCheck)
        .where(CapabilityCheck.camera_id == camera.id)
        .order_by(CapabilityCheck.capability_code, CapabilityCheck.protocol)
    )
    return list(result)


@router.get("/{camera_id}/operations", response_model=list[OperationLogOut])
async def get_operations(camera: CameraDep, session: Session, limit: int = 100):
    result = await session.scalars(
        select(OperationLog)
        .where(OperationLog.camera_id == camera.id)
        .order_by(OperationLog.created_at.desc())
        .limit(min(limit, 500))
    )
    return list(result)
