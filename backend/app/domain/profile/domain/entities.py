"""Entidades do domínio Profile — Zonas FC, Zonas Ritmo (VDOT)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class HRZoneConfig:
    """Configuração de zonas de FC."""

    id: int
    user_id: int
    method: str  # "lthr", "fcr", "fcmax"
    bounds: dict  # {"zones": [{"low": int, "high": int | None} x 5]}
    valid_from: date
    created_at: datetime


@dataclass(frozen=True, slots=True)
class HRMetric:
    """Métrica fisiológica (FCmax, FCrest, FCLTHR)."""

    id: int
    user_id: int
    kind: str  # "fcmax", "fcrest", "fclthr"
    value_bpm: int
    source: str  # "garmin", "manual"
    valid_from: date
    created_at: datetime


@dataclass(frozen=True, slots=True)
class HRSyncPref:
    """Preferência de sincronismo por métrica."""

    id: int
    user_id: int
    kind: str  # "fcmax", "fcrest", "fclthr"
    mode: str  # "garmin" | "manual"
    updated_at: datetime


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