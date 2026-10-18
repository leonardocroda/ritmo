"""Router do domínio evaluation — POST cria o job, GET expõe o status.

Emenda job (18/10): o POST valida o que é rápido (500 zonas na
dependency, 422 do pydantic, 503 key ausente, 404/422 do service) e
cria a avaliação ``pending`` — a NIM roda no worker, não no request.
Falhas da NIM não são HTTP: viram ``status=error`` com o motivo na
própria linha (a tentativa nunca se perde — EVAL-23).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.activities.router import get_zone_config
from app.core.config import Settings, get_settings
from app.db.engine import get_db
from app.evaluation import service
from app.evaluation.schemas import EvaluateIn, EvaluationOut
from app.vdot.zones import ZoneConfig

router = APIRouter(prefix="/api/activities")


@router.post("/{activity_id}/evaluate", status_code=201)
def evaluate_activity(
    activity_id: int,
    request: EvaluateIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    zone_config: ZoneConfig = Depends(get_zone_config),
) -> EvaluationOut:
    """Cria a avaliação pending (EVAL-21) e despacha o worker (EVAL-22/23).

    O request nunca espera a NIM: responde 201 com o registro pending;
    a UI polla o GET de status até done/error.
    """
    settings = get_settings()
    if not settings.nvidia_api_key:
        raise HTTPException(
            status_code=503,
            detail="IA não configurada: defina NVIDIA_API_KEY no ambiente",
        )
    try:
        result = service.create_evaluation(
            db,
            activity_id,
            request.intent_type,
            request.intent_text,
            zone_config,
            settings,
        )
    except service.ActivityNotRunning as exc:
        raise HTTPException(
            status_code=422,
            detail="avaliação disponível apenas para corridas",
        ) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    background_tasks.add_task(service.run_evaluation, result["id"])
    return result


@router.get("/{activity_id}/evaluate/{evaluation_id}")
def get_evaluation_status(
    activity_id: int,
    evaluation_id: int,
    db: Session = Depends(get_db),
) -> EvaluationOut:
    """Status de uma avaliação para o polling da UI (EVAL-25)."""
    result = service.get_evaluation(db, activity_id, evaluation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="avaliação não encontrada")
    return result
