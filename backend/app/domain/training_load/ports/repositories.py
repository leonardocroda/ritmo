"""Ports para repositórios do domínio Training-Load."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from app.domain.activities.domain.entities import Activity


@runtime_checkable
class TrainingLoadRepository(Protocol):
    def get_activities(self, user_id: int, start: date, end: date) -> Sequence[Activity]: ...
    def get_latest_load(self, user_id: int) -> PMCCurve | None: ...