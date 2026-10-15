"""Service do domínio activities — leitura pura do banco (AD-002).

Nenhuma importação do gateway Garmin aqui: lista e detalhe leem
exclusivamente o banco próprio (Success Criteria do spec, TRN-28).
Tipo inferido em tempo de leitura (premissa do spec): as voltas da
página vêm em 1 query IN (sem N+1), são classificadas por zona e
passadas às funções puras do domínio.
"""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activities.infer import ClassifiedSplit, infer_type
from app.core.config import get_settings
from app.db.models import DEFAULT_USER_ID, Activity, Split
from app.vdot.zones import ZoneConfig, load_zone_config

# Vocabulário de corrida do domínio (mesmo conjunto do sync — AD-001/002
# mantêm os domínios desacoplados: aqui é leitura, lá é escrita)
RUNNING_TYPES = ("running", "trail_running")


def _pace_s(distance_m: float, duration_s: float) -> float | None:
    """Spec: duration_s × 1000 / distance_m quando distance_m > 0, senão null."""
    return duration_s * 1000 / distance_m if distance_m > 0 else None


def _classify_splits(splits: list[Split], zone_config: ZoneConfig) -> list[ClassifiedSplit]:
    """Voltas do banco -> ClassifiedSplit com a zona de cada pace (ou None)."""
    classified = []
    for split in splits:
        speed = 1000 / split.pace_s if split.pace_s and split.pace_s > 0 else None
        classified.append(
            ClassifiedSplit(
                dist_m=split.dist_m,
                duration_s=split.duration_s,
                pace_s=split.pace_s,
                intensity_type=split.intensity_type,
                zone=zone_config.classify(speed),
            )
        )
    return classified


def _page_splits(db: Session, activity_ids: list[int]) -> dict[int, list[Split]]:
    """Voltas de TODAS as atividades da página em 1 query IN (sem N+1)."""
    if not activity_ids:
        return {}
    rows = (
        db.execute(
            select(Split)
            .where(Split.activity_id.in_(activity_ids))
            .order_by(Split.activity_id, Split.idx)
        )
        .scalars()
        .all()
    )
    by_activity: dict[int, list[Split]] = defaultdict(list)
    for row in rows:
        by_activity[row.activity_id].append(row)
    return by_activity


def _inferred_type(
    activity: Activity, splits: list[Split], zone_config: ZoneConfig
) -> str | None:
    """Tipo só existe para corrida; não-corrida -> null (spec)."""
    if activity.activity_type not in RUNNING_TYPES:
        return None
    classified = _classify_splits(splits, zone_config)
    return infer_type(activity.raw_json, classified, activity.distance_m)


def list_activities(
    db: Session, activity_type: str, limit: int, offset: int
) -> dict:
    """Lista paginada {items, total, limit, offset} — corridas por padrão (spec).

    Ordenação estável: start_time DESC com desempate id DESC (edge do
    spec — mesma ordem entre páginas).
    """
    zone_config = load_zone_config(get_settings().vdot_zones_path)
    filters = [Activity.user_id == DEFAULT_USER_ID]
    if activity_type != "all":
        filters.append(Activity.activity_type.in_(RUNNING_TYPES))

    total = db.execute(
        select(func.count()).select_from(Activity).where(*filters)
    ).scalar_one()
    activities = (
        db.execute(
            select(Activity)
            .where(*filters)
            .order_by(Activity.start_time.desc(), Activity.id.desc())
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    splits_by_activity = _page_splits(db, [a.id for a in activities])
    items = [
        {
            "id": activity.id,
            "start_time": activity.start_time,
            "activity_type": activity.activity_type,
            "name": activity.name,
            "distance_m": activity.distance_m,
            "duration_s": activity.duration_s,
            "pace_s": _pace_s(activity.distance_m, activity.duration_s),
            "avg_hr": activity.avg_hr,
            "inferred_type": _inferred_type(
                activity, splits_by_activity.get(activity.id, []), zone_config
            ),
            "evaluated": activity.evaluated,
        }
        for activity in activities
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}
