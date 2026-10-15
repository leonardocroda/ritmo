"""Métricas de consistência — funções puras sobre as voltas (design).

Sem DB, sem I/O — a mesma atividade devolve sempre os mesmos valores
(AD-003, TRN-23). As metades são por distância acumulada (premissa do
spec): a volta que atravessa os 50% fica na 1ª metade — mais honesto
que dividir por contagem quando há voltas de tamanho variável.

Gate (spec): só há bloco `consistency` para corridas com
``distance_m >= 8000`` e >= 4 voltas (limites inclusivos). O fade de
cadência só existe com >= 2 voltas com cadência em cada metade —
nenhum número inventado (spec).

Convenções numéricas: campos de porcentagem com 1 decimal; médias de
FC/cadência ponderadas pela duração da volta (mesma convenção da
temperatura no spec); pace da metade = tempo total / distância total
das voltas com pace válido — voltas sem pace não entram nas médias.
"""

from collections.abc import Sequence

# Limites inclusivos do gate (spec: corridas >=8km com >=4 voltas)
MIN_DISTANCE_M = 8000
MIN_SPLITS = 4
MIN_CADENCE_LAPS_PER_HALF = 2


def split_halves(splits: Sequence) -> tuple[list, list]:
    """Divide as voltas em (1ª metade, 2ª metade) por distância acumulada.

    A volta que atinge >=50% da distância total fecha a 1ª metade e
    fica nela (premissa do spec — o atravessamento parcial é a
    imprecisão documentada).
    """
    total = sum(s.dist_m or 0 for s in splits)
    target = total / 2
    first: list = []
    second: list = []
    accumulated = 0.0
    closed = False
    for split in splits:
        if closed:
            second.append(split)
            continue
        first.append(split)
        accumulated += split.dist_m or 0
        if total > 0 and accumulated >= target:
            closed = True
    return first, second


def _valid_pace(split) -> bool:
    """Pace válido: distância e duração > 0 (edge do spec: pace=null caso contrário)."""
    return bool(split.dist_m and split.dist_m > 0 and split.duration_s and split.duration_s > 0)


def _half_pace(splits: Sequence) -> float | None:
    """Pace da metade (s/km): tempo total / distância total das voltas com pace válido."""
    distance = sum(s.dist_m for s in splits if _valid_pace(s))
    duration = sum(s.duration_s for s in splits if _valid_pace(s))
    if distance <= 0 or duration <= 0:
        return None
    return duration / distance * 1000


def _weighted_mean(splits: Sequence, attr: str) -> float | None:
    """Média ponderada pela duração de um campo opcional; None sem dados."""
    weighted = [
        (getattr(s, attr), s.duration_s)
        for s in splits
        if getattr(s, attr) is not None and s.duration_s and s.duration_s > 0
    ]
    total_weight = sum(w for _, w in weighted)
    if total_weight <= 0:
        return None
    return sum(v * w for v, w in weighted) / total_weight


def _count_with(splits: Sequence, attr: str) -> int:
    return sum(1 for s in splits if getattr(s, attr) is not None)


def _decoupling(pace_first: float | None, pace_second: float | None,
                hr_first: float | None, hr_second: float | None) -> float | None:
    """Variação % do razão FC-média/pace-médio entre metades (premissa do spec)."""
    if pace_first is None or pace_second is None or hr_first is None or hr_second is None:
        return None
    if pace_first <= 0 or hr_first <= 0:
        return None
    ratio_first = hr_first / pace_first
    ratio_second = hr_second / pace_second
    return round((ratio_second - ratio_first) / ratio_first * 100, 1)


def consistency_metrics(splits: Sequence, distance_m: float) -> dict | None:
    """Bloco `consistency` do detalhe; None abaixo do gate (spec).

    Equilíbrio (Δ pace s/km + %), drift cardíaco (Δ bpm), decoupling (%)
    e fade de cadência (Δ spm, omitido sem cadência suficiente).
    """
    if distance_m < MIN_DISTANCE_M or len(splits) < MIN_SPLITS:
        return None

    first, second = split_halves(splits)
    pace_first = _half_pace(first)
    pace_second = _half_pace(second)
    hr_first = _weighted_mean(first, "avg_hr")
    hr_second = _weighted_mean(second, "avg_hr")

    metrics: dict = {
        "first_half_pace_s": pace_first,
        "second_half_pace_s": pace_second,
        "balance_delta_s": (
            pace_second - pace_first
            if pace_first is not None and pace_second is not None
            else None
        ),
        "balance_delta_pct": (
            round((pace_second - pace_first) / pace_first * 100, 1)
            if pace_first is not None and pace_second is not None
            else None
        ),
        "first_half_hr": hr_first,
        "second_half_hr": hr_second,
        "hr_drift_bpm": (
            hr_second - hr_first if hr_first is not None and hr_second is not None else None
        ),
        "decoupling_pct": _decoupling(pace_first, pace_second, hr_first, hr_second),
    }

    # Fade de cadência só com >= 2 voltas com cadência em cada metade (spec)
    if (
        _count_with(first, "avg_cadence") >= MIN_CADENCE_LAPS_PER_HALF
        and _count_with(second, "avg_cadence") >= MIN_CADENCE_LAPS_PER_HALF
    ):
        cadence_first = _weighted_mean(first, "avg_cadence")
        cadence_second = _weighted_mean(second, "avg_cadence")
        if cadence_first is not None and cadence_second is not None:
            metrics["cadence_fade_spm"] = cadence_second - cadence_first
    return metrics
