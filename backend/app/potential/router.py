"""Router do painel Potencial — leitura do banco, zero Garmin (AD-002).

Padrão do activities/router.py (modelos de saída inline + HTTPException),
mas um payload único: uma página, um round-trip (design §Abordagens).
`days` validado com bounds (422 antes da query — POT-16); o arquivo de
calibração falhou -> 500 com a mesma mensagem do workouts-list.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import get_db
from app.potential import service
from app.vdot.calibration import load_calibration
from app.vdot.zones import ZoneConfigError

router = APIRouter(prefix="/api/potential")


class TimelinePoint(BaseModel):
    date: date
    vdot: float
    source: str
    label: str
    distance_m: float
    time_s: float


class VdotCurrent(BaseModel):
    vdot: float
    source: str
    test_date: date


class VdotDemonstrated(BaseModel):
    vdot: float
    source: str
    date: date


class VdotBlock(BaseModel):
    current: VdotCurrent
    demonstrated: VdotDemonstrated | None
    gap_pct: float | None
    timeline: list[TimelinePoint]


class PredictionRow(BaseModel):
    garmin_s: float | None
    riegel_s: float | None
    vdot_s: float | None
    average_s: float | None
    pr_s: float | None
    pr_date: date | None


class PmcPoint(BaseModel):
    date: date
    ctl: float | None
    atl: float | None
    tsb: float | None
    acwr: float | None


class PmcBlock(BaseModel):
    days: int
    points: list[PmcPoint]
    current: PmcPoint


class Vo2maxPoint(BaseModel):
    date: date
    value: float


class Vo2maxBlock(BaseModel):
    points: list[Vo2maxPoint]


class DecayRow(BaseModel):
    event: str
    real_pace_s: float
    ideal_pace_s: float
    delta_pct: float


class PotentialOut(BaseModel):
    vdot: VdotBlock
    predictions: dict[str, PredictionRow]
    pmc: PmcBlock | None
    vo2max: Vo2maxBlock | None
    decay: list[DecayRow]


@router.get("")
def get_potential(
    days: int = Query(default=180, ge=1, le=365),
    db: Session = Depends(get_db),
) -> PotentialOut:
    """O painel inteiro em 1 payload (design §Contrato).

    `days` fora de [1, 365] -> 422 antes de qualquer query (POT-16); o
    carregamento da calibração acontece no corpo do handler — um arquivo
    ausente/inválido -> 500 "zonas VDOT não configuradas" (spec: sem
    VDOT corrente não há painel).
    """
    try:
        calibration = load_calibration(get_settings().vdot_zones_path)
    except ZoneConfigError as exc:
        raise HTTPException(
            status_code=500, detail="zonas VDOT não configuradas"
        ) from exc
    return service.get_potential(db, days, calibration)
