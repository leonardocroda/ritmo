"""Adaptador SQLAlchemy para VDOTRepository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity as ActivityModel, VdotZoneConfig, VdotTest, RacePrediction
from app.domain.activity.domain.entities import Activity
from app.domain.vdot.domain.entities import (
    VDOTProfile, TimelinePoint, Prediction, VO2maxPoint
)
from app.domain.vdot.ports.repositories import VDOTRepository


class SQLAlchemyVDOTRepository(VDOTRepository):
    """Implementação SQLAlchemy do VDOTRepository."""

    def __init__(self, session: Session):
        self.session = session

    def get_vdot_profile(self, user_id: int) -> VDOTProfile | None:
        # Busca VDOT mais recente
        config = self.session.execute(
            select(VdotZoneConfig).where(VdotZoneConfig.user_id == user_id)
            .order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc())
        ).scalars().first()

        if not config:
            return None

        return VDOTProfile(
            current_vdot=config.vdot,
            source=config.source,
            test_date=config.test_date,
            test_distance_m=config.distance_m,
            test_time_s=config.time_s,
        )

    def get_timeline(self, user_id: int) -> Sequence[TimelinePoint]:
        tests = self.session.execute(
            select(VdotTest).where(VdotTest.user_id == user_id)
            .order_by(VdotTest.date.desc())
        ).scalars().all()

        return [
            TimelinePoint(
                date=t.date,
                vdot=t.vdot,
                source=t.source,
                label=f"{t.source} {t.distance_m/1000:.1f}km",
                distance_m=t.distance_m,
                time_s=t.time_s,
            )
            for t in tests
        ]

    def get_predictions(self, user_id: int) -> dict[str, dict]:
        preds = self.session.execute(
            select(RacePrediction).where(RacePrediction.user_id == user_id)
        ).scalars().all()

        return {
            p.event: {
                "garmin_s": p.time_s,
                "event": p.event,
            }
            for p in preds
        }

    def get_vo2max_timeline(self, user_id: int) -> Sequence[VO2maxPoint]:
        # Placeholder - usar dados Garmin reais
        return []

    def get_activities_for_performance(self, user_id: int) -> Sequence[Activity]:
        models = self.session.execute(
            select(ActivityModel).where(
                ActivityModel.user_id == user_id,
                ActivityModel.activity_type.in_(["running", "trail_running"])
            ).order_by(ActivityModel.start_time.desc()).limit(200)
        ).scalars().all()

        return [self._to_activity(m) for m in models]

    def save_vdot_profile(self, profile: VDOTProfile) -> VDOTProfile:
        # Placeholder
        return profile

    def _to_activity(self, model) -> Activity:
        return Activity(
            id=model.id,
            user_id=model.user_id,
            start_time=model.start_time,
            activity_type=model.activity_type,
            name=model.name,
            distance_m=model.distance_m,
            duration_s=model.duration_s,
            avg_hr=None,
            max_hr=None,
            avg_cadence=None,
            elevation_gain_m=model.elevation_gain_m,
            aerobic_te=model.aerobic_te,
            anaerobic_te=model.anaerobic_te,
            training_load=model.training_load,
            inferred_type=None,
            structure=None,
            splits=(),
            evaluated=model.evaluated,
        )