"""BFF Service do Activities — composição da tela Treinos via services de domínio."""

from typing import Optional

from sqlalchemy.orm import Session

from app.domain.activity.dependencies import get_activity_service
from app.domain.activity.schemas import ActivityDetailOut as DomainActivityDetailOut
from app.domain.activity.schemas import ActivityListOut as DomainActivityListOut
from app.domain.activity.schemas import ActivityListItemOut as DomainActivityListItemOut
from app.domain.activity.service import ActivityService


class ActivitiesBFFService:
    """Composição da tela Treinos via services de domínio."""

    def __init__(self, activity_service: ActivityService):
        self.activity_service = activity_service

    def list_activities(
        self, user_id: int, activity_type: str, limit: int, offset: int
    ) -> DomainActivityListOut:
        from app.domain.activity.domain.value_objects import ActivityFilter

        filter = ActivityFilter(type=activity_type)
        return self.activity_service.list(user_id, filter, limit, offset)

    def get_detail(
        self, activity_id: int, user_id: int
    ) -> Optional[DomainActivityDetailOut]:
        return self.activity_service.get_detail(activity_id, user_id)