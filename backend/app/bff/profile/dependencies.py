"""DI do BFF Profile — FastAPI Depends."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.profile.service import ProfileBFFService
from app.db.engine import get_db
from app.domain.heart_rate_zones.dependencies import get_hr_zones_service
from app.domain.vdot.dependencies import get_vdot_service


def get_profile_bff_service(
    hr_zones_service: HeartRateZonesService = Depends(get_hr_zones_service),
    vdot_service: VDOTService = Depends(get_vdot_service),
    db: Session = Depends(get_db),
) -> ProfileBFFService:
    return ProfileBFFService(hr_zones_service, vdot_service, db)