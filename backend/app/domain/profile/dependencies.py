"""FastAPI Dependencies para Profile."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.profile.ports.repositories import ProfileRepository
from app.domain.profile.adapters.sqlalchemy_repo import SQLAlchemyProfileRepository
from app.domain.profile.service import ProfileService


def get_profile_repo(db: Session = Depends(get_db)) -> ProfileRepository:
    return SQLAlchemyProfileRepository(db)


def get_profile_service(
    repo: ProfileRepository = Depends(get_profile_repo),
) -> ProfileService:
    return ProfileService(repo)