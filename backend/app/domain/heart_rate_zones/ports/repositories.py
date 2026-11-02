"""Ports para repositórios do domínio Heart Rate Zones."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.heart_rate_zones.domain.entities import HRZoneConfig, HRMetric, HRSyncPref


@runtime_checkable
class HeartRateZonesRepository(Protocol):
    def get_hr_zone_config(self, user_id: int) -> HRZoneConfig | None: ...
    def get_hr_metrics(self, user_id: int) -> Sequence[HRMetric]: ...
    def get_hr_sync_prefs(self, user_id: int) -> Sequence[HRSyncPref]: ...

    def save_hr_zone_config(self, config: HRZoneConfig) -> HRZoneConfig: ...
    def save_hr_metric(self, metric: HRMetric) -> HRMetric: ...
    def save_hr_sync_pref(self, pref: HRSyncPref) -> HRSyncPref: ...