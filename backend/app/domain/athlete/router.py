"""Router da API de domínio Athlete — /api/v1/athlete"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.models import User
from app.domain.athlete.dependencies import get_athlete_service
from app.domain.athlete.service import AthleteService
from app.domain.athlete.schemas import AthleteOut, AthleteUpdate

router = APIRouter(prefix="/api/v1/athlete", tags=["athlete"])


@router.get("")
def get_athlete(
    user: User = Depends(require_session),
    service: AthleteService = Depends(get_athlete_service),
) -> AthleteOut:
    athlete = service.get(user.id)
    if not athlete:
        raise HTTPException(404, "atleta não encontrado")
    return AthleteOut.model_validate(athlete)


@router.patch("")
def update_athlete(
    data: AthleteUpdate,
    user: User = Depends(require_session),
    service: AthleteService = Depends(get_athlete_service),
) -> AthleteOut:
    athlete = service.get(user.id)
    if not athlete:
        raise HTTPException(404, "atleta não encontrado")
    
    # Atualiza campos
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(athlete, field, value)
    
    updated = service.update(athlete)
    return AthleteOut.model_validate(updated)