"""Reglas de AI Open Platform: /ISAPI/Intelligent/AIOpenPlatform/* (JSON, coordenadas 0..1).

Las URLs no están en el manual DeepinView: salieron del JavaScript de la interfaz web de la
iDS-2CD7146G2-IZS (firmware V5.9.24). La regla vive dentro de una "tarea" de análisis de video,
y cada regla se activa por separado con "Valid".
"""

import copy
import json
from typing import Any

from app.domain.rules import Point, Rule, RuleKind, RuleKindInfo, RuleUpdate, clamp01
from app.drivers.errors import InvalidResponse, NotSupported
from app.drivers.isapi.client import IsapiClient

BASE = "/ISAPI/Intelligent/AIOpenPlatform"
# PolygonType 1 = línea, 2 = polígono (inferido de la respuesta real y de CrossDirection).
_TIPO_LINEA = 1


def _config_infos(config: dict[str, Any]) -> list[dict[str, Any]]:
    return config.get("AIRuleConfig", {}).get("VCA_config", {}).get("ConfigInfoList", [])


def _nombres(config: dict[str, Any]) -> dict[int, str]:
    nombres: dict[int, str] = {}
    for orden in config.get("AIRuleConfig", {}).get("algSorting", []):
        for info in orden.get("RuleNameInfo", []):
            nombres[int(info["ruleID"])] = info["ruleName"]
    return nombres


def parse_rules(config: dict[str, Any], labels: dict[int, str]) -> list[Rule]:
    nombres = _nombres(config)
    reglas = []
    for info in _config_infos(config):
        for regla in info.get("ConfigInfo", {}).get("EventRule", {}).get("RuleInfo", []):
            regiones = regla.get("RuleRegion", {}).get("Region", [])
            poligono = regiones[0].get("RulePolygon", {}) if regiones else {}
            puntos: list[Point] = [
                (clamp01(float(p["x"])), clamp01(float(p["y"])))
                for p in poligono.get("PolygonPoint", [])
            ]
            tipo_objetivo = regla.get("TriggerCondition", {}).get("TargetType")
            rule_id = int(regla["RuleID"])
            reglas.append(
                Rule(
                    kind=RuleKind.LINE
                    if poligono.get("PolygonType") == _TIPO_LINEA
                    else RuleKind.AI_ZONE,
                    external_id=str(rule_id),
                    name=nombres.get(rule_id),
                    points=puntos,
                    enabled=regla.get("Valid") == 1,
                    sensitivity=regla.get("RuleParam", {}).get("Sensitive"),
                    target=[labels.get(tipo_objetivo, f"objetivo {tipo_objetivo}")]
                    if tipo_objetivo is not None
                    else [],
                    extra={
                        "node_id": info.get("NodeID"),
                        "target_type": tipo_objetivo,
                        "confidence": regla.get("RuleParam", {}).get("AlertConfThreshold"),
                        "trigger_interval_s": regla.get("RuleParam", {}).get("TriggerInterval"),
                    },
                )
            )
    return reglas


def apply_update(config: dict[str, Any], rule_id: str, update: RuleUpdate) -> dict[str, Any]:
    """Devuelve una copia de la configuración con la regla modificada (el resto intacto)."""
    nuevo = copy.deepcopy(config)
    for info in _config_infos(nuevo):
        for regla in info.get("ConfigInfo", {}).get("EventRule", {}).get("RuleInfo", []):
            if str(regla["RuleID"]) != rule_id:
                continue
            if update.enabled is not None:
                regla["Valid"] = 1 if update.enabled else 0
            if update.sensitivity is not None:
                regla.setdefault("RuleParam", {})["Sensitive"] = max(
                    1, min(100, update.sensitivity)
                )
            if update.points is not None:
                regiones = regla.setdefault("RuleRegion", {}).setdefault("Region", [{}])
                poligono = regiones[0].setdefault("RulePolygon", {})
                poligono["PolygonPoint"] = [
                    {"x": round(clamp01(x), 4), "y": round(clamp01(y), 4)} for x, y in update.points
                ]
            if update.name is not None:
                for orden in nuevo.get("AIRuleConfig", {}).get("algSorting", []):
                    for n in orden.get("RuleNameInfo", []):
                        if str(n["ruleID"]) == rule_id:
                            n["ruleName"] = update.name[:32]
            return nuevo
    raise NotSupported(f"La regla {rule_id} no existe en la tarea de IA")


def parse_labels(engines: dict[str, Any]) -> dict[int, str]:
    """Etiquetas del modelo cargado: '5 RaiseHands_or_HoldHead' -> {5: 'RaiseHands_or_HoldHead'}."""
    etiquetas: dict[int, str] = {}
    for carga in engines.get("LoadingInfoList", []):
        for nodo in carga.get("algSortingParams", {}).get("nodeInfos", []):
            for desc in nodo.get("modelDescription", {}).get("description", []):
                for etiqueta in desc.get("labels", []):
                    numero, _, nombre = etiqueta.partition(" ")
                    if numero.isdigit():
                        etiquetas.setdefault(int(numero), nombre)
    return etiquetas


class AiopRulesDriver:
    def __init__(self, client: IsapiClient, channel: int) -> None:
        self.client = client
        self.channel = channel
        self.task_id: str | None = None

    async def _json(self, path: str) -> dict[str, Any]:
        respuesta = await self.client.get(path)
        try:
            return json.loads(respuesta.content)
        except ValueError as exc:
            raise InvalidResponse(f"JSON inválido en {path}") from exc

    async def load_task(self) -> str:
        tareas = (await self._json(f"{BASE}/videoTask?format=json")).get("Tasks", [])
        if not tareas:
            raise NotSupported("La cámara no tiene ninguna tarea de IA configurada")
        self.task_id = tareas[0]["taskID"]
        return self.task_id

    def rules_resource(self) -> str:
        return f"{BASE}/AIRuleConfig/task/{self.task_id}/channels/{self.channel}?format=json"

    async def read_config(self) -> dict[str, Any]:
        if self.task_id is None:
            await self.load_task()
        return await self._json(self.rules_resource())

    async def read_labels(self) -> dict[int, str]:
        try:
            return parse_labels(await self._json(f"{BASE}/algorithmModel/engines?format=json"))
        except NotSupported:
            return {}

    async def read_max_rules(self) -> int:
        try:
            caps = await self._json(
                f"{BASE}/AIRuleConfig/channels/{self.channel}/capabilities?format=json"
            )
            return int(caps["AIRuleConfigCap"]["ruleID"]["@max"])
        except (NotSupported, KeyError, TypeError, ValueError):
            return 16

    async def write_config(self, config: dict[str, Any]) -> None:
        await self.client.put(
            self.rules_resource(),
            json.dumps(config).encode(),
            content_type="application/json",
        )

    def kind_info(self, max_rules: int, labels: dict[int, str]) -> RuleKindInfo:
        return RuleKindInfo(
            kind=RuleKind.AI_ZONE,
            max_rules=max_rules,
            enabled=True,
            min_points=3,
            max_points=10,
            targets=list(labels.values()),
            toggle_per_rule=True,
        )
