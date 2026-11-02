"""Ports para repositórios do domínio AI Evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.domain.ai_evaluation.domain.entities import EvaluationRecord


@runtime_checkable
class EvaluationRepository(Protocol):
    def get_by_id(self, eval_id: int, user_id: int) -> EvaluationRecord | None: ...
    def list_by_activity(self, activity_id: int, user_id: int) -> Sequence[EvaluationRecord]: ...
    def create(self, record: EvaluationRecord) -> EvaluationRecord: ...
    def update_status(self, eval_id: int, status: str, error: str | None = None) -> EvaluationRecord: ...