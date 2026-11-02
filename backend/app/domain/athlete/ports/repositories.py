"""Ports para repositórios do domínio Athlete."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.athlete.domain.entities import Athlete


@runtime_checkable
class AthleteRepository(Protocol):
    def get_by_user_id(self, user_id: int) -> Athlete | None: ...
    def save(self, athlete: Athlete) -> Athlete: ...
    def update(self, athlete: Athlete) -> Athlete: ...