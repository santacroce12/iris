import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CapabilityCheck
from app.domain.enums import CapabilitySource, Protocol, SupportLevel
from app.drivers.errors import AuthenticationFailed, NotSupported
from app.services.operations import Outcome


def level_from_outcome(outcome: Outcome[Any]) -> SupportLevel:
    if outcome.ok:
        return SupportLevel.SUPPORTED
    if isinstance(outcome.error, NotSupported):
        return SupportLevel.UNSUPPORTED
    if isinstance(outcome.error, AuthenticationFailed):
        # Sin credenciales válidas no se puede afirmar nada sobre la función.
        return SupportLevel.UNVERIFIED
    return SupportLevel.ERROR


async def record_check(
    session: AsyncSession,
    *,
    camera_id: uuid.UUID,
    code: str,
    protocol: Protocol,
    level: SupportLevel,
    source: CapabilitySource,
    evidence: dict[str, Any] | None = None,
    latency_ms: float | None = None,
) -> None:
    values = {
        "level": level,
        "source": source,
        "evidence": evidence,
        "latency_ms": latency_ms,
        "checked_at": func.now(),
    }
    statement = insert(CapabilityCheck).values(
        id=uuid.uuid4(), camera_id=camera_id, capability_code=code, protocol=protocol, **values
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=["camera_id", "capability_code", "protocol"], set_=values
        )
    )


async def record_outcome(
    session: AsyncSession,
    camera_id: uuid.UUID,
    code: str,
    protocol: Protocol,
    outcome: Outcome[Any],
    evidence: dict[str, Any] | None = None,
) -> None:
    await record_check(
        session,
        camera_id=camera_id,
        code=code,
        protocol=protocol,
        level=level_from_outcome(outcome),
        source=CapabilitySource.VERIFIED,
        evidence={**outcome.as_dict(), **(evidence or {})},
        latency_ms=outcome.latency_ms,
    )
