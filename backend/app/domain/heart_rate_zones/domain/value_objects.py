"""Value Objects do domínio Heart Rate Zones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class HRZoneMethod:
    """Método de cálculo de zonas de FC."""

    value: str  # "lthr", "fcr", "fcmax"


@dataclass(frozen=True, slots=True)
class HRZoneBounds:
    """Limites de uma zona de FC."""

    low: int
    high: Optional[int]


@dataclass(frozen=True, slots=True)
class VDOTZone:
    """Zona de ritmo VDOT."""

    key: str
    pace_range: Optional[str] = None
    pace: Optional[str] = None
    ms_min: Optional[float] = None
    ms_max: Optional[float] = None
    ms: Optional[float] = None
    description: str = ""