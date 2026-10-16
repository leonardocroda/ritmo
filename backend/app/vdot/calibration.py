"""Calibração vigente — os campos raiz do `vdot_zones.json` (design).

O painel Potencial lê o VDOT corrente do mesmo arquivo que o
workouts-list usa para as zonas (fonte única): `load_calibration`
expõe os campos raiz do teste que gerou o VDOT. Arquivo ausente ou
inválido -> `ZoneConfigError` — a mesma exceção de `zones.py`, que se
transforma no mesmo HTTP 500 do workouts (POT-16).
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.vdot.zones import ZoneConfigError


@dataclass(frozen=True)
class Calibration:
    """A calibração vigente: VDOT corrente + o teste que o gerou."""

    vdot: float
    source: str
    test_date: date
    distance_m: float
    time_s: float


def load_calibration(path: str | Path) -> Calibration:
    """Parse dos campos raiz do JSON calibrado; ausente/inválido -> ZoneConfigError."""
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ZoneConfigError(f"não foi possível carregar {path}: {exc}") from exc
    try:
        return Calibration(
            vdot=float(data["vdot"]),
            source=data["source"],
            test_date=date.fromisoformat(data["test_date"]),
            distance_m=float(data["distancia_metros"]),
            time_s=float(data["tempo_segundos"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ZoneConfigError(f"JSON de calibração inválido ({path}): {exc}") from exc
