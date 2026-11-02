"""Entidades do domínio Shoes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class Shoe:
    """Tênis do corredor."""

    id: int
    user_id: int
    name: str
    brand: Optional[str]
    model: Optional[str]
    acquired_date: Optional[date]
    initial_km: float
    max_km: Optional[float]
    status: str  # "ativo" | "aposentado"
    strava_gear_id: Optional[str]
    created_at: datetime

    @property
    def is_active(self) -> bool:
        return self.status == "ativo"


@dataclass(frozen=True, slots=True)
class ShoeRun:
    """Corrida associada a um tênis."""

    activity_id: int
    date: date
    distance_m: float
    pace_s: float
    avg_hr: Optional[int]
    run_type: str  # "easy", "marathon", "threshold", etc.


@dataclass(frozen=True, slots=True)
class DegradationSignal:
    """Sinal de degradação do tênis."""

    signal: str
    label: str
    initial: float
    final: float
    delta: float
    unit: str
    direction: Optional[str] = None
    confidence: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ShoeDegradation:
    """Resultado de análise de degradação."""

    shoe_id: int
    total_km: float
    n_runs: int
    signals: tuple[DegradationSignal, ...]
    verdict: Optional[str] = None
    insufficient: bool = False