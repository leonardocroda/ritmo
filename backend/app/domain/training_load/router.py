"""Router da API de domínio Training Load — /api/v1/training-load"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.models import User
from app.domain.training_load.dependencies import get_training_load_service
from app.domain.training_load.service import TrainingLoadService
from app.domain.training_load.schemas import TrainingLoadOut

router = APIRouter(prefix="/api/v1/training-load", tags=["training-load"])


@router.get("")
def get_training_load(
    days: int = 60,
    user: User = Depends(require_session),
    service: TrainingLoadService = Depends(get_training_load_service),
) -> TrainingLoadOut:
    return service.get_training_load(user.id, days)