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
    cors_origins: str = "http://localhost:3000"

    # Banco
    database_url: str = "sqlite:///./ritmo.db"

    # NVIDIA NIM — avaliação de treino com IA
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "z-ai/glm-5.3"

    # Garmin — nomes de env var idênticos aos do garmin_mcp/token_utils
    # (o pydantic-settings casa `garmintokens` com `GARMINTOKENS`)
    garmintokens: str = "~/.garminconnect"
    garmintokens_base64: str = "~/.garminconnect_base64"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
