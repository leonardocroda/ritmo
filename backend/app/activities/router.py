"""Router do domínio activities — leitura do banco, zero Garmin (AD-002).

Padrão do garmin/router.py (modelos de saída inline + HTTPException),
mas o domínio só lê o banco próprio: nenhuma chamada ao Garmin.
`consistency` e `context` ficam como dicts: têm chaves condicionais
(`cadence_fade_spm`/`temperature_c` omitidos quando não há dado — spec).
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.activities import service
from app.core.config import get_settings
from app.db.engine import get_db
from app.evaluation.schemas import EvaluationOut
from app.vdot.zones import ZoneConfig, ZoneConfigError, load_zone_config

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


class ActivityOut(BaseModel):
    id: int
    start_time: datetime
    activity_type: str
    name: str | None
    distance_m: float
    duration_s: float
    pace_s: float | None
    avg_hr: int | None
    max_hr: int | None
    avg_cadence: float | None
    elevation_gain_m: float | None
    aerobic_te: float | None
    anaerobic_te: float | None
    training_load: float | None
    evaluated: bool
    inferred_type: str | None
    structure: str | None


class SplitOut(BaseModel):
    idx: int
    dist_m: float | None
    duration_s: float | None
    pace_s: float | None
    avg_hr: int | None
    avg_cadence: float | None
    avg_temperature: float | None
    elevation_m: float | None
    intensity_type: str | None
    zone: str | None
    km_label: str


class ZoneMetaOut(BaseModel):
    key: str
    label: str
    pace_range: str
    color: str


class ActivityDetailOut(BaseModel):
    activity: ActivityOut
    splits: list[SplitOut]
    zones: list[ZoneMetaOut]
    hr_color: str
    consistency: dict | None
    context: dict
    evaluations: list[EvaluationOut]


def get_zone_config() -> ZoneConfig:
    """Zonas por request, sem cache (design); arquivo falhou -> 500 (spec)."""
    try:
        return load_zone_config(get_settings().vdot_zones_path)
    except ZoneConfigError as exc:
        raise HTTPException(
            status_code=500, detail="zonas VDOT não configuradas"
        ) from exc


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


@router.get("/{activity_id}")
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    zone_config: ZoneConfig = Depends(get_zone_config),
) -> ActivityDetailOut:
    """TRN-13/19: 404 para id inexistente; 500 quando o arquivo de zonas falha."""
    detail = service.get_activity_detail(db, activity_id, zone_config)
    if detail is None:
        raise HTTPException(status_code=404, detail="atividade não encontrada")
    return detail
