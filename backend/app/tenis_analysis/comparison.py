"""Comparação pareada (matched runs) entre dois tênis + nível de confiança.

Funções puras: recebem listas de runs (já lidas do banco) e devolvem pares
válidos + nível de confiança. Não grava nada no banco.

Critério de par válido (decidido pelo usuário, Guided):
  - distância dentro de ±5% E pace médio dentro de ±5% entre os dois tênis
  - data livre: não é critério de proximidade

Nível de confiança (Opção C, decidido pelo usuário):
  - <3 pares: baixo
  - 3–5 pares: médio
  - >5 pares: alto
"""

from collections import defaultdict


def _pace_s(distance_m: float | None, duration_s: float | None) -> float | None:
    if not distance_m or not duration_s or distance_m <= 0:
        return None
    return duration_s * 1000 / distance_m


def _within_pct(value_a: float, value_b: float, pct: float) -> bool:
    if value_a <= 0 or value_b <= 0:
        return False
    return abs(value_a - value_b) / max(value_a, value_b) <= pct / 100.0


def build_matched_pairs(
    runs_a: list[dict], runs_b: list[dict], dist_pct: float = 5.0, pace_pct: float = 5.0
) -> list[dict]:
    """Forma pares de corridas (um de cada tênis) com distância e pace próximos.

    Args:
        runs_a: runs do tênis A (dicts com distance_m, duration_s, avg_hr, etc.)
        runs_b: runs do tênis B
        dist_pct: tolerância de distância em %
        pace_pct: tolerância de pace em %

    Returns:
        lista de dicts com: tênis A, tênis B, distância, pace A, pace B,
        delta pace (B - A), FC média A, FC média B, delta FC.
    """
    pairs: list[dict] = []
    for ra in runs_a:
        da = ra.get("distance_m")
        pa = _pace_s(da, ra.get("duration_s"))
        if da is None or pa is None:
            continue
        for rb in runs_b:
            db = rb.get("distance_m")
            pb = _pace_s(db, rb.get("duration_s"))
            if db is None or pb is None:
                continue
            if not _within_pct(da, db, dist_pct):
                continue
            if not _within_pct(pa, pb, pace_pct):
                continue
            fca = ra.get("avg_hr")
            fcb = rb.get("avg_hr")
            pairs.append(
                {
                    "shoe_a_id": ra.get("shoe_id"),
                    "shoe_b_id": rb.get("shoe_id"),
                    "distance_m": round((da + db) / 2, 1),
                    "pace_a_s": round(pa, 1),
                    "pace_b_s": round(pb, 1),
                    "delta_pace_s": round(pb - pa, 1),
                    "fc_a": fca,
                    "fc_b": fcb,
                    "delta_fc": round((fcb or 0) - (fca or 0), 1)
                    if fca is not None and fcb is not None
                    else None,
                }
            )
    return pairs


def confidence_level(n_pairs: int) -> str:
    """Nível de confiança baseado na quantidade de pares válidos.

    <3: baixo, 3–5: médio, >5: alto.
    """
    if n_pairs < 3:
        return "baixo"
    if n_pairs <= 5:
        return "medio"
    return "alto"


def build_comparison_result(
    runs_a: list[dict], runs_b: list[dict]
) -> dict:
    """Resultado completo de comparação entre dois tênis.

    Retorna pares, nível de confiança e quantidade de pares.
    """
    pairs = build_matched_pairs(runs_a, runs_b)
    return {
        "n_pairs": len(pairs),
        "confidence": confidence_level(len(pairs)),
        "pairs": pairs,
    }
