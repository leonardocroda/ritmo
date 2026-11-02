"""Application Service do domínio Heart Rate Zones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, List, Sequence

from app.domain.heart_rate_zones.domain.entities import HRZoneConfig, HRMetric, HRSyncPref
from app.domain.heart_rate_zones.ports.repositories import HeartRateZonesRepository
from app.domain.heart_rate_zones.schemas import (
    HRZonesOut, HRZonesUpdate, HRZoneConfigOut, HRMetricOut, HRZoneBoundOut,
    HRZonesHistoryOut, MetricHistoryOut, ConfigHistoryOut
)


# Defaults dos 3 métodos
DEFAULT_ZONES = {
    "lthr": [
        {"low": 0, "high": 80},
        {"low": 81, "high": 88},
        {"low": 89, "high": 93},
        {"low": 94, "high": 99},
        {"low": 100, "high": None},
    ],
    "fcr": [
        {"low": 0, "high": 60},
        {"low": 61, "high": 70},
        {"low": 71, "high": 80},
        {"low": 81, "high": 90},
        {"low": 91, "high": None},
    ],
    "fcmax": [
        {"low": 0, "high": 50},
        {"low": 51, "high": 60},
        {"low": 61, "high": 70},
        {"low": 71, "high": 80},
        {"low": 81, "high": None},
    ],
}


@dataclass
class HeartRateZonesService:
    repo: HeartRateZonesRepository

    def get_hr_zones(self, user_id: int) -> HRZonesOut:
        config = self.repo.get_hr_zone_config(user_id)
        metrics = self.repo.get_hr_metrics(user_id)
        prefs = self.repo.get_hr_sync_prefs(user_id)

        metrics_by_kind = {m.kind: m for m in metrics}
        modes_by_kind = {p.kind: p.mode for p in prefs}

        config_out = None
        if config:
            config_out = HRZoneConfigOut(
                method=config.method,
                bounds=config.bounds,
                valid_from=config.valid_from,
            )

        def metric_out(kind: str) -> HRMetricOut | None:
            m = metrics_by_kind.get(kind)
            if m is None:
                return None
            return HRMetricOut(value=m.value_bpm, source=m.source, valid_from=m.valid_from)

        return HRZonesOut(
            metrics={
                "fcmax": metric_out("fcmax"),
                "fcrest": metric_out("fcrest"),
                "fclthr": metric_out("fclthr"),
            },
            modes={
                "fcmax": modes_by_kind.get("fcmax", "garmin"),
                "fcrest": modes_by_kind.get("fcrest", "garmin"),
                "fclthr": modes_by_kind.get("fclthr", "garmin"),
            },
            config=config_out,
            zones=None,
            defaults=DEFAULT_ZONES,
        )

    def update_hr_zones(self, user_id: int, data: HRZonesUpdate) -> HRZonesOut:
        # TODO: implementar atualização real
        return self.get_hr_zones(user_id)

    def get_hr_zones_history(self, user_id: int) -> HRZonesHistoryOut:
        metric_rows = self.repo.get_hr_metrics_history(user_id)
        config_rows = self.repo.get_hr_zone_configs_history(user_id)

        return HRZonesHistoryOut(
            metrics=[
                MetricHistoryOut(
                    kind=row.kind,
                    value=row.value_bpm,
                    source=row.source,
                    valid_from=row.valid_from,
                )
                for row in metric_rows
            ],
            configs=[
                ConfigHistoryOut(
                    method=row.method,
                    bounds=row.bounds,
                    valid_from=row.valid_from,
                )
                for row in config_rows
            ],
        )