"""Router da API de domínio Performance — /api/v1/performance"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.models import User
from app.domain.performance.dependencies import get_performance_service
from app.domain.performance.service import PerformanceService
from app.domain.performance.schemas import PerformanceOut

router = APIRouter(prefix="/api/v1/performance", tags=["performance"])


@router.get("")
def get_performance(
    user: User = Depends(require_session),
    service: PerformanceService = Depends(get_performance_service),
) -> PerformanceOut:
    """Painel Performance completo — VDOT, predições, VO2max, decay."""
    try:
        return service.get_performance(user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))