"""Endpoint de leitura de alerta de degradação por tênis.

Tudo leitura pura do banco (AD-002), zero Garmin. Isolamento por user_id.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import Activity, User
from app.tenis_degradation.baseline import build_baseline
from app.tenis_degradation.mix_gate import group_by_type_band, filter_valid_groups
from app.tenis_degradation.signals import compute_signals

router = APIRouter(prefix="/api/tenis/degradation")


def _fetch_runs_for_shoe(db, user_id: int, shoe_id: int) -> list[dict]:
    runs = (
        db.query(Activity)
        .filter(
            Activity.user_id == user_id,
            Activity.shoe_id == shoe_id,
            Activity.activity_type.in_(("running", "trail_running")),
        )
        .order_by(Activity.start_time)
        .all()
    )
    return [
        {
            "id": r.id,
            "distance_m": r.distance_m,
            "duration_s": r.duration_s,
            "pace_s": (r.duration_s * 1000 / r.distance_m) if r.distance_m else None,
            "avg_hr": r.avg_hr,
            "avg_cadence": r.avg_cadence,
            "inferred_type": r.activity_type,
            "start_time": r.start_time,
            "shoe_id": r.shoe_id,
            "gct_ms": r.raw_json.get("ground_contact_time_ms") if r.raw_json else None,
            "vert_osc_cm": r.raw_json.get("vertical_oscillation_cm") if r.raw_json else None,
        }
        for r in runs
    ]


@router.get("/{shoe_id}")
def degradation_shoe(
    shoe_id: int,
    user: User = Depends(require_session),
    db=Depends(get_db),
):
    """Sinais de degradação de um tênis (baseline ~100 km vs ~50 km)."""
    runs = _fetch_runs_for_shoe(db, user.id, shoe_id)
    if not runs:
        raise HTTPException(status_code=404, detail="tênis não encontrado")

    baseline = build_baseline(runs)
    if baseline is None or baseline.get("insufficient"):
        return {
            "shoe_id": shoe_id,
            "total_km": (baseline or {}).get("total_km", 0),
            "insufficient": True,
            "signals": [],
            "verdict": None,
        }

    groups = group_by_type_band(baseline["initial_runs"] + baseline["final_runs"])
    valid_groups = filter_valid_groups(groups, min_pairs=1)

    signals = compute_signals(baseline["initial_runs"], baseline["final_runs"])

    return {
        "shoe_id": shoe_id,
        "total_km": baseline["total_km"],
        "n_runs": baseline["n_runs"],
        "initial_runs": len(baseline["initial_runs"]),
        "final_runs": len(baseline["final_runs"]),
        "groups": {f"{k[0]}|{k[1]}": len(v) for k, v in valid_groups.items()},
        "signals": signals["signals"],
        "n_signals": signals["n_signals"],
        "verdict": None,  # sinais, não veredito
    }
