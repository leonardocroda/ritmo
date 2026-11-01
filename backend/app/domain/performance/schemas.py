"""Schemas Pydantic para API de domínio Performance."""

from __future__ import annotations

from datetime import date
from typing import Optional, List

from pydantic import BaseModel


class TimelinePointOut(BaseModel):
    date: date
    vdot: float
    source: str
    label: str
    distance_m: float
    time_s: float


class VDOTCurrentOut(BaseModel):
    vdot: float
    source: str
    test_date: date


class VDOTDemonstratedOut(BaseModel):
    vdot: float
    source: str
    date: date


class VDOTBlockOut(BaseModel):
    current: VDOTCurrentOut
    demonstrated: Optional[VDOTDemonstratedOut]
    gap_pct: Optional[float]
    timeline: List[TimelinePointOut]


class PredictionRowOut(BaseModel):
    garmin_s: Optional[float]
    riegel_s: Optional[float]
    vdot_s: Optional[float]
    average_s: Optional[float]
    pr_s: Optional[float]
    pr_date: Optional[date]


class VO2maxPointOut(BaseModel):
    date: date
    value: float


class VO2maxBlockOut(BaseModel):
    points: List[VO2maxPointOut]


class DecayRowOut(BaseModel):
    event: str
    real_pace_s: float
    ideal_pace_s: float
    delta_pct: float


class PerformanceOut(BaseModel):
    vdot: VDOTBlockOut
    predictions: dict[str, PredictionRowOut]
    vo2max: Optional[VO2maxBlockOut]
    decay: List[DecayRowOut]