"""Motor de capacidades y matriz, contra la cámara simulada.

Es la comparación que pide el anteproyecto: para cada función, qué contesta cada protocolo y
si eso se sabe porque la cámara lo declara o porque se llamó de verdad.
"""

import asyncio
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine
from app.drivers.isapi.client import IsapiClient, IsapiTarget
from app.main import app
from app.services import targets
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
    """La plataforma habla con la cámara simulada como si fuera una cámara de la red."""

    def cliente(camera):
        perfil = PROFILES["ptz" if camera.http_port == 8101 else "basica"]
        return IsapiClient(
            IsapiTarget(
                host=camera.host, port=camera.http_port, username="admin", password="simulada"
            ),
            transport=httpx.ASGITransport(app=crear_app(perfil)),
        )

    monkeypatch.setattr(targets, "isapi_client", cliente)
    return cliente


async def _alta(api, nombre: str, puerto: int) -> str:
    respuesta = await api.post(
        "/api/cameras",
        json={
            "name": nombre,
            "host": "127.0.0.1",
            "http_port": puerto,
            # Un puerto ONVIF cerrado: la detección tiene que marcarlo "sin verificar".
            "onvif_port": 9,
            "username": "admin",
            "password": "simulada",
        },
    )
    return respuesta.json()["id"]


def _celdas(fila: dict, camera_id: str) -> dict[str, dict]:
    return {c["protocol"]: c for c in fila["cells"] if c["camera_id"] == camera_id}


def _fila(matriz: dict, code: str) -> dict:
    return next(f for f in matriz["rows"] if f["code"] == code)


async def test_detecta_y_llena_la_matriz(api, simulador):
    camera_id = await _alta(api, "PTZ simulada", 8101)

    respuesta = await api.post(f"/api/cameras/{camera_id}/capabilities/detect")
    assert respuesta.status_code == 202

    matriz = (await api.get("/api/matrix")).json()
    assert camera_id in [c["id"] for c in matriz["cameras"]]

    hora = _celdas(_fila(matriz, "system.time"), camera_id)
    assert hora["isapi"]["level"] == "supported"
    assert hora["isapi"]["source"] == "verified"  # se llamó, no se creyó
    assert hora["isapi"]["latency_ms"] is not None

    imagen = _celdas(_fila(matriz, "video.image"), camera_id)
    assert imagen["isapi"]["level"] == "supported"


async def test_sin_onvif_queda_sin_verificar_no_sin_soporte(api, simulador):
    """No poder preguntar no es lo mismo que la función no exista: la matriz los distingue."""
    camera_id = await _alta(api, "PTZ simulada 2", 8101)
    await api.post(f"/api/cameras/{camera_id}/capabilities/detect")

    matriz = (await api.get("/api/matrix")).json()
    celdas = _celdas(_fila(matriz, "system.time"), camera_id)
    assert celdas["onvif"]["level"] == "unverified"
    assert celdas["onvif"]["evidence"]["error"] in {"unreachable", "auth_failed"}


async def test_el_reinicio_no_se_prueba(api, simulador):
    """Marcarlo 'soportado' sin llamarlo sería justo lo que este trabajo critica."""
    camera_id = await _alta(api, "PTZ simulada 3", 8101)
    await api.post(f"/api/cameras/{camera_id}/capabilities/detect")

    matriz = (await api.get("/api/matrix")).json()
    celda = _celdas(_fila(matriz, "system.reboot"), camera_id)["isapi"]
    assert celda["level"] == "unverified"
    assert "interrumpe el servicio" in celda["evidence"]["motivo"]


async def test_un_modelo_basico_no_tiene_todo(api, simulador):
    """La cámara de gama baja no expone OSD ni imagen: tiene que decir 'no soportada'."""
    camera_id = await _alta(api, "Value simulada", 8102)
    await api.post(f"/api/cameras/{camera_id}/capabilities/detect")

    matriz = (await api.get("/api/matrix")).json()
    assert _celdas(_fila(matriz, "video.osd"), camera_id)["isapi"]["level"] == "unsupported"
    assert _celdas(_fila(matriz, "video.image"), camera_id)["isapi"]["level"] == "unsupported"
    # pero la hora sí la tiene
    assert _celdas(_fila(matriz, "system.time"), camera_id)["isapi"]["level"] == "supported"


async def test_leer_las_funciones_comunes(api, simulador):
    camera_id = await _alta(api, "PTZ funciones", 8101)

    cuerpo = (await api.get(f"/api/cameras/{camera_id}/functions")).json()
    assert cuerpo["protocol"] == "isapi"
    assert cuerpo["time"]["timezone"] == "CST-8:00:00"
    assert cuerpo["osd"]["name"] == "Entrada"
    assert cuerpo["image"]["brightness"] == 50
    assert cuerpo["status"]["cpu_percent"] == 17


async def test_escribir_una_funcion_comun(api, simulador):
    camera_id = await _alta(api, "PTZ escritura", 8101)

    respuesta = await api.patch(
        f"/api/cameras/{camera_id}/functions/image", json={"brightness": 72}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["brightness"] == 72


async def test_el_reinicio_exige_confirmacion(api, simulador):
    camera_id = await _alta(api, "PTZ reinicio", 8101)

    sin_confirmar = await api.post(f"/api/cameras/{camera_id}/functions/reboot")
    assert sin_confirmar.status_code == 422

    confirmado = await api.post(f"/api/cameras/{camera_id}/functions/reboot?confirm=true")
    assert confirmado.status_code == 200
