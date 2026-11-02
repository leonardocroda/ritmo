"""Schemas Pydantic para API de domínio Athlete."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class AthleteOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    email: Optional[str]
    created_at: datetime
    weekly_goal_km: Optional[float]
    preferred_unit: str
    timezone: str
    target_race: Optional[str]
    target_date: Optional[date]
    target_time_s: Optional[int]


class AthleteUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    weekly_goal_km: Optional[float] = None
    preferred_unit: Optional[str] = None
    timezone: Optional[str] = None
    target_race: Optional[str] = None
    target_date: Optional[date] = None
    target_time_s: Optional[int] = None