"""Equipment domain package."""

from app.domain.equipment.domain.entities import Shoe, ShoeRun, DegradationSignal
from app.domain.equipment.domain.value_objects import KM, ShoeStatus, RunTypeBand
from app.domain.equipment.ports.repositories import ShoeRepository
from app.domain.equipment.adapters.sqlalchemy_repo import SQLAlchemyShoeRepository
from app.domain.equipment.schemas import (
    ShoeOut, ShoesListOut, ShoeSummaryOut, ShoeCreateIn, ShoeUpdateIn, DegradationOut, DegradationSignalOut
)
from app.domain.equipment.service import ShoesService
from app.domain.equipment.dependencies import get_shoe_repo, get_shoes_service
from app.domain.equipment.router import router

__all__ = [
    "Shoe", "ShoeRun", "DegradationSignal",
    "KM", "ShoeStatus", "RunTypeBand",
    "ShoeRepository",
    "SQLAlchemyShoeRepository",
    "ShoeOut", "ShoesListOut", "ShoeSummaryOut", "ShoeCreateIn", "ShoeUpdateIn", "DegradationOut", "DegradationSignalOut",
    "ShoesService",
    "get_shoe_repo", "get_shoes_service",
    "router",
]