"""Entidades do domínio Training-Load — PMC, ATL/CTL/TSB, ACWR."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from app.domain.activities.domain.entities import Activity


@dataclass(frozen=True, slots=True)
class PMCDay:
    """Um dia da curva PMC."""

    date: date
    ctl: Optional[float]
    atl: Optional[float]
    tsb: Optional[float]
    acwr: Optional[float]


@dataclass(frozen=True, slots=True)
class PMCCurve:
    """Curva PMC completa."""

    days: int
    points: Sequence[PMCDay]
    current: PMCDay


@dataclass(frozen=True, slots=True)
class VolumeWeek:
    """Volume semanal."""

    week_start: date
    km: float


@dataclass(frozen=True, slots=True)
class TrainingLoadSummary:
    """Resumo de carga de treino."""

    pmc: PMCCurve
    volume_weeks: Sequence[VolumeWeek]
    current_week_km: float
    avg4_km: float
    delta_pct: Optional[float]