"""Infra Postgres (AD-007): config 100% por env, default postgres + psycopg3."""

from app.core.config import Settings


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
