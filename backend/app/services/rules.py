"""Reglas de analítica: leer, escribir con respaldo y verificar releyendo.

La cámara puede responder "200 OK" sin aplicar nada (verificado en la PTZ), así que ninguna
escritura se da por buena: se relee el recurso y se compara con lo que se pidió.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalyticRule, Camera, ConfigBackup
from app.domain.enums import Protocol
from app.domain.rules import (
    Rule,
    RuleFamily,
    RuleKind,
    RuleKindInfo,
    RuleSet,
    RuleUpdate,
)
from app.drivers.errors import DriverError, NotSupported, VerificationFailed
from app.drivers.isapi.client import IsapiClient
from app.drivers.isapi.rules import aiop, smart
from app.services import targets
from app.services.operations import run_operation

CAPABILITY = "analytics.rules"
# Las coordenadas viajan redondeadas (0..1000 en la PTZ, 4 decimales en el domo).
TOLERANCIA = 0.005


@dataclass
class Backend:
    """Resuelve con qué familia de reglas habla esta cámara."""

    family: RuleFamily
    smart_driver: smart.SmartRulesDriver | None = None
    ai_driver: aiop.AiopRulesDriver | None = None
    note: str | None = None


async def detect_backend(client: IsapiClient, channel: int) -> Backend:
    """El domo no soporta /ISAPI/Smart/* y la PTZ no conoce AI Open Platform."""
    driver = aiop.AiopRulesDriver(client, channel)
    try:
        await client.get(f"{aiop.BASE}?format=json")
    except DriverError:
        return Backend(RuleFamily.SMART, smart_driver=smart.SmartRulesDriver(client, channel))
    try:
        await driver.load_task()
    except DriverError as exc:
        return Backend(RuleFamily.AIOP, ai_driver=driver, note=str(exc.message))
    return Backend(RuleFamily.AIOP, ai_driver=driver)


# --- lectura -------------------------------------------------------------------------------


async def _read_smart(driver: smart.SmartRulesDriver) -> tuple[list[RuleKindInfo], list[Rule]]:
    kinds: list[RuleKindInfo] = []
    reglas: list[Rule] = []
    for spec in smart.SMART_KINDS:
        leido = await driver.read_kind(spec)
        if leido is None:
            continue
        info, del_tipo = leido
        kinds.append(info)
        reglas.extend(del_tipo)
    return kinds, reglas


async def _read_aiop(driver: aiop.AiopRulesDriver) -> tuple[list[RuleKindInfo], list[Rule]]:
    etiquetas = await driver.read_labels()
    config = await driver.read_config()
    reglas = aiop.parse_rules(config, etiquetas)
    return [driver.kind_info(await driver.read_max_rules(), etiquetas)], reglas


async def read_rule_set(session: AsyncSession, camera: Camera) -> RuleSet:
    async with targets.isapi_client(camera) as client:
        backend = await detect_backend(client, camera.channel)
        if backend.family is RuleFamily.AIOP and backend.ai_driver is not None:
            if backend.note is not None:  # hay plataforma de IA pero ninguna tarea corriendo
                return RuleSet(RuleFamily.AIOP, [], [], note=backend.note)
            kinds, reglas = await _read_aiop(backend.ai_driver)
        elif backend.smart_driver is not None:
            kinds, reglas = await _read_smart(backend.smart_driver)
        else:  # pragma: no cover - detect_backend siempre deja uno de los dos
            return RuleSet(RuleFamily.NONE, [], [], note="La cámara no expone reglas de analítica")

    if not kinds:
        return RuleSet(
            RuleFamily.NONE, [], [], note="La cámara no soporta ninguna familia de reglas conocida"
        )
    await _persist(session, camera, backend.family, reglas)
    return RuleSet(backend.family, kinds, reglas, note=backend.note)


async def _persist(
    session: AsyncSession, camera: Camera, family: RuleFamily, reglas: list[Rule]
) -> None:
    """Guarda lo leído para que la matriz y los informes no dependan de tener la cámara."""
    existentes = {
        (r.rule_type, r.external_id): r
        for r in await session.scalars(
            select(AnalyticRule).where(
                AnalyticRule.camera_id == camera.id, AnalyticRule.protocol == Protocol.ISAPI
            )
        )
    }
    for regla in reglas:
        fila = existentes.get((regla.kind.value, regla.external_id))
        valores = {
            "enabled": regla.enabled,
            "geometry": {"points": [list(p) for p in regla.points]},
            "params": {
                "name": regla.name,
                "sensitivity": regla.sensitivity,
                "direction": regla.direction,
                "target": regla.target,
                "family": family.value,
                **regla.extra,
            },
        }
        if fila is None:
            session.add(
                AnalyticRule(
                    camera_id=camera.id,
                    protocol=Protocol.ISAPI,
                    rule_type=regla.kind.value,
                    external_id=regla.external_id,
                    channel=camera.channel,
                    **valores,
                )
            )
        else:
            for campo, valor in valores.items():
                setattr(fila, campo, valor)


# --- escritura -----------------------------------------------------------------------------


async def _backup(
    session: AsyncSession, camera: Camera, resource: str, content: str, content_type: str
) -> None:
    session.add(
        ConfigBackup(
            camera_id=camera.id, resource=resource, content=content, content_type=content_type
        )
    )


def _diferencias(regla: Rule, update: RuleUpdate) -> list[str]:
    """Campos que se pidieron y la cámara no aplicó."""
    faltantes = []
    if update.points is not None:
        iguales = len(regla.points) == len(update.points) and all(
            abs(a[0] - b[0]) <= TOLERANCIA and abs(a[1] - b[1]) <= TOLERANCIA
            for a, b in zip(regla.points, update.points, strict=True)
        )
        if not iguales:
            faltantes.append("geometría")
    if update.sensitivity is not None and regla.sensitivity != update.sensitivity:
        faltantes.append("sensibilidad")
    if update.direction is not None and regla.direction != update.direction:
        faltantes.append("dirección")
    if update.enabled is not None and regla.enabled != update.enabled:
        faltantes.append("activación")
    if update.name is not None and regla.name != update.name:
        faltantes.append("nombre")
    if update.target is not None and sorted(regla.target) != sorted(update.target):
        faltantes.append("objetivo")
    return faltantes


def _buscar(reglas: list[Rule], kind: RuleKind, external_id: str) -> Rule:
    for regla in reglas:
        if regla.kind is kind and regla.external_id == external_id:
            return regla
    raise NotSupported(f"La cámara no tiene la regla {external_id} de tipo {kind.value}")


async def update_rule(
    session: AsyncSession,
    camera: Camera,
    kind: RuleKind,
    external_id: str,
    update: RuleUpdate,
) -> Rule:
    async with targets.isapi_client(camera) as client:
        backend = await detect_backend(client, camera.channel)
        if backend.family is RuleFamily.AIOP and backend.ai_driver is not None:
            if backend.note is not None:
                raise NotSupported(backend.note)
            regla = await _update_aiop(session, camera, backend.ai_driver, external_id, update)
        elif backend.smart_driver is not None:
            regla = await _update_smart(
                session, camera, backend.smart_driver, kind, external_id, update
            )
        else:  # pragma: no cover
            raise NotSupported("La cámara no expone reglas de analítica")
    return regla


async def _update_smart(
    session: AsyncSession,
    camera: Camera,
    driver: smart.SmartRulesDriver,
    kind: RuleKind,
    external_id: str,
    update: RuleUpdate,
) -> Rule:
    spec = smart.BY_KIND.get(kind)
    if spec is None:
        raise NotSupported(f"Esta cámara no maneja reglas de tipo {kind.value}")

    # El <enabled> de cada regla se ignora: lo que activa la analítica es el del tipo entero.
    if update.enabled is not None:
        await _set_kind_enabled(session, camera, driver, spec, update.enabled)

    if update.es_solo_activacion:
        leido = await driver.read_kind(spec)
        regla = _buscar(leido[1] if leido else [], kind, external_id)
        _verificar(regla, update, driver.kind_resource(spec))
        await _persist(session, camera, RuleFamily.SMART, [regla])
        return regla

    recurso = driver.item_resource(spec, external_id)
    original = await driver.read_item_raw(spec, external_id)
    await _backup(session, camera, recurso, original, "application/xml")
    nuevo = smart.build_item_xml(original, spec, update)

    resultado = await run_operation(
        session,
        camera_id=camera.id,
        capability=CAPABILITY,
        protocol=Protocol.ISAPI,
        operation=f"PUT {recurso}",
        call=driver.write_item(spec, external_id, nuevo),
        detail={"rule": external_id, "kind": kind.value},
    )
    if resultado.error is not None:
        raise resultado.error

    leido = await driver.read_kind(spec)
    regla = _buscar(leido[1] if leido else [], kind, external_id)
    _verificar(regla, update, recurso)
    await _persist(session, camera, RuleFamily.SMART, [regla])
    return regla


async def _set_kind_enabled(
    session: AsyncSession,
    camera: Camera,
    driver: smart.SmartRulesDriver,
    spec: smart.SmartKind,
    enabled: bool,
) -> None:
    recurso = driver.kind_resource(spec)
    original = await driver.read_kind_raw(spec)
    await _backup(session, camera, recurso, original, "application/xml")
    resultado = await run_operation(
        session,
        camera_id=camera.id,
        capability=CAPABILITY,
        protocol=Protocol.ISAPI,
        operation=f"PUT {recurso}",
        call=driver.write_kind(spec, smart.set_kind_enabled(original, enabled)),
        detail={"kind": spec.kind.value, "enabled": enabled},
    )
    if resultado.error is not None:
        raise resultado.error


async def _update_aiop(
    session: AsyncSession,
    camera: Camera,
    driver: aiop.AiopRulesDriver,
    external_id: str,
    update: RuleUpdate,
) -> Rule:
    config = await driver.read_config()
    recurso = driver.rules_resource()
    await _backup(session, camera, recurso, json.dumps(config, indent=1), "application/json")

    resultado = await run_operation(
        session,
        camera_id=camera.id,
        capability=CAPABILITY,
        protocol=Protocol.ISAPI,
        operation=f"PUT {recurso}",
        call=driver.write_config(aiop.apply_update(config, external_id, update)),
        detail={"rule": external_id},
    )
    if resultado.error is not None:
        raise resultado.error

    etiquetas = await driver.read_labels()
    reglas = aiop.parse_rules(await driver.read_config(), etiquetas)
    regla = _buscar(reglas, RuleKind.AI_ZONE, external_id)
    _verificar(regla, update, recurso)
    await _persist(session, camera, RuleFamily.AIOP, [regla])
    return regla


def _verificar(regla: Rule, update: RuleUpdate, recurso: str) -> None:
    faltantes = _diferencias(regla, update)
    if faltantes:
        raise VerificationFailed(
            f"La cámara aceptó el pedido pero no aplicó: {', '.join(faltantes)} ({recurso})"
        )


async def restore_backup(session: AsyncSession, camera: Camera, backup_id: uuid.UUID) -> None:
    respaldo = await session.get(ConfigBackup, backup_id)
    if respaldo is None or respaldo.camera_id != camera.id:
        raise NotSupported("Ese respaldo no existe para esta cámara")
    async with targets.isapi_client(camera) as client:
        await client.put(
            respaldo.resource, respaldo.content.encode(), content_type=respaldo.content_type
        )
    respaldo.restored_at = _ahora()


def _ahora():

    return datetime.now(UTC)
