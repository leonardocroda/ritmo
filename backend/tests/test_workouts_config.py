"""Config de zonas VDOT (T2) — default e override por env var.

O literal do default vem do spec/design (lição L-001): o default é
`data/vdot_zones.json`, o mesmo arquivo calibrado que a imagem do
backend passa a copiar.
"""

from app.core.config import Settings


def test_default_vdot_zones_path() -> None:
    """T2: default do caminho do arquivo de zonas calibradas."""
    settings = Settings(_env_file=None)
    assert settings.vdot_zones_path == "data/vdot_zones.json"


def test_vdot_zones_path_env_override(monkeypatch) -> None:
    """T2/TRN-15: VDOT_ZONES_PATH do ambiente sobrepõe o default (config 100% env)."""
    monkeypatch.setenv("VDOT_ZONES_PATH", "zonas/recalibradas.json")
    settings = Settings(_env_file=None)
    assert settings.vdot_zones_path == "zonas/recalibradas.json"
