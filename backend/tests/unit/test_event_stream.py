"""Parser del alertStream, probado con mensajes reales de las cámaras."""

from datetime import UTC, datetime

import pytest

from app.domain.events import is_heartbeat, normalize_type
from app.drivers.isapi.events import MultipartBuffer, parse_part

PTZ = "hikvision/DS-2DF8A836IX-AEL/V5.6.0"
VALUE = "hikvision/DS-2CD1023G2-I/V5.8.4"


def _partes(raw: bytes):
    buffer = MultipartBuffer()
    return list(buffer.feed(raw))


def test_line_crossing_real_de_la_ptz(fixture_bytes):
    partes = _partes(fixture_bytes(f"{PTZ}/alertStream_lineDetection.xml"))
    assert len(partes) == 1
    alerta = parse_part(*partes[0])

    assert (alerta.raw_type, alerta.type) == ("linedetection", "line_crossing")
    assert alerta.state == "active" and alerta.is_active
    assert alerta.channel == 1
    assert alerta.rule_ref == "1"
    # La cámara tiene la hora en +08:00 (21:30:37): se guarda normalizada a UTC.
    assert alerta.occurred_at == datetime(2026, 9, 18, 13, 30, 37, tzinfo=UTC)
    coords = alerta.payload["DetectionRegionList"]["DetectionRegionEntry"]["RegionCoordinatesList"]
    assert coords["RegionCoordinates"][0] == {"positionX": "150", "positionY": "500"}


def test_heartbeat_real_no_es_evento(fixture_bytes):
    alerta = parse_part(*_partes(fixture_bytes(f"{PTZ}/alertStream_heartbeat.xml"))[0])
    assert alerta.raw_type == "videoloss"
    assert is_heartbeat(alerta.raw_type, alerta.state)


def test_dos_mensajes_seguidos_en_un_solo_chunk(fixture_bytes):
    partes = _partes(fixture_bytes(f"{VALUE}/alertStream_videoloss.bin"))
    assert len(partes) == 2
    assert all(parse_part(*p).raw_type == "videoloss" for p in partes)


def test_mensaje_partido_en_varios_chunks(fixture_bytes):
    raw = fixture_bytes(f"{PTZ}/alertStream_lineDetection.xml")
    buffer = MultipartBuffer()
    mitad = len(raw) // 2
    assert list(buffer.feed(raw[:mitad])) == []  # todavía no está completo
    partes = list(buffer.feed(raw[mitad:]))
    assert len(partes) == 1
    assert parse_part(*partes[0]).type == "line_crossing"


def test_parte_de_imagen_se_reconoce_como_foto():
    raw = b"--boundary\r\nContent-Type: image/jpeg\r\nContent-Length: 4\r\n\r\n\xff\xd8\xff\xd9"
    parsed = parse_part(*_partes(raw)[0])
    assert parsed == ("image/jpeg", b"\xff\xd8\xff\xd9")


def test_evento_en_json():
    cuerpo = b'{"eventType":"AIOP_Video","eventState":"active","channelID":1,"ruleID":3}'
    raw = b"--boundary\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n%s" % (
        len(cuerpo),
        cuerpo,
    )
    alerta = parse_part(*_partes(raw)[0])
    assert (alerta.type, alerta.rule_ref, alerta.channel) == ("ai_rule", "3", 1)


def test_tipos_desconocidos_quedan_en_minuscula():
    assert normalize_type("ALGOnuevo") == "algonuevo"


async def test_el_feed_termina_cuando_el_servidor_se_apaga():
    """Sin esto uvicorn se queda esperando que cierre la conexión del navegador."""
    from app.api.events import stream_events
    from app.engine.event_bus import EventBus, bus

    original = bus.cerrando
    bus.cerrando = EventBus().cerrando
    try:
        respuesta = await stream_events()
        generador = respuesta.body_iterator
        assert await anext(generador) == ": conectado\n\n"

        bus.cerrando.set()
        with pytest.raises(StopAsyncIteration):
            await anext(generador)
    finally:
        bus.cerrando = original
