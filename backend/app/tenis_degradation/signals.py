"""Sinais de degradação: Δ entre janela inicial e final.

Funções puras: recebem runs da janela inicial e final, calculam Δ para
cada métrica disponível. "Sinais, não veredito" — nunca diz "aposentar".

Sinais: ΔGCT, Δoscilação vertical, Δcadência, ΔEF (velocidade/FC),
ΔHR drift, Δ feel-RPE.
"""

from statistics import mean

from app.tenis_analysis.metrics import ef_factor, hr_drift


def _mean_or_none(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(mean(vals), 2) if vals else None


def _avg_field(runs: list[dict], field: str) -> float | None:
    return _mean_or_none([r.get(field) for r in runs])


def compute_signals(initial_runs: list[dict], final_runs: list[dict]) -> dict:
    """Calcula sinais de degradação entre janela inicial e final.

    Returns:
        dict com:
          - signals: list de {sinal, inicial, final, delta, direcao, confianca}
          - n_signals: int
          - verdict: sempre None ("sinais, não veredito")
    """
    signals: list[dict] = []

    # ΔGCT
    gct_i = _avg_field(initial_runs, "gct_ms")
    gct_f = _avg_field(final_runs, "gct_ms")
    if gct_i is not None and gct_f is not None:
        signals.append(_signal("gct_ms", gct_i, gct_f, "ms", "GCT"))

    # Δoscilação vertical
    osc_i = _avg_field(initial_runs, "vert_osc_cm")
    osc_f = _avg_field(final_runs, "vert_osc_cm")
    if osc_i is not None and osc_f is not None:
        signals.append(_signal("vert_osc_cm", osc_i, osc_f, "cm", "Oscilação vertical"))

    # Δcadência
    cad_i = _avg_field(initial_runs, "avg_cadence")
    cad_f = _avg_field(final_runs, "avg_cadence")
    if cad_i is not None and cad_f is not None:
        signals.append(_signal("avg_cadence", cad_i, cad_f, "spm", "Cadência"))

    # ΔEF
    ef_i = ef_factor(initial_runs)
    ef_f = ef_factor(final_runs)
    if ef_i and ef_f:
        signals.append(
            _signal("ef", mean(ef_i), mean(ef_f), "EF", "EF (velocidade/FC)")
        )

    # ΔHR drift
    drift_i = hr_drift(initial_runs)
    drift_f = hr_drift(final_runs)
    drift_i_valid = [d for d in (drift_i or []) if d is not None]
    drift_f_valid = [d for d in (drift_f or []) if d is not None]
    if drift_i_valid and drift_f_valid:
        signals.append(
            _signal("hr_drift", mean(drift_i_valid), mean(drift_f_valid), "bpm", "HR drift")
        )

    # Δ feel-RPE (se houver)
    feel_i = _avg_field(initial_runs, "rpe")
    feel_f = _avg_field(final_runs, "rpe")
    if feel_i is not None and feel_f is not None:
        signals.append(_signal("rpe", feel_i, feel_f, "pontos", "feel-RPE"))

    # Direção: piorou se delta > 0 (para GCT, oscilação, cadência, HR drift, feel)
    # Melhorou se delta > 0 (para EF)
    piora_sinais = {"gct_ms", "vert_osc_cm", "avg_cadence", "hr_drift", "rpe"}

    resultado = []
    for s in signals:
        direcao = "estável"
        if abs(s["delta"]) > 0.01:
            if s["sinal"] in piora_sinais:
                direcao = "piorou" if s["delta"] > 0 else "melhorou"
            else:  # EF
                direcao = "melhorou" if s["delta"] > 0 else "piorou"
        s["direcao"] = direcao
        s["confianca"] = "baixa" if len(initial_runs) < 3 or len(final_runs) < 3 else "media"
        resultado.append(s)

    return {
        "signals": resultado,
        "n_signals": len(resultado),
        "verdict": None,  # sinais, não veredito — nunca "aposentar"
    }


def _signal(name: str, inicial: float, final: float, unidade: str, label: str) -> dict:
    delta = round(final - inicial, 2)
    return {
        "sinal": name,
        "label": label,
        "inicial": round(inicial, 2),
        "final": round(final, 2),
        "delta": delta,
        "unidade": unidade,
    }
