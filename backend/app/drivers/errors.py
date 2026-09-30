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


class RejectedByCamera(DriverError):
    """La cámara entendió el pedido y lo rechazó por una razón propia del dominio.

    Hikvision usa 403 para casi todo lo que no le gusta, no solo para credenciales (eso es 401):
    plazas de parking que se superponen (`parkingAreaOverlap`), parámetros fuera de rango,
    estados incompatibles. Confundirlo con un problema de autenticación manda a revisar la
    contraseña cuando el problema es el contenido del pedido.
    """

    code = "rejected"


class InvalidResponse(DriverError):
    code = "invalid_response"


class VerificationFailed(DriverError):
    """La cámara respondió OK pero al releer el recurso el cambio no estaba."""

    code = "verification_failed"
