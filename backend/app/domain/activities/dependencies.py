"""FastAPI Dependencies para injeção de dependência do domínio Activities."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.activities.ports.repositories import ActivityRepository, SplitRepository
from app.domain.activities.ports.zone_config import ZoneConfigProvider
from app.domain.activities.adapters.sqlalchemy_repo import (
    SQLAlchemyActivityRepository,
    SQLAlchemySplitRepository,
)
from app.domain.activities.adapters.db_zone_config import DBZoneConfigProvider
from app.domain.activities.domain.services import ConsistencyCalculator
from app.domain.activities.service import ActivityService


def get_activity_repo(db: Session = Depends(get_db)) -> ActivityRepository:
    return SQLAlchemyActivityRepository(db)


def get_split_repo(db: Session = Depends(get_db)) -> SplitRepository:
    return SQLAlchemySplitRepository(db)


def get_zone_provider(db: Session = Depends(get_db)) -> ZoneConfigProvider:
    return DBZoneConfigProvider(db)


def get_consistency() -> ConsistencyCalculator:
    return ConsistencyCalculator()


def get_zone_config(
    db: Session = Depends(get_db),
) -> ZoneConfigProvider:
    """Compatibilidade com router de evaluation antigo."""
    return DBZoneConfigProvider(db)


def get_activity_service(
    repo: ActivityRepository = Depends(get_activity_repo),
    split_repo: SplitRepository = Depends(get_split_repo),
    zone_provider: ZoneConfigProvider = Depends(get_zone_provider),
    consistency: ConsistencyCalculator = Depends(get_consistency),
) -> ActivityService:
    return ActivityService(repo, split_repo, zone_provider, consistency)