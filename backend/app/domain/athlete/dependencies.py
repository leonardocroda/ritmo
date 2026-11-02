"""FastAPI Dependencies para Athlete."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.athlete.ports.repositories import AthleteRepository
# Placeholder adapter
class SQLAlchemyAthleteRepository:
    def __init__(self, db: Session): pass
    def get_by_user_id(self, user_id: int): return None
    def save(self, athlete): return athlete
    def update(self, athlete): return athlete


def get_athlete_repo(db: Session = Depends(get_db)) -> AthleteRepository:
    return SQLAlchemyAthleteRepository(db)


def get_athlete_service(
    repo: AthleteRepository = Depends(get_athlete_repo),
):
    from app.domain.athlete.service import AthleteService
    return AthleteService(repo)