"""Traductor de /ISAPI/Smart/* contra respuestas reales de la PTZ DS-2DF8A836IX-AEL."""

import pytest

from app.domain.rules import RuleKind, RuleUpdate
from app.drivers.isapi.rules import smart

PTZ = "hikvision/DS-2DF8A836IX-AEL/V5.6.0"
LINEA = smart.BY_KIND[RuleKind.LINE]
CAMPO = smart.BY_KIND[RuleKind.FIELD]


def test_eje_vertical_invertido():
    """La PTZ cuenta desde abajo: y=1000 es el borde de arriba de la imagen."""
    assert smart.to_ui(0, 1000) == (0.0, 0.0)
    assert smart.to_ui(1000, 0) == (1.0, 1.0)
    assert smart.to_ui(500, 500) == (0.5, 0.5)


@pytest.mark.parametrize("punto", [(0.0, 0.0), (0.15, 0.5), (1.0, 1.0), (0.349, 0.44)])
def test_ida_y_vuelta_de_coordenadas(punto):
    x, y = smart.to_isapi(punto)
    vuelta = smart.to_ui(x, y)
    assert vuelta == pytest.approx(punto, abs=0.001)


def test_lista_de_reglas(fixture_bytes):
    # Fixture regrabada el 29/09 contra la cámara real, con la línea 1 de la demo activa.
    habilitado, reglas = smart.parse_rules(fixture_bytes(f"{PTZ}/smartLineDetection.xml"), LINEA)
    assert habilitado is True
    assert len(reglas) == 4
    # La lista miente, pero no siempre: la regla 1 (la única activa) muestra su geometría real;
    # las reglas 2 a 4, sin usar, siguen devolviendo (0,1000)-(0,1000). Es un refinamiento del
    # hallazgo original (antes se vio mentir también en la 2 y la 3, cuando ninguna estaba
    # activa a nivel de tipo): lo que la lista sí resuelve bien es la regla que el tipo tiene
    # activa; el resto, no.
    por_id = {r.external_id: r for r in reglas}
    assert por_id["1"].configured
    assert all(not por_id[i].configured for i in ("2", "3", "4"))


def test_regla_individual_dice_la_verdad(fixture_bytes):
    """El mismo recurso que en la lista venía vacío, leído de a uno, trae la geometría."""
    _, reglas = smart.parse_rules(fixture_bytes(f"{PTZ}/smartLineDetectionItem2.xml"), LINEA)
    (regla,) = reglas
    assert regla.external_id == "2"
    assert regla.configured
    assert [(round(x, 3), round(y, 3)) for x, y in regla.points] == [
        (0.349, 0.44),
        (0.619, 0.44),
    ]
    assert regla.target == ["human", "vehicle"]
    assert regla.direction == "any"


def test_region_sin_puntos_no_esta_configurada(fixture_bytes):
    _, reglas = smart.parse_rules(fixture_bytes(f"{PTZ}/smartFieldDetectionRegion1.xml"), CAMPO)
    (regla,) = reglas
    assert regla.points == []
    assert not regla.configured


def test_capacidades(fixture_bytes):
    info = smart.parse_capabilities(
        fixture_bytes(f"{PTZ}/smartLineDetectionCapabilities.xml"), LINEA, enabled=True
    )
    assert info.max_rules == 4
    assert info.min_points == info.max_points == 2
    assert "human" in info.targets
    assert set(info.directions) >= {"any", "a-b", "b-a"}
    # En esta familia se activa el tipo entero, no cada regla.
    assert info.toggle_per_rule is False


def test_escribir_solo_cambia_lo_pedido(fixture_bytes):
    original = fixture_bytes(f"{PTZ}/smartLineDetectionItem1.xml").decode()
    nuevo = smart.build_item_xml(original, LINEA, RuleUpdate(points=[(0.1, 0.9), (0.8, 0.2)]))

    assert "<positionX>100</positionX><positionY>100</positionY>" in nuevo
    assert "<positionX>800</positionX><positionY>800</positionY>" in nuevo
    # Lo que no se pidió queda igual.
    assert "<sensitivityLevel>50</sensitivityLevel>" in nuevo
    assert "<detectionTarget>human,vehicle</detectionTarget>" in nuevo
    assert "<id>1</id>" in nuevo


def test_escribir_sensibilidad_y_objetivo(fixture_bytes):
    original = fixture_bytes(f"{PTZ}/smartLineDetectionItem1.xml").decode()
    nuevo = smart.build_item_xml(
        original, LINEA, RuleUpdate(sensitivity=80, target=["human"], direction="a-b")
    )
    assert "<sensitivityLevel>80</sensitivityLevel>" in nuevo
    assert "<detectionTarget>human</detectionTarget>" in nuevo
    assert "<directionSensitivity>left-right</directionSensitivity>" in nuevo
    # La geometría no se toca si no se pidió.
    assert "<positionX>150</positionX>" in nuevo


def test_activar_toca_solo_el_enabled_global(fixture_bytes):
    original = fixture_bytes(f"{PTZ}/smartLineDetection.xml").decode()
    nuevo = smart.set_kind_enabled(original, True)
    assert nuevo.count("<enabled>true</enabled>") == 1
    # El primero del documento es el del tipo; los de cada regla quedan como estaban.
    assert nuevo.index("<enabled>true</enabled>") < nuevo.index("<LineItemList")


def test_recursos_de_escritura():
    driver = smart.SmartRulesDriver(client=None, channel=1)  # type: ignore[arg-type]
    assert driver.item_resource(LINEA, "2") == "/ISAPI/Smart/LineDetection/1/lineItem/2"
    assert driver.item_resource(CAMPO, "1") == "/ISAPI/Smart/FieldDetection/1/regions/1"
    assert driver.kind_resource(LINEA) == "/ISAPI/Smart/LineDetection/1"
