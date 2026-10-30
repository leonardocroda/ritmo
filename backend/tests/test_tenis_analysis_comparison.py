"""Comparação pareada + nível de confiança — funções puras (T2).

Unit, sem DB. Valida build_matched_pairs, confidence_level, build_comparison_result.
"""

from app.tenis_analysis.comparison import build_comparison_result, build_matched_pairs, confidence_level


def _run(shoe_id, distance_m, duration_s, avg_hr=160):
    return {
        "shoe_id": shoe_id,
        "distance_m": distance_m,
        "duration_s": duration_s,
        "avg_hr": avg_hr,
    }


def test_matched_pairs_distance_and_pace_within_5pct() -> None:
    """Done-when T2: pares formados com distância ±5% e pace ±5%."""
    runs_a = [_run(1, 5000, 1500)]  # pace 300 s/km
    runs_b = [_run(2, 5100, 1530)]  # pace 300 s/km, dist +2%
    pairs = build_matched_pairs(runs_a, runs_b)
    assert len(pairs) == 1
    assert pairs[0]["delta_pace_s"] == 0.0


def test_matched_pairs_outside_tolerance_no_pair() -> None:
    """Done-when T2: distância ou pace fora de ±5% -> sem par."""
    runs_a = [_run(1, 5000, 1500)]  # pace 300
    runs_b = [_run(2, 6000, 1500)]  # dist +20%, pace 250
    pairs = build_matched_pairs(runs_a, runs_b)
    assert pairs == []


def test_matched_pairs_date_is_free() -> None:
    """Done-when T2: data não é critério; corridas em dias diferentes podem formar par."""
    runs_a = [_run(1, 5000, 1500)]
    runs_b = [_run(2, 5000, 1500)]
    pairs = build_matched_pairs(runs_a, runs_b)
    assert len(pairs) == 1


def test_matched_pairs_multiple_runs() -> None:
    """Done-when T2: múltiplos runs geram múltiplos pares válidos."""
    runs_a = [_run(1, 5000, 1500), _run(1, 10000, 3000)]
    runs_b = [_run(2, 5050, 1515), _run(2, 10100, 3020)]
    pairs = build_matched_pairs(runs_a, runs_b)
    assert len(pairs) == 2


def test_confidence_level_baixo_medio_alto() -> None:
    """Done-when T2: <3 baixo, 3–5 médio, >5 alto."""
    assert confidence_level(0) == "baixo"
    assert confidence_level(2) == "baixo"
    assert confidence_level(3) == "medio"
    assert confidence_level(5) == "medio"
    assert confidence_level(6) == "alto"


def test_comparison_result_structure() -> None:
    """Done-when T2: resultado tem n_pairs, confidence e pairs."""
    runs_a = [_run(1, 5000, 1500)] * 4
    runs_b = [_run(2, 5000, 1500)] * 4
    result = build_comparison_result(runs_a, runs_b)
    assert result["n_pairs"] == 16  # 4 x 4
    assert result["confidence"] == "alto"
    assert len(result["pairs"]) == 16
