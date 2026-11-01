"""Ports (Protocol interfaces) para repositórios do domínio Activities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.domain.activities.domain.entities import Activity, Split
from app.domain.activities.domain.value_objects import ActivityFilter


class ActivityRepository(Protocol):
    """Port para persistência de atividades."""

    def get_by_id(self, id: int, user_id: int) -> Activity | None: ...
    def list(self, user_id: int, filter: ActivityFilter) -> Sequence[Activity]: ...
    def count(self, user_id: int, filter: ActivityFilter) -> int: ...
    def save(self, activity: Activity) -> Activity: ...
    def delete(self, id: int, user_id: int) -> bool: ...


class SplitRepository(Protocol):
    """Port para persistência de voltas/splits."""

    def get_by_activity(self, activity_id: int) -> Sequence[Split]: ...
    def save_batch(self, splits: Sequence[Split]) -> None: ...