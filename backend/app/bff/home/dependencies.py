"""DI do BFF Home — FastAPI Depends."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.home.service import HomeBFFService
from app.db.engine import get_db


def get_home_bff_service(
    db: Session = Depends(get_db),
) -> HomeBFFService:
    return HomeBFFService(db)