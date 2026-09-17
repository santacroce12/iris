from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cameras
from app.api.errors import register_error_handlers
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Plataforma unificada de cámaras IP",
        description="ISAPI + ONVIF + RTSP con foco en analítica. Tesis — Luca Santacroce.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(cameras.router)

    @app.get("/api/health", tags=["sistema"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
