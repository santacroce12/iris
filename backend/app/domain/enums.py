from enum import StrEnum


class Protocol(StrEnum):
    ISAPI = "isapi"
    ONVIF = "onvif"
    RTSP = "rtsp"


class SupportLevel(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"
    ERROR = "error"


class CapabilitySource(StrEnum):
    DECLARED = "declared"  # la cámara dice soportarla (capabilities)
    VERIFIED = "verified"  # se llamó a la función y respondió


class CameraStatus(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    DEGRADED = "degraded"  # responde por algún protocolo, no por todos
    OFFLINE = "offline"
    AUTH_ERROR = "auth_error"


class NetworkMode(StrEnum):
    LAN = "lan"
    VPN = "vpn"


class StreamType(StrEnum):
    MAIN = "main"
    SUB = "sub"
    OTHER = "other"
