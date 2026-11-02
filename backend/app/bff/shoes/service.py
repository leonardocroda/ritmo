"""BFF Service do Shoes — composição de tela Equipamentos via services de domínio."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.equipment.dependencies import get_shoes_service
from app.domain.equipment.schemas import (
    DegradationOut as DomainDegradationOut,
    ShoeCreateIn,
    ShoeOut,
    ShoeSummaryOut,
    ShoeUpdateIn,
    ShoesListOut,
)
from app.domain.equipment.service import ShoesService


class ShoesBFFService:
    """Composição da tela Equipamentos via services de domínio."""

    def __init__(self, equipment_service: ShoesService):
        self.equipment_service = equipment_service

    def list_shoes(self, user_id: int) -> ShoesListOut:
        return self.equipment_service.list(user_id)

    def create_shoe(self, user_id: int, data: ShoeCreateIn) -> ShoeOut:
        return self.equipment_service.create(user_id, data)

    def get_shoe(self, shoe_id: int, user_id: int) -> Optional[ShoeOut]:
        return self.equipment_service.get(shoe_id, user_id)

    def update_shoe(self, shoe_id: int, user_id: int, data: ShoeUpdateIn) -> Optional[ShoeOut]:
        return self.equipment_service.update(shoe_id, user_id, data)

    def set_activity_shoe(
        self, activity_id: int, user_id: int, shoe_id: Optional[int]
    ) -> Optional[ShoeSummaryOut]:
        return self.equipment_service.set_activity_shoe(activity_id, user_id, shoe_id)

    def get_degradation(self, shoe_id: int, user_id: int) -> Optional[DomainDegradationOut]:
        return self.equipment_service.get_degradation(shoe_id, user_id)