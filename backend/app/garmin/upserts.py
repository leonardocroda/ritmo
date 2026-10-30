"""Escrita idempotente do sync — toda escrita no banco passa por aqui (design).

Cada função faz upsert pela chave natural e não comita: o service
(controla a fronteira de transação por tipo de dado) decide quando
persistir — SYNC-14 exige que nada parcial seja gravado quando o tipo
crítico (atividades) falha. Reexecuções nunca criam duplicatas
(SYNC-11): contagens estáveis 2× (Independent Test do spec).
"""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Activity, PersonalRecord, RacePrediction, Split, SyncState
from app.profile.service import set_metric

_ACTIVITY_FIELDS = (
    "start_time",
    "activity_type",
    "name",
    "distance_m",
    "duration_s",
    "avg_hr",
    "max_hr",
    "avg_cadence",
    "power",
    "elevation_gain_m",
    "aerobic_te",
    "anaerobic_te",
    "training_load",
    "raw_json",
)
_SPLIT_FIELDS = (
    "dist_m",
    "duration_s",
    "pace_s",
    "avg_hr",
    "avg_cadence",
    "avg_temperature",
    "elevation_m",
    "intensity_type",
    # Running dynamics (feature tenis-running-dynamics)
    "ground_contact_time_ms",
    "stride_length_cm",
    "vertical_oscillation_cm",
    "vertical_ratio",
)


def upsert_activity(db: Session, user_id: int, data: dict) -> str:
    """Upsert por (user_id, garmin_id) — SYNC-11. Retorna "new" ou "updated"."""
    activity = db.execute(
        select(Activity).where(
            Activity.user_id == user_id, Activity.garmin_id == data["garmin_id"]
        )
    ).scalar_one_or_none()
    if activity is None:
        db.add(Activity(user_id=user_id, **data))
        db.flush()  # id disponível na sessão para o upsert dos splits
        return "new"
    for field in _ACTIVITY_FIELDS:
        setattr(activity, field, data[field])
    return "updated"


def upsert_splits(db: Session, activity_id: int, rows: list[dict]) -> int:
    """Upsert por (activity_id, idx) + prune de idx >= len(rows) — SYNC-11.

    O prune espelha edições no Garmin que reduzem os laps da corrida.
    Retorna o número de splits gravados.
    """
    db.execute(delete(Split).where(Split.activity_id == activity_id, Split.idx >= len(rows)))
    parent = db.get(Activity, activity_id)
    for row in rows:
        split = db.execute(
            select(Split).where(Split.activity_id == activity_id, Split.idx == row["idx"])
        ).scalar_one_or_none()
        if split is not None:
            for field in _SPLIT_FIELDS:
                setattr(split, field, row.get(field))
            continue
        new_row = dict(row)
        new_row["activity_id"] = activity_id
        if parent is not None:
            new_row["user_id"] = parent.user_id  # toda escrita carrega user_id (AD-001)
        db.add(Split(**new_row))
    return len(rows)


def upsert_health_rows(db: Session, model: type, user_id: int, rows: list[dict]) -> int:
    """Upsert genérico por (user_id, date) — sleep/hrv/rhr/body_battery/stress (SYNC-18)."""
    for row in rows:
        existing = db.execute(
            select(model).where(model.user_id == user_id, model.date == row["date"])
        ).scalar_one_or_none()
        if existing is None:
            db.add(model(user_id=user_id, **row))
        else:
            for field, value in row.items():
                setattr(existing, field, value)
    return len(rows)


def upsert_records(db: Session, user_id: int, rows: list[dict]) -> int:
    """Upsert por (user_id, event) — SYNC-16. Retorna o número de recordes gravados."""
    for row in rows:
        existing = db.execute(
            select(PersonalRecord).where(
                PersonalRecord.user_id == user_id, PersonalRecord.event == row["event"]
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(PersonalRecord(user_id=user_id, **row))
        else:
            for field, value in row.items():
                setattr(existing, field, value)
    return len(rows)


def upsert_race_predictions(db: Session, user_id: int, rows: list[dict]) -> int:
    """Upsert por (user_id, event) — POT-02: snapshot latest, sem delete.

    Evento ausente no payload -> linha existente intocada (mesma
    semântica do `upsert_records`). Retorna o número de predições gravadas.
    """
    for row in rows:
        existing = db.execute(
            select(RacePrediction).where(
                RacePrediction.user_id == user_id, RacePrediction.event == row["event"]
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(RacePrediction(user_id=user_id, **row))
        else:
            for field, value in row.items():
                setattr(existing, field, value)
    return len(rows)


def update_physio_metrics(
    db: Session,
    user_id: int,
    *,
    fcmax: int | None = None,
    fclthr: int | None = None,
    fcrest: int | None = None,
) -> int:
    """Métricas fisiológicas do sync (HRZ-05) — cada valor não-None vira
    uma escrita `set_metric(source="garmin")`; ausente (None) pula a
    métrica sem erro. Idempotência (valor igual), manual-wins e flip de
    posse vivem no `set_metric` (HRZ-03/06/20/21) — a regra não se
    duplica aqui. Retorna o número de linhas NOVAS; não comita (padrão
    do módulo)."""
    created = 0
    for kind, value in (("fcmax", fcmax), ("fclthr", fclthr), ("fcrest", fcrest)):
        if value is None:
            continue
        if set_metric(db, user_id, kind, value, source="garmin"):
            created += 1
    return created


def set_sync_state(db: Session, user_id: int, data_type: str, last_date: date) -> None:
    """Grava o last_date do tipo — memória do incremental (SYNC-13/21)."""
    state = db.execute(
        select(SyncState).where(
            SyncState.user_id == user_id, SyncState.data_type == data_type
        )
    ).scalar_one_or_none()
    if state is None:
        db.add(SyncState(user_id=user_id, data_type=data_type, last_date=last_date))
    else:
        state.last_date = last_date


def get_sync_state(db: Session, user_id: int, data_type: str) -> date | None:
    """Fim da última janela concluída com sucesso do tipo — None se nunca sincronizou."""
    state = db.execute(
        select(SyncState).where(
            SyncState.user_id == user_id, SyncState.data_type == data_type
        )
    ).scalar_one_or_none()
    return state.last_date if state is not None else None
