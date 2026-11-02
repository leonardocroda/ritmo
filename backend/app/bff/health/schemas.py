"""Schemas do BFF Health — payload 1:1 com o painel (espelho do HealthSummaryOut antigo)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class SleepPoint(BaseModel):
    date: date
    duration_s: float
    score: Optional[int]
    rem_pct: Optional[float]
    deep_pct: Optional[float]
    light_pct: Optional[float]
    awakenings: Optional[int]
    bed_local: Optional[str]
    wake_local: Optional[str]


class BelowFloor(BaseModel):
    nights: int
    pct: float


class WeekdayEntry(BaseModel):
    weekday: int
    avg_duration_s: Optional[float]
    nights: int


class Regularity(BaseModel):
    avg_bed_min: float
    avg_wake_min: float


class SleepBlock(BaseModel):
    days: int
    floor_s: int
    rem_band: list[float]
    below_floor: BelowFloor
    regularity: Optional[Regularity]
    weekday_pattern: list[WeekdayEntry]
    points: list[SleepPoint]


class HrvPoint(BaseModel):
    date: date
    value: Optional[float]
    avg7: Optional[float]
    band_low: Optional[float]
    band_high: Optional[float]


class HrvCurrent(BaseModel):
    date: date
    value: float
    avg7: float
    band_low: Optional[float]
    band_high: Optional[float]
    status: Optional[str]


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
    avg_hrv: Optional[float]
    avg_score: Optional[float]


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
    sleep: Optional[SleepBlock]
    hrv: Optional[HrvBlock]
    rhr: Optional[RhrBlock]
    stress: Optional[StressBlock]
    dose_response: DoseResponse
    lifestyle: Lifestyle