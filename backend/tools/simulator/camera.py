"""Cámara Hikvision simulada: habla ISAPI con autenticación Digest y emite alertStream.

Sirve para desarrollar y para la demo sin depender de la red de las cámaras. Responde con las
grabaciones reales guardadas en tests/fixtures y reproduce las rarezas verificadas del hardware.
"""

import hashlib
import json
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from tools.simulator.alerts import BOUNDARY, Emisor
from tools.simulator.profiles import Profile
from tools.simulator.rarezas import EstadoSmart
from tools.simulator.sistema import NTP_XML, Sistema, status_xml

USUARIO = "admin"
CLAVE = "simulada"
REALM = "IP Camera(SIM01)"

_NO_SOPORTADO = (
    '<?xml version="1.0" encoding="UTF-8"?><ResponseStatus version="2.0">'
    "<statusCode>4</statusCode><statusString>Invalid Operation</statusString>"
    "<subStatusCode>notSupport</subStatusCode></ResponseStatus>"
)
_OK = (
    '<?xml version="1.0" encoding="UTF-8"?><ResponseStatus version="2.0">'
    "<statusCode>1</statusCode><statusString>OK</statusString></ResponseStatus>"
)

# Reglas que expone cada tipo en /ISAPI/Smart/<tipo>/<canal>
SMART_ITEMS = {"LineDetection": "lineItem", "FieldDetection": "regions"}


def _digest_ok(header: str | None, method: str, nonce: str) -> bool:
    """Valida el Digest de verdad: así se ejercita el mismo camino que con la cámara real."""
    if not header or not header.lower().startswith("digest "):
        return False
    campos = dict(re.findall(r'(\w+)="?([^",]+)"?', header[7:]))
    if campos.get("username") != USUARIO or campos.get("nonce") != nonce:
        return False
    ha1 = hashlib.md5(f"{USUARIO}:{REALM}:{CLAVE}".encode()).hexdigest()  # noqa: S324
    ha2 = hashlib.md5(f"{method}:{campos.get('uri', '')}".encode()).hexdigest()  # noqa: S324
    if campos.get("qop"):
        base = f"{ha1}:{nonce}:{campos.get('nc')}:{campos.get('cnonce')}:{campos['qop']}:{ha2}"
    else:
        base = f"{ha1}:{nonce}:{ha2}"
    return hashlib.md5(base.encode()).hexdigest() == campos.get("response")  # noqa: S324


def crear_app(perfil: Profile) -> FastAPI:
    emisor = Emisor(perfil)
    nonce = secrets.token_hex(16)
    estado = _cargar_estado(perfil)
    # La cámara básica no tiene OSD ni ajustes de imagen: la matriz lo tiene que mostrar.
    sistema = Sistema(con_osd=perfil.family != "none", con_imagen=perfil.family != "none")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import asyncio

        latido = asyncio.create_task(emisor.latir())
        yield
        latido.cancel()

    app = FastAPI(lifespan=lifespan, title=f"Cámara simulada {perfil.model}")

    @app.middleware("http")
    async def digest(request: Request, call_next):
        if request.url.path.startswith("/_sim"):
            return await call_next(request)
        if not _digest_ok(request.headers.get("authorization"), request.method, nonce):
            return Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Digest qop="auth", realm="{REALM}", nonce="{nonce}"'
                },
            )
        return await call_next(request)

    # --- identidad y video -----------------------------------------------------------------

    @app.get("/ISAPI/System/deviceInfo")
    async def device_info() -> Response:
        return _xml(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<DeviceInfo version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">'
            f"<deviceName>Camara simulada</deviceName><deviceID>{perfil.key}</deviceID>"
            f"<model>{perfil.model}</model><serialNumber>{perfil.serial}</serialNumber>"
            f"<macAddress>{perfil.mac}</macAddress><firmwareVersion>{perfil.firmware}"
            "</firmwareVersion><deviceType>IPCamera</deviceType></DeviceInfo>"
        )

    @app.get("/ISAPI/Streaming/channels")
    async def canales() -> Response:
        if "/ISAPI/Streaming/channels" in perfil.static:
            return _xml(perfil.read(perfil.static["/ISAPI/Streaming/channels"]).decode())
        return _xml(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<StreamingChannelList version="2.0" '
            'xmlns="http://www.hikvision.com/ver20/XMLSchema">'
            "<StreamingChannel><id>101</id><channelName>Principal</channelName>"
            "<Video><videoCodecType>H.265</videoCodecType><videoResolutionWidth>3840"
            "</videoResolutionWidth><videoResolutionHeight>2160</videoResolutionHeight>"
            "<maxFrameRate>2500</maxFrameRate><constantBitRate>8192</constantBitRate>"
            "</Video></StreamingChannel>"
            "<StreamingChannel><id>102</id><channelName>Secundario</channelName>"
            "<Video><videoCodecType>H.264</videoCodecType><videoResolutionWidth>640"
            "</videoResolutionWidth><videoResolutionHeight>480</videoResolutionHeight>"
            "<maxFrameRate>1500</maxFrameRate><constantBitRate>512</constantBitRate>"
            "</Video></StreamingChannel></StreamingChannelList>"
        )

    @app.get("/ISAPI/Streaming/channels/{canal}/picture")
    async def snapshot(canal: str) -> Response:
        return Response(_imagen(perfil), media_type="image/jpeg")

    # --- eventos ---------------------------------------------------------------------------

    @app.get("/ISAPI/Event/notification/alertStream")
    async def alert_stream() -> StreamingResponse:
        return StreamingResponse(
            emisor.stream(), media_type=f"multipart/mixed; boundary={BOUNDARY}"
        )

    # --- funciones comunes ------------------------------------------------------------------

    @app.get("/ISAPI/System/status")
    async def estado_sistema() -> Response:
        return _xml(status_xml(sistema.uptime_s))

    @app.get("/ISAPI/System/time")
    async def leer_hora() -> Response:
        return _xml(sistema.leer_hora())

    @app.put("/ISAPI/System/time")
    async def escribir_hora(request: Request) -> Response:
        sistema.escribir_hora((await request.body()).decode())
        return _xml(_OK)

    @app.get("/ISAPI/System/time/ntpServers")
    async def servidores_ntp() -> Response:
        return _xml(NTP_XML)

    @app.put("/ISAPI/System/reboot")
    async def reiniciar() -> Response:
        sistema.reiniciar()
        return _xml(_OK)

    @app.get("/ISAPI/System/Video/inputs/channels/{canal}/overlays")
    async def leer_osd(canal: int) -> Response:
        return _xml(sistema.osd) if sistema.osd else _no_soportado()

    @app.put("/ISAPI/System/Video/inputs/channels/{canal}/overlays")
    async def escribir_osd(canal: int, request: Request) -> Response:
        if sistema.osd is None:
            return _no_soportado()
        sistema.osd = (await request.body()).decode()
        return _xml(_OK)

    @app.get("/ISAPI/Image/channels/{canal}/color")
    async def leer_imagen(canal: int) -> Response:
        return _xml(sistema.imagen) if sistema.imagen else _no_soportado()

    @app.put("/ISAPI/Image/channels/{canal}/color")
    async def escribir_imagen(canal: int, request: Request) -> Response:
        if sistema.imagen is None:
            return _no_soportado()
        sistema.imagen = (await request.body()).decode()
        return _xml(_OK)

    @app.get("/ISAPI/System/Video/inputs/channels/{canal}/motionDetection")
    async def leer_movimiento(canal: int) -> Response:
        return _xml(sistema.movimiento)

    @app.put("/ISAPI/System/Video/inputs/channels/{canal}/motionDetection")
    async def escribir_movimiento(canal: int, request: Request) -> Response:
        sistema.movimiento = (await request.body()).decode()
        return _xml(_OK)

    # --- reglas ----------------------------------------------------------------------------

    @app.get("/ISAPI/Smart/{tipo}/{canal}")
    async def leer_tipo(tipo: str, canal: int) -> Response:
        if estado is None or tipo not in estado:
            return _no_soportado()
        return _xml(estado[tipo].leer_lista())

    @app.put("/ISAPI/Smart/{tipo}/{canal}")
    async def escribir_tipo(tipo: str, canal: int, request: Request) -> Response:
        if estado is None or tipo not in estado:
            return _no_soportado()
        estado[tipo].escribir_lista((await request.body()).decode())
        return _xml(_OK)  # dice OK aunque la geometría no se toque

    @app.get("/ISAPI/Smart/{tipo}/{canal}/capabilities")
    async def capacidades_tipo(tipo: str, canal: int) -> Response:
        nombre = {
            "LineDetection": "smartLineDetectionCapabilities.xml",
            "FieldDetection": "smartFieldDetectionCapabilities.xml",
        }.get(tipo)
        if estado is None or nombre is None:
            return _no_soportado()
        return _xml(perfil.read(nombre).decode())

    @app.get("/ISAPI/Smart/{tipo}/{canal}/{sub}/{rule_id}")
    async def leer_regla(tipo: str, canal: int, sub: str, rule_id: str) -> Response:
        if estado is None or tipo not in estado or sub != SMART_ITEMS.get(tipo):
            return _no_soportado()
        xml = estado[tipo].leer_item(rule_id)
        return _xml(xml) if xml else _no_soportado()

    @app.put("/ISAPI/Smart/{tipo}/{canal}/{sub}/{rule_id}")
    async def escribir_regla(
        tipo: str, canal: int, sub: str, rule_id: str, request: Request
    ) -> Response:
        if estado is None or tipo not in estado or sub != SMART_ITEMS.get(tipo):
            return _no_soportado()
        if not estado[tipo].escribir_item(rule_id, (await request.body()).decode()):
            return _no_soportado()
        return _xml(_OK)

    # --- lo que cada modelo sirve tal cual de las grabaciones -------------------------------

    @app.get("/ISAPI/{ruta:path}")
    async def estaticos(ruta: str) -> Response:
        nombre = perfil.static.get(f"/ISAPI/{ruta}")
        if nombre is None:
            return _no_soportado()
        contenido = perfil.read(nombre)
        if nombre.endswith(".json"):
            return Response(contenido, media_type="application/json")
        return Response(contenido, media_type="application/xml")

    # --- control del simulador (no es ISAPI) ------------------------------------------------

    @app.get("/_sim")
    async def info() -> dict[str, Any]:
        return {
            "modelo": perfil.model,
            "familia": perfil.family,
            "eventos_disponibles": list(perfil.events),
            "avisos_emitidos": emisor.emitidos,
            "oyentes": len(emisor.clientes),
            "reinicios": sistema.reinicios,
            "uptime_s": sistema.uptime_s,
            "escrituras_a_la_lista_ignoradas": (
                estado["LineDetection"].escrituras_a_la_lista if estado else 0
            ),
        }

    @app.post("/_sim/disparar")
    async def disparar(
        tipo: str = "linedetection", segundos: int = 5, regla: str = "1"
    ) -> dict[str, Any]:
        avisos = await emisor.disparar(tipo, segundos, regla)
        return {"tipo": tipo, "avisos_enviados": avisos, "segundos": segundos}

    return app


def _cargar_estado(perfil: Profile) -> dict[str, EstadoSmart] | None:
    if perfil.family != "smart":
        return None
    items = {
        "1": perfil.read("smartLineDetectionItem1.xml").decode(),
        "2": perfil.read("smartLineDetectionItem2.xml").decode(),
    }
    # La cámara real tiene 4 casilleros de línea; los que nadie usó se leen vacíos.
    for vacio in ("3", "4"):
        items[vacio] = re.sub(
            r"<positionX>\d+</positionX>\s*<positionY>\d+</positionY>",
            "<positionX>0</positionX><positionY>1000</positionY>",
            items["1"].replace("<id>1</id>", f"<id>{vacio}</id>", 1),
        ).replace(
            "<detectionTarget>human,vehicle</detectionTarget>",
            "<detectionTarget> </detectionTarget>",
        )
    return {
        "LineDetection": EstadoSmart(items, perfil.read("smartLineDetection.xml").decode()),
        "FieldDetection": EstadoSmart(
            {"1": perfil.read("smartFieldDetectionRegion1.xml").decode()},
            perfil.read("smartFieldDetection.xml").decode(),
        ),
    }


def _xml(contenido: str) -> Response:
    return Response(contenido, media_type="application/xml")


def _no_soportado() -> Response:
    # Hikvision responde 403 (no 404) para funciones que el modelo no tiene.
    return Response(_NO_SOPORTADO, status_code=403, media_type="application/xml")


def _json(datos: dict[str, Any]) -> Response:
    return JSONResponse(json.loads(json.dumps(datos)))


PATRON = Path(__file__).with_name("patron.jpg")


def _imagen(perfil: Profile) -> bytes:
    """Un patrón con la rejilla de coordenadas: se ve de una si una regla quedó espejada."""
    return PATRON.read_bytes()
