"""Athlete domain package."""

from app.domain.athlete.domain.entities import Athlete
from app.domain.athlete.ports.repositories import AthleteRepository
from app.domain.athlete.schemas import AthleteOut, AthleteUpdate
from app.domain.athlete.service import AthleteService
from app.domain.athlete.dependencies import get_athlete_repo, get_athlete_service
from app.domain.athlete.router import router

__all__ = [
    "Athlete",
    "AthleteRepository",
    "AthleteOut",
    "AthleteUpdate",
    "AthleteService",
    "get_athlete_repo",
    "get_athlete_service",
    "router",
]