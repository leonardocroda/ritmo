"""Calibração vigente (vdot/calibration.py) — os campos raiz do vdot_zones.json.

Cenários derivados dos done-when de T2 e da premissa do spec ("sem
vdot_zones.json -> 500 zonas não configuradas"): o arquivo real é
pinado campo a campo; toda forma de arquivo ausente/inválido levanta
`ZoneConfigError` — a mesma exceção de `zones.py` (POT-16).
"""

import json
from datetime import date
from pathlib import Path

import pytest

from app.vdot.calibration import load_calibration
from app.vdot.zones import ZoneConfigError

ZONES_FILE = Path(__file__).resolve().parent.parent / "data" / "vdot_zones.json"


def test_load_calibration_reads_real_zones_file() -> None:
    """Done-when T2: o JSON real carrega com os valores da calibração vigente."""
    calibration = load_calibration(ZONES_FILE)
    assert calibration.vdot == 50.2
    assert calibration.source == "10K em 41:15"
    assert calibration.test_date == date(2026, 10, 3)
    assert calibration.distance_m == 10012
    assert calibration.time_s == 2475


def test_load_calibration_missing_file_raises(tmp_path) -> None:
    """Premissa do spec: arquivo ausente -> ZoneConfigError (o endpoint vira 500)."""
    with pytest.raises(ZoneConfigError):
        load_calibration(tmp_path / "vdot_zones.json")


def test_load_calibration_malformed_json_raises(tmp_path) -> None:
    """JSON quebrado -> ZoneConfigError (mesma exceção de zones.py)."""
    bad = tmp_path / "vdot_zones.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ZoneConfigError):
        load_calibration(bad)


def test_load_calibration_missing_root_fields_raises(tmp_path) -> None:
    """JSON válido sem os campos raiz -> ZoneConfigError (nada inventado)."""
    incomplete = {"vdot": 50.2, "source": "10K em 41:15"}  # sem test_date/distância/tempo
    bad = tmp_path / "vdot_zones.json"
    bad.write_text(json.dumps(incomplete), encoding="utf-8")
    with pytest.raises(ZoneConfigError):
        load_calibration(bad)


def test_load_calibration_invalid_test_date_raises(tmp_path) -> None:
    """test_date fora do formato ISO -> ZoneConfigError (inválido = erro, não crash)."""
    bad = tmp_path / "vdot_zones.json"
    bad.write_text(
        json.dumps(
            {
                "vdot": 50.2,
                "source": "10K em 41:15",
                "test_date": "03/10/2026",
                "distancia_metros": 10012,
                "tempo_segundos": 2475,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ZoneConfigError):
        load_calibration(bad)
