"""Baseline de degradação — funções puras (T1).

Unit, sem DB. Valida build_baseline.
"""

from app.tenis_degradation.baseline import build_baseline


def _run(distance_m, inferred_type="running", pace_s=360, start_time="2024-01-15"):
    return {
        "distance_m": distance_m,
        "duration_s": pace_s * distance_m / 1000,
        "pace_s": pace_s,
        "avg_hr": 160,
        "inferred_type": inferred_type,
        "start_time": start_time,
    }


def test_baseline_splits_initial_and_final() -> None:
    """Done-when T1: separados por distância acumulada (não data)."""
    runs = [_run(60000), _run(60000), _run(60000)]  # 180 km total (>150)
    result = build_baseline(runs)
    assert result is not None
    assert result["insufficient"] is False
    assert result["total_km"] == 180.0
    # inicial: primeiros 100 km (2 primeiros runs = 120 km, então pelo menos 1 entra)
    assert len(result["initial_runs"]) >= 1
    # final: últimos 50 km (último run de 60 km entra)
    assert len(result["final_runs"]) >= 1


def test_baseline_insufficient_under_150km() -> None:
    """Done-when T1: menos de 150 km -> dados insuficientes."""
    runs = [_run(50000), _run(50000)]  # 100 km
    result = build_baseline(runs)
    assert result is not None
    assert result["insufficient"] is True
    assert result["initial_runs"] == []
    assert result["final_runs"] == []


def test_baseline_empty() -> None:
    """Done-when T1: sem runs -> None."""
    assert build_baseline([]) is None


def test_baseline_orders_by_distance_not_date() -> None:
    """Done-when T1: ordena por distância acumulada, não por data."""
    runs = [
        _run(80000, start_time="2024-01-20"),  # mais recente
        _run(40000, start_time="2024-01-10"),  # mais antiga
        _run(40000, start_time="2024-01-15"),
    ]  # 160 km total
    result = build_baseline(runs)
    assert result is not None
    # Ordenado por distância acumulada: 40, 40, 80 km
    assert result["initial_runs"][0]["distance_m"] == 40000
    assert result["final_runs"][-1]["distance_m"] == 80000
