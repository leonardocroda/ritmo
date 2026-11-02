"""Router da API de domínio Evaluation — /api/v1/activities/{id}/evaluate"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.auth.deps import require_session
from app.db.models import User
from app.domain.activity.dependencies import get_activity_service, get_zone_config
from app.domain.activity.service import ActivityService
from app.domain.activity.domain.value_objects import ZoneConfigVO
from app.domain.ai_evaluation.dependencies import get_evaluation_service
from app.domain.ai_evaluation.service import EvaluationService
from app.domain.ai_evaluation.schemas import EvaluationOut, EvaluateIn

router = APIRouter(prefix="/api/v1/activities", tags=["evaluation"])


@router.post("/{activity_id}/evaluate", status_code=201)
async def evaluate_activity(
    activity_id: int,
    data: EvaluateIn,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_session),
    activity_service: ActivityService = Depends(get_activity_service),
    zone_config: ZoneConfigVO = Depends(get_zone_config),
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationOut:
    # Busca atividade
    activity = activity_service.repo.get_by_id(activity_id, user.id)
    if not activity:
        raise HTTPException(404, "atividade não encontrada")

    # Cria avaliação
    record = await eval_service.create_evaluation(
        activity, user.id, data.intent_type, data.intent_text, zone_config
    )

    # Dispara worker
    background_tasks.add_task(eval_service.run_evaluation, record.id)

    return eval_service.to_out(record)


@router.get("/{activity_id}/evaluate/{evaluation_id}")
async def get_evaluation_status(
    activity_id: int,
    evaluation_id: int,
    user: User = Depends(require_session),
    eval_service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationOut:
    record = eval_service.repo.get_by_id(evaluation_id, user.id)
    if not record or record.activity_id != activity_id:
        raise HTTPException(404, "avaliação não encontrada")
    return eval_service.to_out(record)