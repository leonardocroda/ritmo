"""Schemas Pydantic para API de domínio Training-Load."""

from __future__ import annotations

from datetime import date
from typing import Optional, List

from pydantic import BaseModel


class PMCDayOut(BaseModel):
    date: date
    ctl: Optional[float]
    atl: Optional[float]
    tsb: Optional[float]
    acwr: Optional[float]


class PMCCurveOut(BaseModel):
    days: int
    points: List[PMCDayOut]
    current: PMCDayOut


class VolumeWeekOut(BaseModel):
    week_start: date
    km: float


class TrainingLoadOut(BaseModel):
    pmc: PMCCurveOut
    volume_weeks: List[VolumeWeekOut]
    current_week_km: float
    avg4_km: float
    delta_pct: Optional[float]