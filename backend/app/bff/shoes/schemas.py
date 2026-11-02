"""Schemas do BFF Shoes — composição de tela Equipamentos."""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel


class ShoeOut(BaseModel):
    id: int
    name: str
    brand: Optional[str]
    model: Optional[str]
    acquired_date: Optional[date]
    initial_km: float
    max_km: Optional[float]
    status: str
    strava_gear_id: Optional[str]
    created_at: datetime
    current_km: float
    run_count: int
    last_use: Optional[datetime]
    life_pct: Optional[float]


class ShoeCreateIn(BaseModel):
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    acquired_date: Optional[date] = None
    initial_km: float = 0.0
    max_km: Optional[float] = None
    status: str = "ativo"


class ShoeUpdateIn(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    acquired_date: Optional[date] = None
    initial_km: Optional[float] = None
    max_km: Optional[float] = None
    status: Optional[str] = None


class ShoeSummaryOut(BaseModel):
    id: int
    name: str
    brand: Optional[str]
    model: Optional[str]
    status: str


class ShoesListOut(BaseModel):
    items: List[ShoeOut]
    attribution_30d_pct: Optional[float]


class DegradationSignalOut(BaseModel):
    signal: str
    label: str
    initial: float
    final: float
    delta: float
    unit: str
    direction: Optional[str] = None
    confidence: Optional[str] = None


class DegradationOut(BaseModel):
    shoe_id: int
    total_km: float
    n_runs: int
    signals: List[DegradationSignalOut]
    verdict: Optional[str] = None
    insufficient: bool = False