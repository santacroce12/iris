"""Verificación de escrituras: la cámara puede responder OK y no aplicar nada."""

from app.domain.rules import Rule, RuleKind, RuleUpdate
from app.services.rules import TOLERANCIA, _diferencias


def _regla(**cambios) -> Rule:
    base = dict(
        kind=RuleKind.LINE,
        external_id="1",
        points=[(0.1, 0.5), (0.9, 0.5)],
        enabled=True,
        sensitivity=50,
        direction="any",
        target=["human"],
    )
    return Rule(**{**base, **cambios})


def test_sin_diferencias():
    assert _diferencias(_regla(), RuleUpdate(points=[(0.1, 0.5), (0.9, 0.5)])) == []


def test_redondeo_de_la_camara_no_cuenta_como_diferencia():
    """0..1000 pierde decimales: eso no es que la cámara haya ignorado el pedido."""
    pedido = [(0.1004, 0.5004), (0.9, 0.5)]
    assert _diferencias(_regla(), RuleUpdate(points=pedido)) == []


def test_geometria_ignorada():
    faltan = _diferencias(_regla(), RuleUpdate(points=[(0.2, 0.2), (0.8, 0.8)]))
    assert faltan == ["geometría"]


def test_cantidad_de_puntos_distinta():
    pedido = [(0.1, 0.5), (0.5, 0.5), (0.9, 0.5)]
    assert _diferencias(_regla(), RuleUpdate(points=pedido)) == ["geometría"]


def test_varios_campos_ignorados():
    faltan = _diferencias(
        _regla(), RuleUpdate(sensitivity=80, direction="a-b", enabled=False, target=["vehicle"])
    )
    assert faltan == ["sensibilidad", "dirección", "activación", "objetivo"]


def test_orden_de_objetivos_no_importa():
    regla = _regla(target=["vehicle", "human"])
    assert _diferencias(regla, RuleUpdate(target=["human", "vehicle"])) == []


def test_tolerancia_es_menor_que_un_paso_de_la_ptz():
    """La PTZ guarda en pasos de 1/1000: la tolerancia tiene que cubrirlo sin tapar errores."""
    assert 0.001 <= TOLERANCIA < 0.01


def test_prender_no_toca_el_recurso_de_la_regla():
    assert RuleUpdate(enabled=True).es_solo_activacion
    assert not RuleUpdate(enabled=True, points=[(0.0, 0.0), (1.0, 1.0)]).es_solo_activacion
