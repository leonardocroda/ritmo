"""FastAPI Dependencies para Evaluation."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.evaluation.ports.repositories import EvaluationRepository
from app.domain.evaluation.ports.ai_client import AIClient
from app.domain.evaluation.service import EvaluationService


# Placeholder adapters - implementar depois
class SQLAlchemyEvaluationRepository:
    def __init__(self, db: Session): pass
    def get_by_id(self, eval_id: int, user_id: int): return None
    def list_by_activity(self, activity_id: int, user_id: int): return []
    def create(self, record): return record
    def update_status(self, eval_id: int, status: str, error: str = None): return None


class NIMClient:
    def __init__(self): pass
    async def evaluate(self, job, zone_config): pass
    def estimate_tokens(self, prompt: str): return 0


def get_evaluation_repo(db: Session = Depends(get_db)) -> EvaluationRepository:
    return SQLAlchemyEvaluationRepository(db)


def get_ai_client() -> AIClient:
    return NIMClient()


def get_evaluation_service(
    repo: EvaluationRepository = Depends(get_evaluation_repo),
    ai_client: AIClient = Depends(get_ai_client),
) -> EvaluationService:
    return EvaluationService(repo, ai_client)