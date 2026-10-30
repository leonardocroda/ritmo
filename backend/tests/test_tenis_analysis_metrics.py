"""Métricas derivadas de tênis — funções puras (T3).

Unit, sem DB. Valida running_dynamics_adjusted, ef_factor, hr_drift, fresh_vs_fatigue.
"""

from app.tenis_analysis.metrics import (
    ef_factor,
    fresh_vs_fatigue,
    hr_drift,
    running_dynamics_adjusted,
)


def test_running_dynamics_adjusted_residuals() -> None:
    """Done-when T3: resíduos de regressão linear de GCT vs pace."""
    runs = [
        {"pace_s": 300, "gct_ms": 250},
        {"pace_s": 320, "gct_ms": 260},
        {"pace_s": 340, "gct_ms": 270},
    ]
    result = running_dynamics_adjusted(runs)
    assert result is not None
    assert "gct_ms" in result
    assert len(result["gct_ms"]) == 3


def test_running_dynamics_adjusted_insufficient_data() -> None:
    """Done-when T3: menos de 2 pontos -> métrica omitida."""
    runs = [{"pace_s": 300, "gct_ms": 250}]
    result = running_dynamics_adjusted(runs)
    assert result == {} or result is None


def test_running_dynamics_adjusted_no_data() -> None:
    """Done-when T3: sem dado -> None."""
    assert running_dynamics_adjusted([]) is None
    assert running_dynamics_adjusted([{"pace_s": 300}]) is None


def test_ef_factor() -> None:
    """Done-when T3: EF = velocidade / FC média."""
    runs = [
        {"pace_s": 300, "avg_hr": 160},  # 12 km/h / 160 = 0.075
        {"pace_s": 360, "avg_hr": 150},  # 10 km/h / 150 = 0.0667
        {"pace_s": 300, "avg_hr": None},  # sem FC -> omitido
    ]
    result = ef_factor(runs)
    assert result is not None
    assert len(result) == 2
    assert result[0] == 0.075


def test_ef_factor_no_data() -> None:
    """Done-when T3: sem FC em nenhuma -> None."""
    assert ef_factor([{"pace_s": 300}]) is None
    assert ef_factor([]) is None


def test_hr_drift_only_when_pace_stable() -> None:
    """Done-when T3: drift só se pace estável entre metades (<=5%)."""
    # pace estável nas duas metades
    runs = [
        {
            "splits": [
                {"avg_hr": 150, "pace_s": 300},
                {"avg_hr": 155, "pace_s": 305},
                {"avg_hr": 160, "pace_s": 300},
                {"avg_hr": 165, "pace_s": 305},
            ]
        }
    ]
    result = hr_drift(runs)
    assert result is not None
    assert result[0] is not None
    assert result[0] > 0  # FC subiu na 2ª metade


def test_hr_drift_omitted_when_pace_unstable() -> None:
    """Done-when T3: pace instável (>5%) -> drift omitido (None)."""
    runs = [
        {
            "splits": [
                {"avg_hr": 150, "pace_s": 300},
                {"avg_hr": 155, "pace_s": 300},
                {"avg_hr": 160, "pace_s": 400},  # pace muito mais lento
                {"avg_hr": 165, "pace_s": 400},
            ]
        }
    ]
    result = hr_drift(runs)
    assert result is not None
    assert result[0] is None


def test_hr_drift_insufficient_splits() -> None:
    """Done-when T3: menos de 2 splits -> None."""
    assert hr_drift([{"splits": [{"avg_hr": 150, "pace_s": 300}]}]) == [None]
    assert hr_drift([]) is None


def test_fresh_vs_fatigue() -> None:
    """Done-when T3: primeiros ~30% vs últimos ~30% da distância."""
    runs = [
        {
            "splits": [
                {"dist_m": 1000, "pace_s": 300, "avg_hr": 150},
                {"dist_m": 1000, "pace_s": 300, "avg_hr": 150},
                {"dist_m": 1000, "pace_s": 320, "avg_hr": 160},
                {"dist_m": 1000, "pace_s": 340, "avg_hr": 170},
            ]
        }
    ]
    result = fresh_vs_fatigue(runs)
    assert result is not None
    assert len(result) == 1
    # pace aumentou (ficou mais lento) no final -> delta positivo
    assert result[0]["pace_delta_s"] is not None
    assert result[0]["pace_delta_s"] > 0
    assert result[0]["fc_delta"] is not None
    assert result[0]["fc_delta"] > 0


def test_fresh_vs_fatigue_insufficient() -> None:
    """Done-when T3: 1 split -> omitido."""
    assert fresh_vs_fatigue([{"splits": [{"dist_m": 1000, "pace_s": 300}]}]) is None
    assert fresh_vs_fatigue([]) is None
