"""Reglas de analítica clásica de Hikvision: /ISAPI/Smart/* (XML, coordenadas 0..1000).

Comportamiento verificado contra la PTZ DS-2DF8A836IX-AEL (firmware V5.6.0):
- Escribir la lista completa de reglas devuelve 200 OK pero no cambia la geometría: hay que
  escribir el recurso individual (…/lineItem/<id>, …/regions/<id>).
- El <enabled> de cada regla individual se ignora: lo que activa la analítica es el <enabled>
  del recurso global del tipo (…/LineDetection/<canal>).
- Leer la lista de reglas devuelve coordenadas vacías para reglas que sí existen: hay que
  leer el recurso individual de cada una.
- Origen de coordenadas: abajo a la izquierda. Verificado midiendo una regla dibujada a mano
  en la interfaz de la cámara (y=560 se ve al 44 % desde arriba).
"""

import re
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from app.domain.rules import Point, Rule, RuleKind, RuleKindInfo, RuleUpdate, clamp01
from app.drivers.errors import NotSupported
from app.drivers.isapi import xml
from app.drivers.isapi.client import IsapiClient

ESCALA = 1000


@dataclass(frozen=True)
class SmartKind:
    kind: RuleKind
    resource: str  # /ISAPI/Smart/<resource>/<canal>
    item_path: str  # sub-recurso de cada regla
    coords_tag: str  # lista de coordenadas dentro de cada regla


SMART_KINDS = (
    SmartKind(RuleKind.LINE, "LineDetection", "lineItem", "CoordinatesList"),
    SmartKind(RuleKind.FIELD, "FieldDetection", "regions", "RegionCoordinatesList"),
    SmartKind(RuleKind.ENTRANCE, "regionEntrance", "regions", "RegionCoordinatesList"),
    SmartKind(RuleKind.EXITING, "regionExiting", "regions", "RegionCoordinatesList"),
)
BY_KIND = {k.kind: k for k in SMART_KINDS}

# "left-right" de Hikvision es "cruzar de A hacia B" mirando la línea de A a B.
_DIRECCION_A_UI = {"any": "any", "left-right": "a-b", "right-left": "b-a"}
_DIRECCION_A_ISAPI = {v: k for k, v in _DIRECCION_A_UI.items()}


def to_ui(x: int, y: int) -> Point:
    return (clamp01(x / ESCALA), clamp01(1 - y / ESCALA))


def to_isapi(point: Point) -> tuple[int, int]:
    x, y = point
    return (round(clamp01(x) * ESCALA), round((1 - clamp01(y)) * ESCALA))


def _points(item: Element, coords_tag: str) -> list[Point]:
    lista = xml.find(item, coords_tag)
    if lista is None:
        return []
    puntos = []
    for coordenada in list(lista):
        x = xml.to_int(xml.text(coordenada, "positionX"))
        y = xml.to_int(xml.text(coordenada, "positionY"))
        if x is not None and y is not None:
            puntos.append(to_ui(x, y))
    return puntos


def _items(root: Element, spec: SmartKind) -> list[Element]:
    """Cada regla es un hijo de la lista que contiene la lista de coordenadas."""
    return [
        e for e in root.iter() if xml.find(e, spec.coords_tag) is not None and xml.text(e, "id")
    ]


def parse_rules(content: bytes, spec: SmartKind) -> tuple[bool, list[Rule]]:
    root = xml.parse(content)
    habilitado = xml.text(root, "enabled") == "true"
    reglas = []
    for item in _items(root, spec):
        objetivo = (xml.text(item, "detectionTarget") or "").replace(" ", "")
        direccion = xml.text(item, "directionSensitivity")
        reglas.append(
            Rule(
                kind=spec.kind,
                external_id=xml.text(item, "id") or "?",
                points=_points(item, spec.coords_tag),
                # En esta familia la regla está activa si el tipo está activo.
                enabled=habilitado,
                sensitivity=xml.to_int(xml.text(item, "sensitivityLevel")),
                direction=_DIRECCION_A_UI.get(direccion or "", direccion),
                target=[t for t in objetivo.split(",") if t],
                extra={"time_threshold": xml.to_int(xml.text(item, "timeThreshold"))},
            )
        )
    return habilitado, reglas


def parse_capabilities(content: bytes, spec: SmartKind, enabled: bool) -> RuleKindInfo:
    raw = content.decode("utf-8", "replace")
    lista = re.search(r"<\w+List[^>]*\ssize=\"(\d+)\"", raw)
    objetivos = re.search(r'<detectionTarget[^>]*opt="([^"]*)"', raw)
    direcciones = re.search(r'<directionSensitivity[^>]*opt="([^"]*)"', raw)
    minimo = re.search(r"<minRegionCoordinatesNum[^>]*>(\d+)<", raw)
    maximo = re.search(r"<maxRegionCoordinatesNum[^>]*>(\d+)<", raw)
    es_linea = spec.kind == RuleKind.LINE
    return RuleKindInfo(
        kind=spec.kind,
        max_rules=int(lista.group(1)) if lista else 1,
        enabled=enabled,
        min_points=2 if es_linea else int(minimo.group(1)) if minimo else 3,
        max_points=2 if es_linea else int(maximo.group(1)) if maximo else 10,
        targets=[t for t in (objetivos.group(1).split(",") if objetivos else []) if t],
        directions=[
            _DIRECCION_A_UI.get(d, d)
            for d in (direcciones.group(1).split(",") if direcciones else [])
        ],
        toggle_per_rule=False,
    )


# --- escritura ------------------------------------------------------------------------------


def _replace_tag(raw: str, tag: str, value: str) -> str:
    patron = re.compile(rf"<{tag}>[^<]*</{tag}>")
    if patron.search(raw):
        return patron.sub(f"<{tag}>{value}</{tag}>", raw, count=1)
    return raw


def build_item_xml(original: str, spec: SmartKind, update: RuleUpdate) -> str:
    """Modifica solo lo pedido sobre el XML que devolvió la cámara (conserva el resto)."""
    nuevo = original
    if update.points is not None:
        coords = "".join(
            f"<{'Coordinates' if spec.kind == RuleKind.LINE else 'RegionCoordinates'}>"
            f"<positionX>{x}</positionX><positionY>{y}</positionY>"
            f"</{'Coordinates' if spec.kind == RuleKind.LINE else 'RegionCoordinates'}>"
            for x, y in (to_isapi(p) for p in update.points)
        )
        tag = spec.coords_tag
        nuevo = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>|<{tag}\s*/>",
            f"<{tag}>{coords}</{tag}>",
            nuevo,
            count=1,
            flags=re.S,
        )
    if update.sensitivity is not None:
        nuevo = _replace_tag(nuevo, "sensitivityLevel", str(max(1, min(100, update.sensitivity))))
    if update.direction is not None:
        nuevo = _replace_tag(
            nuevo, "directionSensitivity", _DIRECCION_A_ISAPI.get(update.direction, "any")
        )
    if update.target is not None:
        nuevo = re.sub(
            r"<detectionTarget>[^<]*</detectionTarget>",
            f"<detectionTarget>{','.join(update.target) or ' '}</detectionTarget>",
            nuevo,
            count=1,
        )
    return nuevo


def set_kind_enabled(original: str, enabled: bool) -> str:
    """Cambia solo el <enabled> global (el primero del documento)."""
    valor = "true" if enabled else "false"
    return re.sub(r"<enabled>\w+</enabled>", f"<enabled>{valor}</enabled>", original, count=1)


class SmartRulesDriver:
    def __init__(self, client: IsapiClient, channel: int) -> None:
        self.client = client
        self.channel = channel

    def _resource(self, spec: SmartKind) -> str:
        return f"/ISAPI/Smart/{spec.resource}/{self.channel}"

    def item_resource(self, spec: SmartKind, rule_id: str) -> str:
        return f"{self._resource(spec)}/{spec.item_path}/{rule_id}"

    def kind_resource(self, spec: SmartKind) -> str:
        return self._resource(spec)

    async def read_kind(self, spec: SmartKind) -> tuple[RuleKindInfo, list[Rule]] | None:
        try:
            respuesta = await self.client.get(self._resource(spec))
        except NotSupported:
            return None
        habilitado, reglas = parse_rules(respuesta.content, spec)
        try:
            caps = await self.client.get(f"{self._resource(spec)}/capabilities")
            info = parse_capabilities(caps.content, spec, habilitado)
        except NotSupported:
            info = RuleKindInfo(spec.kind, len(reglas) or 1, habilitado, 2, 10)

        # La lista miente: devuelve coordenadas vacías para reglas que sí existen (verificado
        # en la PTZ, líneas 2 y 3). Solo el recurso individual dice la verdad.
        for indice, regla in enumerate(reglas):
            try:
                crudo = await self.read_item_raw(spec, regla.external_id)
            except NotSupported:
                continue
            _, individuales = parse_rules(crudo.encode(), spec)
            if individuales:
                real = individuales[0]
                real.enabled = habilitado
                reglas[indice] = real
        return info, reglas

    async def read_item_raw(self, spec: SmartKind, rule_id: str) -> str:
        return (await self.client.get(self.item_resource(spec, rule_id))).content.decode()

    async def read_kind_raw(self, spec: SmartKind) -> str:
        return (await self.client.get(self._resource(spec))).content.decode()

    async def write_item(self, spec: SmartKind, rule_id: str, content: str) -> None:
        await self.client.put(self.item_resource(spec, rule_id), content.encode())

    async def write_kind(self, spec: SmartKind, content: str) -> None:
        await self.client.put(self._resource(spec), content.encode())
