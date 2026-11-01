"""Ports para repositórios do domínio Performance."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.activities.domain.entities import Activity
from app.domain.performance.domain.entities import VDOTProfile, TimelinePoint, Prediction, VO2maxPoint


@runtime_checkable
class PerformanceRepository(Protocol):
    """Port para persistência de performance."""

    def get_vdot_profile(self, user_id: int) -> VDOTProfile | None: ...
    def get_timeline(self, user_id: int) -> Sequence[TimelinePoint]: ...
    def get_predictions(self, user_id: int) -> dict[str, Prediction]: ...
    def get_vo2max_timeline(self, user_id: int) -> Sequence[VO2maxPoint]: ...
    def get_activities_for_performance(self, user_id: int) -> Sequence[Activity]: ...
    def save_vdot_profile(self, profile: VDOTProfile) -> VDOTProfile: ...