"""Corre el experimento de la Fase 5: N repeticiones de cada función por protocolo y cámara.

    uv run python -m tools.experiments --repeticiones 30
    uv run python -m tools.experiments --repeticiones 10 --camera-id <uuid> --camera-id <uuid>

Sin `--camera-id` corre contra todas las cámaras registradas (reales o simuladas). Antes de las
N repeticiones hace una llamada de reconocimiento por protocolo: si la cámara no responde, no
espera N timeouts, lo anota y sigue.

Deja un CSV y un informe en Markdown en docs/evidencias/experimentos/<fecha_hora>/.
"""

import argparse
import asyncio
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal
from app.db.models import Camera
from app.services.experiments import (
    REPETICIONES_POR_DEFECTO,
    agregar,
    exportar_csv,
    exportar_markdown,
    run_experiment,
)

RAIZ_EVIDENCIAS = Path(__file__).resolve().parents[3] / "docs/evidencias/experimentos"


def main() -> None:
    parser = argparse.ArgumentParser(description="Corredor de experimentos (Fase 5)")
    parser.add_argument("--repeticiones", type=int, default=REPETICIONES_POR_DEFECTO)
    parser.add_argument(
        "--camera-id",
        action="append",
        dest="camera_ids",
        default=[],
        help="Repetible. Sin ninguno, corre contra todas las cámaras registradas.",
    )
    parser.add_argument("--salida", type=Path, default=RAIZ_EVIDENCIAS)
    args = parser.parse_args()
    asyncio.run(_main(args))


async def _main(args: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        consulta = select(Camera).order_by(Camera.name)
        if args.camera_ids:
            consulta = consulta.where(Camera.id.in_([uuid.UUID(c) for c in args.camera_ids]))
        camaras = list(await session.scalars(consulta))
        if not camaras:
            print("No hay cámaras que coincidan. Revisá --camera-id o agregá una cámara primero.")
            return

        print(f"Cámaras: {', '.join(c.name for c in camaras)}")
        print(f"Repeticiones por función: {args.repeticiones}")
        experimento = await run_experiment(session, camaras, args.repeticiones)
        estadisticas = await agregar(session, experimento.experiment_id)

    carpeta = args.salida / experimento.iniciado_en.replace(":", "-")
    ruta_csv = exportar_csv(estadisticas, carpeta / "resultados.csv")
    ruta_md = exportar_markdown(experimento, estadisticas, carpeta / "informe.md")

    print(f"\n{len(estadisticas)} combinaciones función×protocolo×cámara medidas.")
    print(f"CSV:     {ruta_csv}")
    print(f"Informe: {ruta_md}")


main()
