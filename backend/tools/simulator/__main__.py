"""Levanta una cámara simulada: `uv run python -m tools.simulator --modelo ptz --puerto 8101`."""

import argparse

import uvicorn

from tools.simulator.camera import crear_app
from tools.simulator.profiles import PROFILES


def main() -> None:
    parser = argparse.ArgumentParser(description="Cámara Hikvision simulada")
    parser.add_argument("--modelo", choices=sorted(PROFILES), default="ptz")
    parser.add_argument("--puerto", type=int, default=8101)
    args = parser.parse_args()

    perfil = PROFILES[args.modelo]
    print(f"Cámara simulada {perfil.model} ({perfil.family}) en http://127.0.0.1:{args.puerto}")
    print("Usuario admin / clave simulada")
    uvicorn.run(crear_app(perfil), host="127.0.0.1", port=args.puerto, log_level="warning")


main()
