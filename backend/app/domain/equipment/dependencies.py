"""FastAPI Dependencies para o domínio Equipment."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.equipment.service import ShoesService


def get_shoes_service(db: Session = Depends(get_db)) -> ShoesService:
    return ShoesService(db)
