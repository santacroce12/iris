"""Corredor de experimentos: la evidencia medible que pide la Fase 5 del anteproyecto.

Repite cada función N veces por protocolo y por cámara, todo bajo un mismo `experiment_id`, y
saca la tasa de éxito y las latencias p50/p95. No inventa infraestructura nueva: reusa las
mismas sondas y el mismo `operation_logs` del motor de capacidades — un experimento es, ni más
ni menos, correr la detección varias veces y medir en vez de solo constatar.

Antes de las N repeticiones se hace **una** llamada de reconocimiento por cámara y protocolo:
si la cámara no responde, no tiene sentido esperar N timeouts de 8 segundos cada uno. Ese
resultado (alcanzable o no) también queda como parte del experimento.
"""

import math
import statistics
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Camera, OperationLog
from app.drivers.errors import DriverError
from app.drivers.onvif.session import onvif_session
from app.services import detection, targets

REPETICIONES_POR_DEFECTO = 30


@dataclass
class ResultadoCamara:
    camera_id: uuid.UUID
    camera_name: str
    isapi_alcanzable: bool
    onvif_alcanzable: bool
    isapi_error: str | None = None
    onvif_error: str | None = None


@dataclass
class Experimento:
    experiment_id: uuid.UUID
    iniciado_en: str
    repeticiones: int
    resultados: list[ResultadoCamara] = field(default_factory=list)


async def _isapi_alcanzable(session: AsyncSession, camera: Camera) -> tuple[bool, str | None]:
    """Una sola llamada de reconocimiento: evita esperar N timeouts si la cámara no responde."""
    try:
        async with targets.isapi_client(camera) as client:
            await client.get("/ISAPI/System/deviceInfo")
    except DriverError as exc:
        return False, f"{exc.code}: {exc.message}"
    return True, None


async def _correr_isapi(
    session: AsyncSession, camera: Camera, repeticiones: int, experiment_id: uuid.UUID
) -> None:
    async with targets.isapi_client(camera) as client:
        sondas = detection.sondas_isapi(client, camera.channel)
        await detection.correr(
            session, camera, sondas, repeticiones=repeticiones, experiment_id=experiment_id
        )


async def _correr_onvif(
    session: AsyncSession, camera: Camera, repeticiones: int, experiment_id: uuid.UUID
) -> None:
    async with onvif_session(targets.onvif_target(camera)) as onvif:
        sondas = detection.sondas_onvif(onvif)
        await detection.correr(
            session, camera, sondas, repeticiones=repeticiones, experiment_id=experiment_id
        )


async def run_experiment(
    session: AsyncSession,
    cameras: list[Camera],
    repeticiones: int = REPETICIONES_POR_DEFECTO,
    log=print,
) -> Experimento:
    experimento = Experimento(
        experiment_id=uuid.uuid4(),
        iniciado_en=datetime.now(UTC).isoformat(timespec="seconds"),
        repeticiones=repeticiones,
    )
    for camera in cameras:
        log(f"\n=== {camera.name} ({camera.host}:{camera.http_port}) ===")
        resultado = ResultadoCamara(camera.id, camera.name, False, False)

        alcanzable, error = await _isapi_alcanzable(session, camera)
        resultado.isapi_alcanzable = alcanzable
        resultado.isapi_error = error
        if alcanzable:
            log(f"  ISAPI: corriendo {repeticiones} repeticiones por función...")
            await _correr_isapi(session, camera, repeticiones, experimento.experiment_id)
            log("  ISAPI: listo")
        else:
            log(f"  ISAPI: no alcanzable ({error}), se omite")

        try:
            await _correr_onvif(session, camera, repeticiones, experimento.experiment_id)
            resultado.onvif_alcanzable = True
            log("  ONVIF: listo")
        except DriverError as exc:
            resultado.onvif_error = f"{exc.code}: {exc.message}"
            log(f"  ONVIF: no alcanzable ({resultado.onvif_error}), se omite")

        experimento.resultados.append(resultado)
        await session.commit()

    return experimento


# --- agregación ------------------------------------------------------------------------------


@dataclass
class Estadistica:
    camera_name: str
    capability_code: str
    protocol: str
    n: int
    exitos: int
    tasa_exito: float
    latencia_p50_ms: float
    latencia_p95_ms: float
    latencia_media_ms: float
    latencia_min_ms: float
    latencia_max_ms: float


def _percentil(valores_ordenados: list[float], p: float) -> float:
    """Interpolación lineal, el mismo método que usa numpy por defecto."""
    if not valores_ordenados:
        return 0.0
    if len(valores_ordenados) == 1:
        return valores_ordenados[0]
    posicion = (len(valores_ordenados) - 1) * (p / 100)
    piso, techo = math.floor(posicion), math.ceil(posicion)
    if piso == techo:
        return valores_ordenados[int(posicion)]
    return valores_ordenados[piso] * (techo - posicion) + valores_ordenados[techo] * (
        posicion - piso
    )


async def agregar(session: AsyncSession, experiment_id: uuid.UUID) -> list[Estadistica]:
    """Junta los `operation_logs` de un experimento en tasa de éxito y latencias por función."""
    nombres = {c.id: c.name for c in await session.scalars(select(Camera))}
    filas = list(
        await session.scalars(
            select(OperationLog).where(OperationLog.experiment_id == experiment_id)
        )
    )

    grupos: dict[tuple[uuid.UUID | None, str, str], list[OperationLog]] = defaultdict(list)
    for fila in filas:
        grupos[(fila.camera_id, fila.capability_code, fila.protocol)].append(fila)

    estadisticas = []
    for (camera_id, code, protocolo), registros in grupos.items():
        latencias = sorted(r.latency_ms for r in registros if r.latency_ms is not None)
        exitos = sum(1 for r in registros if r.success)
        estadisticas.append(
            Estadistica(
                camera_name=nombres.get(camera_id, str(camera_id)) if camera_id else "?",
                capability_code=code,
                protocol=protocolo,
                n=len(registros),
                exitos=exitos,
                tasa_exito=exitos / len(registros) if registros else 0.0,
                latencia_p50_ms=round(_percentil(latencias, 50), 1),
                latencia_p95_ms=round(_percentil(latencias, 95), 1),
                latencia_media_ms=round(statistics.fmean(latencias), 1) if latencias else 0.0,
                latencia_min_ms=round(latencias[0], 1) if latencias else 0.0,
                latencia_max_ms=round(latencias[-1], 1) if latencias else 0.0,
            )
        )
    return sorted(estadisticas, key=lambda e: (e.camera_name, e.capability_code, e.protocol))


# --- exportación -----------------------------------------------------------------------------

_ENCABEZADOS = (
    "camara",
    "funcion",
    "protocolo",
    "repeticiones",
    "exitos",
    "tasa_exito",
    "latencia_p50_ms",
    "latencia_p95_ms",
    "latencia_media_ms",
    "latencia_min_ms",
    "latencia_max_ms",
)


def _fila_csv(e: Estadistica) -> str:
    valores = (
        e.camera_name,
        e.capability_code,
        e.protocol,
        str(e.n),
        str(e.exitos),
        f"{e.tasa_exito:.3f}",
        f"{e.latencia_p50_ms:.1f}",
        f"{e.latencia_p95_ms:.1f}",
        f"{e.latencia_media_ms:.1f}",
        f"{e.latencia_min_ms:.1f}",
        f"{e.latencia_max_ms:.1f}",
    )
    return ",".join(f'"{v}"' for v in valores)


def exportar_csv(estadisticas: list[Estadistica], destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    lineas = [",".join(_ENCABEZADOS)] + [_fila_csv(e) for e in estadisticas]
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


def exportar_markdown(
    experimento: Experimento, estadisticas: list[Estadistica], destino: Path
) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        "# Experimento de evidencia — Fase 5",
        "",
        f"- **Corrido**: {experimento.iniciado_en}",
        f"- **Repeticiones por función**: {experimento.repeticiones}",
        f"- **Identificador**: `{experimento.experiment_id}`",
        "",
        "Cada número sale de repetir la misma llamada N veces contra la cámara real (o "
        "simulada) y medir. La tasa de éxito y la latencia son la evidencia que le falta a "
        "una demo para ser un resultado.",
        "",
    ]

    for resultado in experimento.resultados:
        lineas.append(f"## {resultado.camera_name}")
        lineas.append("")
        detalle_isapi = f" ({resultado.isapi_error})" if resultado.isapi_error else ""
        detalle_onvif = f" ({resultado.onvif_error})" if resultado.onvif_error else ""
        estado_isapi = "alcanzable" if resultado.isapi_alcanzable else "no alcanzable"
        estado_onvif = "alcanzable" if resultado.onvif_alcanzable else "no alcanzable"
        lineas.append(f"- ISAPI: {estado_isapi}{detalle_isapi}")
        lineas.append(f"- ONVIF: {estado_onvif}{detalle_onvif}")
        lineas.append("")

        propias = [e for e in estadisticas if e.camera_name == resultado.camera_name]
        if propias:
            lineas.append(
                "| Función | Protocolo | N | Éxitos | Tasa | p50 (ms) | p95 (ms) | media (ms) |"
            )
            lineas.append("|---|---|---|---|---|---|---|---|")
            for e in propias:
                lineas.append(
                    f"| {e.capability_code} | {e.protocol} | {e.n} | {e.exitos} | "
                    f"{e.tasa_exito:.0%} | {e.latencia_p50_ms} | {e.latencia_p95_ms} | "
                    f"{e.latencia_media_ms} |"
                )
        else:
            lineas.append("_Sin mediciones: ningún protocolo respondió._")
        lineas.append("")

    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino
