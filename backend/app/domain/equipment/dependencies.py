"""FastAPI Dependencies para Equipment."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.equipment.ports.repositories import ShoeRepository
from app.domain.equipment.adapters.sqlalchemy_repo import SQLAlchemyShoeRepository
from app.domain.equipment.service import ShoesService


def get_shoe_repo(db: Session = Depends(get_db)) -> ShoeRepository:
    return SQLAlchemyShoeRepository(db)


def get_shoes_service(
    repo: ShoeRepository = Depends(get_shoe_repo),
) -> ShoesService:
    return ShoesService(repo)