"""FastAPI Dependencies para Heart Rate Zones."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.heart_rate_zones.ports.repositories import HeartRateZonesRepository
# Placeholder adapter
class SQLAlchemyHeartRateZonesRepository:
    def __init__(self, db: Session): pass
    def get_hr_zone_config(self, user_id: int): return None
    def get_hr_metrics(self, user_id: int): return []
    def get_hr_sync_prefs(self, user_id: int): return []
    def save_hr_zone_config(self, config): return config
    def save_hr_metric(self, metric): return metric
    def save_hr_sync_pref(self, pref): return pref


def get_hr_zones_repo(db: Session = Depends(get_db)) -> HeartRateZonesRepository:
    return SQLAlchemyHeartRateZonesRepository(db)


def get_hr_zones_service(
    repo: HeartRateZonesRepository = Depends(get_hr_zones_repo),
):
    from app.domain.heart_rate_zones.service import HeartRateZonesService
    return HeartRateZonesService(repo)