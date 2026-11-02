"""Adaptador SQLAlchemy para TrainingLoadRepository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity as ActivityModel, VdotZoneConfig, VdotTest, RacePrediction
from app.domain.activity.domain.entities import Activity
from app.domain.vdot.domain.entities import VDOTProfile, TimelinePoint, Prediction, VO2maxPoint
from app.domain.training_load.domain.entities import PMCCurve, PMCDay, VolumeWeek
from app.domain.training_load.ports.repositories import TrainingLoadRepository


class SQLAlchemyTrainingLoadRepository(TrainingLoadRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_activities(self, user_id: int, start: date, end: date) -> Sequence[Activity]:
        models = self.session.execute(
            select(ActivityModel).where(
                ActivityModel.user_id == user_id,
                ActivityModel.start_time >= start,
                ActivityModel.start_time <= end,
            )
        ).scalars().all()
        return [self._to_activity(m) for m in models]

    def get_latest_load(self, user_id: int) -> PMCCurve | None:
        from app.db.models import DailyLoad
        model = self.session.execute(
            select(DailyLoad).where(DailyLoad.user_id == user_id)
            .order_by(DailyLoad.date.desc())
        ).scalars().first()
        if not model:
            return None
        return PMCCurve(
            days=1,
            points=(PMCDay(model.date, model.ctl, model.atl, model.tsb, model.acwr),),
            current=PMCDay(model.date, model.ctl, model.atl, model.tsb, model.acwr),
        )

    def _to_activity(self, m) -> Activity:
        return Activity(
            id=m.id, user_id=m.user_id, start_time=m.start_time,
            activity_type=m.activity_type, name=m.name,
            distance_m=m.distance_m, duration_s=m.duration_s,
            avg_hr=None, max_hr=None, avg_cadence=None,
            elevation_gain_m=m.elevation_gain_m,
            aerobic_te=m.aerobic_te, anaerobic_te=m.anaerobic_te,
            training_load=m.training_load,
            inferred_type=None, structure=None, splits=(), evaluated=m.evaluated,
        )