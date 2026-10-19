"""Router do painel Performance (ex-Potencial) — leitura do banco, zero Garmin (AD-002).

Padrão do activities/router.py (modelos de saída inline + HTTPException),
mas um payload único: uma página, um round-trip (design §Abordagens).
Sem `days` e sem `pmc` (CLR-03): a curva de carga mora no health; um
`?days=` qualquer vira query não declarada — ignorada, 200 (CLR-04). O
arquivo de calibração falhou -> 500 com a mesma mensagem do workouts-list.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
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
    vo2max: Vo2maxBlock | None
    decay: list[DecayRow]


@router.get("")
def get_potential(db: Session = Depends(get_db)) -> PotentialOut:
    """O painel inteiro em 1 payload — só os 4 blocos, sem `pmc` (CLR-03).

    Query param não declarado (`?days=90` do cliente antigo) é ignorado:
    200 sem efeito no payload (CLR-04). O carregamento da calibração
    acontece no corpo do handler — um arquivo ausente/inválido -> 500
    "zonas VDOT não configuradas" (spec: sem VDOT corrente não há painel).
    """
    try:
        calibration = load_calibration(get_settings().vdot_zones_path)
    except ZoneConfigError as exc:
        raise HTTPException(
            status_code=500, detail="zonas VDOT não configuradas"
        ) from exc
    return service.get_potential(db, calibration)
