"""DI do BFF Activities — FastAPI Depends."""

from fastapi import Depends

from app.bff.activities.service import ActivitiesBFFService
from app.domain.activity.dependencies import get_activity_service


def get_activities_bff_service(
    activity_service: ActivityService = Depends(get_activity_service),
) -> ActivitiesBFFService:
    return ActivitiesBFFService(activity_service)