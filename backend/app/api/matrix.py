"""Matriz de compatibilidad: qué da cada protocolo, para todas las cámaras."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MatrixCameraOut, MatrixCellOut, MatrixOut, MatrixRowOut
from app.core.db import get_session
from app.db.models import Camera, CapabilityCheck
from app.domain.capabilities import CATALOG
from app.domain.enums import Protocol

router = APIRouter(prefix="/api", tags=["matriz"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/matrix", response_model=MatrixOut)
async def get_matrix(session: Session) -> MatrixOut:
    camaras = list(await session.scalars(select(Camera).order_by(Camera.name)))
    checks = list(await session.scalars(select(CapabilityCheck)))
    # (cámara, función, protocolo) -> chequeo más informativo (verificado gana a declarado)
    por_clave: dict[tuple, CapabilityCheck] = {}
    for check in checks:
        clave = (check.camera_id, check.capability_code, check.protocol)
        anterior = por_clave.get(clave)
        if anterior is None or check.source == "verified":
            por_clave[clave] = check

    filas = []
    for definicion in CATALOG:
        celdas = []
        for camara in camaras:
            for protocolo in Protocol:
                check = por_clave.get((camara.id, definicion.code, protocolo))
                aplica = protocolo in definicion.protocols
                if check is None and not aplica:
                    continue
                celdas.append(
                    MatrixCellOut(
                        camera_id=camara.id,
                        protocol=protocolo,
                        level=check.level if check else "unverified",
                        source=check.source if check else None,
                        latency_ms=check.latency_ms if check else None,
                        checked_at=check.checked_at if check else None,
                        evidence=check.evidence if check else None,
                    )
                )
        filas.append(
            MatrixRowOut(
                code=definicion.code,
                group=definicion.group,
                label=definicion.label,
                protocols=[p.value for p in definicion.protocols],
                cells=celdas,
            )
        )
    return MatrixOut(
        cameras=[
            MatrixCameraOut(id=c.id, name=c.name, model=c.model, host=c.host) for c in camaras
        ],
        rows=filas,
    )
