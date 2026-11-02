"""Router do BFF Activities — /api/v1/bff/activities.

Contrato 1:1 com a tela Treinos (mesmo payload do /api/activities legado —
a diferença é só a URL). `load_zone_config_from_db` sem config -> 500
"zonas VDOT não configuradas", igual ao legado.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.activities.router import ActivityDetailOut, ActivityListOut
from app.auth.deps import require_session
from app.bff.activities.dependencies import get_activities_bff_service
from app.bff.activities.service import ActivitiesBFFService
from app.db.engine import get_db
from app.db.models import User


router = APIRouter(prefix="/api/v1/bff/activities", tags=["bff:activities"])


@router.get("")
def list_activities(
    activity_type: str = Query("running", pattern="^(running|all)$"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_session),
    service: ActivitiesBFFService = Depends(get_activities_bff_service),
) -> ActivityListOut:
    """Lista paginada de atividades (TRN-04/05/06)."""
    return service.list_activities(user.id, activity_type, limit, offset)


@router.get("/{activity_id}")
def get_activity(
    activity_id: int,
    user: User = Depends(require_session),
    service: ActivitiesBFFService = Depends(get_activities_bff_service),
) -> ActivityDetailOut:
    """Detalhe do treino (TRN-13). 404 = id inexistente."""
    detail = service.get_detail(activity_id, user.id)
    if detail is None:
        from fastapi import HTTPException

        raise HTTPException(404, "atividade não encontrada")
    return detail
