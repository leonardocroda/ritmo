"""Value Objects do domínio Health."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True, slots=True)
class HRVStatus:
    """Status do HRV — value object."""

    value: float
    status: Optional[str]  # "balanced", "unbalanced", None
    date: date


@dataclass(frozen=True, slots=True)
class SleepScore:
    """Score de sono — value object."""

    score: Optional[int]
    duration_h: float
    deep_pct: Optional[float]
    rem_pct: Optional[float]


@dataclass(frozen=True, slots=True)
class StressLevel:
    """Nível de estresse — value object."""

    avg: Optional[int]
    date: date


@dataclass(frozen=True, slots=True)
class HRVBaseline:
    """Linha de base HRV — value object com média móvel e banda."""

    date: date
    value: Optional[float]
    avg7: Optional[float]
    band_low: Optional[float]
    band_high: Optional[float]


@dataclass(frozen=True, slots=True)
class DoseResponseBucket:
    """Bucket dose-resposta — value object."""

    nights: int
    avg_hrv: Optional[float]
    avg_score: Optional[float]


@dataclass(frozen=True, slots=True)
class DoseResponse:
    """Resposta dose-resposta completa."""

    short: DoseResponseBucket
    adequate: DoseResponseBucket
    neutral_nights: int


@dataclass(frozen=True, slots=True)
class StrengthLifestyle:
    """Estilo de vida - força."""

    streak_weeks: int
    weeks_hit: int
    weeks_total: int
    current_week_sessions: int


@dataclass(frozen=True, slots=True)
class YogaLifestyle:
    """Estilo de vida - yoga."""

    sessions: int
    per_week_avg: float


@dataclass(frozen=True, slots=True)
class Lifestyle:
    """Estilo de vida combinado."""

    strength: StrengthLifestyle
    yoga: YogaLifestyle


@dataclass(frozen=True, slots=True)
class HRVSignal:
    """Sinal HRV do último dia com dado."""

    value: float
    status: Optional[str]
    date: date


@dataclass(frozen=True, slots=True)
class SleepSignal:
    """Sinal de sono da última noite."""

    duration_s: float
    delta_s: Optional[float]
    date: date


@dataclass(frozen=True, slots=True)
class FitnessSignal:
    """Sinal de forma (PMC)."""

    tsb: Optional[float]
    acwr: Optional[float]
    date: date