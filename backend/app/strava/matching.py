"""Matching Strava↔Garmin (funções puras) — sem DB, 100% testável.

- garmin_id_from_external_id: regex ^garmin_push_(\\d+)$
- find_match: fallback ±2% distância, ±2% moving_time, ±5h start;
  0 ou 2+ candidatos → "ambiguous" (nunca casa).
"""

import re
from datetime import datetime
from typing import Any


# Regex para extrair Garmin activity ID do external_id do Strava
GARMIN_EXTERNAL_ID_PATTERN = re.compile(r"^garmin_push_(\d+)$")


def garmin_id_from_external_id(external_id: str | None) -> str | None:
    """Extrai Garmin activity ID do external_id do Strava.

    Args:
        external_id: ex. "garmin_push_1234567890" ou None

    Returns:
        ID como string (ex. "1234567890") ou None se não casar.
    """
    if not external_id:
        return None
    match = GARMIN_EXTERNAL_ID_PATTERN.match(external_id)
    if match:
        return match.group(1)
    return None


def _within_tolerance(actual: float, expected: float, pct: float) -> bool:
    """Verifica se actual está dentro de ±pct% de expected."""
    if expected == 0:
        return False  # distância 0 não casa (esteira sem GPS)
    return abs(actual - expected) <= expected * (pct / 100.0)


def _time_within_5h(strava_start: str, garmin_start: datetime) -> bool:
    """Verifica se a diferença entre start_date (GMT ISO) e start_time (wall clock) ≤ 5h."""
    try:
        # Strava start_date vem em GMT (ex: "2024-01-15T07:00:00Z")
        # Convertemos para datetime aware UTC e depois para naive UTC
        strava_dt = datetime.fromisoformat(strava_start.replace("Z", "+00:00"))
        strava_dt = strava_dt.replace(tzinfo=None)  # naive UTC
    except (ValueError, AttributeError):
        return False
    # strava_dt é naive UTC, garmin_start é wall clock local naive
    # A diferença absoluta deve ser ≤ 5h (cobre fuso GMT→local para runs noturnas)
    diff = abs((strava_dt - garmin_start).total_seconds())
    return diff <= 5 * 3600  # 5 horas em segundos


def find_match(
    strava_activity: dict[str, Any], candidates: list[dict[str, Any]]
) -> int | None | str:
    """Encontra match entre atividade Strava e candidatos Garmin.

    Critérios de fallback (quando external_id não casa):
    - |Δdistance| ≤ 2%
    - |Δmoving_time| ≤ 2%
    - |Δstart| ≤ 5h (janela cobre fuso GMT→wall clock)

    Args:
        strava_activity: dict com distance (m), moving_time (s), start_date (ISO GMT)
        candidates: lista de dicts com distance_m, duration_s, start_time (datetime)

    Returns:
        int (activity_id) se match único,
        None se nenhum candidato,
        "ambiguous" se 2+ candidatos (nunca casa).
    """
    strava_dist = strava_activity.get("distance", 0.0)
    strava_time = strava_activity.get("moving_time", 0)
    strava_start = strava_activity.get("start_date")

    if strava_dist == 0 or strava_time == 0 or not strava_start:
        return None

    matches = []
    for cand in candidates:
        cand_dist = cand.get("distance_m", 0.0)
        cand_time = cand.get("duration_s", 0)
        cand_start = cand.get("start_time")

        if cand_dist == 0 or cand_time == 0 or cand_start is None:
            continue

        dist_ok = _within_tolerance(cand_dist, strava_dist, 2.0)
        time_ok = _within_tolerance(cand_time, strava_time, 2.0)
        start_ok = _time_within_5h(strava_start, cand_start)

        if dist_ok and time_ok and start_ok:
            matches.append(cand["id"])

    if len(matches) == 1:
        return matches[0]
    if len(matches) >= 2:
        return "ambiguous"
    return None