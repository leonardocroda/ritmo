"""Config de avaliação IA — defaults exatos e override por env vars.

Literais afirmados vêm do design da feature ai-evaluation (EVAL-02:
LTHR de referência; EVAL-13: timeout da chamada NIM), nunca de
constantes compartilhadas com a implementação (lição L-001).
"""

import pytest

from app.core.config import Settings

EVAL_ENV_VARS = (
    "NVIDIA_API_KEY",
    "NVIDIA_BASE_URL",
    "NVIDIA_MODEL",
    "NVIDIA_TIMEOUT_S",
    "LTHR_BPM",
)


@pytest.fixture(autouse=True)
def _clean_eval_env(monkeypatch):
    """Isola a suite de vars de avaliação que possam existir no host."""
    for var in EVAL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_default_nvidia_timeout() -> None:
    """EVAL-13: timeout de 420s — modelo raciocinador passa de 120s (UAT 18/10)."""
    settings = Settings(_env_file=None)
    assert settings.nvidia_timeout_s == 420.0


def test_default_lthr() -> None:
    """EVAL-02: LTHR 177 do perfil calibrado (env sobrepõe na recalibração)."""
    settings = Settings(_env_file=None)
    assert settings.lthr_bpm == 177


def test_default_nim_model_and_url() -> None:
    """Contrato NIM vigente: NIM oficial + glm-5.3 (plano §4.6)."""
    settings = Settings(_env_file=None)
    assert settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
    assert settings.nvidia_model == "z-ai/glm-5.3"


def test_eval_env_overrides(monkeypatch) -> None:
    """Env vars sobrepõem os defaults (config 100% env, INFRA-03)."""
    monkeypatch.setenv("NVIDIA_TIMEOUT_S", "60")
    monkeypatch.setenv("LTHR_BPM", "182")
    monkeypatch.setenv("NVIDIA_MODEL", "z-ai/glm-5.3-flash")
    settings = Settings(_env_file=None)
    assert settings.nvidia_timeout_s == 60.0
    assert settings.lthr_bpm == 182
    assert settings.nvidia_model == "z-ai/glm-5.3-flash"
