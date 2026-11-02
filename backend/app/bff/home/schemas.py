"""Schemas do BFF Home — payload 1:1 com o painel (espelho do HomeOut antigo)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class VerdictOut(BaseModel):
    phrase: str
    tone: str
    rule: str


class HrvSignalOut(BaseModel):
    """HRV do último dia com dado (status None = coletando linha de base)."""

    value: float
    status: Optional[str]
    as_of: date


class SleepSignalOut(BaseModel):
    duration_s: float
    delta_s: Optional[float]
    as_of: date


class FitnessSignalOut(BaseModel):
    tsb: Optional[float]
    acwr: Optional[float]
    as_of: date


class SignalsOut(BaseModel):
    hrv: Optional[HrvSignalOut]
    sleep: Optional[SleepSignalOut]
    fitness: Optional[FitnessSignalOut]


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
    delta_pct: Optional[float]


class CountdownOut(BaseModel):
    name: str
    date: date
    days_left: int


class RecommendationOut(BaseModel):
    text: str
    support: Optional[str]
    why: Optional[str]
    tone: str


class WeekPoint(BaseModel):
    """P2 (T13): uma semana ISO da série de volume."""

    week_start: date
    km: float


class PredictionDigest(BaseModel):
    """P2 (T13): um evento de predição de prova."""

    event: str
    time_s: float


class HomeTodayOut(BaseModel):
    """O painel inteiro em 1 payload — espelho 1:1 (design §Contrato)."""

    date: date
    verdict: Optional[VerdictOut]
    signals: SignalsOut
    strip: list[StripPoint]
    last_activity: Optional[LastActivityOut]
    volume: Optional[VolumeOut]
    countdown: Optional[CountdownOut]
    recommendations: list[RecommendationOut]
    volume_weeks: Optional[list[WeekPoint]]
    predictions: Optional[list[PredictionDigest]]