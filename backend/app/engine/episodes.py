"""Agrupa ráfagas de eventos en episodios.

Una cámara con detección de movimiento manda un "active" por segundo mientras haya
movimiento: 145 mensajes en 2 minutos y medio en la prueba real. Guardar uno por mensaje
llena la base sin agregar información. Un episodio es "esto estuvo ocurriendo desde X hasta Y,
con N avisos".
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from app.domain.events import ParsedAlert

# Si no llega otro aviso en este tiempo, el episodio se considera terminado.
DEFAULT_IDLE_CLOSE = timedelta(seconds=20)
# Tope duro: un evento pegado en "active" no puede quedar abierto para siempre.
DEFAULT_MAX_DURATION = timedelta(minutes=10)


@dataclass
class Episode:
    camera_id: UUID
    key: tuple[str, int | None, str | None]
    alert: ParsedAlert
    started_at: datetime
    last_alert_at: datetime
    hits: int = 1
    event_id: UUID | None = None  # id en la base, una vez persistido
    dirty: bool = True  # tiene cambios sin guardar
    pictures: list[tuple[str, bytes]] = field(default_factory=list)

    def absorb(self, alert: ParsedAlert, now: datetime) -> None:
        self.hits += 1
        self.last_alert_at = now
        self.dirty = True
        # Se conserva el primer payload y se suman las fotos nuevas.
        self.pictures.extend(alert.pictures)
        if alert.target_type and not self.alert.target_type:
            self.alert.target_type = alert.target_type


class EpisodeGrouper:
    """Convierte una ráfaga de avisos en episodios, por cámara y por tipo de evento."""

    def __init__(
        self,
        idle_close: timedelta = DEFAULT_IDLE_CLOSE,
        max_duration: timedelta = DEFAULT_MAX_DURATION,
    ) -> None:
        self.idle_close = idle_close
        self.max_duration = max_duration
        self._open: dict[tuple[UUID, tuple[str, int | None, str | None]], Episode] = {}

    def add(
        self, camera_id: UUID, alert: ParsedAlert, now: datetime
    ) -> tuple[Episode | None, bool, list[Episode]]:
        """Devuelve (episodio, es_nuevo, episodios_cerrados_por_este_aviso).

        El episodio es None cuando el aviso no aporta nada (un "inactive" sin episodio abierto).
        """
        cerrados = self.close_expired(now)
        key = (camera_id, alert.episode_key())

        if not alert.is_active:
            cerrados_ahora = self._close_matching(camera_id, alert, now)
            cerrados.extend(cerrados_ahora)
            # Un "inactive" sin "active" previo es ruido: no se guarda como episodio.
            return (cerrados_ahora[0] if cerrados_ahora else None), False, cerrados

        abierto = self._open.get(key)
        if abierto is None:
            episodio = Episode(camera_id, alert.episode_key(), alert, now, now)
            episodio.pictures.extend(alert.pictures)
            self._open[key] = episodio
            return episodio, True, cerrados

        abierto.absorb(alert, now)
        return abierto, False, cerrados

    def _close_matching(self, camera_id: UUID, alert: ParsedAlert, now: datetime) -> list[Episode]:
        """Cierra lo que termina este "inactive".

        La PTZ real manda el "active" con el número de regla y el "inactive" sin él. Si el
        "inactive" no trae regla, cierra todos los episodios abiertos de ese tipo y canal.
        """
        tipo, canal, regla = alert.episode_key()
        cerrados = []
        for key, episodio in list(self._open.items()):
            cam, (e_tipo, e_canal, e_regla) = key
            if cam != camera_id or e_tipo != tipo or e_canal != canal:
                continue
            if regla is not None and e_regla != regla:
                continue
            del self._open[key]
            episodio.last_alert_at = now
            episodio.dirty = True
            cerrados.append(episodio)
        return cerrados

    def close_expired(self, now: datetime) -> list[Episode]:
        cerrados = []
        for key, episodio in list(self._open.items()):
            if (
                now - episodio.last_alert_at >= self.idle_close
                or now - episodio.started_at >= self.max_duration
            ):
                del self._open[key]
                cerrados.append(episodio)
        return cerrados

    def close_all(self) -> list[Episode]:
        cerrados = list(self._open.values())
        self._open.clear()
        return cerrados

    @property
    def open_count(self) -> int:
        return len(self._open)
