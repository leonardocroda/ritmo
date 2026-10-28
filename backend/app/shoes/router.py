"""Router do domínio shoes — CRUD user-scoped com km derivada.

Padrão do profile/activities: APIRouter, schemas pydantic inline,
require_session + get_db, um commit por endpoint, HTTPException 404/422.
Resposta em envelope {items: [...], attribution_30d_pct: null} — o
campo attribution_30d_pct será calculado na T8.
"""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import User
from app.shoes import service

router = APIRouter(prefix="/api/shoes")


class ShoeCreateIn(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    acquired_date: date | None = None
    initial_km: float | None = 0.0
    max_km: float | None = None
    status: Literal["ativo", "aposentado"] | None = "ativo"
    strava_gear_id: str | None = None


class ShoeUpdateIn(BaseModel):
    name: str | None = None
    brand: str | None = None
    model: str | None = None
    acquired_date: date | None = None
    initial_km: float | None = None
    max_km: float | None = None
    status: Literal["ativo", "aposentado"] | None = None
    strava_gear_id: str | None = None


class ShoeOut(BaseModel):
    id: int
    name: str
    brand: str | None
    model: str | None
    acquired_date: date | None
    initial_km: float
    max_km: float | None
    status: str
    strava_gear_id: str | None
    created_at: datetime
    current_km: float
    run_count: int
    last_use: datetime | None
    life_pct: float | None


class ShoesListOut(BaseModel):
    items: list[ShoeOut]
    attribution_30d_pct: float | None = None


@router.get("")
def list_shoes(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> ShoesListOut:
    """GET /api/shoes — lista tênis do usuário com km derivada.

    current_km = initial_km + Σ distance_m das atividades associadas
    (agregado em 1 query no service). Ordenação: ativos primeiro,
    depois last_use DESC. Envelope com attribution_30d_pct (T8).
    """
    items = service.list_shoes(db, user.id)
    attribution_30d_pct = service.calculate_attribution_30d_pct(db, user.id)
    return ShoesListOut(items=items, attribution_30d_pct=attribution_30d_pct)


@router.post("")
def create_shoe(
    payload: ShoeCreateIn,
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> ShoeOut:
    """POST /api/shoes — cria tênis com status "ativo" default.

    Validações: name não vazio, initial_km >= 0, status válido.
    user_id explícito (nunca DEFAULT_USER_ID do modelo).
    """
    try:
        shoe = service.create_shoe(db, user.id, payload.model_dump())
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ShoeOut(**shoe)


@router.patch("/{shoe_id}")
def update_shoe(
    shoe_id: int,
    payload: ShoeUpdateIn,
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> ShoeOut:
    """PATCH /api/shoes/{shoe_id} — edita tênis do usuário.

    404 se tênis não existe ou pertence a outro usuário.
    422 para validações: name vazio, initial_km < 0, status inválido.
    Sem rota de DELETE (405 se chamada).
    """
    try:
        shoe = service.update_shoe(db, user.id, shoe_id, payload.model_dump(exclude_unset=True))
        if shoe is None:
            raise HTTPException(status_code=404, detail="tênis não encontrado")
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ShoeOut(**shoe)