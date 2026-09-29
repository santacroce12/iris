import asyncio
import json
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import EventOut, ListenerState
from app.core.config import get_settings
from app.core.db import get_session
from app.db.models import Camera, Event, EventMedia
from app.engine.event_bus import bus
from app.engine.event_hub import hub
from app.services.cameras import get_camera

router = APIRouter(prefix="/api", tags=["eventos"])
Session = Annotated[AsyncSession, Depends(get_session)]

HEARTBEAT_S = 20  # sin tráfico, algunos proxys cortan la conexión SSE


@router.get("/events", response_model=list[EventOut])
async def list_events(
    session: Session,
    camera_id: uuid.UUID | None = None,
    type: str | None = None,
    target_type: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[Event]:
    consulta = select(Event).options(selectinload(Event.media))
    if camera_id:
        consulta = consulta.where(Event.camera_id == camera_id)
    if type:
        consulta = consulta.where(Event.type == type)
    if target_type:
        consulta = consulta.where(Event.target_type == target_type)
    if since:
        consulta = consulta.where(Event.occurred_at >= since)
    if until:
        consulta = consulta.where(Event.occurred_at <= until)
    consulta = consulta.order_by(Event.occurred_at.desc()).limit(limit)
    return list(await session.scalars(consulta))


@router.get("/events/stream")
async def stream_events() -> StreamingResponse:
    """Feed en vivo por SSE: el navegador recibe cada episodio nuevo o actualizado."""

    async def generar():
        async with bus.subscribe() as cola:
            yield ": conectado\n\n"
            # El feed también escucha el apagado: si solo esperara eventos, el servidor no
            # podría cerrar (uvicorn se queda esperando que la conexión termine).
            cierre = asyncio.create_task(bus.cerrando.wait())
            try:
                while True:
                    siguiente = asyncio.create_task(cola.get())
                    listos, _ = await asyncio.wait(
                        {siguiente, cierre},
                        timeout=HEARTBEAT_S,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if siguiente in listos:
                        yield f"event: camera-event\ndata: {json.dumps(siguiente.result())}\n\n"
                        continue
                    siguiente.cancel()
                    if cierre in listos:
                        break
                    yield ": latido\n\n"
            finally:
                cierre.cancel()

    return StreamingResponse(
        generar(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/events/{event_id}/media/{media_id}", response_class=Response)
async def get_event_picture(event_id: uuid.UUID, media_id: uuid.UUID, session: Session):
    media = await session.get(EventMedia, media_id)
    if media is None or media.event_id != event_id:
        raise HTTPException(status_code=404, detail="Imagen inexistente")
    archivo = get_settings().media_dir / media.path
    if not archivo.exists():
        raise HTTPException(status_code=410, detail="La imagen ya no está en disco")
    return FileResponse(archivo, media_type=media.mime)


@router.get("/listeners", response_model=list[ListenerState])
async def list_listeners() -> list[dict[str, Any]]:
    return hub.state()


@router.post("/cameras/{camera_id}/listener", response_model=ListenerState)
async def start_listener(camera_id: uuid.UUID, session: Session) -> dict[str, Any]:
    camera = await get_camera(session, camera_id)
    camera.listen_events = True
    await session.commit()
    return hub.start_camera(camera.id).state()


@router.delete("/cameras/{camera_id}/listener", status_code=204)
async def stop_listener(camera_id: uuid.UUID, session: Session) -> None:
    camera = await session.get(Camera, camera_id)
    if camera is not None:
        camera.listen_events = False
        await session.commit()
    await hub.stop_camera(camera_id)
