"""Adaptadores SQLAlchemy para repositórios do domínio Activity."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Activity as ActivityModel, Split as SplitModel
from app.domain.activity.domain.entities import Activity, Split
from app.domain.activity.domain.value_objects import ActivityFilter, ZoneConfigVO
from app.domain.activity.ports.repositories import ActivityRepository, SplitRepository


class SQLAlchemyActivityRepository(ActivityRepository):
    """Implementação SQLAlchemy do ActivityRepository."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, id: int, user_id: int) -> Activity | None:
        model = self.session.execute(
            select(ActivityModel).where(
                ActivityModel.id == id, ActivityModel.user_id == user_id
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        # Note: splits e zone_config serão carregados pelo service
        return self._to_domain(model, None, ())

    def list(self, user_id: int, filter: ActivityFilter) -> Sequence[Activity]:
        filters = [ActivityModel.user_id == user_id]
        if filter.activity_type == "running":
            RUNNING_TYPES = ("running", "trail_running")
            filters.append(ActivityModel.activity_type.in_(RUNNING_TYPES))

        models = self.session.execute(
            select(ActivityModel)
            .where(*filters)
            .order_by(ActivityModel.start_time.desc(), ActivityModel.id.desc())
            .offset(filter.offset)
            .limit(filter.limit)
        ).scalars().all()

        return [self._to_domain(m, None, ()) for m in models]

    def count(self, user_id: int, filter: ActivityFilter) -> int:
        filters = [ActivityModel.user_id == user_id]
        if filter.activity_type == "running":
            RUNNING_TYPES = ("running", "trail_running")
            filters.append(ActivityModel.activity_type.in_(RUNNING_TYPES))

        return self.session.execute(
            select(func.count()).select_from(ActivityModel).where(*filters)
        ).scalar_one()

    def save(self, activity: Activity) -> Activity:
        # Para leitura, não implementamos save completo
        # O save real acontece no sync layer
        raise NotImplementedError("Save not implemented in read-only repository")

    def delete(self, id: int, user_id: int) -> bool:
        model = self.session.execute(
            select(ActivityModel).where(
                ActivityModel.id == id, ActivityModel.user_id == user_id
            )
        ).scalar_one_or_none()
        if model is None:
            return False
        self.session.delete(model)
        return True

    def _to_domain(
        self,
        model: ActivityModel,
        zone_config: ZoneConfigVO | None,
        splits: Sequence[Split],
    ) -> Activity:
        """Converte modelo SQLAlchemy para entidade de domínio."""
        from app.domain.activity.domain.value_objects import HeartRate, Cadence, Pace

        avg_hr = HeartRate(model.avg_hr) if model.avg_hr is not None else None
        max_hr = HeartRate(model.max_hr) if model.max_hr is not None else None
        avg_cadence = Cadence(int(model.avg_cadence)) if model.avg_cadence is not None else None

        cumulative_m = 0.0
        labeled_splits = []
        for split in splits:
            cumulative_m += split.distance_m or 0
            labeled_splits.append(
                Split(
                    idx=split.idx,
                    distance_m=split.distance_m,
                    duration_s=split.duration_s,
                    pace=split.pace,
                    avg_hr=split.avg_hr,
                    avg_cadence=split.avg_cadence,
                    avg_temperature=split.avg_temperature,
                    elevation_m=split.elevation_m,
                    intensity_type=split.intensity_type,
                    zone=split.zone,
                    km_label=f"{cumulative_m / 1000:.1f}".replace(".", ","),
                    dynamics=split.dynamics,
                )
            )

        return Activity(
            id=model.id,
            user_id=model.user_id,
            start_time=model.start_time,
            activity_type=model.activity_type,
            name=model.name,
            distance_m=model.distance_m,
            duration_s=model.duration_s,
            avg_hr=avg_hr,
            max_hr=max_hr,
            avg_cadence=avg_cadence,
            elevation_gain_m=model.elevation_gain_m,
            aerobic_te=model.aerobic_te,
            anaerobic_te=model.anaerobic_te,
            training_load=model.training_load,
            inferred_type=None,  # Será calculado pelo service
            structure=None,  # Será derivado pelo service
            splits=tuple(labeled_splits),
            evaluated=model.evaluated,
            garmin_id=model.garmin_id,
            shoe_id=model.shoe_id,
            feel=model.feel,
            rpe=model.rpe,
        )


class SQLAlchemySplitRepository(SplitRepository):
    """Implementação SQLAlchemy do SplitRepository."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_activity(self, activity_id: int) -> Sequence[Split]:
        models = self.session.execute(
            select(SplitModel)
            .where(SplitModel.activity_id == activity_id)
            .order_by(SplitModel.idx)
        ).scalars().all()

        return [self._to_domain(m) for m in models]

    def save_batch(self, splits: Sequence[Split]) -> None:
        # Para leitura, não implementamos
        raise NotImplementedError("Save not implemented in read-only repository")

    def _to_domain(self, model: SplitModel) -> Split:
        from app.domain.activity.domain.value_objects import HeartRate, Cadence, Pace, ZoneKey
        from app.domain.activity.domain.entities import RunningDynamics

        pace = None
        if model.pace_s and model.pace_s > 0:
            pace = Pace.from_seconds_per_km(model.pace_s)

        avg_hr = HeartRate(model.avg_hr) if model.avg_hr is not None else None
        avg_cadence = Cadence(int(model.avg_cadence)) if model.avg_cadence is not None else None

        zone = None
        if pace is not None:
            # Zona será classificada pelo service com zone_config
            pass

        return Split(
            idx=model.idx,
            distance_m=model.dist_m,
            duration_s=model.duration_s,
            pace=pace,
            avg_hr=avg_hr,
            avg_cadence=avg_cadence,
            avg_temperature=model.avg_temperature,
            elevation_m=model.elevation_m,
            intensity_type=model.intensity_type,
            zone=zone,
            km_label="",  # Preenchido pelo service
            dynamics=RunningDynamics(
                gct_ms=model.ground_contact_time_ms,
                stride_cm=model.stride_length_cm,
                vert_osc_cm=model.vertical_oscillation_cm,
                vert_ratio=model.vertical_ratio,
            ),
        )