from urllib.parse import urlsplit

from app.domain.enums import StreamType
from app.drivers.models import DeviceInfo, StreamProfile
from app.drivers.onvif.session import OnvifSession


async def get_device_info(session: OnvifSession) -> DeviceInfo:
    devicemgmt = await session.call(session.camera.create_devicemgmt_service())
    info = await session.call(devicemgmt.GetDeviceInformation())
    return DeviceInfo(
        vendor=info.Manufacturer,
        model=info.Model,
        serial=info.SerialNumber,
        firmware=info.FirmwareVersion,
        name=None,
        raw={
            "Manufacturer": info.Manufacturer,
            "Model": info.Model,
            "FirmwareVersion": info.FirmwareVersion,
            "SerialNumber": info.SerialNumber,
            "HardwareId": info.HardwareId,
        },
    )


async def get_services(session: OnvifSession) -> list[dict[str, str]]:
    devicemgmt = await session.call(session.camera.create_devicemgmt_service())
    services = await session.call(devicemgmt.GetServices({"IncludeCapability": False}))
    return [
        {"namespace": s.Namespace, "version": f"{s.Version.Major}.{s.Version.Minor}"}
        for s in services or []
    ]


async def get_stream_profiles(session: OnvifSession) -> list[StreamProfile]:
    media = await session.call(session.camera.create_media_service())
    profiles = await session.call(media.GetProfiles())
    result: list[StreamProfile] = []
    for index, profile in enumerate(profiles or []):
        encoder = getattr(profile, "VideoEncoderConfiguration", None)
        resolution = getattr(encoder, "Resolution", None)
        rate = getattr(encoder, "RateControl", None)
        uri = await session.call(
            media.GetStreamUri(
                {
                    "StreamSetup": {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}},
                    "ProfileToken": profile.token,
                }
            )
        )
        parts = urlsplit(uri.Uri)
        result.append(
            StreamProfile(
                token=profile.token,
                name=profile.Name,
                stream_type=StreamType.MAIN if index == 0 else StreamType.SUB,
                channel=1,
                codec=getattr(encoder, "Encoding", None),
                width=getattr(resolution, "Width", None),
                height=getattr(resolution, "Height", None),
                fps=getattr(rate, "FrameRateLimit", None),
                bitrate_kbps=getattr(rate, "BitrateLimit", None),
                rtsp_path=parts.path + (f"?{parts.query}" if parts.query else ""),
            )
        )
    return result
