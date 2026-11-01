"""Router da API de domínio Health — /api/v1/health"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.deps import require_session
from app.db.models import User
from app.domain.health.dependencies import get_health_service
from app.domain.health.service import HealthService
from app.domain.health.schemas import HealthSummaryOut, HealthSignalsOut

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/summary")
def get_health_summary(
    days: int = Query(60, ge=7, le=365),
    user: User = Depends(require_session),
    service: HealthService = Depends(get_health_service),
) -> HealthSummaryOut:
    """Painel Saúde completo — janela configurável (default 60d)."""
    return service.get_summary(user.id, days)


@router.get("/signals")
def get_health_signals(
    user: User = Depends(require_session),
    service: HealthService = Depends(get_health_service),
) -> HealthSignalsOut:
    """Sinais para painel Home — HRV, Sono, Forma."""
    return service.get_signals(user.id)