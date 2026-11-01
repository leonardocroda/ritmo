"""Entidades do domínio Garmin — Sync, Import."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass(frozen=True, slots=True)
class GarminActivity:
    """Atividade bruta do Garmin."""

    garmin_id: str
    start_time: datetime
    activity_type: str
    name: Optional[str]
    distance_m: float
    duration_s: float
    avg_hr: Optional[int]
    max_hr: Optional[int]
    avg_cadence: Optional[float]
    elevation_gain_m: Optional[float]
    aerobic_te: Optional[float]
    anaerobic_te: Optional[float]
    training_load: Optional[float]
    raw_json: dict


@dataclass(frozen=True, slots=True)
class GarminSleep:
    """Sono do Garmin."""

    date: date
    duration_s: float
    score: Optional[int]
    deep_pct: Optional[float]
    rem_pct: Optional[float]
    light_pct: Optional[float]
    awakenings: Optional[int]
    bed_time: Optional[datetime]
    wake_time: Optional[datetime]


@dataclass(frozen=True, slots=True)
class GarminHRV:
    """HRV do Garmin."""

    date: date
    value: float
    status: Optional[str]


@dataclass(frozen=True, slots=True)
class SyncStatus:
    """Status de um job de sync."""

    id: int
    user_id: int
    window_days: int
    status: str  # "pending", "running", "done", "error"
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[str]
    stats_json: Optional[dict]