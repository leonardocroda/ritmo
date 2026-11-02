"""Application Service do domínio Shoes (leitura/CRUD).

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): delega
ao service legado `app.shoes.service` — a implementação completa e provada
(current_km/run_count/last_use/life_pct calculados das atividades). A
primeira versão deste service DEVOLVIA zeros hardcoded (ERR-12 do
audit-erros.md). O domínio equipment assume a implementação própria
quando passar nos parity tests (Fase 2 do plano).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Shoe as ShoeModel
from app.shoes import service as shoes_service
from app.shoes.router import ShoeCreateIn, ShoeOut, ShoesListOut, ShoeUpdateIn
from app.tenis_degradation.service import degradation_payload


class ShoesService:
    """CRUD + leitura de tênis user-scoped, via implementação legada."""

    def __init__(self, db: Session):
        self.db = db

    def list(self, user_id: int, status: str | None = None) -> ShoesListOut:
        items = shoes_service.list_shoes(self.db, user_id)
        if status is not None:
            items = [s for s in items if s["status"] == status]
        attribution = shoes_service.calculate_attribution_30d_pct(self.db, user_id)
        return ShoesListOut(
            items=[ShoeOut(**s) for s in items],
            attribution_30d_pct=attribution,
        )

    def get(self, shoe_id: int, user_id: int) -> ShoeOut | None:
        for shoe in shoes_service.list_shoes(self.db, user_id):
            if shoe["id"] == shoe_id:
                return ShoeOut(**shoe)
        return None

    def create(self, user_id: int, data: ShoeCreateIn) -> ShoeOut:
        shoe = shoes_service.create_shoe(self.db, user_id, data.model_dump())
        self.db.commit()
        return ShoeOut(**shoe)

    def update(self, shoe_id: int, user_id: int, data: ShoeUpdateIn) -> ShoeOut | None:
        shoe = shoes_service.update_shoe(
            self.db, user_id, shoe_id, data.model_dump(exclude_unset=True)
        )
        if shoe is None:
            return None
        self.db.commit()
        return ShoeOut(**shoe)

    def delete(self, shoe_id: int, user_id: int) -> bool:
        model = self.db.get(ShoeModel, shoe_id)
        if model is None or model.user_id != user_id:
            return False
        self.db.delete(model)
        self.db.commit()
        return True

    def get_degradation(self, shoe_id: int, user_id: int) -> dict:
        """Payload de degradação — mesma implementação do router legado.

        Levanta HTTPException 404 quando o tênis não tem corridas.
        """
        return degradation_payload(self.db, user_id, shoe_id)
