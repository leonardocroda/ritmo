"""Router do domínio activities — leitura do banco, zero Garmin (AD-002).

Padrão do garmin/router.py (modelos de saída inline + HTTPException),
mas o domínio só lê o banco próprio: nenhuma chamada ao Garmin.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.activities import service
from app.db.engine import get_db
from app.vdot.zones import ZoneConfigError

router = APIRouter(prefix="/api/activities")


class ActivityListItem(BaseModel):
    id: int
    start_time: datetime
    activity_type: str
    name: str | None
    distance_m: float
    duration_s: float
    pace_s: float | None
    avg_hr: int | None
    inferred_type: str | None
    evaluated: bool


class ActivityListOut(BaseModel):
    items: list[ActivityListItem]
    total: int
    limit: int
    offset: int


@router.get("")
def list_activities(
    activity_type: Literal["running", "all"] = "running",
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ActivityListOut:
    """TRN-04/05/06: corridas por padrão; validação 422 antes da query."""
    try:
        return service.list_activities(db, activity_type, limit, offset)
    except ZoneConfigError as exc:
        raise HTTPException(
            status_code=500, detail="zonas VDOT não configuradas"
        ) from exc
