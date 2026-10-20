"""Service do domínio activities — leitura pura do banco (AD-002).

Nenhuma importação do gateway Garmin aqui: lista e detalhe leem
exclusivamente o banco próprio (Success Criteria do spec, TRN-28).
Tipo inferido em tempo de leitura (premissa do spec): as voltas da
página vêm em 1 query IN (sem N+1), são classificadas por zona e
passadas às funções puras do domínio.
"""

from collections import defaultdict
from dataclasses import asdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.activities.infer import ClassifiedSplit, derive_structure, infer_type
from app.activities.metrics import consistency_metrics
from app.core.config import get_settings
from app.db.models import Activity, Hrv, Rhr, Sleep, Split
from app.vdot.zones import HR_LINE_COLOR, ZoneConfig, load_zone_config

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
    db: Session, user_id: int, activity_type: str, limit: int, offset: int
) -> dict:
    """Lista paginada {items, total, limit, offset} — corridas por padrão (spec).

    Ordenação estável: start_time DESC com desempate id DESC (edge do
    spec — mesma ordem entre páginas). Filtra exclusivamente por
    ``user_id`` do usuário autenticado (never ``DEFAULT_USER_ID``).
    """
    zone_config = load_zone_config(get_settings().vdot_zones_path)
    filters = [Activity.user_id == user_id]
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


def _km_label(cumulative_m: float) -> str:
    """Km acumulado da volta, PT-BR com 1 decimal ("1,6" = 1600m)."""
    return f"{cumulative_m / 1000:.1f}".replace(".", ",")


def _weighted_temperature(splits: list[Split]) -> float | None:
    """Temperatura média ponderada pela duração das voltas com temperatura (spec).

    None quando nenhuma volta tem temperatura — o campo é omitido do payload.
    """
    weighted = [
        (split.avg_temperature, split.duration_s)
        for split in splits
        if split.avg_temperature is not None and split.duration_s and split.duration_s > 0
    ]
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in weighted) / total_weight


def _context(
    db: Session, activity: Activity, splits: list[Split], user_id: int
) -> dict:
    """Sono/HRV/RHR da data local de início (cada um null quando ausente).

    temperature_c só entra no payload quando >=1 volta tem temperatura (spec).
    """
    day = activity.start_time.date()
    sleep = db.execute(
        select(Sleep).where(Sleep.user_id == user_id, Sleep.date == day)
    ).scalar_one_or_none()
    hrv = db.execute(
        select(Hrv).where(Hrv.user_id == user_id, Hrv.date == day)
    ).scalar_one_or_none()
    rhr = db.execute(
        select(Rhr).where(Rhr.user_id == user_id, Rhr.date == day)
    ).scalar_one_or_none()

    context = {
        "sleep": (
            {"duration_s": sleep.duration_s, "score": sleep.score} if sleep else None
        ),
        "hrv": ({"value": hrv.value, "status": hrv.status} if hrv else None),
        "rhr": ({"value": rhr.value} if rhr else None),
    }
    temperature = _weighted_temperature(splits)
    if temperature is not None:
        context["temperature_c"] = temperature
    return context


def get_activity_detail(
    db: Session, activity_id: int, user_id: int, zone_config: ZoneConfig
) -> dict | None:
    """Payload do detalhe (design): voltas classificadas, zonas, consistência,
    contexto e estrutura. None -> 404 no router. Filtra por ``user_id`` do
    usuário autenticado (never ``DEFAULT_USER_ID``)."""
    activity = db.execute(
        select(Activity).where(
            Activity.id == activity_id, Activity.user_id == user_id
        )
    ).scalar_one_or_none()
    if activity is None:
        return None

    splits = (
        db.execute(
            select(Split).where(Split.activity_id == activity.id).order_by(Split.idx)
        )
        .scalars()
        .all()
    )
    classified = _classify_splits(splits, zone_config)

    detail_splits = []
    cumulative_m = 0.0
    for split, item in zip(splits, classified):
        cumulative_m += split.dist_m or 0
        detail_splits.append(
            {
                "idx": split.idx,
                "dist_m": split.dist_m,
                "duration_s": split.duration_s,
                "pace_s": split.pace_s,
                "avg_hr": split.avg_hr,
                "avg_cadence": split.avg_cadence,
                "avg_temperature": split.avg_temperature,
                "elevation_m": split.elevation_m,
                "intensity_type": split.intensity_type,
                "zone": item.zone,
                "km_label": _km_label(cumulative_m),
            }
        )

    # Import em nível de função: evaluation.service importa este módulo
    # (reuso do get_activity_detail no motor de avaliação) — no topo o
    # import seria circular. Uma única implementação da lista (EVAL-17).
    from app.evaluation.service import list_evaluations

    return {
        "activity": {
            "id": activity.id,
            "start_time": activity.start_time,
            "activity_type": activity.activity_type,
            "name": activity.name,
            "distance_m": activity.distance_m,
            "duration_s": activity.duration_s,
            "pace_s": _pace_s(activity.distance_m, activity.duration_s),
            "avg_hr": activity.avg_hr,
            "max_hr": activity.max_hr,
            "avg_cadence": activity.avg_cadence,
            "elevation_gain_m": activity.elevation_gain_m,
            "aerobic_te": activity.aerobic_te,
            "anaerobic_te": activity.anaerobic_te,
            "training_load": activity.training_load,
            "evaluated": activity.evaluated,
            "inferred_type": _inferred_type(activity, splits, zone_config),
            "structure": derive_structure(classified),
        },
        "splits": detail_splits,
        "zones": [asdict(zone) for zone in zone_config.meta()],
        "hr_color": HR_LINE_COLOR,
        "consistency": consistency_metrics(splits, activity.distance_m),
        "context": _context(db, activity, splits, user_id),
        "evaluations": list_evaluations(db, activity.id),
    }
