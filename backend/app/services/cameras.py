import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Camera, VideoProfile
from app.domain.enums import CameraStatus, Protocol, StreamType
from app.drivers.errors import AuthenticationFailed
from app.drivers.isapi import device as isapi_device
from app.drivers.models import DeviceInfo, Snapshot, StreamProfile
from app.drivers.onvif import device as onvif_device
from app.drivers.onvif.session import onvif_session
from app.drivers.rtsp import probe as rtsp_probe
from app.drivers.rtsp.mediamtx import LiveUrls, MediaMtx
from app.services import targets
from app.services.capabilities import record_outcome
from app.services.operations import Outcome, run_operation


class CameraNotFound(LookupError):
    pass


async def get_camera(session: AsyncSession, camera_id: uuid.UUID) -> Camera:
    camera = await session.get(Camera, camera_id)
    if camera is None:
        raise CameraNotFound(str(camera_id))
    return camera


# --- llamadas por protocolo (sin efectos en la base) ---------------------------------------


async def _isapi_info(camera: Camera) -> DeviceInfo:
    async with targets.isapi_client(camera) as client:
        return await isapi_device.get_device_info(client)


async def _onvif_info(camera: Camera) -> DeviceInfo:
    async with onvif_session(targets.onvif_target(camera)) as session:
        return await onvif_device.get_device_info(session)


async def _rtsp_describe(camera: Camera, path: str) -> rtsp_probe.RtspDescription:
    return await rtsp_probe.describe(targets.rtsp_target(camera), path)


async def _isapi_profiles(camera: Camera) -> list[StreamProfile]:
    async with targets.isapi_client(camera) as client:
        return await isapi_device.get_stream_profiles(client)


async def _onvif_profiles(camera: Camera) -> list[StreamProfile]:
    async with onvif_session(targets.onvif_target(camera)) as session:
        return await onvif_device.get_stream_profiles(session)


def default_rtsp_path(camera: Camera) -> str:
    return f"/Streaming/Channels/{camera.channel}01"


# --- casos de uso --------------------------------------------------------------------------


@dataclass
class ConnectionReport:
    isapi: dict[str, Any]
    onvif: dict[str, Any]
    rtsp: dict[str, Any]
    status: CameraStatus


def _status_from(outcomes: list[Outcome[Any]]) -> CameraStatus:
    if all(o.ok for o in outcomes):
        return CameraStatus.ONLINE
    if any(o.ok for o in outcomes):
        return CameraStatus.DEGRADED
    if any(isinstance(o.error, AuthenticationFailed) for o in outcomes):
        return CameraStatus.AUTH_ERROR
    return CameraStatus.OFFLINE


def _apply_device_info(camera: Camera, info: DeviceInfo) -> None:
    camera.vendor = info.vendor or camera.vendor
    camera.model = info.model or camera.model
    camera.serial = info.serial or camera.serial
    camera.firmware = info.firmware or camera.firmware
    camera.mac = info.mac or camera.mac


async def test_connection(session: AsyncSession, camera: Camera) -> ConnectionReport:
    """Prueba los 3 protocolos en paralelo y deja evidencia en la matriz y en el log."""
    rtsp_path = default_rtsp_path(camera)
    common = {"session": session, "camera_id": camera.id}
    isapi, onvif, rtsp = await asyncio.gather(
        run_operation(
            **common,
            capability="device.info",
            protocol=Protocol.ISAPI,
            operation="GET /ISAPI/System/deviceInfo",
            call=_isapi_info(camera),
        ),
        run_operation(
            **common,
            capability="device.info",
            protocol=Protocol.ONVIF,
            operation="GetDeviceInformation",
            call=_onvif_info(camera),
        ),
        run_operation(
            **common,
            capability="media.live",
            protocol=Protocol.RTSP,
            operation=f"DESCRIBE {rtsp_path}",
            call=_rtsp_describe(camera, rtsp_path),
        ),
    )

    # ISAPI es la fuente más rica de identidad; ONVIF la complementa.
    for outcome in (onvif, isapi):
        if outcome.ok and outcome.value is not None:
            _apply_device_info(camera, outcome.value)

    await record_outcome(session, camera.id, "device.info", Protocol.ISAPI, isapi)
    await record_outcome(session, camera.id, "device.info", Protocol.ONVIF, onvif)
    rtsp_evidence = {"path": rtsp_path}
    if rtsp.ok and rtsp.value is not None:
        rtsp_evidence |= {"media": rtsp.value.media, "server": rtsp.value.server}
    await record_outcome(session, camera.id, "media.live", Protocol.RTSP, rtsp, rtsp_evidence)

    camera.status = _status_from([isapi, onvif, rtsp])
    if camera.status in (CameraStatus.ONLINE, CameraStatus.DEGRADED):
        camera.last_seen_at = datetime.now(UTC)
    await session.commit()

    def summary(outcome: Outcome[Any], extra: dict[str, Any]) -> dict[str, Any]:
        return outcome.as_dict() | (extra if outcome.ok else {})

    return ConnectionReport(
        isapi=summary(isapi, {"model": camera.model, "firmware": camera.firmware}),
        onvif=summary(onvif, {"vendor": onvif.value.vendor if onvif.value else None}),
        rtsp=summary(rtsp, rtsp_evidence),
        status=CameraStatus(camera.status),
    )


async def refresh_profiles(session: AsyncSession, camera: Camera) -> list[VideoProfile]:
    common = {"session": session, "camera_id": camera.id, "capability": "media.profiles"}
    isapi, onvif = await asyncio.gather(
        run_operation(
            **common,
            protocol=Protocol.ISAPI,
            operation="GET /ISAPI/Streaming/channels",
            call=_isapi_profiles(camera),
        ),
        run_operation(
            **common, protocol=Protocol.ONVIF, operation="GetProfiles", call=_onvif_profiles(camera)
        ),
    )
    for protocol, outcome in ((Protocol.ISAPI, isapi), (Protocol.ONVIF, onvif)):
        count = {"profiles": len(outcome.value)} if outcome.ok and outcome.value else {}
        await record_outcome(session, camera.id, "media.profiles", protocol, outcome, count)
        if not outcome.ok:
            continue
        await session.execute(
            delete(VideoProfile).where(
                VideoProfile.camera_id == camera.id, VideoProfile.protocol == protocol
            )
        )
        for profile in outcome.value or []:
            session.add(
                VideoProfile(
                    camera_id=camera.id,
                    protocol=protocol,
                    token=profile.token,
                    name=profile.name,
                    stream_type=profile.stream_type,
                    codec=profile.codec,
                    width=profile.width,
                    height=profile.height,
                    fps=profile.fps,
                    bitrate_kbps=profile.bitrate_kbps,
                    rtsp_path=profile.rtsp_path,
                )
            )
    await session.commit()
    return await list_profiles(session, camera.id)


async def list_profiles(session: AsyncSession, camera_id: uuid.UUID) -> list[VideoProfile]:
    result = await session.scalars(
        select(VideoProfile)
        .where(VideoProfile.camera_id == camera_id)
        .order_by(VideoProfile.protocol, VideoProfile.token)
    )
    return list(result)


async def snapshot(session: AsyncSession, camera: Camera) -> Outcome[Snapshot]:
    async def fetch() -> Snapshot:
        async with targets.isapi_client(camera) as client:
            return await isapi_device.get_snapshot(client, camera.channel)

    outcome = await run_operation(
        session,
        camera_id=camera.id,
        capability="media.snapshot",
        protocol=Protocol.ISAPI,
        operation=f"GET /ISAPI/Streaming/channels/{camera.channel}01/picture",
        call=fetch(),
    )
    await record_outcome(session, camera.id, "media.snapshot", Protocol.ISAPI, outcome)
    await session.commit()
    return outcome


def mediamtx_path(camera: Camera, stream_type: StreamType) -> str:
    return f"cam-{camera.id.hex[:12]}-{stream_type}"


async def set_recording(
    session: AsyncSession,
    camera: Camera,
    enabled: bool,
    stream_type: StreamType = StreamType.MAIN,
) -> LiveUrls:
    """Enciende o apaga la grabación continua de esta cámara en MediaMTX."""
    return await publish_live(session, camera, stream_type, record=enabled)


async def recording_state(camera: Camera, stream_type: StreamType = StreamType.MAIN) -> bool:
    config = await MediaMtx(get_settings()).path_config(mediamtx_path(camera, stream_type))
    return bool(config and config.get("record"))


async def list_recordings(
    camera: Camera, stream_type: StreamType = StreamType.MAIN
) -> list[dict[str, Any]]:
    return await MediaMtx(get_settings()).recordings(mediamtx_path(camera, stream_type))


async def publish_live(
    session: AsyncSession,
    camera: Camera,
    stream_type: StreamType = StreamType.MAIN,
    record: bool = False,
) -> LiveUrls:
    stream_digit = 2 if stream_type == StreamType.SUB else 1
    rtsp_path = f"/Streaming/Channels/{camera.channel}0{stream_digit}"
    path = mediamtx_path(camera, stream_type)
    source = rtsp_probe.credential_url(targets.rtsp_target(camera), rtsp_path)
    outcome = await run_operation(
        session,
        camera_id=camera.id,
        capability="media.live",
        protocol=Protocol.RTSP,
        operation=f"MediaMTX publish {rtsp_path}{' + grabación' if record else ''}",
        call=MediaMtx(get_settings()).publish(path, source, record=record),
    )
    await session.commit()
    if not outcome.ok or outcome.value is None:
        assert outcome.error is not None
        raise outcome.error
    return outcome.value
