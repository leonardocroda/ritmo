"""Config SYNC_* — defaults exatos e override por env vars.

Literais afirmados vêm do spec (SYNC-03/07/09/10/15/18), nunca de
constantes compartilhadas com a implementação (lição L-001).
"""

import pytest

from app.core.config import Settings

SYNC_ENV_VARS = (
    "SYNC_REPULL_DAYS",
    "SYNC_BACKFILL_ACTIVITIES_DAYS",
    "SYNC_BACKFILL_HEALTH_DAYS",
    "SYNC_CALL_INTERVAL_S",
    "SYNC_MAX_CALLS",
    "SYNC_RETRY_MAX",
)


@pytest.fixture(autouse=True)
def _clean_sync_env(monkeypatch):
    """Isola a suite de SYNC_* que possa existir no ambiente do host."""
    for var in SYNC_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_default_sync_repull_days() -> None:
    """SYNC-10/18: re-pull de 3 dias em steady-state."""
    settings = Settings(_env_file=None)
    assert settings.sync_repull_days == 3


def test_default_sync_backfill_windows() -> None:
    """SYNC-15/HRV-15: primeiro sync = 180d de atividades / 120d de saúde."""
    settings = Settings(_env_file=None)
    assert settings.sync_backfill_activities_days == 180
    assert settings.sync_backfill_health_days == 120


def test_default_sync_call_interval() -> None:
    """SYNC-03: pausa mínima de 1,0s entre chamadas."""
    settings = Settings(_env_file=None)
    assert settings.sync_call_interval_s == 1.0


def test_default_sync_max_calls() -> None:
    """SYNC-09: guard rail de 1500 chamadas por sync."""
    settings = Settings(_env_file=None)
    assert settings.sync_max_calls == 1500


def test_default_sync_retry_max() -> None:
    """SYNC-07: até 3 retries com backoff 2s/4s/8s."""
    settings = Settings(_env_file=None)
    assert settings.sync_retry_max == 3


def test_sync_env_overrides(monkeypatch) -> None:
    """Env vars SYNC_* sobrepõem os defaults (config 100% env, INFRA-03)."""
    monkeypatch.setenv("SYNC_REPULL_DAYS", "5")
    monkeypatch.setenv("SYNC_BACKFILL_ACTIVITIES_DAYS", "365")
    monkeypatch.setenv("SYNC_BACKFILL_HEALTH_DAYS", "90")
    monkeypatch.setenv("SYNC_CALL_INTERVAL_S", "0.5")
    monkeypatch.setenv("SYNC_MAX_CALLS", "200")
    monkeypatch.setenv("SYNC_RETRY_MAX", "2")
    settings = Settings(_env_file=None)
    assert settings.sync_repull_days == 5
    assert settings.sync_backfill_activities_days == 365
    assert settings.sync_backfill_health_days == 90
    assert settings.sync_call_interval_s == 0.5
    assert settings.sync_max_calls == 200
    assert settings.sync_retry_max == 2
