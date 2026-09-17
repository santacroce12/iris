from app.domain.enums import StreamType
from app.drivers.errors import NotSupported
from app.drivers.isapi import xml
from app.drivers.isapi.client import IsapiClient
from app.drivers.models import DeviceInfo, Snapshot, StreamProfile


async def get_device_info(client: IsapiClient) -> DeviceInfo:
    root = (await client.get("/ISAPI/System/deviceInfo")).xml()
    return DeviceInfo(
        vendor="Hikvision",
        model=xml.text(root, "model"),
        serial=xml.text(root, "serialNumber"),
        firmware=_firmware(root),
        mac=xml.text(root, "macAddress"),
        name=xml.text(root, "deviceName"),
        raw=xml.to_dict(root),
    )


def _firmware(root) -> str | None:
    version = xml.text(root, "firmwareVersion")
    build = xml.text(root, "firmwareReleasedDate")
    if version and build:
        return f"{version} {build}"
    return version


def parse_streaming_channels(content: bytes) -> list[StreamProfile]:
    root = xml.parse(content)
    profiles: list[StreamProfile] = []
    for channel in xml.find_all(root, "StreamingChannel"):
        channel_id = xml.text(channel, "id")
        video = xml.find(channel, "Video")
        if not channel_id or video is None or xml.text(video, "enabled") == "false":
            continue
        stream_digit = int(channel_id) % 100
        max_fps = xml.to_int(xml.text(video, "maxFrameRate"))
        bitrate = xml.text(video, "vbrUpperCap") or xml.text(video, "constantBitRate")
        profiles.append(
            StreamProfile(
                token=channel_id,
                name=xml.text(channel, "channelName"),
                stream_type=_stream_type(stream_digit),
                channel=xml.to_int(xml.text(video, "videoInputChannelID"))
                or int(channel_id) // 100,
                codec=xml.text(video, "videoCodecType"),
                width=xml.to_int(xml.text(video, "videoResolutionWidth")),
                height=xml.to_int(xml.text(video, "videoResolutionHeight")),
                # ISAPI expresa los fps multiplicados por 100 (2500 = 25 fps).
                fps=max_fps / 100 if max_fps else None,
                bitrate_kbps=xml.to_int(bitrate),
                rtsp_path=f"/Streaming/Channels/{channel_id}",
            )
        )
    return profiles


def _stream_type(stream_digit: int) -> StreamType:
    return {1: StreamType.MAIN, 2: StreamType.SUB}.get(stream_digit, StreamType.OTHER)


async def get_stream_profiles(client: IsapiClient) -> list[StreamProfile]:
    response = await client.get("/ISAPI/Streaming/channels")
    return parse_streaming_channels(response.content)


async def get_snapshot(client: IsapiClient, channel: int = 1, stream: int = 1) -> Snapshot:
    response = await client.get(f"/ISAPI/Streaming/channels/{channel}0{stream}/picture")
    if not response.content_type.startswith("image/"):
        raise NotSupported(f"El snapshot devolvió {response.content_type}")
    return Snapshot(content=response.content, mime=response.content_type.split(";")[0])
