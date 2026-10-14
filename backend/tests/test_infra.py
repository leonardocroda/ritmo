"""Infra Postgres (AD-007): config 100% por env, default postgres + psycopg3.

Suite roda contra o banco `ritmo_test` do compose (ver conftest).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.engine import SessionLocal
from app.db.models import DEFAULT_USER_ID, User
from app.main import app
from helpers import ensure_postgres_available


def test_default_database_url_is_postgres(monkeypatch) -> None:
    """Sem DATABASE_URL no ambiente, o default é postgres com driver psycopg3 (INFRA-03/09)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "sqlite" not in settings.database_url


def test_database_url_env_override(monkeypatch) -> None:
    """DATABASE_URL do ambiente sobrepõe qualquer valor do código (INFRA-03)."""
    override = "postgresql+psycopg://outro:senha@db.example.com:5433/ritmo"
    monkeypatch.setenv("DATABASE_URL", override)
    settings = Settings(_env_file=None)
    assert settings.database_url == override


def test_engine_is_postgres() -> None:
    """O engine da suite usa o dialeto postgres+psycopg (INFRA-09)."""
    from app.db.engine import engine

    assert engine.url.drivername == "postgresql+psycopg"


def test_state_pollution_inserts_user() -> None:
    """Passo 1 do par de isolamento: cria um usuário extra, sujando o estado."""
    with TestClient(app):
        with SessionLocal() as db:
            db.add(User(id=42, display_name="Extra"))
            db.commit()
            assert db.execute(select(User.id)).scalars().all() == [DEFAULT_USER_ID, 42]


def test_clean_state_sees_only_seed() -> None:
    """Passo 2: o fixture autouse derrubou o schema — só o usuário default existe (INFRA-05)."""
    with TestClient(app):
        with SessionLocal() as db:
            assert db.execute(select(User.id)).scalars().all() == [DEFAULT_USER_ID]


def test_fail_fast_message_when_postgres_down() -> None:
    """URL morta → RuntimeError citando o comando de subida do compose (INFRA-06).

    O literal é o resultado definido no spec — afirmar a constante compartilhada
    com a implementação deixaria um mutante da mensagem sobreviver (lição L-001).
    """
    dead_url = "postgresql+psycopg://ritmo:ritmo@localhost:59999/ritmo_test"
    with pytest.raises(RuntimeError) as exc_info:
        ensure_postgres_available(dead_url)
    assert "docker compose up -d postgres" in str(exc_info.value)
