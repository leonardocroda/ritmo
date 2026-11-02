"""DI do BFF Shoes — FastAPI Depends."""

from fastapi import Depends

from app.bff.shoes.service import ShoesBFFService
from app.domain.equipment.dependencies import get_shoes_service
from app.domain.equipment.service import ShoesService


def get_shoes_bff_service(
    equipment_service: ShoesService = Depends(get_shoes_service),
) -> ShoesBFFService:
    return ShoesBFFService(equipment_service)