"""Mappers puros: JSON do Garmin -> dicts prontos para o ORM.

Sem DB, sem client — 100% testáveis com fixtures (design). Os shapes
dos payloads foram aterrissados contra os fixtures/curadoria do
garmin_mcp do usuário (mesma lib garminconnect==0.3.2, dados reais).
Divergência de campo é corrigida no spot-check da primeira sync real
(T15) sem re-pull — `raw_json` é sempre preservado (spec).

Decisão de fuso (spec): datas de calendário do Garmin gravadas como
vêm, sem conversão. Horários GMT (época ms) viram datetime UTC naive
— o wall clock GMT entregue pela API, nada inventado.
"""

from datetime import date, datetime, timezone

RUNNING_TYPES = {"running", "trail_running"}

# Recordes de corrida: typeId do Garmin -> evento. Mapa estimado a
# partir de dados reais (mesma tabela do garmin_mcp do usuário);
# typeIds 8+ são cycling/passos/natação e ficam fora (SYNC-16).
RUNNING_PR_EVENTS = {
    1: "FASTEST_1K",
    2: "FASTEST_MILE",
    3: "FASTEST_5K",
    4: "FASTEST_10K",
    5: "FASTEST_HALF_MARATHON",
    6: "FASTEST_MARATHON",
    7: "LONGEST_RUN",
}


def _gmt_ms_to_naive_datetime(ms: int | None) -> datetime | None:
    """Época GMT (ms) -> wall clock UTC naive (sem conversão de fuso)."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)


def map_activity(raw: dict) -> dict:
    """Payload da listagem de atividades -> colunas de `Activity`.

    `garmin_id` é a chave natural de dedup (SYNC-11); `raw_json`
    preserva o payload inteiro para auditoria sem re-pull (spec).
    """
    return {
        "garmin_id": str(raw["activityId"]),
        "start_time": datetime.strptime(raw["startTimeLocal"], "%Y-%m-%d %H:%M:%S"),
        "activity_type": raw["activityType"]["typeKey"],
        "name": raw.get("activityName"),
        "distance_m": raw.get("distance"),
        "duration_s": raw.get("duration"),
        "avg_hr": raw.get("averageHR"),
        "max_hr": raw.get("maxHR"),
        "avg_cadence": raw.get("averageRunningCadenceInStepsPerMinute"),
        "power": raw.get("averagePower"),
        "elevation_gain_m": raw.get("elevationGain"),
        "aerobic_te": raw.get("aerobicTrainingEffect"),
        "anaerobic_te": raw.get("anaerobicTrainingEffect"),
        "training_load": raw.get("activityTrainingLoad"),
        "raw_json": raw,
    }


def is_running(raw: dict) -> bool:
    """Splits são buscados só para corrida (SYNC-12): running/trail_running."""
    return bool((raw.get("activityType") or {}).get("typeKey") in RUNNING_TYPES)


def map_splits(raw: dict | list | None) -> list[dict]:
    """Splits (laps de corrida) -> linhas de `Split`.

    Normaliza os dois shapes — dict com lista interna (`lapDTOs`) ou
    lista direta; `None`/vazio -> `[]` sem warning (edge do spec).
    `pace_s` é derivado (s por km) porque a coluna guarda o derivável.
    """
    laps = raw.get("lapDTOs") or [] if isinstance(raw, dict) else raw or []
    rows = []
    for lap in laps:
        distance = lap.get("distance")
        duration = lap.get("duration")
        rows.append(
            {
                "idx": lap.get("lapIndex"),
                "dist_m": distance,
                "duration_s": duration,
                "pace_s": duration * 1000 / distance if distance and duration else None,
                "avg_hr": lap.get("averageHR"),
                "elevation_m": lap.get("elevationGain"),
                "intensity_type": lap.get("intensityType"),
            }
        )
    return rows


def map_sleep(raw: dict | None) -> dict | None:
    """Sono -> `Sleep`; `None` quando não há noite registrada (SYNC-19)."""
    dto = (raw or {}).get("dailySleepDTO") or {}
    duration_s = dto.get("sleepTimeSeconds")
    if not duration_s or not dto.get("calendarDate"):
        return None
    scores = dto.get("sleepScores") or {}
    overall = scores.get("overall") or {}
    return {
        "date": date.fromisoformat(dto["calendarDate"]),
        "duration_s": duration_s,
        "score": overall.get("value"),
        "deep_pct": (dto.get("deepSleepSeconds") or 0) / duration_s * 100,
        "light_pct": (dto.get("lightSleepSeconds") or 0) / duration_s * 100,
        "rem_pct": (dto.get("remSleepSeconds") or 0) / duration_s * 100,
        "awakenings": dto.get("awakeCount"),
        "bed_time": _gmt_ms_to_naive_datetime(dto.get("sleepStartTimestampGMT")),
        "wake_time": _gmt_ms_to_naive_datetime(dto.get("sleepEndTimestampGMT")),
    }


def map_hrv(raw: dict | None) -> dict | None:
    """HRV -> `Hrv`; `None` em dia sem dado (SYNC-19)."""
    summary = (raw or {}).get("hrvSummary") or {}
    value = summary.get("lastNightAvg")
    if value is None or not summary.get("calendarDate"):
        return None
    return {
        "date": date.fromisoformat(summary["calendarDate"]),
        "value": value,
        "status": summary.get("status"),
    }


def map_rhr(raw: dict | None) -> dict | None:
    """RHR -> `Rhr`; `None` em dia sem dado (SYNC-19)."""
    raw = raw or {}
    if raw.get("restingHeartRate") is None or not raw.get("calendarDate"):
        return None
    return {
        "date": date.fromisoformat(raw["calendarDate"]),
        "value": raw["restingHeartRate"],
    }


def map_stress(raw: dict | None) -> dict | None:
    """Stress -> `Stress` com a média diária; `None` em dia sem dado."""
    raw = raw or {}
    if raw.get("avgStressLevel") is None or not raw.get("calendarDate"):
        return None
    return {
        "date": date.fromisoformat(raw["calendarDate"]),
        "avg": raw["avgStressLevel"],
    }


def map_battery(rows: list | None) -> list[dict]:
    """Body battery (1 chamada de range) -> 1 linha por `calendarDate`.

    Linhas sem `calendarDate` não têm chave de upsert e são puladas.
    """
    mapped = []
    for row in rows or []:
        calendar_date = row.get("calendarDate")
        if not calendar_date:
            continue
        mapped.append(
            {
                "date": date.fromisoformat(calendar_date),
                "value": row.get("bodyBatteryMostRecentValue"),
            }
        )
    return mapped


def map_personal_records(raw: list | dict | None) -> list[dict]:
    """Recordes -> `PersonalRecord`; filtra para corrida (SYNC-16).

    Normaliza lista direta e wrapper `{"personalRecords": [...]}`;
    `raw_json` preserva o recorde original (spec).
    """
    if isinstance(raw, dict):
        raw = raw.get("personalRecords") or []
    rows = []
    for record in raw or []:
        event = RUNNING_PR_EVENTS.get(record.get("typeId"))
        if event is None:
            continue  # não é recorde de corrida
        started = _gmt_ms_to_naive_datetime(record.get("prStartTimeGMT"))
        rows.append(
            {
                "event": event,
                "value": record.get("value"),
                "pr_date": started.date() if started else None,
                "raw_json": record,
            }
        )
    return rows
