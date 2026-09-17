import os
from pathlib import Path

# Debe definirse antes de importar la app: el engine se crea al importar app.core.db.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://camaras:camaras@localhost:5434/camaras_test"
)
os.environ.setdefault("SECRET_KEY", "clave-de-tests")

import pytest  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_bytes():
    def load(relative: str) -> bytes:
        return (FIXTURES / relative).read_bytes()

    return load
