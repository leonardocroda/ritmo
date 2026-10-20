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
from fastapi.testclient import TestClient  # noqa: E402

from app.auth.deps import require_session  # noqa: E402
from app.auth.rate_limit import RateLimiter  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.auth.service import create_session, login  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.engine import SessionLocal, engine  # noqa: E402
from app.db.models import DEFAULT_USER_ID, User, UserSession  # noqa: E402
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


def _make_user(
    db: SessionLocal,
    *,
    email: str = "ana@example.com",
    password: str = "senha-segura-123",
    display_name: str = "Convidada",
) -> User:
    """Cria um usuário de teste com senha hasheada (id > 1 via sequência)."""
    user = User(
        display_name=display_name,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.flush()
    db.commit()
    return user


@pytest.fixture()
def session_client():
    """TestClient com sessão real de um usuário de teste (padrão).

    Remove o override global do conftest (usuário 1) para que o endpoint
    resolva o usuário do cookie real. O lifespan do TestClient roda
    ``init_db`` (tabelas + usuário 1), cria um User + UserSession no banco
    e devolve ``(client, user_id)`` para que os testes semeiem linhas com o
    ``user_id`` do usuário autenticado. Autocontido.
    """
    app.dependency_overrides.pop(require_session, None)
    with TestClient(app) as client:
        with SessionLocal() as db:
            user = _make_user(db)
            token = create_session(db, user.id)
            db.commit()
        client.cookies.set("ritmo_session", token)
        yield client, user.id


@pytest.fixture()
def login_client():
    """TestClient autenticado via login real (email + senha).

    Cria o usuário, chama ``service.login`` (mesmo fluxo do router) e
    devolve o TestClient com o cookie da sessão resultante. Autocontido.
    """
    with TestClient(app) as client:
        with SessionLocal() as db:
            _make_user(db, email="ana@example.com", password="senha-segura-123")
            limiter = RateLimiter()
            _user, token = login(db, "ana@example.com", "senha-segura-123", limiter)
            db.commit()
        client.cookies.set("ritmo_session", token)
        yield client
