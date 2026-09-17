from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"),
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://camaras:camaras@localhost:5434/camaras"
    # Frase secreta para cifrar credenciales de cámaras (Fernet derivado por SHA-256).
    secret_key: str = "desarrollo-cambiar-esta-clave"

    mediamtx_api_url: str = "http://localhost:9997"
    # URLs públicas que usa el navegador (sin credenciales).
    mediamtx_webrtc_url: str = "http://localhost:8889"
    mediamtx_hls_url: str = "http://localhost:8888"
    media_dir: Path = BACKEND_DIR / "media"

    cors_origins: list[str] = ["http://localhost:5173"]

    camera_timeout_s: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
