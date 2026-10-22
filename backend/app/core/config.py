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
    # CORS — lista explícita (AUTH-28): allow_credentials com "*" é
    # rejeitado pelos browsers. Override no .env com o IP da LAN, ex.:
    # CORS_ORIGINS=http://localhost:3000,http://192.168.15.16:3000
    cors_origins: str = "http://localhost:3000"

    # Auth (feature auth — AD-013/018): convite + sessão stateful em banco
    # Vazio/ausente = registro desabilitado (403) até o user-scope no ar
    invite_code: str = ""
    # Sessão sliding: TTL de 30d, renovado quando restam ≤15d (AUTH-12)
    session_ttl_days: int = 30
    session_renew_threshold_days: int = 15
    # Cookie host-only HttpOnly (design auth); Secure exige HTTPS — Fase 2.5
    session_cookie_name: str = "ritmo_session"
    session_cookie_secure: bool = False

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
    # Timeout da chamada de avaliação (EVAL-13) — glm-5.3 é raciocinador:
    # UAT 18/10 mostrou geração real passando de 120s; 420s cobre o
    # pensamento longo com folga (env NVIDIA_TIMEOUT_S sobrepõe)
    nvidia_timeout_s: float = 420.0  # NVIDIA_TIMEOUT_S
    # LTHR de referência para o LLM interpretar FC (EVAL-02 — decisões
    # A/C do ai-evaluation: sem zonas Z1–Z5 formais na v1; 177 = perfil
    # calibrado, recalibração futura sobrepõe por env)
    lthr_bpm: int = 177  # LTHR_BPM

    # Garmin — tokens cifrados em repouso no banco (AD-014, feature
    # garmin-tokens-db). Gere uma chave com:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # e defina TOKEN_ENCRYPTION_KEY no .env/compose — sem ela o backend
    # não sobe (fail-fast, GTDB-14)
    token_encryption_key: str = ""

    # Garmin sync — janelas, cadência e guard rails (SYNC_*)
    sync_repull_days: int = 3                 # SYNC_REPULL_DAYS
    sync_backfill_activities_days: int = 180  # SYNC_BACKFILL_ACTIVITIES_DAYS
    sync_backfill_health_days: int = 120      # SYNC_BACKFILL_HEALTH_DAYS (HRV-15: exibição 60d + lookback de banda 59d)
    sync_call_interval_s: float = 1.0         # SYNC_CALL_INTERVAL_S
    sync_max_calls: int = 1500                 # SYNC_MAX_CALLS
    sync_retry_max: int = 3                   # SYNC_RETRY_MAX (backoff 2/4/8s)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
