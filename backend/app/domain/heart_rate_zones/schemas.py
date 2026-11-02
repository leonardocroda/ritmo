"""Schemas Pydantic para API de domínio Heart Rate Zones."""

from __future__ import annotations

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


class HRZonesUpdate(BaseModel):
    metrics: Optional[dict[str, Optional[int]]] = None
    method: Optional[str] = None
    bounds: Optional[dict] = None
    sync_modes: Optional[dict[str, str]] = None


class MetricHistoryOut(BaseModel):
    kind: str
    value: int
    source: str
    valid_from: date


class ConfigHistoryOut(BaseModel):
    method: str
    bounds: dict
    valid_from: date


class HRZonesHistoryOut(BaseModel):
    metrics: List[MetricHistoryOut]
    configs: List[ConfigHistoryOut]


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