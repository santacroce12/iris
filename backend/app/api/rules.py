import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ConfigBackupOut, RuleOut, RulePatch, RuleSetOut
from app.core.db import get_session
from app.db.models import Camera, ConfigBackup
from app.domain.rules import RuleKind, validar_puntos
from app.services import cameras as camera_service
from app.services import rules as service

router = APIRouter(prefix="/api/cameras", tags=["reglas"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def _camera(camera_id: uuid.UUID, session: Session) -> Camera:
    return await camera_service.get_camera(session, camera_id)


CameraDep = Annotated[Camera, Depends(_camera)]


@router.get("/{camera_id}/rules", response_model=RuleSetOut)
async def read_rules(camera: CameraDep, session: Session) -> RuleSetOut:
    conjunto = await service.read_rule_set(session, camera)
    await session.commit()
    return RuleSetOut.desde(conjunto)


@router.patch("/{camera_id}/rules/{kind}/{external_id}", response_model=RuleOut)
async def update_rule(
    camera: CameraDep, kind: RuleKind, external_id: str, payload: RulePatch, session: Session
) -> RuleOut:
    # La cantidad de puntos depende del tipo, que viene en la ruta y no en el cuerpo: por eso
    # no lo puede validar el esquema solo. Se revisa antes de tocar la cámara.
    if payload.points is not None:
        try:
            validar_puntos(kind, payload.points)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    regla = await service.update_rule(session, camera, kind, external_id, payload.a_update())
    await session.commit()
    return RuleOut.desde(regla)


@router.get("/{camera_id}/backups", response_model=list[ConfigBackupOut])
async def list_backups(camera: CameraDep, session: Session) -> list[ConfigBackup]:
    return list(
        await session.scalars(
            select(ConfigBackup)
            .where(ConfigBackup.camera_id == camera.id)
            .order_by(ConfigBackup.created_at.desc())
            .limit(50)
        )
    )


@router.post("/{camera_id}/backups/{backup_id}/restore", status_code=204)
async def restore_backup(camera: CameraDep, backup_id: uuid.UUID, session: Session) -> None:
    await service.restore_backup(session, camera, backup_id)
    await session.commit()
