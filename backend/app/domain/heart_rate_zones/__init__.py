"""Heart Rate Zones domain package."""

from app.domain.heart_rate_zones.domain.entities import HRZoneConfig, HRMetric, HRSyncPref
from app.domain.heart_rate_zones.domain.value_objects import HRZoneMethod, HRZoneBounds, VDOTZone
from app.domain.heart_rate_zones.ports.repositories import HeartRateZonesRepository
from app.domain.heart_rate_zones.adapters.sqlalchemy_repo import SQLAlchemyHeartRateZonesRepository
from app.domain.heart_rate_zones.schemas import (
    HRZonesOut, HRZonesUpdate, HRZoneConfigOut, HRZoneBoundOut, PaceZonesOut, PaceZoneOut
)
from app.domain.heart_rate_zones.service import HeartRateZonesService
from app.domain.heart_rate_zones.dependencies import get_hr_zones_repo, get_hr_zones_service
from app.domain.heart_rate_zones.router import router

__all__ = [
    "HRZoneConfig", "HRMetric", "HRSyncPref",
    "HRZoneMethod", "HRZoneBounds", "VDOTZone",
    "HeartRateZonesRepository",
    "SQLAlchemyHeartRateZonesRepository",
    "HRZonesOut", "HRZonesUpdate", "HRZoneConfigOut", "HRZoneBoundOut", "PaceZonesOut", "PaceZoneOut",
    "HeartRateZonesService",
    "get_hr_zones_repo", "get_heart_rate_zones_service",
    "router",
]