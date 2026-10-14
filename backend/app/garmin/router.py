"""Router do sync — POST cria o job, GETs expõem o estado (SYNC-01/02/05).

A UI lê progresso exclusivamente daqui (polling de 2s no latest), nunca
do Garmin (AD-002). O 409 carrega o estado do job corrente para o
chamador saber o que está rodando.
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.db.models import DEFAULT_USER_ID, SyncJob
from app.garmin.service import JobConflictError, create_job, run_sync

router = APIRouter(prefix="/api/sync")


class JobCreated(BaseModel):
    id: int
    status: str


class JobOut(BaseModel):
    id: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    stats: dict | None


class LatestJob(BaseModel):
    job: JobOut | None


def _job_out(job: SyncJob) -> JobOut:
    return JobOut(
        id=job.id,
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        stats=job.stats_json,
    )


def _active_job(db: Session, user_id: int) -> SyncJob:
    return db.execute(
        select(SyncJob)
        .where(SyncJob.user_id == user_id, SyncJob.status.in_(("pending", "running")))
        .order_by(SyncJob.id.desc())
        .limit(1)
    ).scalar_one()


@router.post("", status_code=status.HTTP_201_CREATED)
def start_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreated:
    """SYNC-01: cria o job pending e agenda o sync em background."""
    try:
        job = create_job(db, DEFAULT_USER_ID)
    except JobConflictError as exc:
        active = _active_job(db, DEFAULT_USER_ID)  # SYNC-02: estado do job corrente
        raise HTTPException(
            status_code=409,
            detail={
                "id": active.id,
                "status": active.status,
                "started_at": (
                    active.started_at.isoformat() if active.started_at is not None else None
                ),
            },
        ) from exc
    background_tasks.add_task(run_sync, job.id)
    return JobCreated(id=job.id, status=job.status)


@router.get("/jobs/latest")
def get_latest_job(db: Session = Depends(get_db)) -> LatestJob:
    """O endpoint que a UI poleia — último job, qualquer status."""
    job = db.execute(
        select(SyncJob)
        .where(SyncJob.user_id == DEFAULT_USER_ID)
        .order_by(SyncJob.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return LatestJob(job=_job_out(job) if job is not None else None)


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    """SYNC-05: stats parciais/finais do job; 404 se inexistente."""
    job = db.get(SyncJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job não encontrado")
    return _job_out(job)
