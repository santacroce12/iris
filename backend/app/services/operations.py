"""Ejecuta una operación contra la cámara midiendo latencia y dejando registro en operation_logs."""

import time
import uuid
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import redact
from app.db.models import OperationLog
from app.domain.enums import Protocol
from app.drivers.errors import DriverError


@dataclass
class Outcome[T]:
    ok: bool
    value: T | None
    latency_ms: float
    error: DriverError | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "latency_ms": round(self.latency_ms, 1),
            "error_code": self.error.code if self.error else None,
            "message": redact(self.error.message) if self.error else None,
        }


async def run_operation[T](
    session: AsyncSession,
    *,
    camera_id: uuid.UUID,
    capability: str,
    protocol: Protocol,
    operation: str,
    call: Awaitable[T],
    detail: dict[str, Any] | None = None,
    experiment_id: uuid.UUID | None = None,
) -> Outcome[T]:
    started = time.perf_counter()
    try:
        value = await call
        outcome: Outcome[T] = Outcome(True, value, (time.perf_counter() - started) * 1000)
    except DriverError as exc:
        outcome = Outcome(False, None, (time.perf_counter() - started) * 1000, exc)

    session.add(
        OperationLog(
            camera_id=camera_id,
            capability_code=capability,
            protocol=protocol,
            operation=operation,
            http_status=outcome.error.http_status if outcome.error else None,
            success=outcome.ok,
            latency_ms=outcome.latency_ms,
            error_code=outcome.error.code if outcome.error else None,
            detail={
                **(detail or {}),
                **({"message": redact(outcome.error.message)} if outcome.error else {}),
            },
            experiment_id=experiment_id,
        )
    )
    return outcome
