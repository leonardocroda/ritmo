"""Router do painel Saúde — leitura do banco, zero Garmin (AD-002).

Padrão do potential/router.py (modelos de saída inline + Query bounds):
`days` fora de [7, 365] -> 422 antes de qualquer query (HLT-03). O
caminho é `/summary` porque `/api/health` exato é o health check de
infra (INFRA-02 — premissa do spec). O fuso vem de APP_TIMEZONE; valor
inválido -> fallback America/Sao_Paulo + warning (edge do spec, sem
crash).
"""

import logging
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.core.config import get_settings
from app.db.engine import get_db
from app.db.models import User
from app.health import service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health")

DEFAULT_TIMEZONE = "America/Sao_Paulo"


class SleepPoint(BaseModel):
    date: date
    duration_s: float
    score: int | None
    rem_pct: float | None
    deep_pct: float | None
    light_pct: float | None
    awakenings: int | None
    bed_local: str | None
    wake_local: str | None


class BelowFloor(BaseModel):
    nights: int
    pct: float


class WeekdayEntry(BaseModel):
    weekday: int
    avg_duration_s: float | None
    nights: int


class Regularity(BaseModel):
    avg_bed_min: float
    avg_wake_min: float


class SleepBlock(BaseModel):
    days: int
    floor_s: int
    rem_band: list[float]
    below_floor: BelowFloor
    regularity: Regularity | None
    weekday_pattern: list[WeekdayEntry]
    points: list[SleepPoint]


class HrvPoint(BaseModel):
    """Dia corrido da janela de exibição (HRV-01..05): noite individual
    (null = sem captura), média móvel 7d e banda do dia (null sob o
    threshold de 14 valores na janela de 60 dias)."""

    date: date
    value: float | None
    avg7: float | None
    band_low: float | None
    band_high: float | None


class HrvCurrent(BaseModel):
    """Último dia com dado (HRV-06..09): status local BALANCED ou
    UNBALANCED (média 7d vs banda, limites inclusos) e null quando a
    banda ainda não existe ("coletando linha de base") — o status cru
    da Garmin não atravessa mais o contrato."""

    date: date
    value: float
    avg7: float
    band_low: float | None
    band_high: float | None
    status: str | None


class HrvBlock(BaseModel):
    points: list[HrvPoint]
    current: HrvCurrent


class RhrPoint(BaseModel):
    date: date
    value: int


class RhrBlock(BaseModel):
    points: list[RhrPoint]
    baseline: float


class StressPoint(BaseModel):
    date: date
    avg: int


class StressBlock(BaseModel):
    points: list[StressPoint]
    avg_window: float


class DoseBucket(BaseModel):
    nights: int
    avg_hrv: float | None
    avg_score: float | None


class DoseResponse(BaseModel):
    short: DoseBucket
    adequate: DoseBucket
    neutral_nights: int


class Strength(BaseModel):
    streak_weeks: int
    weeks_hit: int
    weeks_total: int
    current_week_sessions: int


class Yoga(BaseModel):
    sessions: int
    per_week_avg: float


class Lifestyle(BaseModel):
    strength: Strength
    yoga: Yoga


class HealthSummaryOut(BaseModel):
    sleep: SleepBlock | None
    hrv: HrvBlock | None
    rhr: RhrBlock | None
    stress: StressBlock | None
    dose_response: DoseResponse
    lifestyle: Lifestyle


def _resolve_tz() -> ZoneInfo:
    """Fuso da conversão de deitar/acordar: APP_TIMEZONE; valor inválido
    -> default + warning (edge do spec — o painel segue no fuso default)."""
    name = get_settings().app_timezone
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(
            "APP_TIMEZONE inválida (%s) — usando %s", name, DEFAULT_TIMEZONE
        )
        return ZoneInfo(DEFAULT_TIMEZONE)


@router.get("/summary")
def get_health_summary(
    user: User = Depends(require_session),
    days: int = Query(default=60, ge=7, le=365),
    db: Session = Depends(get_db),
) -> HealthSummaryOut:
    """O painel inteiro em 1 payload (design §Contrato).

    `days` fora de [7, 365] -> 422 antes de qualquer query (HLT-03,
    padrão POT-16). Toda leitura filtra pelo usuário da sessão
    (user-scope)."""
    return service.get_health(db, user.id, days, _resolve_tz())
