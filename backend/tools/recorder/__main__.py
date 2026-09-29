"""Graba las respuestas de una cámara real como fixtures.

    uv run python -m tools.recorder --host 192.168.239.189 --usuario admin --clave XXXX

Con `--eventos 60` escucha un minuto de alertStream. Guardá el resumen: dice qué contestó
cada endpoint y con cuánta latencia, que es la materia prima de la matriz.
"""

import argparse
import asyncio
from pathlib import Path

from app.drivers.isapi.client import IsapiTarget
from tools.recorder.grabador import grabar

POR_DEFECTO = Path(__file__).resolve().parents[2] / "tests/fixtures/hikvision"


def main() -> None:
    parser = argparse.ArgumentParser(description="Grabador de respuestas de cámaras Hikvision")
    parser.add_argument("--host", required=True)
    parser.add_argument("--puerto", type=int, default=80)
    parser.add_argument("--usuario", default="admin")
    parser.add_argument("--clave", required=True)
    parser.add_argument("--canal", type=int, default=1)
    parser.add_argument("--https", action="store_true")
    parser.add_argument("--eventos", type=int, default=30, help="segundos de alertStream (0 = no)")
    parser.add_argument("--salida", type=Path, default=POR_DEFECTO)
    args = parser.parse_args()

    target = IsapiTarget(
        host=args.host,
        port=args.puerto,
        username=args.usuario,
        password=args.clave,
        use_https=args.https,
        timeout_s=15,
    )
    resumen = asyncio.run(grabar(target, args.salida, args.canal, args.eventos))

    print(f"\n{resumen.respondieron} de {len(resumen.registros)} endpoints respondieron")
    print(f"índice en {resumen.destino}\indice.json")
    no_soportados = [r.nombre for r in resumen.registros if not r.ok]
    if no_soportados:
        print(f"sin soporte o con error ({len(no_soportados)}): {', '.join(no_soportados)}")


main()
