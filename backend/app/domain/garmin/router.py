"""Router da API de domínio Garmin — /api/v1/garmin"""

from __future__ import annotations

from fastapi import APIRouter, Depends, BackgroundTasks

from app.auth.deps import require_session
from app.db.models import User
from app.domain.garmin.dependencies import get_sync_service
from app.domain.garmin.service import SyncService
from app.domain.garmin.schemas import SyncCreatedOut, LatestJobOut, SyncJobOut

router = APIRouter(prefix="/api/v1/garmin", tags=["garmin"])


@router.post("/sync", status_code=201)
async def start_sync(
    background_tasks: BackgroundTasks,
    window_days: int = 3,
    user: User = Depends(require_session),
    service: SyncService = Depends(get_sync_service),
) -> SyncCreatedOut:
    job = await service.start_sync(user.id, window_days)
    background_tasks.add_task(service.run_sync, job.id)
    return job


@router.get("/sync/jobs/latest")
def get_latest_job(
    user: User = Depends(require_session),
    service: SyncService = Depends(get_sync_service),
) -> LatestJobOut:
    return service.get_latest_job(user.id)


@router.get("/sync/jobs/{job_id}")
def get_job(
    job_id: int,
    user: User = Depends(require_session),
    service: SyncService = Depends(get_sync_service),
) -> SyncJobOut:
    job = service.get_job(job_id, user.id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(404, "job não encontrado")
    return job