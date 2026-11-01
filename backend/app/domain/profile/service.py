"""Application Service do domínio Profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from app.domain.profile.domain.entities import (
    HRZoneConfig, HRMetric, HRSyncPref, PaceZoneConfig
)
from app.domain.profile.ports.repositories import ProfileRepository
from app.domain.profile.schemas import (
    HRZonesOut, HRZonesUpdate, PaceZonesOut,
    HRMetricOut, HRZoneConfigOut, HRZoneBoundOut, PaceZoneOut
)


@dataclass
class ProfileService:
    repo: ProfileRepository

    def get_hr_zones(self, user_id: int) -> HRZonesOut:
        config = self.repo.get_hr_zone_config(user_id)
        metrics = self.repo.get_hr_metrics(user_id)
        prefs = self.repo.get_hr_sync_prefs(user_id)

        # Métricas atuais por kind
        metrics_by_kind = {m.kind: m for m in metrics}
        modes_by_kind = {p.kind: p.mode for p in prefs}

        # Config atual
        config_out = None
        if config:
            config_out = HRZoneConfigOut(
                method=config.method,
                bounds=config.bounds,
                valid_from=config.valid_from,
            )

        # Zonas derivadas (placeholder)
        zones = None

        # Defaults dos 3 métodos
        defaults = {
            "lthr": [
                HRZoneBoundOut(low=0, high=80),
                HRZoneBoundOut(low=81, high=88),
                HRZoneBoundOut(low=89, high=93),
                HRZoneBoundOut(low=94, high=99),
                HRZoneBoundOut(low=100, high=None),
            ],
            "fcr": [
                HRZoneBoundOut(low=0, high=60),
                HRZoneBoundOut(low=61, high=70),
                HRZoneBoundOut(low=71, high=80),
                HRZoneBoundOut(low=81, high=90),
                HRZoneBoundOut(low=91, high=None),
            ],
            "fcmax": [
                HRZoneBoundOut(low=0, high=50),
                HRZoneBoundOut(low=51, high=60),
                HRZoneBoundOut(low=61, high=70),
                HRZoneBoundOut(low=71, high=80),
                HRZoneBoundOut(low=81, high=None),
            ],
        }

        return HRZonesOut(
            metrics={
                "fcmax": HRMetricOut(
                    value=metrics_by_kind.get("fcmax", HRMetric(value_bpm=0, source="", valid_from=date.today())).value_bpm,
                    source=metrics_by_kind.get("fcmax", HRMetric(value_bpm=0, source="", valid_from=date.today())).source,
                    valid_from=metrics_by_kind.get("fcmax", HRMetric(value_bpm=0, source="", valid_from=date.today())).valid_from,
                ) if "fcmax" in metrics_by_kind else None,
                "fcrest": HRMetricOut(
                    value=metrics_by_kind.get("fcrest", HRMetric(value_bpm=0, source="", valid_from=date.today())).value_bpm,
                    source=metrics_by_kind.get("fcrest", HRMetric(value_bpm=0, source="", valid_from=date.today())).source,
                    valid_from=metrics_by_kind.get("fcrest", HRMetric(value_bpm=0, source="", valid_from=date.today())).valid_from,
                ) if "fcrest" in metrics_by_kind else None,
                "fclthr": HRMetricOut(
                    value=metrics_by_kind.get("fclthr", HRMetric(value_bpm=0, source="", valid_from=date.today())).value_bpm,
                    source=metrics_by_kind.get("fclthr", HRMetric(value_bpm=0, source="", valid_from=date.today())).source,
                    valid_from=metrics_by_kind.get("fclthr", HRMetric(value_bpm=0, source="", valid_from=date.today())).valid_from,
                ) if "fclthr" in metrics_by_kind else None,
            },
            modes={
                "fcmax": modes_by_kind.get("fcmax", "garmin"),
                "fcrest": modes_by_kind.get("fcrest", "garmin"),
                "fclthr": modes_by_kind.get("fclthr", "garmin"),
            },
            config=config_out,
            zones=zones,
            defaults=defaults,
        )

    def update_hr_zones(self, user_id: int, data: HRZonesUpdate) -> HRZonesOut:
        # Placeholder
        return self.get_hr_zones(user_id)

    def get_pace_zones(self, user_id: int) -> PaceZonesOut:
        config = self.repo.get_pace_zone_config(user_id)
        if not config:
            raise ValueError("Zonas de ritmo não configuradas")

        return PaceZonesOut(
            vdot=config.vdot,
            source=config.source,
            test_date=config.test_date,
            distancia_metros=config.distance_m,
            tempo_segundos=config.time_s,
            zones={
                k: PaceZoneOut(**v) for k, v in config.zones.items()
            },
            equivalencias=config.equivalencias,
        )