"""DI do BFF Shoes — FastAPI Depends.

FASE DE TRANSIÇÃO: service db-based delegando ao legado (ver service.py).
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.shoes.service import ShoesBFFService
from app.db.engine import get_db


def get_shoes_bff_service(db: Session = Depends(get_db)) -> ShoesBFFService:
    return ShoesBFFService(db)
