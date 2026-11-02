"""Adaptadores SQLAlchemy para repositórios do domínio Health Metrics."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Sleep, Hrv, Rhr, Stress, DailyLoad
from app.domain.health_metrics.domain.entities import SleepNight, HRVReading, RHRReading, StressReading, DailyLoad
from app.domain.health_metrics.ports.repositories import HealthRepository


class SQLAlchemyHealthRepository(HealthRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_sleep_range(self, user_id: int, start: date, end: date) -> Sequence[SleepNight]:
        models = self.session.execute(
            select(Sleep).where(
                Sleep.user_id == user_id,
                Sleep.date >= start,
                Sleep.date <= end,
            ).order_by(Sleep.date)
        ).scalars().all()
        return [self._to_sleep_night(m) for m in models]

    def get_hrv_range(self, user_id: int, start: date, end: date) -> Sequence[HRVReading]:
        models = self.session.execute(
            select(Hrv).where(
                Hrv.user_id == user_id,
                Hrv.date >= start,
                Hrv.date <= end,
            ).order_by(Hrv.date)
        ).scalars().all()
        return [self._to_hrv(m) for m in models]

    def get_rhr_range(self, user_id: int, start: date, end: date) -> Sequence[RHRReading]:
        models = self.session.execute(
            select(Rhr).where(
                Rhr.user_id == user_id,
                Rhr.date >= start,
                Rhr.date <= end,
            ).order_by(Rhr.date)
        ).scalars().all()
        return [self._to_rhr(m) for m in models]

    def get_stress_range(self, user_id: int, start: date, end: date) -> Sequence[StressReading]:
        models = self.session.execute(
            select(Stress).where(
                Stress.user_id == user_id,
                Stress.date >= start,
                Stress.date <= end,
            ).order_by(Stress.date)
        ).scalars().all()
        return [self._to_stress(m) for m in models]

    def get_load_range(self, user_id: int, start: date, end: date) -> Sequence[DailyLoad]:
        models = self.session.execute(
            select(DailyLoad).where(
                DailyLoad.user_id == user_id,
                DailyLoad.date >= start,
                DailyLoad.date <= end,
            ).order_by(DailyLoad.date)
        ).scalars().all()
        return [self._to_load(m) for m in models]

    def get_latest_sleep(self, user_id: int) -> SleepNight | None:
        model = self.session.execute(
            select(Sleep).where(Sleep.user_id == user_id).order_by(Sleep.date.desc())
        ).scalars().first()
        return self._to_sleep_night(model) if model else None

    def get_latest_hrv(self, user_id: int) -> HRVReading | None:
        model = self.session.execute(
            select(Hrv).where(Hrv.user_id == user_id).order_by(Hrv.date.desc())
        ).scalars().first()
        return self._to_hrv(model) if model else None

    def get_latest_rhr(self, user_id: int) -> RHRReading | None:
        model = self.session.execute(
            select(Rhr).where(Rhr.user_id == user_id).order_by(Rhr.date.desc())
        ).scalars().first()
        return self._to_rhr(model) if model else None

    def get_latest_stress(self, user_id: int) -> StressReading | None:
        model = self.session.execute(
            select(Stress).where(Stress.user_id == user_id).order_by(Stress.date.desc())
        ).scalars().first()
        return self._to_stress(model) if model else None

    def get_latest_load(self, user_id: int) -> DailyLoad | None:
        model = self.session.execute(
            select(DailyLoad).where(DailyLoad.user_id == user_id).order_by(DailyLoad.date.desc())
        ).scalars().first()
        return self._to_load(model) if model else None

    # --- Conversão modelos -> entidades ---

    def _to_sleep_night(self, m) -> SleepNight:
        return SleepNight(
            id=m.id,
            user_id=m.user_id,
            date=m.date,
            duration_s=m.duration_s,
            score=m.score,
            deep_pct=m.deep_pct,
            rem_pct=m.rem_pct,
            light_pct=m.light_pct,
            awakenings=m.awakenings,
            bed_time=m.bed_time,
            wake_time=m.wake_time,
        )

    def _to_hrv(self, m) -> HRVReading:
        return HRVReading(
            id=m.id,
            user_id=m.user_id,
            date=m.date,
            value=m.value,
            status=m.status,
        )

    def _to_rhr(self, m) -> RHRReading:
        return RHRReading(
            id=m.id,
            user_id=m.user_id,
            date=m.date,
            value=m.value,
        )

    def _to_stress(self, m) -> StressReading:
        return StressReading(
            id=m.id,
            user_id=m.user_id,
            date=m.date,
            avg=m.avg,
        )

    def _to_load(self, m) -> DailyLoad:
        return DailyLoad(
            id=m.id,
            user_id=m.user_id,
            date=m.date,
            ctl=m.ctl,
            atl=m.atl,
            tsb=m.tsb,
            acwr=m.acwr,
        )