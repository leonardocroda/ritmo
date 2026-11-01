"""Router da API de domínio Activities — /api/v1/activities"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import User
from app.domain.activities.dependencies import get_activity_service
from app.domain.activities.service import ActivityService
from app.domain.activities.schemas import ActivityListOut, ActivityDetailOut
from app.domain.activities.domain.value_objects import ActivityFilter

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


@router.get("")
def list_activities(
    activity_type: str = Query("running", pattern="^(running|all)$"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_session),
    service: ActivityService = Depends(get_activity_service),
) -> ActivityListOut:
    """Lista atividades paginada — corridas por padrão."""
    filter = ActivityFilter(activity_type=activity_type, limit=limit, offset=offset)
    return service.list(user.id, filter, limit, offset)


@router.get("/{activity_id}")
def get_activity(
    activity_id: int,
    user: User = Depends(require_session),
    service: ActivityService = Depends(get_activity_service),
) -> ActivityDetailOut:
    """Detalhe completo de uma atividade."""
    detail = service.get_detail(activity_id, user.id)
    if detail is None:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    return detail