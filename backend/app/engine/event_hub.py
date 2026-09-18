"""Mantiene abierto el alertStream de cada cámara y persiste los episodios."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import redact
from app.db.models import Camera, Event, EventMedia
from app.domain.enums import Protocol
from app.domain.events import ParsedAlert, is_heartbeat
from app.drivers.errors import DriverError
from app.drivers.isapi.events import read_alert_stream
from app.engine.episodes import Episode, EpisodeGrouper
from app.engine.event_bus import bus
from app.services import targets

log = logging.getLogger(__name__)

RECONNECT_MIN_S = 2
RECONNECT_MAX_S = 60
MAX_PICTURES = 4  # por episodio: alcanza como evidencia y no llena el disco


class CameraListener:
    """Una tarea por cámara: escucha, agrupa y guarda."""

    def __init__(self, camera_id: uuid.UUID) -> None:
        self.camera_id = camera_id
        self.grouper = EpisodeGrouper()
        self.status = "detenido"
        self.last_error: str | None = None
        self.alerts_received = 0
        self.episodes_saved = 0
        self.connected_since: datetime | None = None
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name=f"alertStream-{self.camera_id}")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        async with SessionLocal() as session:
            await self._flush(session, self.grouper.close_all())
            await session.commit()
        self.status = "detenido"
        self.connected_since = None

    async def _run(self) -> None:
        espera = RECONNECT_MIN_S
        while True:
            try:
                await self._listen_once()
                espera = RECONNECT_MIN_S
            except asyncio.CancelledError:
                raise
            except DriverError as exc:
                self.status = "reconectando"
                self.last_error = redact(exc.message)
            except Exception as exc:  # que un error inesperado no mate la tarea
                self.status = "reconectando"
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.exception("alertStream %s", self.camera_id)
            self.connected_since = None
            await asyncio.sleep(espera)
            espera = min(espera * 2, RECONNECT_MAX_S)

    async def _listen_once(self) -> None:
        async with SessionLocal() as session:
            camera = await session.get(Camera, self.camera_id)
            if camera is None:
                raise DriverError("La cámara ya no existe")
            client = targets.isapi_client(camera)
        try:
            async with client:
                self.status = "conectado"
                self.last_error = None
                self.connected_since = datetime.now(UTC)
                async for alerta in read_alert_stream(client):
                    await self._handle(alerta)
        finally:
            if self.status == "conectado":
                self.status = "reconectando"

    async def _handle(self, alerta: ParsedAlert) -> None:
        self.alerts_received += 1
        now = datetime.now(UTC)
        if is_heartbeat(alerta.raw_type, alerta.state):
            # El latido solo confirma que la cámara sigue viva.
            async with SessionLocal() as session:
                camera = await session.get(Camera, self.camera_id)
                if camera is not None:
                    camera.last_seen_at = now
                    await session.commit()
            await self._flush_expired(now)
            return

        episodio, es_nuevo, cerrados = self.grouper.add(self.camera_id, alerta, now)
        async with SessionLocal() as session:
            await self._persist(session, episodio, es_nuevo)
            await self._flush(session, cerrados)
            await session.commit()

    async def _flush_expired(self, now: datetime) -> None:
        cerrados = self.grouper.close_expired(now)
        if not cerrados:
            return
        async with SessionLocal() as session:
            await self._flush(session, cerrados)
            await session.commit()

    async def _flush(self, session: AsyncSession, episodios: list[Episode]) -> None:
        for episodio in episodios:
            await self._persist(session, episodio, episodio.event_id is None, cerrado=True)

    async def _persist(
        self, session: AsyncSession, episodio: Episode, es_nuevo: bool, cerrado: bool = False
    ) -> None:
        if not episodio.dirty and not cerrado:
            return
        if es_nuevo and episodio.event_id is None:
            evento = Event(
                camera_id=episodio.camera_id,
                protocol=Protocol.ISAPI,
                raw_type=episodio.alert.raw_type,
                type=episodio.alert.type,
                state="active",
                channel=episodio.alert.channel,
                occurred_at=episodio.alert.occurred_at,
                rule_ref=episodio.alert.rule_ref,
                target_type=episodio.alert.target_type,
                bbox=episodio.alert.bbox,
                payload=episodio.alert.payload,
                hits=episodio.hits,
            )
            session.add(evento)
            await session.flush()
            episodio.event_id = evento.id
            self.episodes_saved += 1
        else:
            evento = await session.get(Event, episodio.event_id)
            if evento is None:
                return
            evento.hits = episodio.hits
            evento.target_type = episodio.alert.target_type or evento.target_type

        if cerrado:
            evento.ended_at = episodio.last_alert_at
            evento.state = "ended"
        fotos = await self._save_pictures(session, episodio, evento)
        episodio.dirty = False
        bus.publish(_to_payload(evento, fotos))

    async def _save_pictures(self, session: AsyncSession, episodio: Episode, evento: Event) -> int:
        guardadas = await session.scalar(
            select(func.count(EventMedia.id)).where(EventMedia.event_id == evento.id)
        )
        if not episodio.pictures:
            return guardadas or 0
        carpeta = get_settings().media_dir / str(evento.camera_id)
        carpeta.mkdir(parents=True, exist_ok=True)
        for mime, contenido in episodio.pictures:
            if guardadas >= MAX_PICTURES:
                break
            nombre = f"{evento.id}-{guardadas}.jpg"
            (carpeta / nombre).write_bytes(contenido)
            session.add(
                EventMedia(
                    event_id=evento.id,
                    kind="full",
                    path=f"{evento.camera_id}/{nombre}",
                    mime=mime,
                    bytes=len(contenido),
                )
            )
            guardadas += 1
        episodio.pictures.clear()
        return guardadas

    def state(self) -> dict[str, object]:
        return {
            "camera_id": str(self.camera_id),
            "status": self.status,
            "connected_since": self.connected_since.isoformat() if self.connected_since else None,
            "alerts_received": self.alerts_received,
            "episodes_saved": self.episodes_saved,
            "open_episodes": self.grouper.open_count,
            "last_error": self.last_error,
        }


def _to_payload(evento: Event, fotos: int) -> dict[str, object]:
    return {
        "id": str(evento.id),
        "camera_id": str(evento.camera_id),
        "type": evento.type,
        "raw_type": evento.raw_type,
        "state": evento.state,
        "channel": evento.channel,
        "occurred_at": evento.occurred_at.isoformat(),
        "ended_at": evento.ended_at.isoformat() if evento.ended_at else None,
        "hits": evento.hits,
        "rule_ref": evento.rule_ref,
        "target_type": evento.target_type,
        "pictures": fotos,
    }


class EventHub:
    """Arranca y detiene los oyentes de todas las cámaras marcadas."""

    def __init__(self) -> None:
        self.listeners: dict[uuid.UUID, CameraListener] = {}

    def start_camera(self, camera_id: uuid.UUID) -> CameraListener:
        oyente = self.listeners.get(camera_id)
        if oyente is None:
            oyente = CameraListener(camera_id)
            self.listeners[camera_id] = oyente
        oyente.start()
        return oyente

    async def stop_camera(self, camera_id: uuid.UUID) -> None:
        oyente = self.listeners.pop(camera_id, None)
        if oyente is not None:
            await oyente.stop()

    async def start_enabled(self) -> None:
        async with SessionLocal() as session:
            camaras = await session.scalars(select(Camera).where(Camera.listen_events.is_(True)))
            for camara in camaras:
                self.start_camera(camara.id)

    async def stop_all(self) -> None:
        for camera_id in list(self.listeners):
            await self.stop_camera(camera_id)

    def state(self) -> list[dict[str, object]]:
        return [oyente.state() for oyente in self.listeners.values()]


hub = EventHub()
