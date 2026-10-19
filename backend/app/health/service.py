"""Service do painel Saúde — leitura pura do banco (AD-002).

Nenhuma importação do gateway Garmin: as 5 fontes (sleep, hrv, rhr,
stress, activities) já estão no banco próprio, populadas pelo sync —
o painel inteiro é montável offline (Success Criteria do spec). O
cruzamento sono↔HRV é por `date` (mesma noite — premissa do spec) e a
conversão de fuso dos horários de deitar/acordar acontece aqui, com a
ZoneInfo injetada pelo router (config 100% env var). O filtro de
typeKey é em Python (AD-001: escala pessoal, ~233 linhas).
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    DEFAULT_USER_ID,
    Activity,
    Hrv,
    Rhr,
    Sleep,
    Stress,
)
from app.health.calc import (
    HRV_BASELINE_DAYS,
    REM_BAND,
    SLEEP_FLOOR_S,
    below_floor,
    dose_response,
    hrv_model,
    local_minute,
    regularity,
    strength_weeks,
    weekday_pattern,
)

# typeKey exatos das activities (spec: detecção em tempo de leitura,
# nada persistido — mesma postura do tipo inferido do workouts-list)
STRENGTH_TYPE = "strength_training"
YOGA_TYPE = "yoga"


def _today(tz: ZoneInfo) -> date:
    """Hoje no fuso do app — âncora da janela do lifestyle (seam de
    teste: os pins fixam a data injetando o retorno)."""
    return datetime.now(tz).date()


def _series(db: Session, model, days: int) -> list:
    """Janela da série: últimas `days` linhas, mais antiga primeiro
    (padrão do painel Performance). Janela maior que o histórico devolve
    as linhas disponíveis (edge do spec — a pedida, não uma inventada)."""
    rows = (
        db.execute(
            select(model)
            .where(model.user_id == DEFAULT_USER_ID)
            .order_by(model.date.desc())
            .limit(days)
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))


def _hhmm(minute: int | None) -> str | None:
    """Minuto do dia local -> "HH:MM" (o payload já entrega o wall clock
    pronto; a UI nunca converte fuso — design §Contrato)."""
    return None if minute is None else f"{minute // 60:02d}:{minute % 60:02d}"


def _night(row: Sleep, hrv_by_date: dict, tz: ZoneInfo) -> dict:
    """Noite para as funções puras: HRV da mesma data + minutos locais."""
    return {
        "date": row.date,
        "duration_s": row.duration_s,
        "score": row.score,
        "hrv": hrv_by_date.get(row.date),
        "bed_min": local_minute(row.bed_time, tz) if row.bed_time is not None else None,
        "wake_min": local_minute(row.wake_time, tz) if row.wake_time is not None else None,
    }


def _sleep_block(sleep_rows: list[Sleep], nights: list[dict], days: int) -> dict | None:
    """Bloco sono (AC 4): pontos ASC com fases e horários locais,
    réguas do backend (piso/banda) e derivados do calc."""
    if not sleep_rows:
        return None
    points = [
        {
            "date": row.date,
            "duration_s": row.duration_s,
            "score": row.score,
            "rem_pct": row.rem_pct,
            "deep_pct": row.deep_pct,
            "light_pct": row.light_pct,
            "awakenings": row.awakenings,
            "bed_local": _hhmm(night["bed_min"]),
            "wake_local": _hhmm(night["wake_min"]),
        }
        for row, night in zip(sleep_rows, nights)
    ]
    return {
        "days": days,
        "floor_s": SLEEP_FLOOR_S,
        "rem_band": list(REM_BAND),
        "below_floor": below_floor(nights),
        "regularity": regularity(nights),
        "weekday_pattern": weekday_pattern(nights),
        "points": points,
    }


def _hrv_history(db: Session, days: int) -> list[Hrv]:
    """Janela do modelo de HRV (hrv-baseline, design §Components.2):
    exibição de `days` dias corridos + lookback de banda de 59 — todas
    as linhas do usuário a partir de L−(days+58), ASC. Sem linhas -> []."""
    latest = db.execute(
        select(func.max(Hrv.date)).where(Hrv.user_id == DEFAULT_USER_ID)
    ).scalar()
    if latest is None:
        return []
    start = latest - timedelta(days=days - 1 + HRV_BASELINE_DAYS - 1)
    return (
        db.execute(
            select(Hrv)
            .where(Hrv.user_id == DEFAULT_USER_ID, Hrv.date >= start)
            .order_by(Hrv.date.asc())
        )
        .scalars()
        .all()
    )


def _hrv_block(rows: list[Hrv], days: int) -> dict | None:
    """Bloco HRV (HRV-01..HRV-09): modelo científico do calc — pontos
    por dia corrido (noite + média 7d + banda), `current` = último dia
    com dado com status local. O `status` cru da Garmin sai do payload
    (continua na tabela — decisão da spec); 1 casa é só de exibição, a
    comparação do status acontece sem arredondar no calc."""
    if not rows:
        return None
    model = hrv_model([(r.date, r.value) for r in rows], days)

    def _one(value: float | None) -> float | None:
        return None if value is None else round(value, 1)

    return {
        "points": [
            {
                "date": p["date"],
                "value": p["value"],
                "avg7": _one(p["avg7"]),
                "band_low": _one(p["band_low"]),
                "band_high": _one(p["band_high"]),
            }
            for p in model["points"]
        ],
        "current": {
            "date": model["current"]["date"],
            "value": model["current"]["value"],
            "avg7": _one(model["current"]["avg7"]),
            "band_low": _one(model["current"]["band_low"]),
            "band_high": _one(model["current"]["band_high"]),
            "status": model["current"]["status"],
        },
    }


def _rhr_block(rows: list[Rhr]) -> dict | None:
    """Bloco RHR (AC 7): série ASC + baseline = média da janela (1 casa)
    — régua honesta e recalculável (premissa do spec)."""
    if not rows:
        return None
    return {
        "points": [{"date": r.date, "value": r.value} for r in rows],
        "baseline": round(sum(r.value for r in rows) / len(rows), 1),
    }


def _stress_block(rows: list[Stress]) -> dict | None:
    """Bloco estresse (AC 8): dia sem `avg` (NULL) fica fora da série
    (design §Riscos — mesma postura "filtra o que existe" do sync); a
    janela inteira sem avg -> bloco null."""
    points = [{"date": r.date, "avg": r.avg} for r in rows if r.avg is not None]
    if not points:
        return None
    return {
        "points": points,
        "avg_window": round(sum(p["avg"] for p in points) / len(points), 1),
    }


def _lifestyle_block(activities: list[Activity], today: date, window_start: date) -> dict:
    """Checklist de vida (AC 10): força via semanas ISO (a streak olha o
    histórico todo — pode exceder a janela) e yoga por presença na
    janela (duração não importa — edge do spec)."""
    strength_days = [
        a.start_time.date() for a in activities if a.activity_type == STRENGTH_TYPE
    ]
    yoga_days = [
        a.start_time.date() for a in activities if a.activity_type == YOGA_TYPE
    ]
    strength = strength_weeks(strength_days, today, window_start)
    sessions = sum(1 for d in yoga_days if window_start <= d <= today)
    return {
        "strength": strength,
        "yoga": {
            "sessions": sessions,
            "per_week_avg": round(sessions / strength["weeks_total"], 1),
        },
    }


def get_health(db: Session, days: int, tz: ZoneInfo) -> dict:
    """Payload completo do painel — os 6 blocos do design §Contrato.

    Sem `pmc`: a curva de carga voltou ao painel Performance (AD-017
    reverte a CLR-03 — o bloco mudou de endpoint junto com a tela,
    AD-009). `days` já validado (7–365) pelo router; a matemática vive
    em calc.py (pura, AD-003) — aqui é leitura e montagem. Séries vazias
    -> bloco null (HLT-11); `dose_response`/`lifestyle` sempre presentes,
    com zeros honestos."""
    sleep_rows = _series(db, Sleep, days)
    hrv_rows = _series(db, Hrv, days)
    rhr_rows = _series(db, Rhr, days)
    stress_rows = _series(db, Stress, days)
    activities = (
        db.execute(select(Activity).where(Activity.user_id == DEFAULT_USER_ID))
        .scalars()
        .all()
    )

    hrv_by_date = {row.date: row.value for row in hrv_rows}
    nights = [_night(row, hrv_by_date, tz) for row in sleep_rows]

    today = _today(tz)
    window_start = today - timedelta(days=days - 1)

    return {
        "sleep": _sleep_block(sleep_rows, nights, days),
        "hrv": _hrv_block(_hrv_history(db, days), days),
        "rhr": _rhr_block(rhr_rows),
        "stress": _stress_block(stress_rows),
        "dose_response": dose_response(nights),
        "lifestyle": _lifestyle_block(activities, today, window_start),
    }
