"""Fotos en los eventos, replanteado (bitácora §6.6, PENDIENTES.md).

Al menos la PTZ no tiene forma de adjuntar su propia foto al alertStream. En vez de eso, si el
aviso que abre un episodio no trajo ninguna imagen, `CameraListener` pide su propio snapshot antes
de guardar el episodio. Se prueba `_snapshot_on_open` directamente: es el método nuevo, y probarlo
aislado evita tener que levantar un alertStream completo para algo que no depende de él.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
import respx
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

import app.engine.event_hub as event_hub_module
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.security import encrypt
from app.db.models import Camera, EventMedia
from app.domain.enums import CameraStatus
from app.domain.events import ParsedAlert
from app.engine.episodes import Episode
from app.engine.event_hub import CameraListener

BACKEND = Path(__file__).resolve().parents[2]
HOST = "10.0.0.90"


@dataclass
class _FakeSettings:
    """Solo lo que `_save_pictures` necesita de `get_settings()`: dónde escribir los archivos.
    Apunta a `tmp_path` para no dejar fotos de prueba en `backend/media/`."""

    media_dir: Path


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
async def session():
    async with SessionLocal() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def camera_id(session) -> uuid.UUID:
    camara = Camera(
        name="Cámara de prueba",
        host=HOST,
        http_port=80,
        username="admin",
        secret_enc=encrypt("x"),
        channel=1,
        status=CameraStatus.ONLINE,
    )
    session.add(camara)
    await session.commit()
    return camara.id


def _episodio(camera_id: uuid.UUID) -> Episode:
    alerta = ParsedAlert(
        raw_type="linedetection",
        type="line_crossing",
        state="active",
        channel=1,
        occurred_at=datetime(2026, 9, 29, 12, 0, 0, tzinfo=UTC),
        rule_ref="1",
    )
    return Episode(
        camera_id=camera_id,
        key=alerta.episode_key(),
        alert=alerta,
        started_at=alerta.occurred_at,
        last_alert_at=alerta.occurred_at,
    )


async def test_pide_su_propio_snapshot_si_no_llego_ninguna_foto(session, camera_id):
    episodio = _episodio(camera_id)
    assert episodio.pictures == []

    listener = CameraListener(camera_id)
    with respx.mock(assert_all_called=True) as mock:
        mock.get(f"http://{HOST}/ISAPI/Streaming/channels/101/picture").respond(
            200,
            content=b"\xff\xd8\xff-una-foto-jpg-de-mentira",
            headers={"content-type": "image/jpeg"},
        )
        await listener._snapshot_on_open(session, episodio)

    assert len(episodio.pictures) == 1
    mime, contenido = episodio.pictures[0]
    assert mime == "image/jpeg"
    assert contenido.startswith(b"\xff\xd8\xff")


async def test_persist_no_pide_snapshot_si_la_camara_ya_mando_una_foto(
    session, camera_id, monkeypatch, tmp_path
):
    """El guardado completo (`_persist`), no el método nuevo aislado: cuando el aviso que abre el
    episodio ya trae una foto de la propia cámara, no hay que pedir ninguna de más."""
    monkeypatch.setattr(event_hub_module, "get_settings", lambda: _FakeSettings(tmp_path))

    episodio = _episodio(camera_id)
    episodio.pictures.append(("image/jpeg", b"ya-vino-adjunta-en-el-alertstream"))
    listener = CameraListener(camera_id)

    with respx.mock(assert_all_called=False) as mock:
        ruta = mock.get(f"http://{HOST}/ISAPI/Streaming/channels/101/picture").respond(200)
        await listener._persist(session, episodio, es_nuevo=True)
        await session.commit()

    assert ruta.call_count == 0  # nunca se llamó: ya había una foto
    guardadas = (
        await session.scalars(select(EventMedia).where(EventMedia.event_id == episodio.event_id))
    ).all()
    assert len(guardadas) == 1
    assert (
        tmp_path / str(camera_id) / f"{episodio.event_id}-0.jpg"
    ).read_bytes() == b"ya-vino-adjunta-en-el-alertstream"


async def test_persist_completo_pide_snapshot_y_lo_guarda_en_disco(
    session, camera_id, monkeypatch, tmp_path
):
    """Punta a punta: episodio sin fotos → `_persist` pide el snapshot → queda un `EventMedia`
    real y el archivo aparece en disco, no solo un registro en la base."""
    monkeypatch.setattr(event_hub_module, "get_settings", lambda: _FakeSettings(tmp_path))

    episodio = _episodio(camera_id)
    listener = CameraListener(camera_id)

    with respx.mock(assert_all_called=True) as mock:
        mock.get(f"http://{HOST}/ISAPI/Streaming/channels/101/picture").respond(
            200, content=b"\xff\xd8\xff-snapshot-real", headers={"content-type": "image/jpeg"}
        )
        await listener._persist(session, episodio, es_nuevo=True)
        await session.commit()

    assert episodio.event_id is not None
    archivo = tmp_path / str(camera_id) / f"{episodio.event_id}-0.jpg"
    assert archivo.exists()
    assert archivo.read_bytes() == b"\xff\xd8\xff-snapshot-real"


async def test_si_la_camara_no_responde_no_rompe_el_episodio(session, camera_id):
    episodio = _episodio(camera_id)

    listener = CameraListener(camera_id)
    with respx.mock(assert_all_called=True) as mock:
        mock.get(f"http://{HOST}/ISAPI/Streaming/channels/101/picture").respond(
            403,
            content=b"<ResponseStatus><subStatusCode>notSupport</subStatusCode></ResponseStatus>",
        )
        # No debe propagar la excepción: un snapshot fallido no puede tirar abajo el guardado
        # del episodio en sí, que es lo que sí importa.
        await listener._snapshot_on_open(session, episodio)

    assert episodio.pictures == []


async def test_camara_borrada_no_rompe_nada(session):
    episodio = _episodio(uuid.uuid4())  # cámara que no existe en la base
    listener = CameraListener(episodio.camera_id)
    await listener._snapshot_on_open(session, episodio)
    assert episodio.pictures == []
