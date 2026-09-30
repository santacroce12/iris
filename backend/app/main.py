import signal
from contextlib import asynccontextmanager
from types import FrameType

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cameras, events, functions, matrix, rules
from app.api.errors import register_error_handlers
from app.core.config import get_settings
from app.engine.event_bus import bus
from app.engine.event_hub import hub

# Señales que uvicorn ya escucha para apagarse (ver `uvicorn.server.Server.capture_signals`).
_SEÑALES_DE_APAGADO = (signal.SIGINT, signal.SIGTERM)


def _instalar_cierre_temprano_del_bus() -> None:
    """Corta los feeds SSE en cuanto llega la señal de apagado, no cuando uvicorn corre el
    shutdown de la app.

    Se creía resuelto con `bus.close()` en el `lifespan` de abajo, pero volvió a colgarse al
    recargar (`--reload`) con la pantalla de Eventos abierta. La causa, confirmada leyendo
    `uvicorn.server.Server.shutdown`: uvicorn espera a que **todas** las conexiones HTTP terminen
    (`_wait_tasks_to_complete`, sin timeout por defecto) *antes* de mandar el evento de shutdown al
    `lifespan` de la app. Un SSE que solo se corta escuchando ese mismo shutdown nunca lo va a ver:
    espera una señal que uvicorn no manda hasta que el SSE termine — un candado circular.

    La solución es no depender del `lifespan` para esto: uvicorn instala sus propios manejadores
    de SIGINT/SIGTERM antes de arrancar la app (`Server.capture_signals`), así que acá se
    reemplazan por unos que primero liberan el bus y  después llaman al manejador original de
    uvicorn, para no pisarle su propio apagado."""
    originales = {sig: signal.getsignal(sig) for sig in _SEÑALES_DE_APAGADO}

    def _manejador(sig: int, frame: FrameType | None) -> None:
        bus.close()
        anterior = originales[sig]
        if callable(anterior):
            anterior(sig, frame)

    for sig in _SEÑALES_DE_APAGADO:
        signal.signal(sig, _manejador)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _instalar_cierre_temprano_del_bus()
    # Al arrancar se reconectan los oyentes de las cámaras marcadas.
    await hub.start_enabled()
    yield
    bus.close()  # por si el apagado no vino de una señal (p. ej. los tests)
    await hub.stop_all()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app = FastAPI(
        lifespan=lifespan,
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
    app.include_router(events.router)
    app.include_router(rules.router)
    app.include_router(functions.router)
    app.include_router(matrix.router)

    @app.get("/api/health", tags=["sistema"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
