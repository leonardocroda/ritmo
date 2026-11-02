"""Router do BFF Shoes — /api/v1/bff/shoes"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.bff.shoes.dependencies import get_shoes_bff_service
from app.bff.shoes.schemas import (
    DegradationOut,
    ShoeCreateIn,
    ShoeOut,
    ShoeSummaryOut,
    ShoeUpdateIn,
    ShoesListOut,
)
from app.db.models import User

router = APIRouter(prefix="/api/v1/bff/shoes", tags=["bff:shoes"])


@router.get("")
def list_shoes(
    user: User = Depends(require_session),
    service: ShoesBFFService = Depends(get_shoes_bff_service),
) -> ShoesListOut:
    """Lista os tênis do usuário."""
    return service.list_shoes(user.id)


@router.post("")
def create_shoe(
    data: ShoeCreateIn,
    user: User = Depends(require_session),
    service: ShoesBFFService = Depends(get_shoes_bff_service),
) -> ShoeOut:
    """Cria um tênis."""
    return service.create_shoe(user.id, data)


@router.get("/{shoe_id}")
def get_shoe(
    shoe_id: int,
    user: User = Depends(require_session),
    service: ShoesBFFService = Depends(get_shoes_bff_service),
) -> ShoeOut:
    """Detalhe de um tênis."""
    shoe = service.get_shoe(shoe_id, user.id)
    if not shoe:
        raise HTTPException(404, "tênis não encontrado")
    return shoe


@router.patch("/{shoe_id}")
def update_shoe(
    shoe_id: int,
    data: ShoeUpdateIn,
    user: User = Depends(require_session),
    service: ShoesBFFService = Depends(get_shoes_bff_service),
) -> ShoeOut:
    """Edita um tênis."""
    shoe = service.update_shoe(shoe_id, user.id, data)
    if not shoe:
        raise HTTPException(404, "tênis não encontrado")
    return shoe


@router.get("/{shoe_id}/degradation")
def get_degradation(
    shoe_id: int,
    user: User = Depends(require_session),
    service: ShoesBFFService = Depends(get_shoes_bff_service),
) -> DegradationOut:
    """Alerta de degradação de um tênis."""
    degradation = service.get_degradation(shoe_id, user.id)
    if not degradation:
        raise HTTPException(404, "tênis não encontrado")
    return degradation