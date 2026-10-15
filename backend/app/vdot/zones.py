"""Zonas VDOT — a única fonte de verdade de zona (design workouts-list).

Carrega o JSON calibrado (``VDOT_ZONES_PATH``, default
``data/vdot_zones.json``) e classifica a velocidade de cada volta em
uma das 5 zonas de Daniels. As fronteiras entre zonas são cut points
de midpoint entre os limites adjacentes — determinísticos e
recalculáveis quando as zonas forem recalibradas (premissa do spec):
abaixo do primeiro cut → easy, acima do último → repetition, borda
exata pertence à zona mais rápida.

Cores definidas no backend (design): fonte única para o frontend —
verde=easy, azul=marathon, laranja=threshold, vermelho=interval,
roxo=repetition. A linha de FC usa a cor reservada ``HR_LINE_COLOR``,
distinta de todas as zonas (TRN-17).
"""

import json
from dataclasses import dataclass
from pathlib import Path


class ZoneConfigError(Exception):
    """``vdot_zones.json`` ausente ou inválido — cor de zona é requisito (spec)."""


# Cor da linha de FC no gráfico de splits (design): quase branco, contrasta
# com TODAS as cores de zona no tema escuro — zero colisão com vermelho=interval.
HR_LINE_COLOR = "#f8fafc"

# Rótulos exibíveis por chave de zona (a UI renderiza o que o payload manda)
_LABELS = {
    "easy": "Easy",
    "marathon": "Maratona",
    "threshold": "Limiar",
    "interval": "Intervalado",
    "repetition": "Repetição",
}

_ZONE_KEYS = ("easy", "marathon", "threshold", "interval", "repetition")

# Cores por zona (design §Tech Decisions — verde/azul/laranja/vermelho/roxo)
_COLORS = {
    "easy": "#22c55e",
    "marathon": "#3b82f6",
    "threshold": "#f97316",
    "interval": "#ef4444",
    "repetition": "#a855f7",
}


@dataclass(frozen=True)
class ZoneMeta:
    key: str
    label: str
    pace_range: str
    color: str


def _mid(a: float, b: float) -> float:
    """Cut point de midpoint entre zonas adjacentes (premissa do spec)."""
    return (a + b) / 2


def _pace_range_label(data: dict) -> str:
    """Faixa exibível: "5:51/km-4:53/km" -> "5:51–4:53/km"; pace único -> "4:30/km"."""
    if "pace_range" in data:
        lo, hi = data["pace_range"].split("-")
        return f"{lo.removesuffix('/km')}–{hi}"
    return data["pace"]


class ZoneConfig:
    """Zonas calibradas + cut points de midpoint — classificação pura."""

    def __init__(self, zones: dict):
        self._zones = zones
        self._cuts = (
            _mid(float(zones["easy"]["ms_max"]), float(zones["marathon"]["ms"])),
            _mid(float(zones["marathon"]["ms"]), float(zones["threshold"]["ms_min"])),
            _mid(float(zones["threshold"]["ms_max"]), float(zones["interval"]["ms_min"])),
            _mid(float(zones["interval"]["ms_max"]), float(zones["repetition"]["ms"])),
        )

    def classify(self, speed_ms: float | None) -> str | None:
        """Velocidade (m/s) -> chave da zona; pace inválido (None/≤0) -> None."""
        if speed_ms is None or speed_ms <= 0:
            return None
        if speed_ms < self._cuts[0]:
            return "easy"
        if speed_ms < self._cuts[1]:
            return "marathon"
        if speed_ms < self._cuts[2]:
            return "threshold"
        if speed_ms < self._cuts[3]:
            return "interval"
        return "repetition"

    def meta(self) -> list[ZoneMeta]:
        """As 5 zonas com chave, rótulo, faixa exibível e cor (legenda do gráfico)."""
        return [
            ZoneMeta(
                key=key,
                label=_LABELS[key],
                pace_range=_pace_range_label(self._zones[key]),
                color=_COLORS[key],
            )
            for key in _ZONE_KEYS
        ]


def load_zone_config(path: str | Path) -> ZoneConfig:
    """Parse do JSON calibrado; arquivo ausente/inválido -> ZoneConfigError (spec)."""
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ZoneConfigError(f"não foi possível carregar {path}: {exc}") from exc
    try:
        return ZoneConfig(data["zones"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ZoneConfigError(f"JSON de zonas inválido ({path}): {exc}") from exc
