"""Orquestrador do sync — máquina de estados do SyncJob + fases sequenciais.

Fases em sequência rígida (AD-002: nunca concorrente). Atividades são
tipo crítico: falha após os retries do gateway -> job `error` sem nada
parcial gravado (SYNC-14). Tipos de saúde e recordes falham por tipo:
warning em `stats_json` e o sync segue até `done` (SYNC-20);
`sync_state` só avança em tipo bem-sucedido (SYNC-13/21).
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import (
    Activity,
    BodyBattery,
    DEFAULT_USER_ID,
    Hrv,
    Rhr,
    Sleep,
    Stress,
    SyncJob,
)
from app.garmin.client import (
    GarminAuthExpiredError,
    GarminGateway,
    SyncBudgetExceededError,
)
from app.garmin.mappers import (
    is_running,
    map_activity,
    map_battery,
    map_hrv,
    map_personal_records,
    map_rhr,
    map_sleep,
    map_splits,
    map_stress,
)
from app.garmin.pmc import recompute
from app.garmin.upserts import (
    get_sync_state,
    set_sync_state,
    upsert_activity,
    upsert_health_rows,
    upsert_records,
    upsert_splits,
)


class JobConflictError(Exception):
    """Já existe um job ativo para o usuário (SYNC-02) — o endpoint devolve 409."""


_TRANSITIONS = {"running": "pending", "done": "running", "error": "running"}


def _today() -> date:
    """Hoje no calendário local do container (TZ do compose). Seam de teste."""
    return date.today()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _transition(job: SyncJob, to_status: str) -> None:
    """SYNC-04: pending -> running -> done|error; fora dessa sequência levanta."""
    if job.status != _TRANSITIONS[to_status]:
        raise RuntimeError(f"Transição inválida: {job.status} -> {to_status}")
    job.status = to_status
    if to_status == "running":
        job.started_at = _now()
    else:
        job.finished_at = _now()


def _initial_stats() -> dict:
    """Schema exato do stats_json (design, SYNC-05/06)."""
    return {
        "step": "activities",
        "message": "Iniciando sync…",
        "activities_new": 0,
        "activities_updated": 0,
        "splits": 0,
        "sleep_days": 0,
        "hrv_days": 0,
        "rhr_days": 0,
        "battery_days": 0,
        "stress_days": 0,
        "records": 0,
        "calls_made": 0,
        "duration_s": 0.0,
        "warnings": [],
        "reauth_needed": False,
    }


def _save_stats(db: Session, job: SyncJob, stats: dict) -> None:
    """Persiste o progresso — a UI lê stats_json por polling (SYNC-05)."""
    stats["duration_s"] = (_now() - job.started_at).total_seconds()
    job.stats_json = dict(stats)
    db.commit()


def create_job(db: Session, user_id: int = DEFAULT_USER_ID) -> SyncJob:
    """Cria o job pending; job ativo existente -> JobConflictError (SYNC-02).

    O índice parcial de `sync_jobs` transforma o insert concorrente em
    IntegrityError — sem janela de corrida entre check e insert.
    """
    job = SyncJob(user_id=user_id, status="pending")
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise JobConflictError("Já existe um sync em andamento para o usuário.") from exc
    return job


def _window_start(
    db: Session, user_id: int, data_type: str, backfill_days: int, repull_days: int
) -> date:
    """SYNC-10/15: sem sync_state -> janela de backfill; senão last_date - repull."""
    last = get_sync_state(db, user_id, data_type)
    if last is None:
        return _today() - timedelta(days=backfill_days)
    return last - timedelta(days=repull_days)


def _activity_db_id(db: Session, user_id: int, garmin_id: str) -> int:
    return db.execute(
        select(Activity.id).where(
            Activity.user_id == user_id, Activity.garmin_id == garmin_id
        )
    ).scalar_one()


def _sync_activities(db, gateway, job, stats, user_id, settings) -> date:
    """Fase crítica (SYNC-14): atividades+splits em UMA transação.

    Falha em qualquer ponto -> rollback: nada parcial gravado. O dia
    mais antigo tocado volta para o recompute da PMC (SYNC-23).
    """
    start = _window_start(
        db,
        user_id,
        "activities",
        settings.sync_backfill_activities_days,
        settings.sync_repull_days,
    )
    end = _today()
    raws = gateway.get_activities(start, end)
    stats["step"] = "activities"
    stats["message"] = f"Puxando {len(raws)} {'atividade' if len(raws) == 1 else 'atividades'}…"
    stats["calls_made"] = gateway.calls_made
    _save_stats(db, job, stats)
    try:
        oldest = end
        for raw in raws:
            data = map_activity(raw)
            status = upsert_activity(db, user_id, data)
            if status == "new":
                stats["activities_new"] += 1
            else:
                stats["activities_updated"] += 1
            if is_running(raw):
                splits = map_splits(gateway.get_splits(raw["activityId"]))
                stats["splits"] += upsert_splits(
                    db, _activity_db_id(db, user_id, data["garmin_id"]), splits
                )
            stats["calls_made"] = gateway.calls_made
            oldest = min(oldest, data["start_time"].date())
        set_sync_state(db, user_id, "activities", end)
        db.commit()
    except Exception:
        db.rollback()
        stats["activities_new"] = 0  # nada foi gravado — contadores honestos
        stats["activities_updated"] = 0
        stats["splits"] = 0
        raise
    _save_stats(db, job, stats)
    return oldest


def _sync_daily_health(
    db, gateway, job, stats, user_id, *, data_type, model, getter, mapper, counter, label, settings
) -> None:
    """Tipo por dia (SYNC-18): 1 chamada/dia; dia vazio é pulado (SYNC-19).

    Falha do tipo -> warning e o sync segue (SYNC-20); os dados só são
    gravados no fim, então o rollback deixa o tipo limpo.
    """
    start = _window_start(
        db, user_id, data_type, settings.sync_backfill_health_days, settings.sync_repull_days
    )
    end = _today()
    stats["step"] = data_type
    stats["message"] = f"Puxando {label}…"
    stats["calls_made"] = gateway.calls_made
    _save_stats(db, job, stats)
    rows = []
    try:
        day = start
        while day <= end:
            mapped = mapper(getter(day))  # None -> skip silencioso (SYNC-19)
            if mapped is not None:
                rows.append(mapped)
            stats[counter] = len(rows)
            days_word = "dia" if len(rows) == 1 else "dias"
            stats["message"] = f"Puxando {label}: {len(rows)} {days_word}…"
            stats["calls_made"] = gateway.calls_made
            _save_stats(db, job, stats)
            day += timedelta(days=1)
        upsert_health_rows(db, model, user_id, rows)
        set_sync_state(db, user_id, data_type, end)
        db.commit()
    except (GarminAuthExpiredError, SyncBudgetExceededError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        stats[counter] = 0  # o tipo não gravou nada
        stats["warnings"].append({"tipo": data_type, "erro": str(exc)})
        _save_stats(db, job, stats)


def _sync_battery(db, gateway, job, stats, user_id, settings) -> None:
    """Body battery (SYNC-18): 1 chamada de range para a janela toda."""
    start = _window_start(
        db, user_id, "body_battery", settings.sync_backfill_health_days, settings.sync_repull_days
    )
    end = _today()
    stats["step"] = "body_battery"
    stats["message"] = "Puxando body battery…"
    stats["calls_made"] = gateway.calls_made
    _save_stats(db, job, stats)
    try:
        rows = map_battery(gateway.get_body_battery(start, end))
        upsert_health_rows(db, BodyBattery, user_id, rows)
        stats["battery_days"] = len(rows)
        set_sync_state(db, user_id, "body_battery", end)
        stats["calls_made"] = gateway.calls_made
        db.commit()
    except (GarminAuthExpiredError, SyncBudgetExceededError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        stats["battery_days"] = 0
        stats["warnings"].append({"tipo": "body_battery", "erro": str(exc)})
        stats["calls_made"] = gateway.calls_made
        _save_stats(db, job, stats)


def _sync_records(db, gateway, job, stats, user_id) -> None:
    """Recordes (SYNC-16): todo sync, independente de janela de datas."""
    stats["step"] = "records"
    stats["message"] = "Puxando recordes…"
    stats["calls_made"] = gateway.calls_made
    _save_stats(db, job, stats)
    try:
        rows = map_personal_records(gateway.get_personal_records())
        upsert_records(db, user_id, rows)
        stats["records"] = len(rows)
        stats["calls_made"] = gateway.calls_made
        db.commit()
    except (GarminAuthExpiredError, SyncBudgetExceededError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        stats["records"] = 0
        stats["warnings"].append({"tipo": "records", "erro": str(exc)})
        stats["calls_made"] = gateway.calls_made
        _save_stats(db, job, stats)


def _sync_pmc(db, job, stats, user_id, oldest: date) -> None:
    """PMC (SYNC-22/23): recompute só da janela afetada — zero chamadas extras."""
    stats["step"] = "pmc"
    stats["message"] = "Recalculando carga…"
    _save_stats(db, job, stats)
    recompute(db, user_id, oldest, _today())
    db.commit()


def _finish(db, job, stats, status, error_text=None) -> None:
    """Fim do job: done|error gravando finished_at (SYNC-04)."""
    if error_text is not None:
        stats["message"] = error_text
        job.error = error_text
    _transition(job, status)
    _save_stats(db, job, stats)


def run_sync(job_id: int) -> None:
    """Entrada do BackgroundTasks: pending -> running -> fases -> done|error."""
    settings = get_settings()
    with SessionLocal() as db:
        job = db.get(SyncJob, job_id)
        stats = _initial_stats()
        _transition(job, "running")
        _save_stats(db, job, stats)
        gateway = None
        try:
            gateway = GarminGateway.from_settings()
            user_id = job.user_id
            oldest = _sync_activities(db, gateway, job, stats, user_id, settings)
            _sync_daily_health(
                db, gateway, job, stats, user_id,
                data_type="sleep", model=Sleep, getter=gateway.get_sleep,
                mapper=map_sleep, counter="sleep_days", label="sono", settings=settings,
            )
            _sync_daily_health(
                db, gateway, job, stats, user_id,
                data_type="hrv", model=Hrv, getter=gateway.get_hrv,
                mapper=map_hrv, counter="hrv_days", label="HRV", settings=settings,
            )
            _sync_daily_health(
                db, gateway, job, stats, user_id,
                data_type="rhr", model=Rhr, getter=gateway.get_rhr,
                mapper=map_rhr, counter="rhr_days", label="RHR", settings=settings,
            )
            _sync_daily_health(
                db, gateway, job, stats, user_id,
                data_type="stress", model=Stress, getter=gateway.get_stress,
                mapper=map_stress, counter="stress_days", label="stress", settings=settings,
            )
            _sync_battery(db, gateway, job, stats, user_id, settings)
            _sync_records(db, gateway, job, stats, user_id)
            _sync_pmc(db, job, stats, user_id, oldest)
            stats["message"] = "Sync concluído."
            _finish(db, job, stats, "done")
        except GarminAuthExpiredError as exc:
            db.rollback()
            stats["reauth_needed"] = True  # SYNC-25: estado "Reconectar Garmin"
            if gateway is not None:
                stats["calls_made"] = gateway.calls_made
            _finish(db, job, stats, "error", error_text=str(exc))
        except Exception as exc:
            db.rollback()
            if gateway is not None:
                stats["calls_made"] = gateway.calls_made
            _finish(db, job, stats, "error", error_text=str(exc))
