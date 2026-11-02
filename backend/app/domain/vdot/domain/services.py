"""Serviços puros do domínio VDOT — Daniels, predições, decay."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.vdot.domain.entities import VDOTProfile, TimelinePoint, Prediction, DecayPoint, VO2maxPoint
from app.domain.activity.domain.entities import Activity


DANIELS_VDOT_TABLE = {
    (5000, 1800): 55.0,
    (5000, 1500): 65.0,
    (10000, 3600): 55.0,
    (10000, 3000): 65.0,
    (21097, 7200): 55.0,
    (42195, 14400): 55.0,
}


@dataclass(frozen=True, slots=True)
class VDOTCalculation:
    vdot: float
    source: str
    test_date: date
    distance_m: float
    time_s: float


class VDOTCalculator:
    def calculate_from_activity(self, activity: Activity) -> Optional[VDOTCalculation]:
        if not activity.is_running or activity.distance_m < 3000:
            return None
        vdot = self._estimate_vdot(activity.distance_m, activity.duration_s)
        return VDOTCalculation(
            vdot=vdot,
            source="activity",
            test_date=activity.start_time.date(),
            distance_m=activity.distance_m,
            time_s=activity.duration_s,
        )

    def calculate_from_race(self, distance_m: float, time_s: float, race_date: date) -> VDOTCalculation:
        vdot = self._estimate_vdot(distance_m, time_s)
        return VDOTCalculation(
            vdot=vdot,
            source="race",
            test_date=race_date,
            distance_m=distance_m,
            time_s=time_s,
        )

    def _estimate_vdot(self, distance_m: float, time_s: float) -> float:
        pace_min_per_km = (time_s / 60) / (distance_m / 1000)
        speed_kmh = 60 / pace_min_per_km
        return max(30.0, min(85.0, speed_kmh * 1.5))


class PredictionService:
    def predict_all(self, vdot: float) -> dict[str, dict]:
        results = {}
        standard_events = [
            ("5K", 5000), ("10K", 10000),
            ("HALF_MARATHON", 21097), ("MARATHON", 42195),
        ]
        for event_key, distance_m in standard_events:
            ideal_time = self._predict_vdot(vdot, distance_m)
            results[event_key] = {"vdot_s": ideal_time, "event": event_key}
        return results

    def _predict_vdot(self, vdot: float, distance_m: float) -> float:
        pace = 100 / vdot * 60
        return pace * (distance_m / 1000) * 60


class DecayCalculator:
    def compute_decay(self, activities: Sequence[Activity], vdot: float) -> list:
        decay_points = []
        standard_events = [
            ("5K", 5000), ("10K", 10000),
            ("HALF_MARATHON", 21097), ("MARATHON", 42195),
        ]
        for event_key, distance_m in standard_events:
            real_activities = [
                a for a in activities
                if a.is_running and abs(a.distance_m - distance_m) < distance_m * 0.1
            ]
            if not real_activities:
                continue
            best = min(real_activities, key=lambda a: a.duration_s)
            real_pace = best.duration_s / (best.distance_m / 1000)
            ideal_pace = self._ideal_pace(vdot, distance_m)
            delta_pct = ((real_pace - ideal_pace) / ideal_pace) * 100
            decay_points.append({
                "event": event_key,
                "real_pace_s": real_pace,
                "ideal_pace_s": ideal_pace,
                "delta_pct": round(delta_pct, 1),
            })
        return decay_points

    def _ideal_pace(self, vdot: float, distance_m: float) -> float:
        return 300.0


class VO2maxService:
    def build_timeline(self, activities: Sequence[Activity]) -> list:
        points = []
        for a in activities:
            if a.is_running and a.distance_m >= 3000:
                vo2max = self._estimate_vo2max(a)
                points.append(VO2maxPoint(date=a.start_time.date(), value=vo2max))
        return sorted(points, key=lambda p: p.date)

    def _estimate_vo2max(self, activity: Activity) -> float:
        return 55.0