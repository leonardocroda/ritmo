"""Entidades do domínio Evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class EvaluationJob:
    """Job de avaliação."""

    id: int
    activity_id: int
    user_id: int
    intent_type: str
    intent_text: Optional[str]
    status: str  # "pending", "done", "error"
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Verdict:
    """Veredito da avaliação."""

    verdict: str  # "on_target", "too_hard", "too_easy", "context_explained", "fatigue_signal"
    headline: str
    execution_vs_intent: dict
    what_worked: list[str]
    fix_next_time: list[str]
    relevant_context: list[str]
    confidence: str  # "alta", "média", "baixa"


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    """Registro completo de avaliação."""

    id: int
    activity_id: int
    user_id: int
    intent_type: str
    intent_text: Optional[str]
    verdict: Verdict
    model: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    status: str
    error: Optional[str]
    created_at: datetime