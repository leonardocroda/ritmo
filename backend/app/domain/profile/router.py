"""Router da API de domínio Profile — /api/v1/profile"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.models import User
from app.domain.profile.dependencies import get_profile_service
from app.domain.profile.service import ProfileService
from app.domain.profile.schemas import HRZonesOut, HRZonesUpdate, PaceZonesOut

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("/hr-zones")
def get_hr_zones(
    user: User = Depends(require_session),
    service: ProfileService = Depends(get_profile_service),
) -> HRZonesOut:
    return service.get_hr_zones(user.id)


@router.put("/hr-zones")
def update_hr_zones(
    data: HRZonesUpdate,
    user: User = Depends(require_session),
    service: ProfileService = Depends(get_profile_service),
) -> HRZonesOut:
    return service.update_hr_zones(user.id, data)


@router.get("/pace-zones")
def get_pace_zones(
    user: User = Depends(require_session),
    service: ProfileService = Depends(get_profile_service),
) -> PaceZonesOut:
    try:
        return service.get_pace_zones(user.id)
    except ValueError as e:
        raise HTTPException(404, str(e))