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
    VideoProfileOut,
)
from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import encrypt
from app.db.models import Camera, CapabilityCheck, OperationLog
from app.domain.enums import StreamType
from app.drivers.rtsp.mediamtx import MediaMtx
from app.services import cameras as service

router = APIRouter(prefix="/api/cameras", tags=["cámaras"])
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
    if password := data.pop("password", None):
        camera.secret_enc = encrypt(password)
    if "onvif_password" in data:
        onvif_password = data.pop("onvif_password")
        camera.onvif_secret_enc = encrypt(onvif_password) if onvif_password else None
    for key, value in data.items():
        setattr(camera, key, value)
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
