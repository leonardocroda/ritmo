"""Entidades do domínio Performance — VDOT, Predições, Decay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Sequence

from app.domain.activities.domain.value_objects import Pace


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

    event: str  # "5K", "10K", "HALF_MARATHON", "MARATHON"
    garmin_s: Optional[float]
    riegel_s: Optional[float]
    vdot_s: Optional[float]
    average_s: Optional[float]
    pr_s: Optional[float]
    pr_date: Optional[date]


@dataclass(frozen=True, slots=True)
class DecayPoint:
    """Ponto de decay (desempenho vs ideal)."""

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
class VO2maxBlock:
    """Bloco VO2max."""

    points: Sequence[VO2maxPoint]


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    """Resumo completo de performance."""

    vdot: VDOTProfile
    demonstrated_vdot: Optional[float]
    gap_pct: Optional[float]
    timeline: Sequence[TimelinePoint]
    predictions: dict[str, Prediction]
    vo2max: Optional[VO2maxBlock]
    decay: Sequence[DecayPoint]