"""Entidades do domínio VDOT — pace zones, predições, decay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Sequence


@dataclass(frozen=True, slots=True)
class VDOTProfile:
    """Perfil VDOT do atleta."""

    current_vdot: float
    source: str  # "test", "race", "manual", "garmin"
    test_date: date
    test_distance_m: float
    test_time_s: float
    demonstrated_vdot: Optional[float] = None
    demonstrated_source: Optional[str] = None
    demonstrated_date: Optional[date] = None


@dataclass(frozen=True, slots=True)
class TimelinePoint:
    """Ponto da timeline VDOT — PR, prova ou teste."""

    date: date
    vdot: float
    source: str
    label: str
    distance_m: float
    time_s: float


@dataclass(frozen=True, slots=True)
class Prediction:
    """Predição de tempo de prova."""

    event: str
    garmin_s: Optional[float]
    riegel_s: Optional[float]
    vdot_s: Optional[float]
    average_s: Optional[float]
    pr_s: Optional[float]
    pr_date: Optional[date]


@dataclass(frozen=True, slots=True)
class DecayPoint:
    """Ponto de decay (desempenho real vs ideal)."""

    event: str
    real_pace_s: float
    ideal_pace_s: float
    delta_pct: float


@dataclass(frozen=True, slots=True)
class VO2maxPoint:
    """Ponto da série VO2max."""

    date: date
    value: float


@dataclass(frozen=True, slots=True)
class PaceZoneConfig:
    """Configuração de zonas de ritmo (VDOT)."""

    id: int
    user_id: int
    vdot: float
    source: str
    test_date: date
    distance_m: float
    time_s: float
    zones: dict
    equivalencias: dict
    valid_from: date
    created_at: datetime