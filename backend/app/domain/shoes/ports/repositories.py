"""Ports para repositórios do domínio Shoes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.domain.shoes.domain.entities import Shoe, ShoeRun, DegradationSignal


@runtime_checkable
class ShoeRepository(Protocol):
    """Port para persistência de tênis."""

    def get_by_id(self, shoe_id: int, user_id: int) -> Shoe | None: ...
    def list(self, user_id: int, status: str | None = None) -> Sequence[Shoe]: ...
    def save(self, shoe: Shoe) -> Shoe: ...
    def delete(self, shoe_id: int, user_id: int) -> bool: ...

    def get_runs(self, shoe_id: int) -> Sequence[ShoeRun]: ...
    def get_degradation(self, shoe_id: int) -> tuple[DegradationSignal, ...] | None: ...