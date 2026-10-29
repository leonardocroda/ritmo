"""Mapper de splits com running dynamics — funções puras (T2).

Unit, sem DB: `map_splits` extrai groundContactTime→gct_ms,
strideLength→stride_cm, verticalOscillation→vert_osc_cm,
verticalRatio→vert_ratio de cada lapDTO. Ausente = None, nunca zero.
lapDTO None/vazio → [].
"""

from app.garmin.mappers import map_splits


def _lap(with_dynamics: bool = True) -> dict:
    base = {
        "lapIndex": 1,
        "distance": 1000.0,
        "duration": 360.0,
        "averageHR": 160,
        "averageRunCadence": 175.0,
        "averageTemperature": 22.0,
        "elevationGain": 5.0,
        "intensityType": "ACTIVE",
    }
    if with_dynamics:
        base.update(
            {
                "groundContactTime": 250,
                "strideLength": 145.5,
                "verticalOscillation": 8.2,
                "verticalRatio": 5.8,
            }
        )
    return base


def test_map_splits_with_running_dynamics() -> None:
    """Done-when T2: lapDTO com as 4 métricas → chaves gct_ms, stride_cm,
    vert_osc_cm, vert_ratio com os valores."""
    rows = map_splits({"lapDTOs": [_lap(True)]})
    assert len(rows) == 1
    assert rows[0]["gct_ms"] == 250
    assert rows[0]["stride_cm"] == 145.5
    assert rows[0]["vert_osc_cm"] == 8.2
    assert rows[0]["vert_ratio"] == 5.8


def test_map_splits_missing_dynamics_none() -> None:
    """Done-when T2: campo ausente no lapDTO → None (não zero, não falha)."""
    rows = map_splits({"lapDTOs": [_lap(False)]})
    assert len(rows) == 1
    assert rows[0]["gct_ms"] is None
    assert rows[0]["stride_cm"] is None
    assert rows[0]["vert_osc_cm"] is None
    assert rows[0]["vert_ratio"] is None


def test_map_splits_partial_dynamics() -> None:
    """Done-when T2: lapDTO com só parte das métricas → presente tem valor,
    ausente é None."""
    lap = _lap(False)
    lap["groundContactTime"] = 260
    lap["verticalOscillation"] = 7.9
    rows = map_splits({"lapDTOs": [lap]})
    assert rows[0]["gct_ms"] == 260
    assert rows[0]["stride_cm"] is None
    assert rows[0]["vert_osc_cm"] == 7.9
    assert rows[0]["vert_ratio"] is None


def test_map_splits_empty_lapdto() -> None:
    """Done-when T2: lapDTO None/vazio → [] sem warning (mesmo comportamento
    de splits comuns)."""
    assert map_splits(None) == []
    assert map_splits({"lapDTOs": []}) == []
    assert map_splits({}) == []


def test_map_splits_direct_list_shape() -> None:
    """Done-when T2: shape lista direta (não dict com lapDTOs) funciona com
    running dynamics."""
    rows = map_splits([_lap(True)])
    assert len(rows) == 1
    assert rows[0]["gct_ms"] == 250
    assert rows[0]["stride_cm"] == 145.5


def test_map_splits_preserves_existing_fields() -> None:
    """Done-when T2: campos existentes (idx, dist_m, pace_s, avg_hr, etc.)
    continuam presentes junto dos novos."""
    rows = map_splits({"lapDTOs": [_lap(True)]})
    r = rows[0]
    assert r["idx"] == 1
    assert r["dist_m"] == 1000.0
    assert r["duration_s"] == 360.0
    assert r["pace_s"] == 360.0
    assert r["avg_hr"] == 160
    assert r["avg_cadence"] == 175.0
