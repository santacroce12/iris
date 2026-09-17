class DriverError(Exception):
    """Error normalizado de cualquier protocolo. `code` es estable y se guarda en los logs."""

    code = "driver_error"

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.http_status = http_status


class CameraUnreachable(DriverError):
    code = "unreachable"


class AuthenticationFailed(DriverError):
    code = "auth_failed"


class NotSupported(DriverError):
    code = "not_supported"


class InvalidResponse(DriverError):
    code = "invalid_response"
