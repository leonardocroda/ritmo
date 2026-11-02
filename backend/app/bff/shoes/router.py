"""Router do BFF Shoes — /api/v1/bff/shoes.

Contrato 1:1 com a tela Equipamentos (mesmo payload do /api/shoes legado,
incl. current_km/vida útil e o payload de degradação do tenis_degradation).
Códigos de erro do legado: 422 validação (ValueError), 404 inexistente/
alheio.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.bff.shoes.dependencies import get_shoes_bff_service
from app.bff.shoes.service import ShoesBFFService
from app.db.models import User
from app.shoes.router import ShoeCreateIn, ShoeOut, ShoesListOut, ShoeUpdateIn

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
    try:
        return service.create_shoe(user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    try:
        shoe = service.update_shoe(shoe_id, user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not shoe:
        raise HTTPException(404, "tênis não encontrado")
    return shoe


@router.get("/{shoe_id}/degradation")
def get_degradation(
    shoe_id: int,
    user: User = Depends(require_session),
    service: ShoesBFFService = Depends(get_shoes_bff_service),
) -> dict:
    """Alerta de degradação de um tênis."""
    return service.get_degradation(shoe_id, user.id)
