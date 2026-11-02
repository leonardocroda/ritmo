"""Router da API de domínio Equipment — /api/v1/equipment.

FASE DE TRANSIÇÃO: o service delega ao legado (ver service.py). O router
mantém os códigos de erro do legado: 422 para validação (ValueError),
404 para inexistente/alheio.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import User
from app.domain.equipment.dependencies import get_shoes_service
from app.domain.equipment.service import ShoesService
from app.shoes.router import ShoeCreateIn, ShoeOut, ShoesListOut, ShoeUpdateIn

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
    try:
        return service.create(user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{shoe_id}")
def update_shoe(
    shoe_id: int,
    data: ShoeUpdateIn,
    user: User = Depends(require_session),
    service: ShoesService = Depends(get_shoes_service),
) -> ShoeOut:
    try:
        shoe = service.update(shoe_id, user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
) -> dict:
    return service.get_degradation(shoe_id, user.id)
