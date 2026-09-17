import httpx
import pytest
import respx

from app.domain.enums import StreamType
from app.drivers.errors import AuthenticationFailed, CameraUnreachable, NotSupported
from app.drivers.isapi import device
from app.drivers.isapi.client import IsapiClient, IsapiTarget

TARGET = IsapiTarget(host="cam.test", port=80, username="admin", password="secreto")
DEEPINVIEW = "hikvision/iDS-2CD7A46G0-P-IZHSY/V5.8.61"
VALUE = "hikvision/DS-2CD1023G2-I/V5.8.4"


@respx.mock(base_url="http://cam.test:80")
async def test_device_info_deepinview_real_response(respx_mock, fixture_bytes):
    respx_mock.get("/ISAPI/System/deviceInfo").respond(
        200, content=fixture_bytes(f"{DEEPINVIEW}/deviceInfo.xml"), content_type="application/xml"
    )
    async with IsapiClient(TARGET) as client:
        info = await device.get_device_info(client)

    assert info.model == "iDS-2CD7A46G0/P-IZHSY"
    assert info.firmware == "V5.8.61 build 250901"
    assert info.mac == "08:54:11:74:99:5d"
    assert info.raw["OSCoreVersionInfo"]["minisysVersion"] == "2.6.1"


def test_streaming_channels_real_response(fixture_bytes):
    profiles = device.parse_streaming_channels(fixture_bytes(f"{VALUE}/streamingChannels.xml"))

    assert [p.token for p in profiles] == ["101", "102"]
    main, sub = profiles
    assert (main.stream_type, main.width, main.height, main.fps) == (
        StreamType.MAIN,
        1920,
        1080,
        25,
    )
    assert main.codec == "H.264" and main.bitrate_kbps == 4096
    assert main.rtsp_path == "/Streaming/Channels/101"
    assert (sub.stream_type, sub.width) == (StreamType.SUB, 640)


@respx.mock(base_url="http://cam.test:80")
async def test_not_support_comes_as_403_and_is_not_an_auth_error(respx_mock, fixture_bytes):
    respx_mock.get("/ISAPI/Smart/LineDetection/1").respond(
        403, content=fixture_bytes(f"{VALUE}/smartLineDetection_notSupport.xml")
    )
    async with IsapiClient(TARGET) as client:
        with pytest.raises(NotSupported):
            await client.get("/ISAPI/Smart/LineDetection/1")


@respx.mock(base_url="http://cam.test:80")
async def test_401_is_authentication_failure(respx_mock):
    respx_mock.get("/ISAPI/System/deviceInfo").respond(401, text="Unauthorized")
    async with IsapiClient(TARGET) as client:
        with pytest.raises(AuthenticationFailed):
            await client.get("/ISAPI/System/deviceInfo")


@respx.mock(base_url="http://cam.test:80")
async def test_network_errors_are_unreachable(respx_mock):
    respx_mock.get("/ISAPI/System/deviceInfo").mock(side_effect=httpx.ConnectTimeout("lento"))
    async with IsapiClient(TARGET) as client:
        with pytest.raises(CameraUnreachable):
            await client.get("/ISAPI/System/deviceInfo")


@respx.mock(base_url="http://cam.test:80")
async def test_snapshot_rejects_non_image(respx_mock):
    respx_mock.get("/ISAPI/Streaming/channels/101/picture").respond(
        200, text="<xml/>", content_type="application/xml"
    )
    async with IsapiClient(TARGET) as client:
        with pytest.raises(NotSupported):
            await device.get_snapshot(client)
