"""Métricas derivadas de tênis: running dynamics ajustados, EF, HR drift, janela fresco vs fadiga.

Funções puras: recebem listas de runs/splits já lidas do banco.
"""

from statistics import mean


def _linear_regression_residuals(x: list[float], y: list[float]) -> list[float]:
    """Resíduos de regressão linear simples y = a*x + b. Retorna y_pred - y_real (resíduo)."""
    n = len(x)
    if n < 2:
        return []
    mx = mean(x)
    my = mean(y)
    denom = sum((xi - mx) ** 2 for xi in x)
    if denom == 0:
        return [0.0] * n
    slope = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / denom
    intercept = my - slope * mx
    return [slope * xi + intercept - yi for xi, yi in zip(x, y)]


def running_dynamics_adjusted(runs_with_rd: list[dict]) -> dict | None:
    """Running dynamics ajustados por ritmo via resíduo de regressão.

    Para cada métrica (GCT, passada, oscilação), regressa contra o pace
    da corrida e retorna os resíduos (desvio do esperado pelo ritmo).
    Só inclui métricas que tenham dado em pelo menos 2 corridas.

    Args:
        runs_with_rd: lista de dicts com pace_s e, opcionalmente,
                      gct_ms, stride_cm, vert_osc_cm.

    Returns:
        dict com resíduos por métrica, ou None se não houver dado suficiente.
    """
    result: dict = {}
    for field, label in (
        ("gct_ms", "gct_ms"),
        ("stride_cm", "stride_cm"),
        ("vert_osc_cm", "vert_osc_cm"),
    ):
        xs = [r["pace_s"] for r in runs_with_rd if r.get("pace_s") and r.get(field)]
        ys = [r[field] for r in runs_with_rd if r.get("pace_s") and r.get(field)]
        if len(xs) >= 2:
            residuals = _linear_regression_residuals(xs, ys)
            result[label] = [round(r, 2) for r in residuals]
    return result or None


def ef_factor(runs: list[dict]) -> dict | None:
    """EF (Efficiency Factor) = velocidade / FC média por corrida.

    Retorna lista de EFs por corrida (só onde houver FC). None se nenhuma.
    """
    efs = []
    for r in runs:
        pace_s = r.get("pace_s")
        fc = r.get("avg_hr")
        if pace_s and pace_s > 0 and fc:
            velocidade_km_h = 3600 / pace_s  # pace_s é s/km -> km/h
            efs.append(round(velocidade_km_h / fc, 4))
    return efs or None


def hr_drift(runs_with_splits: list[dict]) -> list[float | None] | None:
    """HR drift = FC 2ª metade − FC 1ª metade, só se pace estável entre metades.

    Pace estável: Δ pace entre metades <= 5% (AD-005: drift só se interpreta a ritmo constante).
    Retorna None se nenhuma corrida tem dado suficiente.
    """
    drifts: list[float | None] = []
    for r in runs_with_splits:
        splits = r.get("splits") or []
        if len(splits) < 2:
            drifts.append(None)
            continue
        mid = len(splits) // 2
        first_half = splits[:mid]
        second_half = splits[mid:]
        fcs_first = [s.get("avg_hr") for s in first_half if s.get("avg_hr")]
        fcs_second = [s.get("avg_hr") for s in second_half if s.get("avg_hr")]
        paces_first = [s.get("pace_s") for s in first_half if s.get("pace_s")]
        paces_second = [s.get("pace_s") for s in second_half if s.get("pace_s")]
        if not fcs_first or not fcs_second or not paces_first or not paces_second:
            drifts.append(None)
            continue
        pace_first = mean(paces_first)
        pace_second = mean(paces_second)
        if pace_first <= 0:
            drifts.append(None)
            continue
        pace_delta_pct = abs(pace_second - pace_first) / pace_first * 100
        if pace_delta_pct > 5:
            drifts.append(None)  # não é ritmo constante, drift não interpreta
            continue
        drift = mean(fcs_second) - mean(fcs_first)
        drifts.append(round(drift, 1))
    return drifts or None


def fresh_vs_fatigue(runs_with_splits: list[dict]) -> dict | None:
    """Janela fresco vs fadiga: primeiros ~30% vs últimos ~30% da distância.

    Retorna delta de pace e FC entre janela final e inicial, por corrida.
    None se não houver dado suficiente.
    """
    results: list[dict] = []
    for r in runs_with_splits:
        splits = r.get("splits") or []
        if len(splits) < 2:
            continue
        total_dist = sum(s.get("dist_m") or 0 for s in splits)
        if total_dist <= 0:
            continue
        cutoff = total_dist * 0.30
        cum = 0.0
        first_idx = 0
        for i, s in enumerate(splits):
            cum += s.get("dist_m") or 0
            if cum >= cutoff:
                first_idx = i
                break
        # janela inicial: até first_idx (inclusive); janela final: últimos 30% da distância
        cum = 0.0
        last_idx = len(splits) - 1
        for i in range(len(splits) - 1, -1, -1):
            cum += splits[i].get("dist_m") or 0
            if cum >= cutoff:
                last_idx = i
                break
        if last_idx <= first_idx:
            continue
        first_window = splits[: first_idx + 1]
        last_window = splits[last_idx:]
        pace_first = mean([s["pace_s"] for s in first_window if s.get("pace_s")]) or None
        pace_last = mean([s["pace_s"] for s in last_window if s.get("pace_s")]) or None
        fc_first = mean([s["avg_hr"] for s in first_window if s.get("avg_hr")]) or None
        fc_last = mean([s["avg_hr"] for s in last_window if s.get("avg_hr")]) or None
        results.append(
            {
                "pace_delta_s": round(pace_last - pace_first, 1)
                if pace_first and pace_last
                else None,
                "fc_delta": round(fc_last - fc_first, 1)
                if fc_first and fc_last
                else None,
            }
        )
    return results or None
