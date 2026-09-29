"""Modelo común de reglas de analítica, independiente de la API que las implementa.

Coordenadas: siempre normalizadas 0..1 con origen ARRIBA a la izquierda, como las ve el
usuario sobre la imagen. Cada driver traduce desde y hacia el sistema de su cámara.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RuleKind(StrEnum):
    LINE = "line"  # cruce de línea (2 puntos)
    FIELD = "field"  # intrusión (polígono)
    ENTRANCE = "entrance"  # entrada a zona (polígono)
    EXITING = "exiting"  # salida de zona (polígono)
    AI_ZONE = "ai_zone"  # zona de una regla de IA (AI Open Platform)


class RuleFamily(StrEnum):
    SMART = "smart"  # /ISAPI/Smart/* (XML, 0..1000)
    AIOP = "aiop"  # /ISAPI/Intelligent/AIOpenPlatform/* (JSON, 0..1)
    NONE = "none"


POLYGON_KINDS = {RuleKind.FIELD, RuleKind.ENTRANCE, RuleKind.EXITING, RuleKind.AI_ZONE}

Point = tuple[float, float]


@dataclass
class Rule:
    kind: RuleKind
    external_id: str
    points: list[Point]
    enabled: bool
    name: str | None = None
    sensitivity: int | None = None  # 1..100
    direction: str | None = None  # any | a-b | b-a (solo líneas)
    target: list[str] = field(default_factory=list)  # human, vehicle, others
    # Datos propios de la cámara que no se editan pero hay que conservar.
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        """Una regla sin geometría útil es un casillero vacío de la cámara."""
        minimo = 3 if self.kind in POLYGON_KINDS else 2
        distintos = {(round(x, 3), round(y, 3)) for x, y in self.points}
        return len(distintos) >= minimo


@dataclass
class RuleKindInfo:
    """Lo que la cámara permite para un tipo de regla."""

    kind: RuleKind
    max_rules: int
    enabled: bool  # en la PTZ se activa el tipo entero, no cada regla
    min_points: int
    max_points: int
    targets: list[str] = field(default_factory=list)
    directions: list[str] = field(default_factory=list)
    toggle_per_rule: bool = False


@dataclass
class RuleSet:
    family: RuleFamily
    kinds: list[RuleKindInfo]
    rules: list[Rule]
    note: str | None = None  # p. ej. por qué no hay reglas o qué modo VCA está activo


@dataclass
class RuleUpdate:
    points: list[Point] | None = None
    enabled: bool | None = None
    sensitivity: int | None = None
    direction: str | None = None
    target: list[str] | None = None
    name: str | None = None

    @property
    def es_solo_activacion(self) -> bool:
        """Prender o apagar no toca el recurso de la regla, solo el del tipo."""
        return all(
            campo is None
            for campo in (self.points, self.sensitivity, self.direction, self.target, self.name)
        )


def clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))
