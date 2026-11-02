"""Schemas do BFF Activities — composição de tela Treinos (lista + detalhe)."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class RunningDynamicsOut(BaseModel):
    gct_ms: Optional[int] = None
    stride_cm: Optional[float] = None
    vert_osc_cm: Optional[float] = None
    vert_ratio: Optional[float] = None


class SplitOut(BaseModel):
    idx: int
    dist_m: Optional[float]
    duration_s: Optional[float]
    pace_s: Optional[float]
    avg_hr: Optional[int]
    avg_cadence: Optional[float]
    avg_temperature: Optional[float]
    elevation_m: Optional[float]
    intensity_type: Optional[str]
    zone: Optional[str]
    km_label: str
    dynamics: RunningDynamicsOut = RunningDynamicsOut()


class ZoneMetaOut(BaseModel):
    key: str
    label: str
    pace_range: str
    color: str


class ConsistencyOut(BaseModel):
    first_half_pace_s: Optional[float]
    second_half_pace_s: Optional[float]
    balance_delta_s: Optional[float]
    balance_delta_pct: Optional[float]
    first_half_hr: Optional[float]
    second_half_hr: Optional[float]
    hr_drift_bpm: Optional[float]
    decoupling_pct: Optional[float]
    cadence_fade_spm: Optional[float] = None


class ContextOut(BaseModel):
    sleep: Optional[dict] = None
    hrv: Optional[dict] = None
    rhr: Optional[dict] = None
    temperature_c: Optional[float] = None


class ShoeSummaryOut(BaseModel):
    id: int
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    status: str


class ActivityOut(BaseModel):
    id: int
    start_time: datetime
    activity_type: str
    name: Optional[str] = None
    distance_m: float
    duration_s: float
    pace_s: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_cadence: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    aerobic_te: Optional[float] = None
    anaerobic_te: Optional[float] = None
    training_load: Optional[float] = None
    evaluated: bool = False
    inferred_type: Optional[str] = None
    structure: Optional[str] = None


class ActivityListItemOut(BaseModel):
    id: int
    start_time: datetime
    activity_type: str
    name: Optional[str] = None
    distance_m: float
    duration_s: float
    pace_s: Optional[float] = None
    avg_hr: Optional[int] = None
    inferred_type: Optional[str] = None
    evaluated: bool = False


class ActivityListOut(BaseModel):
    items: List[ActivityListItemOut]
    total: int
    limit: int
    offset: int


class ActivityDetailOut(BaseModel):
    activity: ActivityOut
    splits: List[SplitOut]
    zones: List[ZoneMetaOut]
    hr_color: str
    consistency: Optional[ConsistencyOut] = None
    context: ContextOut
    evaluations: List[dict] = []
    shoe: Optional[ShoeSummaryOut] = None