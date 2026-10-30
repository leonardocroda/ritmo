"""Service do domínio shoes — CRUD, km derivada, associação atividade↔tênis.

Regras: km acumulada é derivada (initial_km + Σ activities.distance_m),
reatribuição retroativa recalcula sozinha. Service não commita — quem
chama controla a transação. Isolamento por user_id sempre explícito.
"""

from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Activity, Shoe
from app.garmin.mappers import RUNNING_TYPES


class AssociationError(Exception):
    """Erro de domínio na associação atividade↔tênis — carrega code para
    o router mapear para 404/422 exato."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def list_shoes(db: Session, user_id: int) -> list[dict]:
    """Lista tênis do usuário com km derivada agregada em 1 query.

    Outerjoin Activity.shoe_id + group by Shoe.id → campos do shoe +
    current_km (initial_km + soma), run_count, last_use, life_pct.
    Ordenação: ativos primeiro, depois last_use DESC.
    """
    stmt = (
        select(
            Shoe,
            func.count(Activity.id),
            func.coalesce(func.sum(Activity.distance_m), 0.0),
            func.max(Activity.start_time),
        )
        .outerjoin(Activity, Activity.shoe_id == Shoe.id)
        .where(Shoe.user_id == user_id)
        .group_by(Shoe.id)
        .order_by(
            (Shoe.status != "aposentado").desc(),  # ativos (True) primeiro
            func.max(Activity.start_time).desc().nullslast(),
        )
    )
    rows = db.execute(stmt).all()

    result = []
    for shoe, run_count, sum_distance, last_use in rows:
        current_km = shoe.initial_km + (sum_distance / 1000.0)
        life_pct = None
        if shoe.max_km and shoe.max_km > 0:
            life_pct = round((current_km / shoe.max_km) * 100, 1)
        result.append(
            {
                "id": shoe.id,
                "name": shoe.name,
                "brand": shoe.brand,
                "model": shoe.model,
                "acquired_date": shoe.acquired_date,
                "initial_km": shoe.initial_km,
                "max_km": shoe.max_km,
                "status": shoe.status,
                "strava_gear_id": shoe.strava_gear_id,
                "created_at": shoe.created_at,
                "current_km": round(current_km, 2),
                "run_count": run_count,
                "last_use": last_use,
                "life_pct": life_pct,
            }
        )
    return result


def calculate_attribution_30d_pct(db: Session, user_id: int) -> float | None:
    """Calcula % de corridas dos últimos 30 dias com tênis associado.

    Returns None se não há corridas na janela (evita 0% enganoso).
    """
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    # Total de corridas nos últimos 30 dias
    total_runs = db.execute(
        select(func.count(Activity.id)).where(
            Activity.user_id == user_id,
            Activity.activity_type.in_(RUNNING_TYPES),
            Activity.start_time >= cutoff,
        )
    ).scalar_one()
    
    if total_runs == 0:
        return None
    
    # Corridas com tênis associado
    runs_with_shoe = db.execute(
        select(func.count(Activity.id)).where(
            Activity.user_id == user_id,
            Activity.activity_type.in_(RUNNING_TYPES),
            Activity.start_time >= cutoff,
            Activity.shoe_id.is_not(None),
        )
    ).scalar_one()
    
    return round((runs_with_shoe / total_runs) * 100, 1)


def _normalize_optional_str(v: str | None) -> str | None:
    """Converte string vazia, 'undefined', 'null' → None."""
    if v is None:
        return None
    s = v.strip()
    if s == "" or s.lower() in ("undefined", "null"):
        return None
    return s


def create_shoe(db: Session, user_id: int, data: dict) -> dict:
    """Cria tênis com validações: name não vazio, initial_km >= 0,
    status in {ativo, aposentado}. user_id explícito (nunca default)."""
    name = data.get("name", "").strip()
    if not name:
        raise ValueError("name: nome é obrigatório")

    initial_km = data.get("initial_km", 0.0)
    if initial_km < 0:
        raise ValueError("initial_km: deve ser >= 0")

    status = data.get("status", "ativo")
    if status not in ("ativo", "aposentado"):
        raise ValueError("status: deve ser 'ativo' ou 'aposentado'")

    shoe = Shoe(
        user_id=user_id,
        name=name,
        brand=_normalize_optional_str(data.get("brand")),
        model=_normalize_optional_str(data.get("model")),
        acquired_date=data.get("acquired_date"),
        initial_km=initial_km,
        max_km=data.get("max_km"),
        status=status,
        strava_gear_id=data.get("strava_gear_id"),
    )
    db.add(shoe)
    db.flush()
    return {
        "id": shoe.id,
        "name": shoe.name,
        "brand": shoe.brand,
        "model": shoe.model,
        "acquired_date": shoe.acquired_date,
        "initial_km": shoe.initial_km,
        "max_km": shoe.max_km,
        "status": shoe.status,
        "strava_gear_id": shoe.strava_gear_id,
        "created_at": shoe.created_at,
        "current_km": shoe.initial_km,
        "run_count": 0,
        "last_use": None,
        "life_pct": None,
    }


def update_shoe(db: Session, user_id: int, shoe_id: int, patch: dict) -> dict | None:
    """Edita tênis do usuário (404 se não existe/é de outro). Campos
    opcionais; validações iguais ao create quando enviados."""
    shoe = db.execute(
        select(Shoe).where(Shoe.id == shoe_id, Shoe.user_id == user_id)
    ).scalar_one_or_none()
    if shoe is None:
        return None

    if "name" in patch:
        name = patch["name"].strip() if patch["name"] is not None else ""
        if not name:
            raise ValueError("name: nome é obrigatório")
        shoe.name = name

    if "brand" in patch:
        shoe.brand = _normalize_optional_str(patch["brand"])

    if "model" in patch:
        shoe.model = _normalize_optional_str(patch["model"])

    if "acquired_date" in patch:
        shoe.acquired_date = patch["acquired_date"]

    if "initial_km" in patch:
        initial_km = patch["initial_km"]
        if initial_km is not None and initial_km < 0:
            raise ValueError("initial_km: deve ser >= 0")
        shoe.initial_km = initial_km if initial_km is not None else 0.0

    if "max_km" in patch:
        shoe.max_km = patch["max_km"]

    if "status" in patch:
        status = patch["status"]
        if status not in ("ativo", "aposentado"):
            raise ValueError("status: deve ser 'ativo' ou 'aposentado'")
        shoe.status = status

    if "strava_gear_id" in patch:
        shoe.strava_gear_id = patch["strava_gear_id"]

    db.flush()
    # Recalcula km derivada para resposta
    sum_distance = db.execute(
        select(func.coalesce(func.sum(Activity.distance_m), 0.0)).where(
            Activity.shoe_id == shoe.id
        )
    ).scalar_one()
    run_count = db.execute(
        select(func.count(Activity.id)).where(Activity.shoe_id == shoe.id)
    ).scalar_one()
    last_use = db.execute(
        select(func.max(Activity.start_time)).where(Activity.shoe_id == shoe.id)
    ).scalar_one()

    current_km = shoe.initial_km + (sum_distance / 1000.0)
    life_pct = None
    if shoe.max_km and shoe.max_km > 0:
        life_pct = round((current_km / shoe.max_km) * 100, 1)

    return {
        "id": shoe.id,
        "name": shoe.name,
        "brand": shoe.brand,
        "model": shoe.model,
        "acquired_date": shoe.acquired_date,
        "initial_km": shoe.initial_km,
        "max_km": shoe.max_km,
        "status": shoe.status,
        "strava_gear_id": shoe.strava_gear_id,
        "created_at": shoe.created_at,
        "current_km": round(current_km, 2),
        "run_count": run_count,
        "last_use": last_use,
        "life_pct": life_pct,
    }


def associate(
    db: Session, user_id: int, activity_id: int, shoe_id: int | None
) -> dict:
    """Associa/desassocia tênis à atividade.

    Validações:
    - Atividade existe e pertence ao usuário → 404 se não
    - Atividade é running/trail_running → 422 se não (code="not_running")
    - Tênis existe e pertence ao usuário → 404 se não (code="shoe_not_found"/"shoe_not_owned")
    - shoe_id=None desassocia (sempre permitido para atividades do usuário)
    """
    activity = db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user_id)
    ).scalar_one_or_none()
    if activity is None:
        raise AssociationError("activity_not_found")

    if activity.activity_type not in RUNNING_TYPES:
        raise AssociationError("not_running")

    if shoe_id is not None:
        shoe = db.execute(
            select(Shoe).where(Shoe.id == shoe_id, Shoe.user_id == user_id)
        ).scalar_one_or_none()
        if shoe is None:
            raise AssociationError("shoe_not_found")

    activity.shoe_id = shoe_id
    db.flush()

    if shoe_id is None:
        return {"shoe": None}

    shoe = db.get(Shoe, shoe_id)
    return {
        "shoe": {
            "id": shoe.id,
            "name": shoe.name,
            "brand": shoe.brand,
            "model": shoe.model,
            "status": shoe.status,
        }
    }