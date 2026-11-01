"""Schemas Pydantic para API de domínio Health."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel


class SleepPointOut(BaseModel):
    date: date
    duration_s: float
    score: Optional[int]
    rem_pct: Optional[float]
    deep_pct: Optional[float]
    light_pct: Optional[float]
    awakenings: Optional[int]
    bed_local: Optional[str]
    wake_local: Optional[str]


class BelowFloorOut(BaseModel):
    nights: int
    pct: float


class WeekdayEntryOut(BaseModel):
    weekday: int
    avg_duration_s: Optional[float]
    nights: int


class RegularityOut(BaseModel):
    avg_bed_min: float
    avg_wake_min: float


class SleepBlockOut(BaseModel):
    days: int
    floor_s: float
    rem_band: List[float]
    below_floor: BelowFloorOut
    regularity: Optional[RegularityOut]
    weekday_pattern: List[WeekdayEntryOut]
    points: List[SleepPointOut]


class HrvPointOut(BaseModel):
    date: date
    value: Optional[float]
    avg7: Optional[float]
    band_low: Optional[float]
    band_high: Optional[float]


class HrvCurrentOut(BaseModel):
    date: date
    value: float
    avg7: float
    band_low: Optional[float]
    band_high: Optional[float]
    status: Optional[str]


class HrvBlockOut(BaseModel):
    points: List[HrvPointOut]
    current: HrvCurrentOut


class RhrPointOut(BaseModel):
    date: date
    value: int


class RhrBlockOut(BaseModel):
    points: List[RhrPointOut]
    baseline: int


class StressPointOut(BaseModel):
    date: date
    avg: int


class StressBlockOut(BaseModel):
    points: List[StressPointOut]
    avg_window: int


class PmcPointOut(BaseModel):
    date: date
    ctl: Optional[float]
    atl: Optional[float]
    tsb: Optional[float]
    acwr: Optional[float]


class PmcBlockOut(BaseModel):
    days: int
    points: List[PmcPointOut]
    current: PmcPointOut


class DoseBucketOut(BaseModel):
    nights: int
    avg_hrv: Optional[float]
    avg_score: Optional[float]


class DoseResponseOut(BaseModel):
    short: DoseBucketOut
    adequate: DoseBucketOut
    neutral_nights: int


class StrengthOut(BaseModel):
    streak_weeks: int
    weeks_hit: int
    weeks_total: int
    current_week_sessions: int


class YogaOut(BaseModel):
    sessions: int
    per_week_avg: float


class LifestyleOut(BaseModel):
    strength: StrengthOut
    yoga: YogaOut


class HealthSummaryOut(BaseModel):
    sleep: Optional[SleepBlockOut]
    hrv: Optional[HrvBlockOut]
    rhr: Optional[RhrBlockOut]
    stress: Optional[StressBlockOut]
    dose_response: DoseResponseOut
    lifestyle: LifestyleOut


class HealthSignalsOut(BaseModel):
    hrv: Optional[HrvCurrentOut]
    sleep: Optional[dict]
    fitness: Optional[dict]