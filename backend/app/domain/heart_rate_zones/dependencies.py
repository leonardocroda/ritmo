"""FastAPI Dependencies para Heart Rate Zones."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.heart_rate_zones.ports.repositories import HeartRateZonesRepository
from app.domain.heart_rate_zones.adapters.sqlalchemy_repo import SQLAlchemyHeartRateZonesRepository


def get_hr_zones_repo(db: Session = Depends(get_db)) -> HeartRateZonesRepository:
    return SQLAlchemyHeartRateZonesRepository(db)


def get_hr_zones_service(
    repo: HeartRateZonesRepository = Depends(get_hr_zones_repo),
):
    from app.domain.heart_rate_zones.service import HeartRateZonesService
    return HeartRateZonesService(repo)