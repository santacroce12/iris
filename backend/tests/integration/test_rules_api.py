"""La API de reglas contra una cámara simulada con las respuestas reales de la PTZ.

Prueba el camino completo: leer → escribir → releer y verificar, incluido el caso en el que la
cámara responde 200 OK y no aplica nada (lo que hace de verdad la DS-2DF8A836IX-AEL).
"""

import asyncio
import re
import uuid
from pathlib import Path

import httpx
import pytest
import respx
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.db.models import ConfigBackup
from app.main import app

BACKEND = Path(__file__).resolve().parents[2]
PTZ = BACKEND / "tests/fixtures/hikvision/DS-2DF8A836IX-AEL/V5.6.0"
HOST = "http://10.0.0.77"
OK = (
    b'<?xml version="1.0" encoding="UTF-8"?><ResponseStatus>'
    b"<statusCode>1</statusCode><statusString>OK</statusString></ResponseStatus>"
)


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
async def camera_id(api):
    response = await api.post(
        "/api/cameras",
        json={"name": "PTZ simulada", "host": "10.0.0.77", "username": "admin", "password": "x"},
    )
    return response.json()["id"]


class CamaraFalsa:
    """Responde como la PTZ: la lista miente y solo el recurso individual se puede escribir."""

    def __init__(self, *, aplica_la_escritura: bool = True) -> None:
        self.items = {
            "1": (PTZ / "smartLineDetectionItem1.xml").read_text(),
            "2": (PTZ / "smartLineDetectionItem2.xml").read_text(),
        }
        self.aplica_la_escritura = aplica_la_escritura
        self.escrituras: list[str] = []

    def montar(self, mock: respx.MockRouter) -> None:
        # El domo tiene AI Open Platform; la PTZ no: responde 403 notSupport.
        mock.get(url__startswith=f"{HOST}/ISAPI/Intelligent/AIOpenPlatform").respond(
            403,
            content=b"<ResponseStatus><subStatusCode>notSupport</subStatusCode></ResponseStatus>",
        )
        # La PTZ está en modo de VCA `smart`, así que rechaza la familia de parking igual que
        # rechaza AI Open Platform (verificado contra la bullet, que hace lo simétrico).
        mock.get(url__startswith=f"{HOST}/ISAPI/Parking").respond(
            403,
            content=b"<ResponseStatus><subStatusCode>notSupport</subStatusCode></ResponseStatus>",
        )
        for tipo in ("FieldDetection", "regionEntrance", "regionExiting"):
            mock.get(url__startswith=f"{HOST}/ISAPI/Smart/{tipo}/1").respond(
                403,
                content=b"<ResponseStatus><subStatusCode>notSupport</subStatusCode></ResponseStatus>",
            )
        mock.get(f"{HOST}/ISAPI/Smart/LineDetection/1").respond(
            200, content=(PTZ / "smartLineDetection.xml").read_bytes()
        )
        mock.get(f"{HOST}/ISAPI/Smart/LineDetection/1/capabilities").respond(
            200, content=(PTZ / "smartLineDetectionCapabilities.xml").read_bytes()
        )
        mock.route(
            method="GET",
            url__regex=rf"{re.escape(HOST)}/ISAPI/Smart/LineDetection/1/lineItem/\d+",
        ).mock(side_effect=self._leer_item)
        mock.route(
            method="PUT",
            url__regex=rf"{re.escape(HOST)}/ISAPI/Smart/LineDetection/1/lineItem/\d+",
        ).mock(side_effect=self._escribir_item)

    def _rule_id(self, request: httpx.Request) -> str:
        return request.url.path.rsplit("/", 1)[-1]

    def _leer_item(self, request: httpx.Request) -> httpx.Response:
        rule = self._rule_id(request)
        if rule not in self.items:
            return httpx.Response(
                403,
                content=b"<ResponseStatus><subStatusCode>notSupport</subStatusCode></ResponseStatus>",
            )
        return httpx.Response(200, content=self.items[rule].encode())

    def _escribir_item(self, request: httpx.Request) -> httpx.Response:
        rule = self._rule_id(request)
        self.escrituras.append(rule)
        if self.aplica_la_escritura:
            self.items[rule] = request.content.decode()
        return httpx.Response(200, content=OK)  # la cámara siempre dice que sí


async def test_leer_reglas(api, camera_id):
    camara = CamaraFalsa()
    with respx.mock(assert_all_called=False) as mock:
        camara.montar(mock)
        response = await api.get(f"/api/cameras/{camera_id}/rules")

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["family"] == "smart"
    assert [k["kind"] for k in cuerpo["kinds"]] == ["line"]
    assert cuerpo["kinds"][0]["toggle_per_rule"] is False

    reglas = {r["external_id"]: r for r in cuerpo["rules"]}
    # La lista devolvía las 4 vacías; el recurso individual trae la geometría de verdad.
    assert reglas["2"]["configured"] is True
    assert [[round(x, 3), round(y, 3)] for x, y in reglas["2"]["points"]] == [
        [0.349, 0.44],
        [0.619, 0.44],
    ]
    assert reglas["3"]["configured"] is False


async def test_escribir_y_verificar(api, camera_id):
    camara = CamaraFalsa()
    with respx.mock(assert_all_called=False) as mock:
        camara.montar(mock)
        response = await api.patch(
            f"/api/cameras/{camera_id}/rules/line/1",
            json={"points": [[0.2, 0.8], [0.9, 0.3]], "sensitivity": 70},
        )

    assert response.status_code == 200
    regla = response.json()
    assert [[round(x, 3), round(y, 3)] for x, y in regla["points"]] == [
        [0.2, 0.8],
        [0.9, 0.3],
    ]
    assert regla["sensitivity"] == 70
    assert camara.escrituras == ["1"]
    # El eje vertical se invierte al bajar a la cámara: 0.8 arriba -> 200 en ISAPI.
    assert "<positionY>200</positionY>" in camara.items["1"]

    respaldos = (await api.get(f"/api/cameras/{camera_id}/backups")).json()
    assert respaldos[0]["resource"] == "/ISAPI/Smart/LineDetection/1/lineItem/1"
    # El respaldo tiene que guardar la geometría vieja, no la nueva.
    async with SessionLocal() as session:
        guardado = await session.get(ConfigBackup, uuid.UUID(respaldos[0]["id"]))
        assert guardado is not None
        assert "<positionY>500</positionY>" in guardado.content


async def test_la_camara_dice_ok_y_no_aplica(api, camera_id):
    camara = CamaraFalsa(aplica_la_escritura=False)
    with respx.mock(assert_all_called=False) as mock:
        camara.montar(mock)
        response = await api.patch(
            f"/api/cameras/{camera_id}/rules/line/1",
            json={"points": [[0.2, 0.8], [0.9, 0.3]]},
        )

    assert response.status_code == 502
    assert response.json()["error_code"] == "verification_failed"
    assert "geometría" in response.json()["message"]


async def test_regla_inexistente(api, camera_id):
    camara = CamaraFalsa()
    with respx.mock(assert_all_called=False) as mock:
        camara.montar(mock)
        response = await api.patch(
            f"/api/cameras/{camera_id}/rules/line/9", json={"sensitivity": 50}
        )

    assert response.status_code == 422
    assert response.json()["error_code"] == "not_supported"
