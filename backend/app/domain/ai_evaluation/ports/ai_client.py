"""Port para cliente de IA (NIM)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.ai_evaluation.domain.entities import EvaluationJob, Verdict
from app.domain.activity.domain.value_objects import ZoneConfigVO


@runtime_checkable
class AIClient(Protocol):
    async def evaluate(self, job: EvaluationJob, zone_config: ZoneConfigVO) -> Verdict: ...
    def estimate_tokens(self, prompt: str) -> int: ...