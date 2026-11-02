"""Router da API de domínio VDOT — /api/v1/vdot"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.models import User
from app.domain.vdot.dependencies import get_vdot_service
from app.domain.vdot.service import VDOTService
from app.domain.vdot.schemas import VDOTOut

router = APIRouter(prefix="/api/v1/vdot", tags=["vdot"])


@router.get("")
def get_vdot(
    user: User = Depends(require_session),
    service: VDOTService = Depends(get_vdot_service),
) -> VDOTOut:
    try:
        return service.get_vdot(user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))