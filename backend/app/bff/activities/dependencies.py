"""DI do BFF Activities — FastAPI Depends.

FASE DE TRANSIÇÃO: o service é db-based (delega ao legado) — ver
service.py. O dependencies.py antigo apontava para o domínio novo
inacabado (causa dos ERR-06..10).
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.bff.activities.service import ActivitiesBFFService
from app.db.engine import get_db


def get_activities_bff_service(
    db: Session = Depends(get_db),
) -> ActivitiesBFFService:
    return ActivitiesBFFService(db)
