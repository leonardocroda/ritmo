"""DI do BFF Profile — FastAPI Depends.

FASE DE TRANSIÇÃO: service db-based delegando aos builders legados
(ver service.py). O dependencies.py antigo injetava os services de
domínio stub (ERR-11).
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.profile.service import ProfileBFFService
from app.db.engine import get_db


def get_profile_bff_service(db: Session = Depends(get_db)) -> ProfileBFFService:
    return ProfileBFFService(db)
