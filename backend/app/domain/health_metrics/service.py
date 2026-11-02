"""Application Service (Use Cases) do domínio Health Metrics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from app.domain.health_metrics.domain.entities import SleepNight, HRVReading, RHRReading, StressReading, DailyLoad
from app.domain.health_metrics.domain.services import (
    HRVCalculator, SleepCalculator, DoseResponseCalculator, LifestyleCalculator
)
from app.domain.health_metrics.domain.value_objects import (
    HRVSignal, SleepSignal, FitnessSignal,
    DoseResponse, DoseResponseBucket, StrengthLifestyle, YogaLifestyle, Lifestyle
)
from app.domain.health_metrics.ports.repositories import HealthRepository
from app.domain.health_metrics.schemas import (
    HealthSummaryOut, SleepBlockOut, SleepPointOut, BelowFloorOut, WeekdayEntryOut,
    RegularityOut, HrvBlockOut, HrvPointOut, HrvCurrentOut, RhrBlockOut, RhrPointOut,
    StressBlockOut, StressPointOut, PmcBlockOut, PmcPointOut, DoseResponseOut,
    DoseBucketOut, LifestyleOut, StrengthOut, YogaOut, HealthSignalsOut
)


@dataclass
class HealthMetricsService:
    """Service de aplicação que orquestra repositórios e serviços de domínio."""

    repo: HealthRepository
    hrv_calc: HRVCalculator
    sleep_calc: SleepCalculator
    dose_calc: DoseResponseCalculator
    lifestyle_calc: LifestyleCalculator

    def get_summary(self, user_id: int, days: int = 60) -> HealthSummaryOut:
        end = date.today()
        start = end - timedelta(days=days)

        sleep_nights = self.repo.get_sleep_range(user_id, start, end)
        hrv_readings = self.repo.get_hrv_range(user_id, start, end)
        rhr_readings = self.repo.get_rhr_range(user_id, start, end)
        stress_readings = self.repo.get_stress_range(user_id, start, end)
        load_points = self.repo.get_load_range(user_id, start, end)

        hrv_baseline = self.hrv_calc.compute_baseline(hrv_readings)
        hrv_signal = self.hrv_calc.get_current_signal(hrv_baseline)

        sleep_signal = self._compute_sleep_signal(sleep_nights)
        dose_response = self.dose_calc.compute(sleep_nights, hrv_readings)
        lifestyle = self.lifestyle_calc.compute([], [])

        sleep_block = self._build_sleep_block(sleep_nights)
        hrv_block = self._build_hrv_block(hrv_baseline, hrv_signal)
        rhr_block = self._build_rhr_block(rhr_readings)
        stress_block = self._build_stress_block(stress_readings)
        pmc_block = self._build_pmc_block(load_points)
        dose_response_out = self._build_dose_response(dose_response)
        lifestyle_out = self._build_lifestyle(lifestyle)

        return HealthSummaryOut(
            sleep=sleep_block,
            hrv=hrv_block,
            rhr=rhr_block,
            stress=stress_block,
            dose_response=dose_response_out,
            lifestyle=lifestyle_out,
        )

    def get_signals(self, user_id: int) -> HealthSignalsOut:
        end = date.today()
        start = end - timedelta(days=60)

        hrv_readings = self.repo.get_hrv_range(user_id, start, end)
        sleep_nights = self.repo.get_sleep_range(user_id, start, end)
        load_points = self.repo.get_load_range(user_id, start, end)

        hrv_baseline = self.hrv_calc.compute_baseline(hrv_readings)
        hrv_signal = self.hrv_calc.get_current_signal(hrv_baseline)

        sleep_signal = self._compute_sleep_signal(sleep_nights)

        fitness_signal = FitnessSignal(
            tsb=load_points[-1].tsb if load_points else None,
            acwr=load_points[-1].acwr if load_points else None,
            date=load_points[-1].date if load_points else end,
        )

        return HealthSignalsOut(
            hrv=hrv_signal,
            sleep=sleep_signal,
            fitness=fitness_signal,
        )

    def _compute_sleep_signal(self, nights: Sequence) -> Optional[SleepSignal]:
        if not nights:
            return None
        latest = max(nights, key=lambda n: n.date)
        prev_nights = [n for n in nights if n.date < latest.date]
        prev_nights.sort(key=lambda n: n.date, reverse=True)
        prev_7 = prev_nights[:7]

        delta = None
        if prev_7:
            avg_prev = sum(n.duration_s for n in prev_7) / len(prev_7)
            delta = latest.duration_s - avg_prev

        return SleepSignal(
            duration_s=latest.duration_s,
            delta_s=delta,
            date=latest.date,
        )

    def _build_sleep_block(self, nights: Sequence) -> Optional[SleepBlockOut]:
        if not nights:
            return None

        points = [
            SleepPointOut(
                date=n.date,
                duration_s=n.duration_s,
                score=n.score,
                rem_pct=n.rem_pct,
                deep_pct=n.deep_pct,
                light_pct=n.light_pct,
                awakenings=n.awakenings,
                bed_local=n.bed_time.strftime("%H:%M") if n.bed_time else None,
                wake_local=n.wake_time.strftime("%H:%M") if n.wake_time else None,
            )
            for n in nights
        ]

        floor_s = 7 * 3600
        below = [n for n in nights if n.duration_s < floor_s]
        below_floor = BelowFloorOut(
            nights=len(below),
            pct=len(below) / len(nights) * 100 if nights else 0,
        )

        weekday_calc = self.sleep_calc.weekday_pattern(nights)
        weekday_pattern = [
            WeekdayEntryOut(
                weekday=w["weekday"],
                avg_duration_s=w["avg_duration_s"],
                nights=w["nights"],
            )
            for w in weekday_calc
        ]

        bed_min, wake_min = self.sleep_calc.compute_regularity(nights)
        regularity = None
        if bed_min is not None and wake_min is not None:
            regularity = RegularityOut(avg_bed_min=bed_min, avg_wake_min=wake_min)

        return SleepBlockOut(
            days=len(nights),
            floor_s=floor_s,
            rem_band=[15.0, 25.0],
            below_floor=below_floor,
            regularity=regularity,
            weekday_pattern=weekday_pattern,
            points=points,
        )

    def _build_hrv_block(self, baseline: list, signal: Optional) -> Optional[HrvBlockOut]:
        if not baseline:
            return None

        points = [
            HrvPointOut(
                date=b.date,
                value=b.value,
                avg7=b.avg7,
                band_low=b.band_low,
                band_high=b.band_high,
            )
            for b in baseline
        ]

        current = None
        if signal:
            current = HrvCurrentOut(
                date=signal.date,
                value=signal.value,
                avg7=baseline[-1].avg7 or 0,
                band_low=baseline[-1].band_low,
                band_high=baseline[-1].band_high,
                status=signal.status,
            )

        return HrvBlockOut(points=points, current=current)

    def _build_rhr_block(self, readings: Sequence) -> Optional[RhrBlockOut]:
        if not readings:
            return None

        points = [RhrPointOut(date=r.date, value=r.value) for r in readings]
        baseline = int(sum(r.value for r in readings) / len(readings))

        return RhrBlockOut(points=points, baseline=baseline)

    def _build_stress_block(self, readings: Sequence) -> Optional[StressBlockOut]:
        if not readings:
            return None

        points = [StressPointOut(date=s.date, avg=s.avg or 0) for s in readings]
        avg_window = sum(s.avg or 0 for s in readings) / len(readings)

        return StressBlockOut(points=points, avg_window=avg_window)

    def _build_pmc_block(self, loads: Sequence) -> Optional[PmcBlockOut]:
        if not loads:
            return None

        points = [
            PmcPointOut(
                date=l.date,
                ctl=l.ctl,
                atl=l.atl,
                tsb=l.tsb,
                acwr=l.acwr,
            )
            for l in loads
        ]

        return PmcBlockOut(
            days=len(loads),
            points=points,
            current=PmcPointOut(
                date=loads[-1].date,
                ctl=loads[-1].ctl,
                atl=loads[-1].atl,
                tsb=loads[-1].tsb,
                acwr=loads[-1].acwr,
            ),
        )

    def _build_dose_response(self, dr: DoseResponse) -> DoseResponseOut:
        return DoseResponseOut(
            short=DoseBucketOut(
                nights=dr.short.nights,
                avg_hrv=dr.short.avg_hrv,
                avg_score=dr.short.avg_score,
            ),
            adequate=DoseBucketOut(
                nights=dr.adequate.nights,
                avg_hrv=dr.adequate.avg_hrv,
                avg_score=dr.adequate.avg_score,
            ),
            neutral_nights=dr.neutral_nights,
        )

    def _build_lifestyle(self, ls: Lifestyle) -> LifestyleOut:
        return LifestyleOut(
            strength=StrengthOut(
                streak_weeks=ls.strength.streak_weeks,
                weeks_hit=ls.strength.weeks_hit,
                weeks_total=ls.strength.weeks_total,
                current_week_sessions=ls.strength.current_week_sessions,
            ),
            yoga=YogaOut(
                sessions=ls.yoga.sessions,
                per_week_avg=ls.yoga.per_week_avg,
            ),
        )