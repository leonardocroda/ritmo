"""Entidades do domínio Athlete — perfil do corredor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class Athlete:
    """Perfil do atleta/corredor."""

    id: int
    user_id: int
    display_name: str
    email: Optional[str]
    created_at: datetime
    # Configurações do atleta
    weekly_goal_km: Optional[float] = None
    preferred_unit: str = "metric"  # "metric" | "imperial"
    timezone: str = "UTC"
    # Metas
    target_race: Optional[str] = None  # ex: "10K", "HALF_MARATHON", "MARATHON"
    target_date: Optional[date] = None
    target_time_s: Optional[int] = None