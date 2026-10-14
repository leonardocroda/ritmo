"""Ambiente de teste: banco descartável, isolado do banco de dev.

Força DATABASE_URL em arquivo próprio antes de qualquer import da app
(o engine é criado no primeiro import, a partir do settings).
"""

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ritmo.db"

_DB_FILES = [Path("test_ritmo.db"), Path("test_ritmo.db-wal"), Path("test_ritmo.db-shm")]


def _remove_test_db() -> None:
    for path in _DB_FILES:
        if path.exists():
            path.unlink()
