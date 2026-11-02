"""Router da API de domínio Health Metrics — /api/v1/health-metrics"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.deps import require_session
from app.db.models import User
from app.domain.health_metrics.dependencies import get_health_metrics_service
from app.domain.health_metrics.service import HealthMetricsService
from app.domain.health_metrics.schemas import HealthSummaryOut, HealthSignalsOut

router = APIRouter(prefix="/api/v1/health-metrics", tags=["health-metrics"])


@router.get("/summary")
def get_health_summary(
    days: int = 60,
    user: User = Depends(require_session),
    service: HealthMetricsService = Depends(get_health_metrics_service),
) -> HealthSummaryOut:
    """Painel Saúde completo — janela configurável (default 60d)."""
    return service.get_summary(user.id, days)


@router.get("/signals")
def get_health_signals(
    user: User = Depends(require_session),
    service: HealthMetricsService = Depends(get_health_metrics_service),
) -> HealthSignalsOut:
    """Sinais para painel Home — HRV, Sono, Forma."""
    return service.get_signals(user.id)