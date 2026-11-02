"""Router do BFF Health — /api/v1/bff/health/summary"""

from fastapi import APIRouter, Depends, Query

from app.auth.deps import require_session
from app.bff.health.dependencies import get_health_bff_service
from app.bff.health.schemas import HealthSummaryOut
from app.bff.health.service import HealthBFFService
from app.core.tz import app_tz
from app.db.models import User

router = APIRouter(prefix="/api/v1/bff/health", tags=["bff:health"])


@router.get("/summary")
def get_health_summary(
    user: User = Depends(require_session),
    days: int = Query(default=60, ge=7, le=365),
    service: HealthBFFService = Depends(get_health_bff_service),
) -> HealthSummaryOut:
    """O painel inteiro em 1 payload (design §Contrato).

    `days` fora de [7, 365] -> 422 antes de qualquer query.
    Toda leitura filtra pelo usuário da sessão (user-scope)."""
    return HealthSummaryOut(**service.get_summary(user.id, days, app_tz()))