"""El grabador de fixtures: lo que se lleva y lo que borra antes de guardarlo."""

import httpx
import pytest

from app.drivers.isapi.client import IsapiClient, IsapiTarget
from tools.recorder.catalogo import catalogo
from tools.recorder.grabador import Grabador, Resumen, sanitizar
from tools.simulator.camera import crear_app
from tools.simulator.profiles import PROFILES


@pytest.fixture
async def client():
    target = IsapiTarget(host="sim", port=80, username="admin", password="simulada")
    async with IsapiClient(
        target, transport=httpx.ASGITransport(app=crear_app(PROFILES["ptz"]))
    ) as isapi:
        yield isapi


def test_el_catalogo_incluye_funciones_que_muchos_modelos_no_tienen():
    """Un 403 notSupport grabado es evidencia: así se probó que el domo no tiene Smart."""
    nombres = {p.nombre for p in catalogo()}
    assert {"deviceInfo", "systemCapabilities", "subscribeEventCap"} <= nombres
    assert {"aiopVideoTask", "anpr", "parking", "ptzPresets"} <= nombres
    # De cada tipo de regla se piden los 4 casilleros, no solo la lista.
    assert {"smartLineDetectionItem1", "smartLineDetectionItem4"} <= nombres


def test_se_borran_los_datos_que_identifican_al_equipo():
    """Las fixtures se versionan en el repositorio: no pueden llevar serie ni MAC reales."""
    crudo = (
        b"<DeviceInfo><serialNumber>DS-2DF8A836IX-AEL20190422CCWR232522407X</serialNumber>"
        b"<macAddress>98:8b:0a:75:33:b0</macAddress>"
        b"<ipAddress>192.168.239.189</ipAddress></DeviceInfo>"
    )
    limpio = sanitizar(crudo)
    assert b"CCWR232522407X" not in limpio
    assert b"98:8b:0a" not in limpio
    assert b"192.168.239.189" not in limpio
    assert b"SERIE-OCULTA" in limpio


def test_las_credenciales_nunca_quedan_en_la_fixture():
    crudo = b"<User><userName>admin</userName><password>Cuencotech2026</password></User>"
    limpio = sanitizar(crudo)
    assert b"Cuencotech2026" not in limpio
    assert b"admin" not in limpio


async def test_graba_lo_que_responde_y_lo_que_no(client, tmp_path):
    grabador = Grabador(client, tmp_path, canal=1)
    resumen = Resumen(modelo="X", firmware="Y", grabado_en="ahora", destino=str(tmp_path))
    await grabador.barrer(resumen)

    por_nombre = {r.nombre: r for r in resumen.registros}
    # Lo que contestó quedó en un archivo...
    assert por_nombre["deviceInfo"].ok
    assert (tmp_path / por_nombre["deviceInfo"].archivo).exists()
    # ...y lo que no, queda registrado igual, con el motivo.
    assert not por_nombre["anpr"].ok
    assert por_nombre["anpr"].archivo is None
    assert por_nombre["anpr"].status == 403
    # Todas las llamadas quedan con su latencia: es la materia prima de la matriz.
    assert all(r.latencia_ms >= 0 for r in resumen.registros)


async def test_el_snapshot_se_guarda_como_imagen(client, tmp_path):
    grabador = Grabador(client, tmp_path, canal=1)
    resumen = Resumen(modelo="X", firmware="Y", grabado_en="ahora", destino=str(tmp_path))
    await grabador.snapshot(resumen)

    archivo = tmp_path / "snapshot.jpg"
    assert archivo.exists()
    assert archivo.read_bytes().startswith(b"\xff\xd8")  # cabecera JPEG


async def test_identifica_modelo_y_firmware(client, tmp_path):
    """El modelo y el firmware deciden en qué carpeta se guardan las fixtures."""
    grabador = Grabador(client, tmp_path, canal=1)
    modelo, firmware = await grabador.identificar()
    assert modelo == "DS-2DF8A836IX-AEL"
    assert firmware == "V5.6.0"
