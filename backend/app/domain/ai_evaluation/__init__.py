"""AI Evaluation domain package."""

from app.domain.ai_evaluation.domain.entities import EvaluationJob, EvaluationRecord, Verdict
from app.domain.ai_evaluation.ports.repositories import EvaluationRepository
from app.domain.ai_evaluation.ports.ai_client import AIClient
from app.domain.ai_evaluation.schemas import EvaluationOut, EvaluateIn, VerdictOut
from app.domain.ai_evaluation.service import EvaluationService
from app.domain.ai_evaluation.dependencies import get_evaluation_repo, get_ai_client, get_evaluation_service
from app.domain.ai_evaluation.router import router

__all__ = [
    "EvaluationJob", "EvaluationRecord", "Verdict",
    "EvaluationRepository", "AIClient",
    "EvaluationOut", "EvaluateIn", "VerdictOut",
    "EvaluationService",
    "get_evaluation_repo", "get_ai_client", "get_evaluation_service",
    "router",
]