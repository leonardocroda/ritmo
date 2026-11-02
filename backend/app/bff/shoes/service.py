"""BFF Service do Shoes — composição da tela Equipamentos.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): delega
ao service legado `app.shoes.service` (current_km/run_count/last_use/
life_pct reais) e ao service de degradação `app.tenis_degradation.service`.
A primeira versão devolvia zeros hardcoded e degradação stub (ERR-12).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.shoes import service as shoes_service
from app.shoes.router import ShoeCreateIn, ShoeOut, ShoesListOut, ShoeUpdateIn
from app.tenis_degradation.service import degradation_payload


class ShoesBFFService:
    """Composição da tela Equipamentos via services legados."""

    def __init__(self, db: Session):
        self.db = db

    def list_shoes(self, user_id: int) -> ShoesListOut:
        items = shoes_service.list_shoes(self.db, user_id)
        attribution = shoes_service.calculate_attribution_30d_pct(self.db, user_id)
        return ShoesListOut(
            items=[ShoeOut(**s) for s in items],
            attribution_30d_pct=attribution,
        )

    def create_shoe(self, user_id: int, data: ShoeCreateIn) -> ShoeOut:
        shoe = shoes_service.create_shoe(self.db, user_id, data.model_dump())
        self.db.commit()
        return ShoeOut(**shoe)

    def get_shoe(self, shoe_id: int, user_id: int) -> ShoeOut | None:
        for shoe in shoes_service.list_shoes(self.db, user_id):
            if shoe["id"] == shoe_id:
                return ShoeOut(**shoe)
        return None

    def update_shoe(self, shoe_id: int, user_id: int, data: ShoeUpdateIn) -> ShoeOut | None:
        shoe = shoes_service.update_shoe(
            self.db, user_id, shoe_id, data.model_dump(exclude_unset=True)
        )
        if shoe is None:
            return None
        self.db.commit()
        return ShoeOut(**shoe)

    def get_degradation(self, shoe_id: int, user_id: int) -> dict:
        """Mesma implementação do router legado (404 quando sem corridas)."""
        return degradation_payload(self.db, user_id, shoe_id)
