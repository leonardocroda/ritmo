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

from app.auth.deps import require_session  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.engine import SessionLocal, engine  # noqa: E402
from app.db.models import DEFAULT_USER_ID, User  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_database():
    """Estado limpo por teste: derruba o schema antes de cada teste (INFRA-05).

    O lifespan do TestClient recria as tabelas e semeia o usuário default.
    """
    Base.metadata.drop_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _bypass_session_protection():
    """Interim do spec auth (assumption travada): a suite existente não
    conhece sessão — o override devolve o usuário seed e os routers
    protegidos se comportam como antes. Os testes da API de auth
    (test_auth_api) limpam o override para exercer a proteção real
    (401/cookie/sliding) — o comportamento coberto por lá é o real."""
    from app.main import app as fastapi_app

    def _seed_user():
        with SessionLocal() as db:
            return db.get(User, DEFAULT_USER_ID)

    fastapi_app.dependency_overrides[require_session] = _seed_user
    yield
    fastapi_app.dependency_overrides.pop(require_session, None)
