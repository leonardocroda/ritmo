"""Router do domínio evaluation — POST /api/activities/{id}/evaluate.

Mapa de erros (EVAL-09..15, design): zonas 500 (dependency compartilhada
do activities); 503 com `NVIDIA_API_KEY` vazia — checada antes de qualquer
chamada à NIM (config de IA ausente, nada gravado); 404 inexistente;
422 não-corrida ou intenção inválida (pydantic automático); 502 NIM/JSON
inválido; 504 timeout. Mensagens em PT-BR.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.activities.router import get_zone_config
from app.core.config import Settings, get_settings
from app.db.engine import get_db
from app.evaluation import service
from app.evaluation.nim import NimError, NimTimeout
from app.evaluation.schemas import EvaluateIn, EvaluationOut
from app.vdot.zones import ZoneConfig

router = APIRouter(prefix="/api/activities")


@router.post("/{activity_id}/evaluate")
def evaluate_activity(
    activity_id: int,
    request: EvaluateIn,
    db: Session = Depends(get_db),
    zone_config: ZoneConfig = Depends(get_zone_config),
) -> EvaluationOut:
    """Avalia a corrida sob a intenção declarada (EVAL-02/03/04)."""
    settings = get_settings()
    if not settings.nvidia_api_key:
        raise HTTPException(
            status_code=503,
            detail="IA não configurada: defina NVIDIA_API_KEY no ambiente",
        )
    try:
        result = service.evaluate(
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
    except NimTimeout as exc:
        raise HTTPException(
            status_code=504,
            detail="A IA demorou demais para responder — tente novamente",
        ) from exc
    except NimError as exc:
        raise HTTPException(status_code=502, detail=f"Falha na IA: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail=f"Resposta da IA fora do contrato: {exc}"
        ) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    return result
