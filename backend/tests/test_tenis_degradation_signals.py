"""Sinais de degradação — funções puras (T3).

Unit, sem DB. Valida compute_signals.
"""

from app.tenis_degradation.signals import compute_signals


def _run(gct_ms=None, vert_osc_cm=None, avg_cadence=None, rpe=None, pace_s=360, avg_hr=160):
    return {
        "gct_ms": gct_ms,
        "vert_osc_cm": vert_osc_cm,
        "avg_cadence": avg_cadence,
        "rpe": rpe,
        "pace_s": pace_s,
        "avg_hr": avg_hr,
        "distance_m": 5000,
        "duration_s": pace_s * 5000 / 1000,
    }


def test_signals_computes_deltas() -> None:
    """Done-when T3: calcula Δ entre janela inicial e final."""
    initial = [_run(gct_ms=250, vert_osc_cm=8.0, avg_cadence=170, rpe=4)]
    final = [_run(gct_ms=270, vert_osc_cm=9.0, avg_cadence=175, rpe=6)]
    result = compute_signals(initial, final)
    assert result["verdict"] is None  # sinais, não veredito
    sinais = {s["sinal"]: s for s in result["signals"]}
    assert sinais["gct_ms"]["delta"] == 20.0
    assert sinais["vert_osc_cm"]["delta"] == 1.0
    assert sinais["avg_cadence"]["delta"] == 5.0
    assert sinais["rpe"]["delta"] == 2.0


def test_signals_omits_missing_data() -> None:
    """Done-when T3: sinal sem dado -> omitido."""
    initial = [_run(gct_ms=250)]  # sem oscilação
    final = [_run(vert_osc_cm=9.0)]  # sem GCT
    result = compute_signals(initial, final)
    sinais = {s["sinal"]: s for s in result["signals"]}
    assert "gct_ms" not in sinais  # final não tem GCT
    assert "vert_osc_cm" not in sinais  # inicial não tem oscilação


def test_signals_empty() -> None:
    """Done-when T3: sem dados -> lista vazia, verdict None."""
    result = compute_signals([], [])
    assert result["signals"] == []
    assert result["n_signals"] == 0
    assert result["verdict"] is None
