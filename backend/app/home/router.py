"""Router do painel Home — contrato HomeOut, espelho 1:1 do painel (AD-009).

Um endpoint, um payload: cada campo renderiza na Home, nenhum bloco de
outro painel. Sessão obrigatória (401 pela dependency antes de
qualquer query — padrão dos demais routers); o fuso vem do resolvedor
único `app_tz()`. Os blocos P2 (`volume_weeks`, `predictions`) já
existem no contrato e ficam None até a task que os semeia.
"""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.core.tz import app_tz
from app.db.engine import get_db
from app.db.models import User
from app.home import service

router = APIRouter(prefix="/api/home")


class VerdictOut(BaseModel):
    phrase: str
    tone: str
    rule: str


class HrvSignalOut(BaseModel):
    """HRV do último dia com dado (status None = coletando linha de base)."""

    value: float
    status: str | None
    as_of: date


class SleepSignalOut(BaseModel):
    duration_s: float
    delta_s: float | None
    as_of: date


class FitnessSignalOut(BaseModel):
    tsb: float | None
    acwr: float | None
    as_of: date


class SignalsOut(BaseModel):
    hrv: HrvSignalOut | None
    sleep: SleepSignalOut | None
    fitness: FitnessSignalOut | None


class StripPoint(BaseModel):
    date: date
    load: float


class LastActivityOut(BaseModel):
    id: int
    date: date
    distance_m: float
    evaluated: bool


class VolumeOut(BaseModel):
    week_km: float
    avg4_km: float
    delta_pct: float | None


class CountdownOut(BaseModel):
    name: str
    date: date
    days_left: int


class RecommendationOut(BaseModel):
    text: str
    support: str | None
    why: str | None
    tone: str


class WeekPoint(BaseModel):
    """P2 (T13): uma semana ISO da série de volume."""

    week_start: date
    km: float


class PredictionDigest(BaseModel):
    """P2 (T13): um evento de predição de prova."""

    event: str
    time_s: float


class HomeOut(BaseModel):
    """O painel inteiro em 1 payload — espelho 1:1 (design §Contrato)."""

    date: date
    verdict: VerdictOut | None
    signals: SignalsOut
    strip: list[StripPoint]
    last_activity: LastActivityOut | None
    volume: VolumeOut | None
    countdown: CountdownOut | None
    recommendations: list[RecommendationOut]
    volume_weeks: list[WeekPoint] | None
    predictions: list[PredictionDigest] | None


@router.get("/today")
def get_home_today(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> HomeOut:
    """O dia em um payload: veredito, sinais, strip, roteamento e
    recomendações. Toda leitura filtra pelo usuário da sessão."""
    return HomeOut(**service.get_home(db, user.id, app_tz()))
