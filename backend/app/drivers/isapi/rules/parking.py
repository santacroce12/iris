"""Plazas de estacionamiento: /ISAPI/Parking/* (JSON, coordenadas 0..1).

Tercera familia de analítica encontrada en este trabajo, y la que menos se parece a lo que su
propia documentación sugiere. Verificado contra una iDS-2CD7A46G0/P-IZHSY (firmware V5.8.61):

- **`?format=json` no es opcional.** Sin ese parámetro el mismo recurso responde
  `403 invalidOperation`, que parece decir "esta operación no corresponde" y no "te falta un
  parámetro".
- **La ruta distingue mayúsculas**: `packingSpaceRecognition` responde, `PackingSpaceRecognition`
  da `403`. La cámara usa las dos grafías en su propio documento de capacidades.
- **"Packing" es un error de tipeo del fabricante** ("embalaje" en vez de "estacionamiento"), y
  está congelado en la ruta, en el tipo de evento y en el modo de VCA. Adentro del payload hay un
  segundo error: `absoulteParkingNum` en vez de `absolute`. Los dos hay que reproducirlos tal cual.
- El manual ISAPI de la serie DeepinView **no documenta este árbol de endpoints**: nombra la
  función en un par de enums y nunca dice cómo se configura.

A diferencia de la analítica clásica y de AI Open Platform, acá no hay tipos de regla: hay una
sola lista de plazas, cada una un polígono de exactamente 4 puntos, y un único interruptor global
para toda la función.
"""

import copy
import json
from typing import Any

from app.domain.rules import Point, Rule, RuleKind, RuleKindInfo, RuleUpdate, clamp01
from app.drivers.errors import InvalidResponse, NotSupported
from app.drivers.isapi import xml
from app.drivers.isapi.client import IsapiClient

BASE = "/ISAPI/Parking/channels"
PUNTOS_POR_PLAZA = 4  # la cámara declara Region.maxSize = 4 y rechaza otra cantidad
MAX_PLAZAS_POR_DEFECTO = 40


def _raiz(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("PackingSpaceRecognition", {})


def _plazas(config: dict[str, Any]) -> list[dict[str, Any]]:
    return _raiz(config).get("PackingSpaceInfoList", [])


def _puntos_de(info: dict[str, Any]) -> list[Point]:
    puntos: list[Point] = []
    for entrada in info.get("Region", []):
        punto = entrada.get("Point", {})
        if "positionX" in punto and "positionY" in punto:
            puntos.append((clamp01(float(punto["positionX"])), clamp01(float(punto["positionY"]))))
    return puntos


def parse_status(contenido: bytes) -> dict[str, dict[str, Any]]:
    """Ocupación en vivo por plaza. Llega en XML: este recurso no acepta `?format=json`.

    Rareza: el elemento raíz se llama `ParkingStatusCap` aunque devuelva estado, no capacidades.
    """
    raiz = xml.parse(contenido)
    estado: dict[str, dict[str, Any]] = {}
    for plaza in xml.find_all(raiz, "ParkingStatus"):
        numero = xml.text(plaza, "parkingNo")
        if not numero:
            continue
        estado[numero] = {
            "ocupada": xml.text(plaza, "carStatus") == "true",
            "segundos_estacionado": xml.to_int(xml.text(plaza, "parkingTime")),
        }
    return estado


def parse_rules(
    config: dict[str, Any], estado: dict[str, dict[str, Any]] | None = None
) -> list[Rule]:
    """Cada plaza es una regla. El `enabled` es global, así que todas comparten el mismo valor."""
    habilitado = bool(_raiz(config).get("enable"))
    estado = estado or {}
    reglas = []
    for entrada in _plazas(config):
        info = entrada.get("PackingSpaceInfo", {})
        numero = str(info.get("absoulteParkingNum") or info.get("absoluteParkingNum") or "")
        if not numero:
            continue
        vivo = estado.get(numero, {})
        reglas.append(
            Rule(
                kind=RuleKind.PARKING_SPACE,
                external_id=numero,
                name=f"Plaza {numero}",
                points=_puntos_de(info),
                enabled=habilitado,
                extra={
                    "ocupada": vivo.get("ocupada"),
                    "segundos_estacionado": vivo.get("segundos_estacionado"),
                },
            )
        )
    return reglas


def apply_update(config: dict[str, Any], space_id: str, update: RuleUpdate) -> dict[str, Any]:
    """Copia de la configuración con una plaza modificada; el resto queda intacto.

    `enabled` no es de la plaza sino de la función entera: se escribe en la raíz.
    """
    nuevo = copy.deepcopy(config)
    if update.enabled is not None:
        _raiz(nuevo)["enable"] = update.enabled

    if update.points is None:
        if update.enabled is None:
            raise NotSupported("No hay nada para cambiar en esta plaza")
        return nuevo

    if len(update.points) != PUNTOS_POR_PLAZA:
        raise NotSupported(
            f"Una plaza necesita exactamente {PUNTOS_POR_PLAZA} puntos, "
            f"llegaron {len(update.points)}"
        )

    for entrada in _plazas(nuevo):
        info = entrada.get("PackingSpaceInfo", {})
        numero = str(info.get("absoulteParkingNum") or info.get("absoluteParkingNum") or "")
        if numero != space_id:
            continue
        info["Region"] = [
            {"Point": {"positionX": round(clamp01(x), 3), "positionY": round(clamp01(y), 3)}}
            for x, y in update.points
        ]
        return nuevo
    raise NotSupported(f"La cámara no tiene la plaza {space_id}")


class ParkingRulesDriver:
    def __init__(self, client: IsapiClient, channel: int) -> None:
        self.client = client
        self.channel = channel

    def rules_resource(self) -> str:
        return f"{BASE}/{self.channel}/packingSpaceRecognition?format=json"

    def status_resource(self) -> str:
        return f"{BASE}/{self.channel}/parkingStatus"

    async def _json(self, path: str) -> dict[str, Any]:
        respuesta = await self.client.get(path)
        try:
            return json.loads(respuesta.content)
        except ValueError as exc:
            raise InvalidResponse(f"JSON inválido en {path}") from exc

    async def read_config(self) -> dict[str, Any]:
        return await self._json(self.rules_resource())

    async def read_status(self) -> dict[str, dict[str, Any]]:
        """La ocupación es un extra: si falla, las plazas igual se pueden leer y dibujar."""
        try:
            return parse_status((await self.client.get(self.status_resource())).content)
        except (NotSupported, InvalidResponse):
            return {}

    async def read_max_spaces(self) -> int:
        try:
            caps = await self._json(
                f"{BASE}/{self.channel}/packingSpaceRecognition/capabilities?format=json"
            )
            region = caps["PackingSpaceRecognitionCap"]["PackingSpaceRegionList"]
            return int(region["PackingSpaceRegion"]["packingSpaceNum"]["@max"])
        except (NotSupported, InvalidResponse, KeyError, TypeError, ValueError):
            return MAX_PLAZAS_POR_DEFECTO

    async def write_config(self, config: dict[str, Any]) -> None:
        await self.client.put(
            self.rules_resource(), json.dumps(config).encode(), content_type="application/json"
        )

    def kind_info(self, max_spaces: int, enabled: bool) -> RuleKindInfo:
        return RuleKindInfo(
            kind=RuleKind.PARKING_SPACE,
            max_rules=max_spaces,
            enabled=enabled,
            min_points=PUNTOS_POR_PLAZA,
            max_points=PUNTOS_POR_PLAZA,
            toggle_per_rule=False,  # un solo interruptor para toda la función
        )
