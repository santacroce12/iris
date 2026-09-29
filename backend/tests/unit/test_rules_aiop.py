"""Traductor de AI Open Platform contra respuestas reales del domo iDS-2CD7146G2-IZS."""

import copy
import json

import pytest

from app.domain.rules import RuleKind, RuleUpdate
from app.drivers.errors import NotSupported
from app.drivers.isapi.rules import aiop

DOMO = "hikvision/iDS-2CD7146G2-IZS/V5.9.24"


@pytest.fixture
def config(fixture_bytes):
    return json.loads(fixture_bytes(f"{DOMO}/aiopRuleConfig.json"))


@pytest.fixture
def etiquetas(fixture_bytes):
    return aiop.parse_labels(json.loads(fixture_bytes(f"{DOMO}/aiopAlgorithmEngines.json")))


def test_etiquetas_del_modelo(etiquetas):
    """El modelo cargado define qué detecta: '5 RaiseHands_or_HoldHead' -> {5: ...}."""
    assert etiquetas[1] == "Human_body"
    assert etiquetas[5] == "RaiseHands_or_HoldHead"


def test_leer_la_regla(config, etiquetas):
    (regla,) = aiop.parse_rules(config, etiquetas)
    assert regla.external_id == "1"
    assert regla.name == "Regla1"
    assert regla.kind is RuleKind.AI_ZONE  # PolygonType 2 = polígono
    assert regla.enabled is True  # Valid = 1
    assert regla.target == ["RaiseHands_or_HoldHead"]
    assert regla.sensitivity == 90
    assert regla.extra["confidence"] == 800
    assert regla.extra["trigger_interval_s"] == 60
    # El domo cuenta desde arriba a la izquierda: se usa tal cual.
    assert regla.points[0] == (0.01, 0.01)
    assert len(regla.points) == 4


def test_actualizar_no_toca_el_original(config, etiquetas):
    antes = copy.deepcopy(config)
    nuevo = aiop.apply_update(config, "1", RuleUpdate(points=[(0.2, 0.3), (0.8, 0.3), (0.8, 0.9)]))
    assert config == antes

    (regla,) = aiop.parse_rules(nuevo, etiquetas)
    assert regla.points == [(0.2, 0.3), (0.8, 0.3), (0.8, 0.9)]


def test_actualizar_conserva_el_resto(config, etiquetas):
    nuevo = aiop.apply_update(config, "1", RuleUpdate(enabled=False, name="Manos arriba"))
    (regla,) = aiop.parse_rules(nuevo, etiquetas)
    assert regla.enabled is False
    assert regla.name == "Manos arriba"
    # Nada más cambió.
    assert regla.sensitivity == 90
    assert regla.extra["confidence"] == 800
    assert regla.points[0] == (0.01, 0.01)


def test_regla_inexistente(config):
    with pytest.raises(NotSupported):
        aiop.apply_update(config, "7", RuleUpdate(enabled=True))


def test_limite_de_reglas(fixture_bytes):
    caps = json.loads(fixture_bytes(f"{DOMO}/aiopRuleCapabilities.json"))
    assert int(caps["AIRuleConfigCap"]["ruleID"]["@max"]) == 16


def test_recurso_de_reglas():
    driver = aiop.AiopRulesDriver(client=None, channel=1)  # type: ignore[arg-type]
    driver.task_id = "545933c16c6bfe2g"
    assert driver.rules_resource() == (
        "/ISAPI/Intelligent/AIOpenPlatform/AIRuleConfig/task/545933c16c6bfe2g"
        "/channels/1?format=json"
    )
