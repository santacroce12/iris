"""Integración real contra Postgres (base camaras_test). Requiere `docker compose up db`."""

import asyncio
import socket
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine
from app.main import app

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


def _closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def test_create_camera_never_exposes_password(api):
    response = await api.post(
        "/api/cameras",
        json={"name": "Entrada", "host": "10.0.0.5", "username": "admin", "password": "Hik12345"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "unknown"
    assert "Hik12345" not in response.text
    assert "secret_enc" not in body

    listed = await api.get("/api/cameras")
    assert [c["name"] for c in listed.json()] == ["Entrada"]


async def test_connection_test_offline_camera_records_matrix_and_log(api):
    port = _closed_port()
    created = await api.post(
        "/api/cameras",
        json={
            "name": "Apagada",
            "host": "127.0.0.1",
            "http_port": port,
            "rtsp_port": port,
            "onvif_port": port,
            "username": "admin",
            "password": "x",
        },
    )
    camera_id = created.json()["id"]

    report = (await api.post(f"/api/cameras/{camera_id}/connection-test")).json()
    assert report["status"] == "offline"
    assert {report[p]["error_code"] for p in ("isapi", "onvif", "rtsp")} == {"unreachable"}

    capabilities = (await api.get(f"/api/cameras/{camera_id}/capabilities")).json()
    assert {(c["capability_code"], c["protocol"], c["level"]) for c in capabilities} == {
        ("device.info", "isapi", "error"),
        ("device.info", "onvif", "error"),
        ("media.live", "rtsp", "error"),
    }
    operations = (await api.get(f"/api/cameras/{camera_id}/operations")).json()
    assert len(operations) == 3 and not any(o["success"] for o in operations)


async def test_unknown_camera_is_404(api):
    response = await api.get("/api/cameras/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
