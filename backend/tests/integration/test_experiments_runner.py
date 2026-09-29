"""El corredor de experimentos (Fase 5) contra la cámara simulada.

No hace falta hardware real para producir la evidencia medible que pide el anteproyecto: el
mismo motor de capacidades, repetido N veces, ya da tasa de éxito y latencias.
"""

import asyncio
import uuid
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.db.models import Camera, OperationLog
from app.drivers.isapi.client import IsapiClient, IsapiTarget
from app.main import app
from app.services import targets
from app.services.experiments import agregar, run_experiment
from tools.simulator.camera import crear_app
from tools.simulator.profiles import PROFILES

BACKEND = Path(__file__).resolve().parents[2]


def _migrate_fresh() -> None:
    async def reset() -> None:
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(reset())
    config = Config(BACKEND / "alembic.ini")
    config.attributes["database_url"] = get_settings().database_url
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest.fixture(scope="module", autouse=True)
def database():
    _migrate_fresh()


@pytest.fixture
async def api():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await engine.dispose()


@pytest.fixture
def simulador(monkeypatch):
    """La plataforma habla con la PTZ simulada como si fuera de red."""

    def cliente(camera):
        return IsapiClient(
            IsapiTarget(
                host=camera.host, port=camera.http_port, username="admin", password="simulada"
            ),
            transport=httpx.ASGITransport(app=crear_app(PROFILES["ptz"])),
        )

    monkeypatch.setattr(targets, "isapi_client", cliente)
    return cliente


async def _alta_ptz_simulada(api, nombre: str = "PTZ simulada") -> uuid.UUID:
    respuesta = await api.post(
        "/api/cameras",
        json={
            "name": nombre,
            "host": "127.0.0.1",
            "http_port": 8101,
            "onvif_port": 9,  # puerto sin nada escuchando: ONVIF falla rápido, no cuelga
            "username": "admin",
            "password": "x",
        },
    )
    assert respuesta.status_code == 201
    return uuid.UUID(respuesta.json()["id"])


async def test_corre_n_repeticiones_y_las_marca_con_el_experiment_id(api, simulador):
    camera_id = await _alta_ptz_simulada(api)

    async with SessionLocal() as session:
        camera = await session.get(Camera, camera_id)
        experimento = await run_experiment(session, [camera], repeticiones=3, log=lambda *_: None)

        resultado = experimento.resultados[0]
        assert resultado.isapi_alcanzable is True
        assert resultado.onvif_alcanzable is False  # nada escucha en el puerto 9

        filas = list(
            await session.scalars(
                select(OperationLog).where(
                    OperationLog.experiment_id == experimento.experiment_id,
                    OperationLog.protocol == "isapi",
                    OperationLog.capability_code == "device.info",
                )
            )
        )
        # 3 repeticiones pedidas -> 3 filas, todas con el mismo experiment_id.
        assert len(filas) == 3
        assert all(f.success for f in filas)
        assert all(f.latency_ms is not None and f.latency_ms >= 0 for f in filas)


async def test_agregar_calcula_tasa_de_exito_y_percentiles(api, simulador):
    camera_id = await _alta_ptz_simulada(api, "PTZ para agregación")

    async with SessionLocal() as session:
        camera = await session.get(Camera, camera_id)
        experimento = await run_experiment(session, [camera], repeticiones=5, log=lambda *_: None)
        estadisticas = await agregar(session, experimento.experiment_id)

    por_funcion = {(e.capability_code, e.protocol): e for e in estadisticas}
    info = por_funcion[("device.info", "isapi")]
    assert info.n == 5
    assert info.exitos == 5
    assert info.tasa_exito == 1.0
    assert info.latencia_p50_ms >= 0
    assert info.latencia_p95_ms >= info.latencia_p50_ms
    assert info.camera_name == "PTZ para agregación"

    # ONVIF no respondió: no hay filas en operation_logs para ese protocolo en este experimento.
    assert ("device.info", "onvif") not in por_funcion


async def test_dos_experimentos_no_se_mezclan(api, simulador):
    camera_id = await _alta_ptz_simulada(api, "PTZ repetida")

    async with SessionLocal() as session:
        camera = await session.get(Camera, camera_id)
        primero = await run_experiment(session, [camera], repeticiones=2, log=lambda *_: None)
        segundo = await run_experiment(session, [camera], repeticiones=4, log=lambda *_: None)

        stats_primero = await agregar(session, primero.experiment_id)
        stats_segundo = await agregar(session, segundo.experiment_id)

    n_primero = next(e.n for e in stats_primero if e.capability_code == "device.info")
    n_segundo = next(e.n for e in stats_segundo if e.capability_code == "device.info")
    assert n_primero == 2
    assert n_segundo == 4
