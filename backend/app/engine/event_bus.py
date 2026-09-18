"""Reparte los eventos nuevos a los navegadores conectados por SSE."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

_MAX_PENDIENTES = 100  # si un cliente no lee, se le descartan eventos viejos


class EventBus:
    def __init__(self) -> None:
        self._suscriptores: set[asyncio.Queue[dict[str, Any]]] = set()

    def publish(self, evento: dict[str, Any]) -> None:
        for cola in list(self._suscriptores):
            if cola.qsize() >= _MAX_PENDIENTES:
                try:
                    cola.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            cola.put_nowait(evento)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        cola: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._suscriptores.add(cola)
        try:
            yield cola
        finally:
            self._suscriptores.discard(cola)

    @property
    def subscriber_count(self) -> int:
        return len(self._suscriptores)


bus = EventBus()
