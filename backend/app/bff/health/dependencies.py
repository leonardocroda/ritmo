"""DI do BFF Health — FastAPI Depends."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.health.service import HealthBFFService
from app.db.engine import get_db


def get_health_bff_service(
    db: Session = Depends(get_db),
) -> HealthBFFService:
    return HealthBFFService(db)