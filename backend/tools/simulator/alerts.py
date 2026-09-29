"""El flujo de eventos de la cámara simulada, con el comportamiento real del alertStream."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from tools.simulator.profiles import Profile

BOUNDARY = "boundary"
LATIDO_S = 10  # la cámara manda videoloss/inactive cada ~10 s aunque no pase nada
HUSO = timedelta(hours=8)  # la PTZ real reporta en +08:00


def _ahora() -> str:
    return (datetime.now(UTC) + HUSO).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _region(rule_id: str, puntos: list[tuple[int, int]]) -> str:
    coords = "".join(
        f"<RegionCoordinates><positionX>{x}</positionX>"
        f"<positionY>{y}</positionY></RegionCoordinates>"
        for x, y in puntos
    )
    return (
        "<DetectionRegionList><DetectionRegionEntry>"
        f"<regionID>{rule_id}</regionID><sensitivityLevel>50</sensitivityLevel>"
        f"<RegionCoordinatesList>{coords}</RegionCoordinatesList>"
        "</DetectionRegionEntry></DetectionRegionList>"
    )


def alerta_xml(
    perfil: Profile,
    tipo: str,
    estado: str,
    rule_id: str | None = None,
    puntos: list[tuple[int, int]] | None = None,
    objetivo: str | None = None,
) -> bytes:
    region = _region(rule_id, puntos or [(150, 500), (850, 500)]) if rule_id else ""
    destino = f"<detectionTarget>{objetivo}</detectionTarget>" if objetivo else ""
    cuerpo = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<EventNotificationAlert version="2.0" '
        'xmlns="http://www.hikvision.com/ver20/XMLSchema">\n'
        "<ipAddress>127.0.0.1</ipAddress>\n<portNo>80</portNo>\n<protocol>HTTP</protocol>\n"
        f"<macAddress>{perfil.mac}</macAddress>\n<channelID>1</channelID>\n"
        f"<dateTime>{_ahora()}</dateTime>\n"
        f"<activePostCount>{1 if estado == 'active' else 0}</activePostCount>\n"
        f"<eventType>{tipo}</eventType>\n<eventState>{estado}</eventState>\n"
        f"<eventDescription>{tipo} alarm</eventDescription>\n"
        f"{region}{destino}\n<channelName></channelName>\n"
        '<Extensions version="1.0" xmlns="urn:psialliance-org">\n'
        '<serialNumber xmlns="urn:selfextension:psiaext-ver10-xsd">'
        f"{perfil.serial}</serialNumber>\n"
        "</Extensions>\n</EventNotificationAlert>\n"
    ).encode()
    cabecera = (
        f"--{BOUNDARY}\r\n"
        'Content-Type: application/xml; charset="UTF-8"\r\n'
        f"Content-Length: {len(cuerpo)}\r\n\r\n"
    ).encode()
    return cabecera + cuerpo + b"\r\n"


class Emisor:
    """Reparte los avisos a todos los alertStream abiertos."""

    def __init__(self, perfil: Profile) -> None:
        self.perfil = perfil
        self.clientes: set[asyncio.Queue[bytes]] = set()
        self.emitidos = 0

    def publicar(self, datos: bytes) -> None:
        self.emitidos += 1
        for cola in list(self.clientes):
            if cola.full():  # un cliente lento no frena a la cámara
                continue
            cola.put_nowait(datos)

    async def latir(self) -> None:
        while True:
            await asyncio.sleep(LATIDO_S)
            self.publicar(alerta_xml(self.perfil, "videoloss", "inactive"))

    async def disparar(
        self,
        tipo: str,
        segundos: int = 5,
        rule_id: str | None = "1",
        objetivo: str | None = "human",
    ) -> int:
        """Un evento real no es un aviso: es una ráfaga de uno por segundo.

        Y el `inactive` que lo cierra viene SIN regionID, que es lo que dejaba filas huérfanas
        en la base antes de agrupar por (tipo, canal).
        """
        avisos = 0
        for _ in range(max(1, segundos)):
            self.publicar(alerta_xml(self.perfil, tipo, "active", rule_id, objetivo=objetivo))
            avisos += 1
            await asyncio.sleep(1)
        self.publicar(alerta_xml(self.perfil, tipo, "inactive"))
        return avisos + 1

    async def stream(self) -> AsyncIterator[bytes]:
        cola: asyncio.Queue[bytes] = asyncio.Queue(maxsize=64)
        self.clientes.add(cola)
        try:
            # La cámara saluda con un latido en cuanto se abre la conexión.
            yield alerta_xml(self.perfil, "videoloss", "inactive")
            while True:
                yield await cola.get()
        finally:
            self.clientes.discard(cola)
