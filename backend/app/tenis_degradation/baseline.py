"""Baseline de degradação: primeiros ~100 km vs últimos ~50 km por tênis.

Funções puras: recebem runs ordenados por distância acumulada e separam
em janela inicial e final. Menos de ~150 km totais → dados insuficientes.

Cada run dict esperado:
    distance_m, duration_s, pace_s, avg_hr, avg_cadence, inferred_type,
    start_time, shoe_id, splits (lista opcional)
"""

KM_BASELINE_INITIAL = 100.0  # km
KM_BASELINE_FINAL = 50.0     # km
KM_MIN_TOTAL = 150.0         # km mínimo para ter janela final significativa


def _accumulated_km(runs: list[dict]) -> list[tuple[dict, float]]:
    """Retorna (run, km_acumulada) ordenado por distância acumulada.

    A km acumulada é a soma de distance_m dos runs anteriores + a própria.
    Ordena por start_time como desempate (mas a janela é por distância).
    """
    ordered = sorted(runs, key=lambda r: (r.get("start_time") or "", r.get("id") or 0))
    cum = 0.0
    out = []
    for r in ordered:
        cum += (r.get("distance_m") or 0) / 1000.0
        out.append((r, cum))
    return out


def build_baseline(runs: list[dict]) -> dict | None:
    """Separa corridas em janela inicial (~100 km) e final (~50 km).

    Args:
        runs: lista de dicts de corridas de um mesmo tênis.

    Returns:
        dict com:
          - total_km: float
          - n_runs: int
          - initial_runs: list[dict] (primeiros ~100 km)
          - final_runs: list[dict] (últimos ~50 km)
          - insufficient: bool (True se < ~150 km totais)
        None se não houver runs.
    """
    if not runs:
        return None

    ordered = _accumulated_km(runs)
    total_km = ordered[-1][1] if ordered else 0.0

    if total_km < KM_MIN_TOTAL:
        return {
            "total_km": round(total_km, 2),
            "n_runs": len(runs),
            "insufficient": True,
            "initial_runs": [],
            "final_runs": [],
        }

    initial_runs: list[dict] = []
    final_runs: list[dict] = []
    for run, cum_km in ordered:
        if cum_km <= KM_BASELINE_INITIAL:
            initial_runs.append(run)
        if cum_km > (total_km - KM_BASELINE_FINAL):
            final_runs.append(run)

    return {
        "total_km": round(total_km, 2),
        "n_runs": len(runs),
        "insufficient": False,
        "initial_runs": initial_runs,
        "final_runs": final_runs,
    }
