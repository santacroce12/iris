"""Contratos de aceptación de la auditoría del 01/10/2026.

Los fallos son defectos del producto por corregir, no xfails silenciados.
Usa solamente camaras_test; nunca hace escrituras contra hardware.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
import respx
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.db.models import Camera, CapabilityCheck, ConfigBackup, VideoProfile
from app.domain.enums import CapabilitySource, Protocol, SupportLevel
from app.main import app
from app.services.capabilities import record_check
from tests.integration.test_rules_api import CamaraFalsa

BACKEND = Path(__file__).resolve().parents[2]
PTZ = BACKEND / "tests/fixtures/hikvision/DS-2DF8A836IX-AEL/V5.6.0"
HOST = "http://10.0.0.77"
OK = b"<ResponseStatus><statusCode>1</statusCode><statusString>OK</statusString></ResponseStatus>"
pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module", autouse=True)
def database():
    assert make_url(get_settings().database_url).database == "camaras_test", "QA exige camaras_test"

    async def reset():
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(reset())
    config = Config(BACKEND / "alembic.ini")
    config.attributes["database_url"] = get_settings().database_url
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest_asyncio.fixture(loop_scope="module")
async def api():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield client
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="module")
async def camera_id(api):
    response = await api.post(
        "/api/cameras",
        json={"name": "QA contrato", "host": "10.0.0.77", "username": "admin", "password": "qa"},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize(
    "patch",
    [{"name": ""}, {"host": ""}, {"username": ""}, {"name": "x" * 121}, {"host": "x" * 256}],
)
async def test_patch_rejects_invalid_camera_fields_before_commit(api, camera_id, patch):
    response = await api.patch(f"/api/cameras/{camera_id}", json=patch)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("field", ["name", "host", "username"])
async def test_create_rejects_whitespace_only_fields(api, field):
    data = {"name": "QA", "host": "127.0.0.1", "username": "admin", "password": "qa"}
    data[field] = "   "
    response = await api.post("/api/cameras", json=data)
    assert response.status_code == 422, response.text


async def test_operations_limit_negative_is_validation_error(api, camera_id):
    response = await api.get(f"/api/cameras/{camera_id}/operations?limit=-1")
    assert response.status_code == 422, response.text


async def test_connection_edit_invalidates_previous_evidence_and_profiles(api, camera_id):
    async with SessionLocal() as session:
        await record_check(
            session,
            camera_id=uuid.UUID(camera_id),
            code="device.info",
            protocol=Protocol.ISAPI,
            level=SupportLevel.SUPPORTED,
            source=CapabilitySource.VERIFIED,
        )
        session.add(
            VideoProfile(
                camera_id=uuid.UUID(camera_id),
                protocol="isapi",
                token="101",
                stream_type="main",
                codec="H.264",
                rtsp_path="/old-device",
            )
        )
        await session.commit()
    with respx.mock:
        respx.delete(url__startswith="http://localhost:9997/").respond(404)
        response = await api.patch(f"/api/cameras/{camera_id}", json={"host": "10.0.0.88"})
    assert response.status_code == 200
    checks = (await api.get(f"/api/cameras/{camera_id}/capabilities")).json()
    profiles = (await api.get(f"/api/cameras/{camera_id}/profiles")).json()
    assert not any(c["level"] == "supported" for c in checks) and not profiles, (checks, profiles)


async def test_false_capability_flag_is_not_declared_supported(camera_id):
    from app.drivers.isapi.client import IsapiClient, IsapiTarget
    from app.services.detection import _declaradas_isapi

    with respx.mock:
        respx.get(HOST + "/ISAPI/System/capabilities").respond(
            200, content=b"<Capabilities><isSupportSmart>false</isSupportSmart></Capabilities>"
        )
        async with (
            SessionLocal() as session,
            IsapiClient(IsapiTarget("10.0.0.77", 80, "admin", "qa")) as client,
        ):
            camera = await session.get(Camera, uuid.UUID(camera_id))
            await _declaradas_isapi(session, camera, client)
            await session.commit()
            check = await session.scalar(
                select(CapabilityCheck).where(
                    CapabilityCheck.camera_id == camera.id,
                    CapabilityCheck.capability_code == "analytics.rules",
                )
            )
            assert check.level != "supported", check.evidence


async def test_rule_failure_keeps_backup_and_operation_log(api, camera_id):
    with respx.mock as mock:
        CamaraFalsa(aplica_la_escritura=False).montar(mock)
        response = await api.patch(
            f"/api/cameras/{camera_id}/rules/line/1", json={"points": [[0.1, 0.2], [0.8, 0.9]]}
        )
    assert response.status_code == 502 and response.json()["error_code"] == "verification_failed"
    backups = (await api.get(f"/api/cameras/{camera_id}/backups")).json()
    operations = (await api.get(f"/api/cameras/{camera_id}/operations")).json()
    assert backups and operations, {"backups": backups, "operations": operations}


async def test_failed_restore_is_not_reported_as_success(api, camera_id):
    from app.domain.rules import RuleKind, RuleUpdate
    from app.drivers.isapi.rules import smart

    different = smart.build_item_xml(
        (PTZ / "smartLineDetectionItem1.xml").read_text(),
        smart.BY_KIND[RuleKind.LINE],
        RuleUpdate(points=[(0.11, 0.22), (0.77, 0.88)]),
    )
    async with SessionLocal() as session:
        backup = ConfigBackup(
            camera_id=uuid.UUID(camera_id),
            resource="/ISAPI/Smart/LineDetection/1/lineItem/1",
            content=different,
            content_type="application/xml",
        )
        session.add(backup)
        await session.commit()
        bid = backup.id
    with respx.mock as mock:
        CamaraFalsa(aplica_la_escritura=False).montar(mock)
        response = await api.post(f"/api/cameras/{camera_id}/backups/{bid}/restore")
    # Un 200 de la cámara no basta: la restauración también debe releer/comparar.
    assert response.status_code == 502, f"restore informó {response.status_code} sin verificar"


@pytest.mark.parametrize(
    "resource,fixture,patch",
    [
        ("image", "imageColor.xml", {"brightness": 31}),
        ("osd", "overlays.xml", {"show_date": False}),
        ("motion", "motionDetection.xml", {"sensitivity": 31}),
    ],
)
async def test_common_write_detects_camera_ignoring_change(
    api, camera_id, resource, fixture, patch
):
    paths = {
        "image": "/ISAPI/Image/channels/1/color",
        "osd": "/ISAPI/System/Video/inputs/channels/1/overlays",
        "motion": "/ISAPI/System/Video/inputs/channels/1/motionDetection",
    }
    with respx.mock:
        respx.get(HOST + paths[resource]).respond(200, content=(PTZ / fixture).read_bytes())
        respx.put(HOST + paths[resource]).respond(200, content=OK)
        response = await api.patch(f"/api/cameras/{camera_id}/functions/{resource}", json=patch)
    assert response.status_code == 502, response.text


async def test_common_write_saves_backup_and_log(api, camera_id):
    content = (PTZ / "imageColor.xml").read_bytes()
    with respx.mock:
        respx.get(HOST + "/ISAPI/Image/channels/1/color").respond(200, content=content)
        respx.put(HOST + "/ISAPI/Image/channels/1/color").respond(200, content=OK)
        response = await api.patch(
            f"/api/cameras/{camera_id}/functions/image", json={"brightness": 50}
        )
    assert response.status_code == 200
    backups = (await api.get(f"/api/cameras/{camera_id}/backups")).json()
    operations = (await api.get(f"/api/cameras/{camera_id}/operations")).json()
    assert backups and operations, {"backups": backups, "operations": operations}


async def test_invalid_rule_geometry_is_rejected_before_camera_write(api, camera_id):
    fake = CamaraFalsa()
    with respx.mock as mock:
        fake.montar(mock)
        response = await api.patch(
            f"/api/cameras/{camera_id}/rules/line/1", json={"points": [[-3, 7], [2, -1]]}
        )
    assert response.status_code == 422 and not fake.escrituras, (
        response.status_code,
        len(fake.escrituras),
    )


async def test_invalid_line_point_count_is_rejected(api, camera_id):
    fake = CamaraFalsa()
    with respx.mock as mock:
        fake.montar(mock)
        response = await api.patch(
            f"/api/cameras/{camera_id}/rules/line/1",
            json={"points": [[0.2, 0.3], [0.7, 0.8], [0.4, 0.6]]},
        )
    assert response.status_code == 422 and not fake.escrituras, (
        response.status_code,
        len(fake.escrituras),
    )


@pytest.mark.parametrize(
    "path", ["functions", "functions/time/sync", "functions/reboot?confirm=true"]
)
async def test_rtsp_is_not_accepted_as_system_protocol(api, camera_id, path, monkeypatch):
    calls = []

    @asynccontextmanager
    async def forbidden_onvif(target):
        from app.drivers.errors import NotSupported

        calls.append(target)
        if calls:
            raise NotSupported("QA: se invocó ONVIF para un pedido RTSP")
        yield None

    monkeypatch.setattr("app.api.functions.onvif_session", forbidden_onvif)
    suffix = "&protocol=rtsp" if "?" in path else "?protocol=rtsp"
    with respx.mock:
        response = await api.request(
            "GET" if path == "functions" else "POST", f"/api/cameras/{camera_id}/{path}{suffix}"
        )
    assert response.status_code == 422 and not calls, (response.text, len(calls))


async def test_nonexistent_event_media_is_404(api):
    response = await api.get(f"/api/events/{uuid.uuid4()}/media/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.parametrize("query", ["limit=0", "limit=501", "since=foo", "camera_id=no-uuid"])
async def test_event_filter_validation(api, query):
    response = await api.get("/api/events?" + query)
    assert response.status_code == 422


async def test_reboot_needs_explicit_confirmation(api, camera_id):
    response = await api.post(f"/api/cameras/{camera_id}/functions/reboot")
    assert response.status_code == 422


async def test_opening_live_does_not_disable_active_recording(api, camera_id):
    configuration = {"record": True, "sourceOnDemand": False}

    def publish(request):
        import json

        configuration.update(json.loads(request.content))
        return httpx.Response(200, json={})

    with respx.mock:
        respx.post(url__startswith="http://localhost:9997/v3/config/paths/replace/").mock(
            side_effect=publish
        )
        response = await api.post(f"/api/cameras/{camera_id}/live")
    assert response.status_code == 200
    assert configuration["record"] is True, configuration


async def test_delete_camera_stops_its_listener(api, camera_id):
    from app.engine.event_hub import CameraListener, hub

    cid = uuid.UUID(camera_id)
    hub.listeners[cid] = CameraListener(cid)
    try:
        with respx.mock:
            respx.delete(url__startswith="http://localhost:9997/").respond(404)
            response = await api.delete(f"/api/cameras/{camera_id}")
        assert response.status_code == 204
        assert cid not in hub.listeners
    finally:
        hub.listeners.pop(cid, None)


async def test_osd_name_with_ampersand_produces_valid_xml(api, camera_id):
    from defusedxml import ElementTree

    sent = []
    content = (
        b"<VideoOverlay><channelNameOverlay><enabled>true</enabled>"
        b"<name>Entrada</name></channelNameOverlay></VideoOverlay>"
    )

    def save(request):
        sent.append(request.content)
        return httpx.Response(200, content=OK)

    with respx.mock:
        respx.get(HOST + "/ISAPI/System/Video/inputs/channels/1/overlays").respond(
            200, content=content
        )
        respx.put(HOST + "/ISAPI/System/Video/inputs/channels/1/overlays").mock(side_effect=save)
        await api.patch(f"/api/cameras/{camera_id}/functions/osd", json={"name": "Entrada & Patio"})
    root = ElementTree.fromstring(sent[0])
    assert root.find("channelNameOverlay/name").text == "Entrada & Patio"
