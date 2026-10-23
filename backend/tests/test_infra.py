"""Infra Postgres (AD-007): config 100% por env, default postgres + psycopg3.

Suite roda contra o banco `ritmo_test` do compose (ver conftest).
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.core.config import Settings
from app.db.engine import SessionLocal, engine
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


def test_startup_fails_fast_without_token_encryption_key() -> None:
    """GTDB-14 (T8): sem TOKEN_ENCRYPTION_KEY o backend NÃO sobe — o lifespan
    levanta TokenKeyError apontando a geração da chave, ANTES do init_db
    (nenhuma tabela é recriada). Higiene de cache: o teste seta a env VAZIA
    (env var vence o .env do pydantic-settings) e restaura valor + cache no
    fim — os demais testes dependem do cache com a chave boa do conftest."""
    from app.core.config import get_settings
    from app.garmin.tokens_store import TokenKeyError

    original = os.environ.get("TOKEN_ENCRYPTION_KEY")
    os.environ["TOKEN_ENCRYPTION_KEY"] = ""
    get_settings.cache_clear()
    try:
        with pytest.raises(TokenKeyError) as exc_info:
            with TestClient(app):
                pass
        # Literais do spec/design (L-001): mensagem aponta a correção
        assert "TOKEN_ENCRYPTION_KEY" in str(exc_info.value)
        assert "Fernet.generate_key()" in str(exc_info.value)
        # Falhou ANTES do init_db: o fixture derrubou o schema e nada voltou
        assert not inspect(engine).has_table("users")
    finally:
        if original is None:
            os.environ.pop("TOKEN_ENCRYPTION_KEY", None)
        else:
            os.environ["TOKEN_ENCRYPTION_KEY"] = original
        get_settings.cache_clear()
