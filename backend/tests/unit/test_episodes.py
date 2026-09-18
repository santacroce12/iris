"""Agrupación en episodios: el caso real fue 145 avisos de movimiento en 2,5 minutos."""

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.events import ParsedAlert
from app.engine.episodes import EpisodeGrouper

CAMARA = uuid.uuid4()
T0 = datetime(2026, 9, 18, 21, 30, tzinfo=UTC)


def alerta(tipo="motion", estado="active", canal=1, regla=None, raw="VMD"):
    return ParsedAlert(
        raw_type=raw, type=tipo, state=estado, channel=canal, occurred_at=T0, rule_ref=regla
    )


def test_una_rafaga_de_movimiento_es_un_solo_episodio():
    grouper = EpisodeGrouper()
    nuevos = 0
    for i in range(145):  # lo que mandó la cámara real
        episodio, es_nuevo, _ = grouper.add(CAMARA, alerta(), T0 + timedelta(seconds=i))
        nuevos += es_nuevo
    assert nuevos == 1
    assert episodio.hits == 145
    assert grouper.open_count == 1


def test_el_inactive_cierra_el_episodio():
    grouper = EpisodeGrouper()
    grouper.add(CAMARA, alerta(), T0)
    episodio, es_nuevo, cerrados = grouper.add(
        CAMARA, alerta(estado="inactive"), T0 + timedelta(seconds=5)
    )
    assert not es_nuevo
    assert cerrados == [episodio] and episodio.hits == 1
    assert grouper.open_count == 0


def test_un_silencio_largo_abre_un_episodio_nuevo():
    grouper = EpisodeGrouper(idle_close=timedelta(seconds=20))
    primero, _, _ = grouper.add(CAMARA, alerta(), T0)
    segundo, es_nuevo, cerrados = grouper.add(CAMARA, alerta(), T0 + timedelta(seconds=30))
    assert es_nuevo and cerrados == [primero]
    assert segundo is not primero


def test_tipos_y_reglas_distintas_no_se_mezclan():
    grouper = EpisodeGrouper()
    grouper.add(CAMARA, alerta(), T0)
    grouper.add(CAMARA, alerta(tipo="line_crossing", regla="1", raw="linedetection"), T0)
    grouper.add(CAMARA, alerta(tipo="line_crossing", regla="2", raw="linedetection"), T0)
    otra_camara, es_nuevo, _ = grouper.add(uuid.uuid4(), alerta(), T0)
    assert es_nuevo and otra_camara.hits == 1
    assert grouper.open_count == 4


def test_un_evento_pegado_en_active_se_corta_por_duracion_maxima():
    grouper = EpisodeGrouper(idle_close=timedelta(minutes=5), max_duration=timedelta(minutes=10))
    primero, _, _ = grouper.add(CAMARA, alerta(), T0)
    for minuto in range(1, 10):
        grouper.add(CAMARA, alerta(), T0 + timedelta(minutes=minuto))
    _, es_nuevo, cerrados = grouper.add(CAMARA, alerta(), T0 + timedelta(minutes=11))
    assert cerrados == [primero] and es_nuevo


def test_un_inactive_suelto_se_guarda_cerrado():
    grouper = EpisodeGrouper()
    episodio, es_nuevo, cerrados = grouper.add(CAMARA, alerta(estado="inactive"), T0)
    assert es_nuevo and cerrados == [episodio]
    assert grouper.open_count == 0
