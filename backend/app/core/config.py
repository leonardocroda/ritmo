"""Configuração central do Ritmo.

Requisito travado (Fase 1): 100% env vars — nada hardcoded.
Na Fase 2.5, migrar SQLite -> Postgres é trocar ``DATABASE_URL``.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Ritmo"
    app_env: str = "dev"
    cors_origins: str = "*"

    # Fuso da conversão de deitar/acordar do painel Saúde (bed_time/wake_time
    # são gravados GMT naive; o horário exibido usa este fuso)
    app_timezone: str = "America/Sao_Paulo"

    # Banco — Postgres desde a v1 (AD-007); driver psycopg3
    database_url: str = "postgresql+psycopg://ritmo:ritmo@localhost:5432/ritmo"

    # Zonas VDOT — arquivo calibrado como fonte de verdade da v1 (spec
    # workouts-list); a tabela `zones` é da feature de calibração (Fase 2)
    vdot_zones_path: str = "data/vdot_zones.json"

    # NVIDIA NIM — avaliação de treino com IA
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "z-ai/glm-5.3"

    # Garmin — nomes de env var idênticos aos do garmin_mcp/token_utils
    # (o pydantic-settings casa `garmintokens` com `GARMINTOKENS`)
    garmintokens: str = "~/.garminconnect"
    garmintokens_base64: str = "~/.garminconnect_base64"

    # Garmin sync — janelas, cadência e guard rails (SYNC_*)
    sync_repull_days: int = 3                 # SYNC_REPULL_DAYS
    sync_backfill_activities_days: int = 180  # SYNC_BACKFILL_ACTIVITIES_DAYS
    sync_backfill_health_days: int = 60       # SYNC_BACKFILL_HEALTH_DAYS
    sync_call_interval_s: float = 1.0         # SYNC_CALL_INTERVAL_S
    sync_max_calls: int = 1500                 # SYNC_MAX_CALLS
    sync_retry_max: int = 3                   # SYNC_RETRY_MAX (backoff 2/4/8s)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
