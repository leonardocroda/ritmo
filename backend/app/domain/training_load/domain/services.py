"""Serviços puros do domínio Training-Load — PMC, Volume, ACWR."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.domain.activity.domain.entities import Activity
from app.domain.training_load.domain.entities import PMCDay, PMCCurve, VolumeWeek


CTL_CONSTANT = 42
ATL_CONSTANT = 7
ACWR_WINDOW_DAYS = 28


@dataclass(frozen=True, slots=True)
class PMCCalculator:
    """Calculadora pura de PMC (CTL/ATL/TSB/ACWR)."""

    def compute(self, activities: Sequence[Activity], end_date: Optional[date] = None) -> PMCCurve:
        if not activities:
            return PMCCurve(days=0, points=(), current=PMCDay(end_date or date.today(), None, None, None, None))

        sorted_activities = sorted(activities, key=lambda a: a.start_time.date())

        daily_load = {}
        for a in sorted_activities:
            day = a.start_time.date()
            load = a.training_load or 0
            daily_load[day] = daily_load.get(day, 0) + load

        start = min(daily_load.keys())
        end = end_date or max(daily_load.keys()) if daily_load else date.today()

        ctl = 0.0
        atl = 0.0
        points = []

        current = start
        while current <= end:
            load = daily_load.get(current, 0.0)

            atl = atl + (load - atl) / ATL_CONSTANT
            ctl = ctl + (load - ctl) / CTL_CONSTANT
            tsb = ctl - atl

            acwr = None
            window_start = current - timedelta(days=ACWR_WINDOW_DAYS - 1)
            acute_load = sum(daily_load.get(d, 0.0) for d in daily_load if window_start <= d <= current)
            chronic_load = ctl * ACWR_WINDOW_DAYS
            if chronic_load > 0:
                acwr = acute_load / chronic_load

            points.append(PMCDay(current, ctl, atl, tsb, acwr))
            current += timedelta(days=1)

        current_point = points[-1] if points else PMCDay(end, None, None, None, None)
        return PMCCurve(days=len(points), points=tuple(points), current=current_point)


class VolumeCalculator:
    """Calculadora de volume semanal."""

    def compute_weekly(self, activities: Sequence[Activity], weeks: int = 10) -> Sequence[VolumeWeek]:
        if not activities:
            return []

        weekly_km = {}
        for a in activities:
            if a.is_running:
                week_start = a.start_time.date() - timedelta(days=a.start_time.weekday())
                weekly_km[week_start] = weekly_km.get(week_start, 0.0) + a.distance_m / 1000

        today = date.today()
        current_week = today - timedelta(days=today.weekday())
        weeks_list = []

        for i in range(weeks):
            week = current_week - timedelta(weeks=i)
            km = weekly_km.get(week, 0.0)
            weeks_list.append(VolumeWeek(week_start=week, km=km))

        return list(reversed(weeks_list))

    def get_current_week_volume(self, activities: Sequence[Activity]) -> tuple[float, float, Optional[float]]:
        weekly = self.compute_weekly(activities, weeks=5)
        if not weekly:
            return (0.0, 0.0, None)
        current = weekly[-1].km
        prev_4 = [w.km for w in weekly[-5:-1]]
        avg4 = sum(prev_4) / len(prev_4) if prev_4 else 0.0

        delta = None
        if avg4 > 0:
            delta = round((current - avg4) / avg4 * 100, 1)
        return (current, avg4, delta)