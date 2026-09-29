"""Funciones comunes por ISAPI, contra la cámara simulada."""

import httpx
import pytest

from app.drivers.errors import NotSupported
from app.drivers.isapi import system
from app.drivers.isapi.client import IsapiClient, IsapiTarget
from tools.simulator.camera import crear_app
from tools.simulator.profiles import PROFILES


def _cliente(clave: str) -> IsapiClient:
    target = IsapiTarget(host="sim", port=80, username="admin", password="simulada")
    return IsapiClient(target, transport=httpx.ASGITransport(app=crear_app(PROFILES[clave])))


@pytest.fixture
async def ptz():
    async with _cliente("ptz") as client:
        yield client


@pytest.fixture
async def basica():
    async with _cliente("basica") as client:
        yield client


async def test_estado_calcula_el_porcentaje_de_memoria(ptz):
    """La cámara informa memoria usada y libre con decimales, no un porcentaje."""
    estado = await system.get_status(ptz)
    assert estado.cpu_percent == 17
    assert estado.memory_percent == 40  # 412.35 de 1024
    assert estado.uptime_s is not None


async def test_hora_incluye_el_huso_y_el_servidor_ntp(ptz):
    hora = await system.get_time(ptz)
    assert hora.mode == "NTP"
    assert hora.timezone == "CST-8:00:00"
    assert hora.ntp_server == "time.windows.com"
    # La cámara reporta en su huso, no en UTC: por eso la plataforma normaliza al guardar.
    assert hora.local_time.endswith("+08:00")


async def test_poner_en_hora_pasa_a_manual(ptz):
    hora = await system.set_time(ptz, local_time="2026-09-25T18:30:00+00:00")
    assert hora.mode == "manual"
    assert hora.local_time == "2026-09-25T18:30:00+00:00"


async def test_leer_osd(ptz):
    osd = await system.get_osd(ptz)
    assert osd.show_name is True
    assert osd.show_date is True
    assert osd.name == "Entrada"
    assert osd.lines == ["Camara simulada"]


async def test_escribir_osd_solo_cambia_lo_pedido(ptz):
    osd = await system.set_osd(ptz, show_date=False, name="Porton")
    assert osd.show_date is False
    assert osd.name == "Porton"
    assert osd.show_name is True  # no se pidió, no se tocó
    assert osd.lines == ["Camara simulada"]


async def test_ajustes_de_imagen(ptz):
    antes = await system.get_image(ptz)
    assert antes.brightness == 50

    despues = await system.set_image(ptz, brightness=72, contrast=64)
    assert (despues.brightness, despues.contrast) == (72, 64)
    assert despues.saturation == 50


async def test_los_valores_de_imagen_se_recortan(ptz):
    imagen = await system.set_image(ptz, brightness=500)
    assert imagen.brightness == 100


async def test_movimiento(ptz):
    antes = await system.get_motion(ptz)
    assert antes.enabled is False

    despues = await system.set_motion(ptz, enabled=True, sensitivity=80)
    assert despues.enabled is True
    assert despues.sensitivity == 80


async def test_la_camara_basica_no_tiene_osd_ni_imagen(basica):
    """Un modelo de gama baja no expone todo: la matriz tiene que poder decir 'no soportada'."""
    with pytest.raises(NotSupported):
        await system.get_osd(basica)
    with pytest.raises(NotSupported):
        await system.get_image(basica)
    # pero sí tiene hora y movimiento
    assert (await system.get_time(basica)).timezone is not None
    assert (await system.get_motion(basica)).enabled is False


async def test_reiniciar_es_una_llamada_explicita(ptz):
    respuesta = await system.reboot(ptz)
    assert respuesta["status"] == 200
