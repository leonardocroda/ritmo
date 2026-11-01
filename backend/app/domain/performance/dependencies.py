"""FastAPI Dependencies para Performance."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.performance.ports.repositories import PerformanceRepository
from app.domain.performance.adapters.sqlalchemy_repo import SQLAlchemyPerformanceRepository
from app.domain.performance.domain.services import (
    VDOTCalculator, PredictionService, DecayCalculator, VO2maxService
)
from app.domain.performance.service import PerformanceService


def get_performance_repo(db: Session = Depends(get_db)) -> PerformanceRepository:
    return SQLAlchemyPerformanceRepository(db)


def get_vdot_calc() -> VDOTCalculator:
    return VDOTCalculator()


def get_prediction_service() -> PredictionService:
    return PredictionService()


def get_decay_calc() -> DecayCalculator:
    return DecayCalculator()


def get_vo2max_service() -> VO2maxService:
    return VO2maxService()


def get_performance_service(
    repo: PerformanceRepository = Depends(get_performance_repo),
    vdot_calc: VDOTCalculator = Depends(get_vdot_calc),
    pred_service: PredictionService = Depends(get_prediction_service),
    decay_calc: DecayCalculator = Depends(get_decay_calc),
    vo2max_service: VO2maxService = Depends(get_vo2max_service),
) -> PerformanceService:
    return PerformanceService(repo, vdot_calc, pred_service, decay_calc, vo2max_service)