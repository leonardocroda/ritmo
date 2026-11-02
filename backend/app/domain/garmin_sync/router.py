"""Router da API de domínio Garmin Sync — /api/v1/garmin-sync.

Mesmos códigos de erro do router legado (/api/sync): 201 criado,
409 conflito com o estado do job corrente no detail (SYNC-02) — o
SyncButton espera 409 para apenas atualizar a UI (ERR-13: a primeira
versão deixava o JobConflictError escapar como 500).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import SyncJob, User
from app.domain.garmin_sync.dependencies import get_sync_service
from app.domain.garmin_sync.schemas import SyncCreatedOut, LatestJobOut, SyncJobOut, ConnectionOut
from app.domain.garmin_sync.service import JobConflictError, SyncService

router = APIRouter(prefix="/api/v1/garmin-sync", tags=["garmin-sync"])


@router.post("/sync", status_code=201)
async def start_sync(
    background_tasks: BackgroundTasks,
    user: User = Depends(require_session),
    service: SyncService = Depends(get_sync_service),
) -> SyncCreatedOut:
    try:
        job = await service.start_sync(user.id)
    except JobConflictError as exc:
        active = _active_job(user.id)
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
    background_tasks.add_task(service.run_sync, job.id)
    return job


def _active_job(user_id: int) -> SyncJob:
    """Job ativo corrente (SYNC-02) — para o detail do 409, igual ao legado."""
    from app.db.engine import SessionLocal

    with SessionLocal() as db:
        return (
            db.execute(
                select(SyncJob)
                .where(SyncJob.user_id == user_id, SyncJob.status.in_(("pending", "running")))
                .order_by(SyncJob.id.desc())
                .limit(1)
            )
            .scalar_one()
        )


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
