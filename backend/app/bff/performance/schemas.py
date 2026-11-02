"""Schemas do BFF Performance — payload 1:1 com o painel (espelho do PotentialOut antigo)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class TimelinePoint(BaseModel):
    date: date
    vdot: float
    source: str
    label: str
    distance_m: float
    time_s: float


class VdotCurrent(BaseModel):
    vdot: float
    source: str
    test_date: date


class VdotDemonstrated(BaseModel):
    vdot: float
    source: str
    date: date


class VdotBlock(BaseModel):
    current: VdotCurrent
    demonstrated: Optional[VdotDemonstrated]
    gap_pct: Optional[float]
    timeline: list[TimelinePoint]


class PredictionRow(BaseModel):
    garmin_s: Optional[float]
    riegel_s: Optional[float]
    vdot_s: Optional[float]
    average_s: Optional[float]
    pr_s: Optional[float]
    pr_date: Optional[date]


class Vo2maxPoint(BaseModel):
    date: date
    value: float


class Vo2maxBlock(BaseModel):
    points: list[Vo2maxPoint]


class DecayRow(BaseModel):
    event: str
    real_pace_s: float
    ideal_pace_s: float
    delta_pct: float


class PmcPoint(BaseModel):
    date: date
    ctl: Optional[float]
    atl: Optional[float]
    tsb: Optional[float]
    acwr: Optional[float]


class PmcBlock(BaseModel):
    days: int
    points: list[PmcPoint]
    current: PmcPoint


class PerformanceOut(BaseModel):
    vdot: VdotBlock
    predictions: dict[str, PredictionRow]
    vo2max: Optional[Vo2maxBlock]
    decay: list[DecayRow]
    pmc: Optional[PmcBlock]