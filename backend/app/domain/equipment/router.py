"""Router da API de domínio Equipment — /api/v1/equipment"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import require_session
from app.db.models import User
from app.domain.equipment.dependencies import get_shoes_service
from app.domain.equipment.service import ShoesService
from app.domain.equipment.schemas import (
    ShoesListOut, ShoeOut, ShoeSummaryOut, ShoeCreateIn, ShoeUpdateIn, DegradationOut
)

router = APIRouter(prefix="/api/v1/equipment", tags=["equipment"])


@router.get("")
def list_shoes(
    status: str | None = Query(None, pattern="^(ativo|aposentado)$"),
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
) -> ShoesListOut:
    return service.list(user.id, status)


@router.get("/{shoe_id}")
def get_shoe(
    shoe_id: int,
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
) -> ShoeOut:
    shoe = service.get(shoe_id, user.id)
    if not shoe:
        raise HTTPException(404, "tênis não encontrado")
    return shoe


@router.post("", status_code=201)
def create_shoe(
    data: ShoeCreateIn,
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
) -> ShoeOut:
    return service.create(user.id, data)


@router.patch("/{shoe_id}")
def update_shoe(
    shoe_id: int,
    data: ShoeUpdateIn,
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
) -> ShoeOut:
    shoe = service.update(shoe_id, user.id, data)
    if not shoe:
        raise HTTPException(404, "tênis não encontrado")
    return shoe


@router.delete("/{shoe_id}", status_code=204)
def delete_shoe(
    shoe_id: int,
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
):
    if not service.delete(shoe_id, user.id):
        raise HTTPException(404, "tênis não encontrado")


@router.get("/{shoe_id}/degradation")
def get_degradation(
    shoe_id: int,
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
) -> DegradationOut:
    result = service.get_degradation(shoe_id, user.id)
    if not result:
        raise HTTPException(404, "tênis não encontrado")
    return result