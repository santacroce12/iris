from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.security import redact
from app.drivers.errors import AuthenticationFailed, CameraUnreachable, DriverError, NotSupported
from app.services.cameras import CameraNotFound

_STATUS = {
    CameraUnreachable: 504,
    AuthenticationFailed: 502,  # el fallo es de la cámara, no del usuario de la plataforma
    NotSupported: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(CameraNotFound)
    async def camera_not_found(_: Request, exc: CameraNotFound) -> JSONResponse:
        return JSONResponse(
            {"error_code": "camera_not_found", "message": "Cámara inexistente"}, status_code=404
        )

    @app.exception_handler(DriverError)
    async def driver_error(_: Request, exc: DriverError) -> JSONResponse:
        status = next((s for cls, s in _STATUS.items() if isinstance(exc, cls)), 502)
        return JSONResponse(
            {"error_code": exc.code, "message": redact(exc.message)}, status_code=status
        )
