"""Router da API de domínio Heart Rate Zones — /api/v1/heart-rate-zones"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.models import User
from app.domain.heart_rate_zones.dependencies import get_hr_zones_service
from app.domain.heart_rate_zones.service import HeartRateZonesService
from app.domain.heart_rate_zones.schemas import HRZonesOut, HRZonesUpdate, HRZonesHistoryOut

router = APIRouter(prefix="/api/v1/heart-rate-zones", tags=["heart-rate-zones"])


@router.get("")
def get_hr_zones(
    user: User = Depends(require_session),
    service: HeartRateZonesService = Depends(get_hr_zones_service),
) -> HRZonesOut:
    return service.get_hr_zones(user.id)


@router.get("/history")
def get_hr_zones_history(
    user: User = Depends(require_session),
    service: HeartRateZonesService = Depends(get_hr_zones_service),
) -> HRZonesHistoryOut:
    """HRZ-15: mudanças de métricas e configs, mais recente primeiro —
    DESC por (valid_from, id), com data e fonte."""
    return service.get_hr_zones_history(user.id)


@router.put("")
def update_hr_zones(
    data: HRZonesUpdate,
    user: User = Depends(require_session),
    service: HeartRateZonesService = Depends(get_hr_zones_service),
) -> HRZonesOut:
    return service.update_hr_zones(user.id, data)