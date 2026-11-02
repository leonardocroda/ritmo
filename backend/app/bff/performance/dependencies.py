"""DI do BFF Performance — FastAPI Depends."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.performance.service import PerformanceBFFService
from app.db.engine import get_db


def get_performance_bff_service(
    db: Session = Depends(get_db),
) -> PerformanceBFFService:
    return PerformanceBFFService(db)