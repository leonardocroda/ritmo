"""Endpoints de leitura da análise comparativa entre tênis.

Tudo leitura pura do banco (AD-002), zero Garmin em tempo de análise.
Isolamento por user_id da sessão (user-scope).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.activities.service import _pace_s
from app.auth.deps import require_session
from app.core.config import get_settings
from app.db.engine import get_db
from app.db.models import Activity, Split, User
from app.tenis_analysis.comparison import build_comparison_result
from app.tenis_analysis.metrics import ef_factor, fresh_vs_fatigue, hr_drift, running_dynamics_adjusted
from app.tenis_analysis.profile import build_shoe_profile

router = APIRouter(prefix="/api/tenis/analysis")


def _fetch_runs_for_shoe(db: Session, user_id: int, shoe_id: int) -> list[dict]:
    """Busca runs de um tênis com seus splits (para métricas derivadas)."""
    runs = (
        db.execute(
            select(Activity)
            .where(
                Activity.user_id == user_id,
                Activity.shoe_id == shoe_id,
                Activity.activity_type.in_(("running", "trail_running")),
            )
            .order_by(Activity.start_time)
        )
    ).scalars().all()
    if not runs:
        return []
    run_ids = [r.id for r in runs]
    splits_map: dict[int, list[dict]] = {}
    if run_ids:
        splits = (
            db.execute(
                select(Split)
                .where(Split.activity_id.in_(run_ids))
                .order_by(Split.activity_id, Split.idx)
            )
        ).scalars().all()
        for s in splits:
            splits_map.setdefault(s.activity_id, []).append(
                {
                    "idx": s.idx,
                    "dist_m": s.dist_m,
                    "duration_s": s.duration_s,
                    "pace_s": s.pace_s,
                    "avg_hr": s.avg_hr,
                    "avg_cadence": s.avg_cadence,
                    "gct_ms": s.ground_contact_time_ms,
                    "stride_cm": s.stride_length_cm,
                    "vert_osc_cm": s.vertical_oscillation_cm,
                    "vert_ratio": s.vertical_ratio,
                }
            )
    out = []
    for r in runs:
        out.append(
            {
                "id": r.id,
                "distance_m": r.distance_m,
                "duration_s": r.duration_s,
                "pace_s": _pace_s(r.distance_m, r.duration_s),
                "avg_hr": r.avg_hr,
                "avg_cadence": r.avg_cadence,
                "inferred_type": r.activity_type,
                "start_time": r.start_time,
                "shoe_id": r.shoe_id,
                "splits": splits_map.get(r.id, []),
            }
        )
    return out


@router.get("/shoes")
def analysis_shoes(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Perfil de todos os tênis do usuário, fatiado por tipo × banda de pace."""
    shoes = (
        db.execute(
            select(Activity.shoe_id).distinct().where(
                Activity.user_id == user.id,
                Activity.activity_type.in_(("running", "trail_running")),
                Activity.shoe_id.is_not(None),
            )
        )
    ).scalars().all()
    result = []
    for shoe_id in shoes:
        runs = _fetch_runs_for_shoe(db, user.id, shoe_id)
        profile = build_shoe_profile(runs)
        profile["shoe_id"] = shoe_id
        result.append(profile)
    return result


@router.get("/shoes/{shoe_id}")
def analysis_shoe_detail(
    shoe_id: int,
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    """Perfil detalhado de um tênis, incluindo métricas derivadas."""
    # Verifica que o tênis pertence ao usuário (tem pelo menos uma corrida)
    runs = _fetch_runs_for_shoe(db, user.id, shoe_id)
    if not runs:
        raise HTTPException(status_code=404, detail="tênis não encontrado")
    profile = build_shoe_profile(runs)
    profile["shoe_id"] = shoe_id
    # Métricas derivadas (opcionais, omitidas quando não há dado)
    rd = running_dynamics_adjusted(runs)
    if rd:
        profile["running_dynamics_adjusted"] = rd
    ef = ef_factor(runs)
    if ef:
        profile["ef"] = ef
    drift = hr_drift(runs)
    if drift is not None:
        profile["hr_drift"] = drift
    window = fresh_vs_fatigue(runs)
    if window:
        profile["fresh_vs_fatigue"] = window
    return profile


@router.get("/compare")
def analysis_compare(
    shoe_a: int = Query(...),
    shoe_b: int = Query(...),
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    """Comparação pareada entre dois tênis com nível de confiança."""
    runs_a = _fetch_runs_for_shoe(db, user.id, shoe_a)
    runs_b = _fetch_runs_for_shoe(db, user.id, shoe_b)
    if not runs_a or not runs_b:
        raise HTTPException(status_code=404, detail="um dos tênis não foi encontrado")
    return build_comparison_result(runs_a, runs_b)
