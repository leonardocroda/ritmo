"""FastAPI Dependencies para VDOT."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.vdot.ports.repositories import VDOTRepository
from app.domain.vdot.domain.services import VDOTCalculator, PredictionService, DecayCalculator, VO2maxService
from app.domain.vdot.service import VDOTService


# Placeholder adapter
class SQLAlchemyVDOTRepository:
    def __init__(self, db: Session): pass
    def get_vdot_profile(self, user_id: int): return None
    def get_timeline(self, user_id: int): return []
    def get_predictions(self, user_id: int): return {}
    def get_vo2max_timeline(self, user_id: int): return []
    def get_activities_for_performance(self, user_id: int): return []
    def save_vdot_profile(self, profile): return profile


def get_vdot_repo(db: Session = Depends(get_db)) -> VDOTRepository:
    return SQLAlchemyVDOTRepository(db)


def get_vdot_calc() -> VDOTCalculator:
    return VDOTCalculator()


def get_prediction_service() -> PredictionService:
    return PredictionService()


def get_decay_calc() -> DecayCalculator:
    return DecayCalculator()


def get_vo2max_service() -> VO2maxService:
    return VO2maxService()


def get_vdot_service(
    repo: VDOTRepository = Depends(get_vdot_repo),
    vdot_calc: VDOTCalculator = Depends(get_vdot_calc),
    pred_service: PredictionService = Depends(get_prediction_service),
    decay_calc: DecayCalculator = Depends(get_decay_calc),
    vo2max_service: VO2maxService = Depends(get_vo2max_service),
) -> VDOTService:
    return VDOTService(repo, vdot_calc, pred_service, decay_calc, vo2max_service)