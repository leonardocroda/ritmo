"""Entidades do domínio Health — imutáveis, sem dependências de infra."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class SleepNight:
    """Uma noite de sono — entidade imutável."""

    id: int
    user_id: int
    date: date
    duration_s: float
    score: Optional[int]
    deep_pct: Optional[float]
    rem_pct: Optional[float]
    light_pct: Optional[float]
    awakenings: Optional[int]
    bed_time: Optional[datetime]
    wake_time: Optional[datetime]

    @property
    def duration_h(self) -> float:
        return self.duration_s / 3600


@dataclass(frozen=True, slots=True)
class HRVReading:
    """Leitura de HRV — entidade imutável."""

    id: int
    user_id: int
    date: date
    value: float
    status: Optional[str]


@dataclass(frozen=True, slots=True)
class RHRReading:
    """Leitura de RHR (FC de repouso) — entidade imutável."""

    id: int
    user_id: int
    date: date
    value: int


@dataclass(frozen=True, slots=True)
class StressReading:
    """Leitura de estresse — entidade imutável."""

    id: int
    user_id: int
    date: date
    avg: Optional[int]


@dataclass(frozen=True, slots=True)
class DailyLoad:
    """Carga diária (PMC) — entidade imutável."""

    id: int
    user_id: int
    date: date
    ctl: Optional[float]
    atl: Optional[float]
    tsb: Optional[float]
    acwr: Optional[float]