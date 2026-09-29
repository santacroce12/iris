"""El simulador tiene que mentir igual que la cámara real, o no sirve para probar nada."""

import httpx
import pytest

from app.domain.rules import RuleKind, RuleUpdate
from app.drivers.isapi.client import IsapiClient, IsapiTarget
from app.drivers.isapi.rules import smart
from app.drivers.isapi.rules.smart import SmartRulesDriver
from tools.simulator.alerts import Emisor, alerta_xml
from tools.simulator.camera import crear_app
from tools.simulator.profiles import PROFILES

LINEA = smart.BY_KIND[RuleKind.LINE]


@pytest.fixture
def perfil():
    return PROFILES["ptz"]


def _cliente(perfil) -> IsapiClient:
    """Un IsapiClient real hablando con el simulador, sin red de por medio."""
    target = IsapiTarget(host="sim", port=80, username="admin", password="simulada")
    return IsapiClient(target, transport=httpx.ASGITransport(app=crear_app(perfil)))


@pytest.fixture
async def client(perfil):
    async with _cliente(perfil) as isapi:
        yield isapi


async def test_pide_autenticacion(perfil):
    app = crear_app(perfil)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://sim") as sin_auth:
        respuesta = await sin_auth.get("/ISAPI/System/deviceInfo")
    assert respuesta.status_code == 401
    assert "Digest" in respuesta.headers["www-authenticate"]


async def test_identidad_dice_que_es_simulada(client, perfil):
    respuesta = await client.get("/ISAPI/System/deviceInfo")
    assert perfil.model.encode() in respuesta.content
    assert b"SIMULADA" in respuesta.content


async def test_la_lista_de_reglas_miente(client):
    """Como la PTZ: la colección devuelve (0,1000) para reglas que sí tienen geometría."""
    driver = SmartRulesDriver(client, 1)
    _, desde_la_lista = smart.parse_rules(
        (await client.get("/ISAPI/Smart/LineDetection/1")).content, LINEA
    )
    assert all(not r.configured for r in desde_la_lista)

    leido = await driver.read_kind(LINEA)
    assert leido is not None
    reglas = {r.external_id: r for r in leido[1]}
    # El driver va al recurso individual y ahí sí aparece.
    assert reglas["1"].configured
    assert [round(c, 3) for c in reglas["1"].points[0]] == [0.15, 0.5]


async def test_escribir_la_lista_no_aplica_la_geometria(client):
    driver = SmartRulesDriver(client, 1)
    original = await driver.read_kind_raw(LINEA)
    trucado = original.replace("<positionX>150</positionX>", "<positionX>999</positionX>")

    await driver.write_kind(LINEA, trucado)  # responde 200 OK

    crudo = await driver.read_item_raw(LINEA, "1")
    assert "<positionX>150</positionX>" in crudo  # no cambió nada


async def test_escribir_la_regla_individual_si_aplica(client):
    driver = SmartRulesDriver(client, 1)
    original = await driver.read_item_raw(LINEA, "1")
    nuevo = smart.build_item_xml(original, LINEA, RuleUpdate(points=[(0.2, 0.8), (0.9, 0.3)]))

    await driver.write_item(LINEA, "1", nuevo)

    leido = await driver.read_kind(LINEA)
    assert leido is not None
    regla = next(r for r in leido[1] if r.external_id == "1")
    assert [round(c, 2) for c in regla.points[0]] == [0.2, 0.8]


async def test_el_enabled_de_la_regla_se_ignora(client):
    """Verificado en la PTZ: el interruptor que vale es el del tipo, no el de cada regla."""
    driver = SmartRulesDriver(client, 1)
    original = await driver.read_item_raw(LINEA, "1")
    await driver.write_item(LINEA, "1", original.replace("<enabled>false", "<enabled>true"))

    assert "<enabled>false</enabled>" in await driver.read_item_raw(LINEA, "1")

    # En cambio el global sí se aplica.
    lista = await driver.read_kind_raw(LINEA)
    await driver.write_kind(LINEA, smart.set_kind_enabled(lista, True))
    leido = await driver.read_kind(LINEA)
    assert leido is not None
    assert leido[0].enabled is True


async def test_funcion_inexistente_responde_403_no_soportado(client):
    from app.drivers.errors import NotSupported

    with pytest.raises(NotSupported):
        await client.get("/ISAPI/Smart/ANPR/1")


async def test_el_domo_no_tiene_analitica_clasica():
    from app.drivers.errors import NotSupported

    async with _cliente(PROFILES["domo"]) as isapi:
        with pytest.raises(NotSupported):
            await isapi.get("/ISAPI/Smart/LineDetection/1")
        # pero sí expone AI Open Platform
        respuesta = await isapi.get("/ISAPI/Intelligent/AIOpenPlatform")
        assert b"algorithmVersion" in respuesta.content


def test_el_aviso_de_cierre_no_trae_la_regla(perfil):
    """El `inactive` de la PTZ viene sin regionID: por eso el agrupador cierra por tipo."""
    activo = alerta_xml(perfil, "linedetection", "active", rule_id="1")
    inactivo = alerta_xml(perfil, "linedetection", "inactive")
    assert b"<regionID>1</regionID>" in activo
    assert b"regionID" not in inactivo


async def test_la_rafaga_es_un_aviso_por_segundo(perfil, monkeypatch):
    import asyncio

    async def sin_esperar(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", sin_esperar)
    emisor = Emisor(perfil)
    avisos = await emisor.disparar("linedetection", segundos=5)
    # 5 "active" y un "inactive" que lo cierra.
    assert avisos == 6
    assert emisor.emitidos == 6
