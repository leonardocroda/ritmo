"""Application Service do domínio Training-Load."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.domain.training_load.domain.entities import PMCCurve, PMCDay, VolumeWeek
from app.domain.training_load.domain.services import PMCCalculator, VolumeCalculator
from app.domain.training_load.ports.repositories import TrainingLoadRepository
from app.domain.training_load.schemas import (
    TrainingLoadOut, PMCCurveOut, PMCDayOut, VolumeWeekOut
)


@dataclass
class TrainingLoadService:
    repo: TrainingLoadRepository
    pmc_calc: PMCCalculator
    volume_calc: VolumeCalculator

    def get_training_load(self, user_id: int, days: int = 60) -> TrainingLoadOut:
        end = date.today()
        start = end - timedelta(days=days)

        activities = self.repo.get_activities(user_id, start, end)

        pmc = self.pmc_calc.compute(activities, end)
        volume_weeks = self.volume_calc.compute_weekly(activities, weeks=10)
        current_km, avg4_km, delta_pct = self.volume_calc.get_current_week_volume(activities)

        return TrainingLoadOut(
            pmc=PMCCurveOut(
                days=pmc.days,
                points=[
                    PMCDayOut(date=p.date, ctl=p.ctl, atl=p.atl, tsb=p.tsb, acwr=p.acwr)
                    for p in pmc.points
                ],
                current=PMCDayOut(
                    date=pmc.current.date, ctl=pmc.current.ctl,
                    atl=pmc.current.atl, tsb=pmc.current.tsb, acwr=pmc.current.acwr
                ),
            ),
            volume_weeks=[
                VolumeWeekOut(week_start=w.week_start, km=w.km)
                for w in volume_weeks
            ],
            current_week_km=current_km,
            avg4_km=avg4_km,
            delta_pct=delta_pct,
        )