"""Ports para repositórios do domínio Training-Load."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.activity.domain.entities import Activity
from app.domain.vdot.domain.entities import VDOTProfile, TimelinePoint, Prediction, VO2maxPoint


@runtime_checkable
class TrainingLoadRepository(Protocol):
    def get_activities(self, user_id: int, start: date, end: date) -> Sequence[Activity]: ...
    def get_latest_load(self, user_id: int) -> PMCCurve | None: ...