"""Application Service do domínio Performance."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.activities.domain.entities import Activity
from app.domain.performance.domain.entities import (
    VDOTProfile, TimelinePoint, Prediction
)
from app.domain.performance.domain.services import (
    VDOTCalculator, PredictionService, DecayCalculator, VO2maxService
)
from app.domain.performance.ports.repositories import PerformanceRepository
from app.domain.performance.schemas import (
    PerformanceOut, VDOTBlockOut, TimelinePointOut, VDOTCurrentOut,
    VDOTDemonstratedOut, PredictionRowOut, VO2maxBlockOut, VO2maxPointOut,
    DecayRowOut
)


@dataclass
class PerformanceService:
    repo: PerformanceRepository
    vdot_calc: VDOTCalculator
    pred_service: PredictionService
    decay_calc: DecayCalculator
    vo2max_service: VO2maxService

    def get_performance(self, user_id: int) -> PerformanceOut:
        # VDOT
        vdot_profile = self.repo.get_vdot_profile(user_id)
        if not vdot_profile:
            raise ValueError("VDOT não configurado")

        timeline = self.repo.get_timeline(user_id)
        demonstrated = None
        if timeline:
            best = max(timeline, key=lambda t: t.vdot)
            demonstrated = VDOTDemonstratedOut(
                vdot=best.vdot,
                source=best.source,
                date=best.date,
            )

        gap_pct = None
        if demonstrated:
            gap_pct = round((demonstrated.vdot - vdot_profile.current_vdot) / vdot_profile.current_vdot * 100, 1)

        vdot_block = VDOTBlockOut(
            current=VDOTCurrentOut(
                vdot=vdot_profile.current_vdot,
                source=vdot_profile.source,
                test_date=vdot_profile.test_date,
            ),
            demonstrated=demonstrated,
            gap_pct=gap_pct,
            timeline=[
                TimelinePointOut(
                    date=t.date,
                    vdot=t.vdot,
                    source=t.source,
                    label=t.label,
                    distance_m=t.distance_m,
                    time_s=t.time_s,
                )
                for t in timeline
            ],
        )

        # Predições
        predictions_raw = self.repo.get_predictions(user_id)
        pred_service = self.pred_service.predict_all(vdot_profile.current_vdot)

        predictions = {}
        for event_key, row in pred_service.items():
            garmin = predictions_raw.get(event_key, {}).get("garmin_s")
            predictions[event_key] = PredictionRowOut(
                garmin_s=garmin,
                vdot_s=row["vdot_s"],
                average_s=row["vdot_s"],  # placeholder
            )

        # VO2max
        vo2max_timeline = self.repo.get_vo2max_timeline(user_id)
        vo2max_block = VO2maxBlockOut(
            points=[
                VO2maxPointOut(date=p.date, value=p.value)
                for p in vo2max_timeline
            ]
        ) if vo2max_timeline else None

        # Decay
        activities = self.repo.get_activities_for_performance(user_id)
        decay_raw = self.decay_calc.compute_decay(activities, vdot_profile.current_vdot)
        decay = [
            DecayRowOut(
                event=d["event"],
                real_pace_s=d["real_pace_s"],
                ideal_pace_s=d["ideal_pace_s"],
                delta_pct=d["delta_pct"],
            )
            for d in decay_raw
        ]

        return PerformanceOut(
            vdot=vdot_block,
            predictions=predictions,
            vo2max=vo2max_block,
            decay=decay,
        )