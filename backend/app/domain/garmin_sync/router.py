"""Router da API de domínio Garmin Sync — /api/v1/garmin-sync"""

from __future__ import annotations

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import User
from app.domain.garmin_sync.dependencies import get_sync_service
from app.domain.garmin_sync.service import SyncService
from app.domain.garmin_sync.schemas import SyncCreatedOut, LatestJobOut, SyncJobOut, ConnectionOut

router = APIRouter(prefix="/api/v1/garmin-sync", tags=["garmin-sync"])


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


@router.get("/status")
def get_connection_status(
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> ConnectionOut:
    """Estado da conexão Garmin do usuário da sessão (GTDB-16):
    Conectado, Reautenticação necessária ou Não conectado — só exibição,
    o re-login é CLI do operador. A derivação pura (3 estados) vive no
    service; a resposta carrega apenas metadados (GTDB-17)."""
    from app.profile.service import garmin_connection
    state, tokens_updated_at = garmin_connection(db, user.id)
    return ConnectionOut(
        state=state,
        tokens_updated_at=tokens_updated_at.isoformat() if tokens_updated_at else None,
    )