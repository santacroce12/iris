from app.core.config import get_settings
from app.core.security import decrypt
from app.db.models import Camera
from app.domain.enums import NetworkMode
from app.drivers.isapi.client import IsapiClient, IsapiTarget
from app.drivers.onvif.session import OnvifTarget
from app.drivers.rtsp.probe import RtspTarget


def _timeout(camera: Camera) -> float:
    base = get_settings().camera_timeout_s
    return base * 2 if camera.network_mode == NetworkMode.VPN else base


def isapi_target(camera: Camera) -> IsapiTarget:
    return IsapiTarget(
        host=camera.host,
        port=camera.http_port,
        username=camera.username,
        password=decrypt(camera.secret_enc),
        use_https=camera.use_https,
        verify_tls=camera.verify_tls,
        timeout_s=_timeout(camera),
    )


def isapi_client(camera: Camera) -> IsapiClient:
    return IsapiClient(isapi_target(camera))


def onvif_target(camera: Camera) -> OnvifTarget:
    if camera.onvif_username and camera.onvif_secret_enc:
        username, password = camera.onvif_username, decrypt(camera.onvif_secret_enc)
    else:
        username, password = camera.username, decrypt(camera.secret_enc)
    return OnvifTarget(
        host=camera.host,
        port=camera.onvif_port,
        username=username,
        password=password,
        timeout_s=_timeout(camera),
        nat_override=camera.network_mode == NetworkMode.VPN,
    )


def rtsp_target(camera: Camera) -> RtspTarget:
    return RtspTarget(
        host=camera.host,
        port=camera.rtsp_port,
        username=camera.username,
        password=decrypt(camera.secret_enc),
        timeout_s=_timeout(camera),
    )
