"""Equações de Daniels (vdot/daniels.py) — pins literais contra cálculo manual.

Cenários derivados dos done-when de T1 e do contrato do design
potential-panel: a mesma forma fechada que gerou a calibração vigente
(10K 41:15 -> 50.2) e os VDOTs dos PRs reais do banco (5K 19:23,8 ->
51,62). Valores afirmados são literais, nunca constantes compartilhadas
com o módulo implementado (lição L-001).
"""

import json
from pathlib import Path

from app.vdot.calibrate_vdot import gerar_zonas
from app.vdot.daniels import calculate_vdot, equivalent_time, speed_for_vo2, vo2_cost

ZONES_FILE = Path(__file__).resolve().parent.parent / "data" / "vdot_zones.json"


def test_calculate_vdot_pins_personal_records() -> None:
    """Done-when T1: VDOT dos PRs reais pela forma fechada (design §Contrato)."""
    assert round(calculate_vdot(5000, 1163.83), 2) == 51.62  # 5K 19:23,8
    assert round(calculate_vdot(10000, 2425), 2) == 51.32  # 10K 40:25
    assert round(calculate_vdot(21097.5, 5409.188), 2) == 50.88  # Meia 1:30:09
    assert round(calculate_vdot(42195, 13925.76), 2) == 39.48  # Maratona 3:52:05


def test_calculate_vdot_calibration_test_matches_current_vdot() -> None:
    """O teste de calibração vigente (10K em 41:15, 10.012 m medidos) devolve
    o VDOT do vdot_zones.json — a mesma forma fechada que o gerou (o 50.2 do
    arquivo é o round(..., 1) do cálculo)."""
    assert round(calculate_vdot(10012, 2475), 2) == 50.18


def test_equivalent_time_pins_for_current_vdot() -> None:
    """Done-when T1: equivalent_time(50.2, 42.195) ≈ 11.401 s (4:30,2/km — o
    pace de maratona gravado no vdot_zones.json); demais distâncias do contrato."""
    assert round(equivalent_time(50.2, 5.0), 1) == 1191.9
    assert round(equivalent_time(50.2, 10.0), 1) == 2471.1
    assert round(equivalent_time(50.2, 21.0975), 1) == 5472.3
    assert round(equivalent_time(50.2, 42.195), 1) == 11401.4


def test_equivalent_time_inverts_calculate_vdot() -> None:
    """Done-when T1 (inversibilidade): o tempo equivalente devolve o VDOT informado."""
    for distance_km in (5.0, 10.0, 21.0975, 42.195):
        time_s = equivalent_time(50.2, distance_km)
        assert round(calculate_vdot(distance_km * 1000, time_s), 6) == 50.2


def test_speed_for_vo2_inverts_vo2_cost() -> None:
    """Done-when T1: speed_for_vo2(vo2_cost(v)) ≈ v nas velocidades típicas
    (m/min) de easy a repetition."""
    for speed in (150.0, 250.0, 300.0, 375.0):
        assert round(speed_for_vo2(vo2_cost(speed)), 6) == speed


def test_gerar_zonas_50_2_reproduces_calibrated_file() -> None:
    """Done-when T1: o CLI (gerar_zonas) com o VDOT vigente produz zonas
    idênticas às gravadas no vdot_zones.json — o move não alterou o comportamento."""
    with open(ZONES_FILE, encoding="utf-8") as file:
        data = json.load(file)
    assert gerar_zonas(data["vdot"]) == data["zones"]
