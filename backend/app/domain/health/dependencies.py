"""FastAPI Dependencies para injeção de dependência do domínio Health."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.health.ports.repositories import HealthRepository
from app.domain.health.adapters.sqlalchemy_repo import SQLAlchemyHealthRepository
from app.domain.health.domain.services import (
    HRVCalculator, SleepCalculator, DoseResponseCalculator, LifestyleCalculator
)
from app.domain.health.service import HealthService


def get_health_repo(db: Session = Depends(get_db)) -> HealthRepository:
    return SQLAlchemyHealthRepository(db)


def get_hrv_calc() -> HRVCalculator:
    return HRVCalculator()


def get_sleep_calc() -> SleepCalculator:
    return SleepCalculator()


def get_dose_calc() -> DoseResponseCalculator:
    return DoseResponseCalculator()


def get_lifestyle_calc() -> LifestyleCalculator:
    return LifestyleCalculator()


def get_health_service(
    repo: HealthRepository = Depends(get_health_repo),
    hrv_calc: HRVCalculator = Depends(get_hrv_calc),
    sleep_calc: SleepCalculator = Depends(get_sleep_calc),
    dose_calc: DoseResponseCalculator = Depends(get_dose_calc),
    lifestyle_calc: LifestyleCalculator = Depends(get_lifestyle_calc),
) -> HealthService:
    return HealthService(repo, hrv_calc, sleep_calc, dose_calc, lifestyle_calc)