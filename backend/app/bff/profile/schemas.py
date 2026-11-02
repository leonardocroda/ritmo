"""Schemas do BFF Profile — composição de tela Perfil (Zonas FC + Zonas Ritmo)."""

from datetime import date
from typing import Optional, List

from pydantic import BaseModel


class HRZoneBoundOut(BaseModel):
    low: int
    high: Optional[int]


class HRZoneConfigOut(BaseModel):
    method: str
    bounds: dict
    valid_from: date


class HRMetricOut(BaseModel):
    value: int
    source: str
    valid_from: date


class HRZonesOut(BaseModel):
    metrics: dict[str, Optional[HRMetricOut]]
    modes: dict[str, str]
    config: Optional[HRZoneConfigOut]
    zones: Optional[List[dict]]
    defaults: dict[str, List[HRZoneBoundOut]]


class PaceZoneOut(BaseModel):
    key: str
    pace_range: Optional[str] = None
    pace: Optional[str] = None
    ms_min: Optional[float] = None
    ms_max: Optional[float] = None
    ms: Optional[float] = None
    description: str


class PaceZonesOut(BaseModel):
    vdot: float
    source: str
    test_date: date
    distancia_metros: float
    tempo_segundos: float
    zones: dict[str, PaceZoneOut]
    equivalencias: dict[str, str]


class ProfileZonesOut(BaseModel):
    """Composição: Zonas FC + Zonas Ritmo em 1 payload para /perfil."""
    hr_zones: HRZonesOut
    pace_zones: PaceZonesOut