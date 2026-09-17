"""Integración real contra Postgres (base camaras_test). Requiere `docker compose up db`."""

import asyncio
import socket
import uuid
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.security import decrypt
from app.db.models import Camera
from app.domain.enums import CameraStatus
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


async def _stored_camera(camera_id: str) -> Camera:
    async with SessionLocal() as session:
        return await session.get(Camera, uuid.UUID(camera_id))


async def test_update_rename_keeps_credentials_and_status(api):
    created = (
        await api.post(
            "/api/cameras",
            json={"name": "Vieja", "host": "10.0.0.9", "username": "admin", "password": "Hik1"},
        )
    ).json()
    await _set_status(created["id"], CameraStatus.ONLINE)

    # Contraseña vacía y campos obligatorios en null = no tocar nada de eso.
    response = await api.patch(
        f"/api/cameras/{created['id']}",
        json={"name": "Nueva", "password": "", "host": None},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["host"], body["status"]) == ("Nueva", "10.0.0.9", "online")

    stored = await _stored_camera(created["id"])
    assert decrypt(stored.secret_enc) == "Hik1"


async def test_update_connection_data_resets_status_and_rotates_secrets(api):
    created = (
        await api.post(
            "/api/cameras",
            json={
                "name": "Domo",
                "host": "10.0.0.10",
                "username": "admin",
                "password": "Hik1",
                "onvif_username": "onvif",
                "onvif_password": "Onv1",
            },
        )
    ).json()
    await _set_status(created["id"], CameraStatus.ONLINE)

    response = await api.patch(
        f"/api/cameras/{created['id']}",
        json={"host": "10.0.0.11", "network_mode": "vpn", "password": "Hik2"},
    )
    body = response.json()
    assert (body["host"], body["network_mode"], body["status"]) == ("10.0.0.11", "vpn", "unknown")
    assert "Hik2" not in response.text

    stored = await _stored_camera(created["id"])
    assert decrypt(stored.secret_enc) == "Hik2"
    assert decrypt(stored.onvif_secret_enc) == "Onv1"

    # Vaciar el usuario ONVIF vuelve a usar las credenciales principales.
    await api.patch(f"/api/cameras/{created['id']}", json={"onvif_username": ""})
    stored = await _stored_camera(created["id"])
    assert (stored.onvif_username, stored.onvif_secret_enc) == (None, None)


async def _set_status(camera_id: str, status: CameraStatus) -> None:
    async with SessionLocal() as session:
        camera = await session.get(Camera, uuid.UUID(camera_id))
        camera.status = status
        await session.commit()


async def test_unknown_camera_is_404(api):
    response = await api.get("/api/cameras/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
