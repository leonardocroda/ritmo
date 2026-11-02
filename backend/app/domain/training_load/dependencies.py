"""FastAPI Dependencies para Training-Load."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.training_load.ports.repositories import TrainingLoadRepository
from app.domain.training_load.adapters.sqlalchemy_repo import SQLAlchemyTrainingLoadRepository
from app.domain.training_load.domain.services import PMCCalculator, VolumeCalculator
from app.domain.training_load.service import TrainingLoadService


def get_training_load_repo(db: Session = Depends(get_db)) -> TrainingLoadRepository:
    return SQLAlchemyTrainingLoadRepository(db)


def get_pmc_calc() -> PMCCalculator:
    return PMCCalculator()


def get_volume_calc() -> VolumeCalculator:
    return VolumeCalculator()


def get_training_load_service(
    repo: TrainingLoadRepository = Depends(get_training_load_repo),
    pmc_calc: PMCCalculator = Depends(get_pmc_calc),
    volume_calc: VolumeCalculator = Depends(get_volume_calc),
) -> TrainingLoadService:
    return TrainingLoadService(repo, pmc_calc, volume_calc)