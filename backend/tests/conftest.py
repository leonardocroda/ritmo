"""Ambiente de teste: suite roda no Postgres do compose (AD-007).

Banco de testes: `ritmo_test` (criado pelo init script do compose),
isolado do banco de dev `ritmo`. `DATABASE_URL` é forçada antes de
qualquer import da app — o engine é criado no primeiro import.
"""

import os

TEST_DATABASE_URL = "postgresql+psycopg://ritmo:ritmo@localhost:5432/ritmo_test"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from helpers import ensure_postgres_available  # noqa: E402

ensure_postgres_available(TEST_DATABASE_URL)

import pytest  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.engine import engine  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_database():
    """Estado limpo por teste: derruba o schema antes de cada teste (INFRA-05).

    O lifespan do TestClient recria as tabelas e semeia o usuário default.
    """
    Base.metadata.drop_all(bind=engine)
    yield
