"""Adaptador SQLAlchemy para HeartRateZonesRepository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    HrZoneConfig, UserHrMetric, HrZoneConfig as HrZoneConfigModel,
    VdotZoneConfig, UserHrSyncPref
)
from app.domain.heart_rate_zones.domain.entities import HRZoneConfig, HRMetric, HRSyncPref
from app.domain.vdot.domain.entities import PaceZoneConfig
from app.domain.heart_rate_zones.ports.repositories import HeartRateZonesRepository


class SQLAlchemyHeartRateZonesRepository(HeartRateZonesRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_hr_zone_config(self, user_id: int) -> HRZoneConfig | None:
        model = self.session.execute(
            select(HrZoneConfig).where(HrZoneConfig.user_id == user_id)
            .order_by(HrZoneConfig.valid_from.desc(), HrZoneConfig.id.desc())
        ).scalars().first()
        return self._to_hr_zone_config(model) if model else None

    def get_hr_metrics(self, user_id: int) -> Sequence[HRMetric]:
        models = self.session.execute(
            select(UserHrMetric).where(UserHrMetric.user_id == user_id)
            .order_by(UserHrMetric.kind, UserHrMetric.valid_from.desc())
        ).scalars().all()
        return [self._to_hr_metric(m) for m in models]

    def get_hr_sync_prefs(self, user_id: int) -> Sequence[HRSyncPref]:
        models = self.session.execute(
            select(UserHrSyncPref).where(UserHrSyncPref.user_id == user_id)
        ).scalars().all()
        return [self._to_hr_sync_pref(m) for m in models]

    def get_pace_zone_config(self, user_id: int) -> PaceZoneConfig | None:
        model = self.session.execute(
            select(VdotZoneConfig).where(VdotZoneConfig.user_id == user_id)
            .order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc())
        ).scalars().first()
        return self._to_pace_zone_config(model) if model else None

    def save_hr_zone_config(self, config: HRZoneConfig) -> HRZoneConfig:
        # Placeholder
        return config

    def save_hr_metric(self, metric: HRMetric) -> HRMetric:
        return metric

    def save_hr_sync_pref(self, pref: HRSyncPref) -> HRSyncPref:
        return pref

    def save_pace_zone_config(self, config: PaceZoneConfig) -> PaceZoneConfig:
        return config

    def _to_hr_zone_config(self, m) -> HRZoneConfig:
        return HRZoneConfig(
            id=m.id,
            user_id=m.user_id,
            method=m.method,
            bounds=m.bounds,
            valid_from=m.valid_from,
            created_at=m.created_at,
        )

    def _to_hr_metric(self, m) -> HRMetric:
        return HRMetric(
            id=m.id,
            user_id=m.user_id,
            kind=m.kind,
            value_bpm=m.value_bpm,
            source=m.source,
            valid_from=m.valid_from,
            created_at=m.created_at,
        )

    def _to_hr_sync_pref(self, m) -> HRSyncPref:
        return HRSyncPref(
            id=m.id,
            user_id=m.user_id,
            kind=m.kind,
            mode=m.mode,
            updated_at=m.updated_at,
        )

    def _to_pace_zone_config(self, m) -> PaceZoneConfig:
        return PaceZoneConfig(
            id=m.id,
            user_id=m.user_id,
            vdot=m.vdot,
            source=m.source,
            test_date=m.test_date,
            distance_m=m.distance_m,
            time_s=m.time_s,
            zones=m.zones,
            equivalencias=m.equivalencias,
            valid_from=m.valid_from,
            created_at=m.created_at,
        )