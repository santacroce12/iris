"""Driver de plazas de estacionamiento, con la respuesta real de la iDS-2CD7A46G0/P-IZHSY.

Los payloads reproducen las rarezas del equipo tal como llegan: `absoulteParkingNum` con el error
de tipeo del fabricante, y el estado en vivo en XML bajo un elemento raíz llamado
`ParkingStatusCap` aunque no devuelva capacidades.
"""

import pytest

from app.domain.rules import RuleKind, RuleUpdate
from app.drivers.errors import NotSupported
from app.drivers.isapi.rules import parking


def _plaza(numero: str, x: float, y: float) -> dict:
    """Una plaza cuadrada de 0,05 de lado a partir de la esquina dada."""
    return {
        "PackingSpaceInfo": {
            "absoulteParkingNum": numero,
            "Region": [
                {"Point": {"positionX": x, "positionY": y}},
                {"Point": {"positionX": x + 0.05, "positionY": y}},
                {"Point": {"positionX": x + 0.05, "positionY": y + 0.1}},
                {"Point": {"positionX": x, "positionY": y + 0.1}},
            ],
        }
    }


@pytest.fixture
def config() -> dict:
    return {
        "PackingSpaceRecognition": {
            "channelID": 1,
            "enable": True,
            "PackingSpaceInfoList": [_plaza("001", 0.311, 0.809), _plaza("002", 0.373, 0.806)],
        }
    }


ESTADO_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<ParkingStatusCap version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<ParkingNum>2</ParkingNum>
<ParkingStatusList>
<ParkingStatus><parkingNo>001</parkingNo><carStatus>true</carStatus>
<parkingNumber>0</parkingNumber><parkingTime>360</parkingTime></ParkingStatus>
<ParkingStatus><parkingNo>002</parkingNo><carStatus>false</carStatus>
<parkingNumber>0</parkingNumber><parkingTime>0</parkingTime></ParkingStatus>
</ParkingStatusList>
</ParkingStatusCap>"""


def test_cada_plaza_es_una_regla_con_cuatro_puntos(config):
    reglas = parking.parse_rules(config)
    assert [r.external_id for r in reglas] == ["001", "002"]
    assert all(r.kind is RuleKind.PARKING_SPACE for r in reglas)
    assert all(len(r.points) == 4 for r in reglas)
    assert reglas[0].points[0] == pytest.approx((0.311, 0.809))
    # Con cuatro puntos distintos, la plaza cuenta como configurada.
    assert all(r.configured for r in reglas)


def test_el_interruptor_es_global_no_por_plaza(config):
    assert all(r.enabled for r in parking.parse_rules(config))
    config["PackingSpaceRecognition"]["enable"] = False
    assert not any(r.enabled for r in parking.parse_rules(config))


def test_el_estado_en_vivo_se_lee_del_xml():
    estado = parking.parse_status(ESTADO_XML)
    assert estado["001"] == {"ocupada": True, "segundos_estacionado": 360}
    assert estado["002"]["ocupada"] is False


def test_la_ocupacion_viaja_con_cada_plaza(config):
    reglas = parking.parse_rules(config, parking.parse_status(ESTADO_XML))
    assert reglas[0].extra["ocupada"] is True
    assert reglas[0].extra["segundos_estacionado"] == 360
    assert reglas[1].extra["ocupada"] is False


def test_mover_una_plaza_no_toca_las_demas(config):
    nuevos = [(0.1, 0.2), (0.2, 0.2), (0.2, 0.3), (0.1, 0.3)]
    resultado = parking.apply_update(config, "001", RuleUpdate(points=nuevos))

    reglas = parking.parse_rules(resultado)
    assert reglas[0].points == [pytest.approx(p) for p in nuevos]
    # La segunda quedó igual que en el original.
    assert reglas[1].points == parking.parse_rules(config)[1].points
    # Y el original no se modificó.
    assert parking.parse_rules(config)[0].points[0] == pytest.approx((0.311, 0.809))


def test_una_plaza_exige_exactamente_cuatro_puntos(config):
    with pytest.raises(NotSupported, match="exactamente 4 puntos"):
        parking.apply_update(config, "001", RuleUpdate(points=[(0.1, 0.2), (0.2, 0.3)]))


def test_activar_escribe_en_la_raiz_no_en_la_plaza(config):
    resultado = parking.apply_update(config, "001", RuleUpdate(enabled=False))
    assert resultado["PackingSpaceRecognition"]["enable"] is False
    # La geometría no se tocó.
    assert parking.parse_rules(resultado)[0].points == parking.parse_rules(config)[0].points


def test_una_plaza_que_no_existe_se_rechaza(config):
    with pytest.raises(NotSupported, match="no tiene la plaza"):
        parking.apply_update(config, "099", RuleUpdate(points=[(0.1, 0.2)] * 4))


def test_las_coordenadas_se_recortan_a_la_imagen(config):
    fuera = [(-0.5, 0.2), (1.8, 0.2), (1.8, 0.3), (-0.5, 0.3)]
    reglas = parking.parse_rules(parking.apply_update(config, "001", RuleUpdate(points=fuera)))
    assert reglas[0].points == [(0.0, 0.2), (1.0, 0.2), (1.0, 0.3), (0.0, 0.3)]
