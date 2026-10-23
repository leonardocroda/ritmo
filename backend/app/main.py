"""Ritmo API — entrypoint FastAPI.

Fase 0: health check + criação do schema + usuário default.
As features da Fase 1 (sync Garmin, painéis, avaliação IA) entram pelo
workflow spec-driven (.opencode/skills/tlc-spec-driven): uma feature,
um spec validado, tasks atômicas, commits atômicos.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.activities.router import router as activities_router
from app.auth.deps import require_session
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.db.engine import init_db
from app.evaluation.router import router as evaluation_router
from app.evaluation.service import recover_stale_evaluations
from app.garmin.router import router as sync_router
from app.garmin.service import recover_stale_jobs
from app.garmin.tokens_store import require_key
from app.health.router import router as health_router
from app.home.router import router as home_router
from app.potential.router import router as potential_router
from app.profile.router import router as profile_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # GTDB-14: fail-fast ANTES de tudo — sem a chave é impossível ler
    # tokens nem garantir criptografia em repouso (AD-014)
    require_key(get_settings())
    init_db()
    recover_stale_jobs()  # SYNC-02: nenhum 409 eterno após restart
    recover_stale_evaluations()  # EVAL-24: pending órfãs viram error "interrompida"
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    description="Plataforma pessoal de corrida — sync Garmin + avaliação de treino com IA.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth (feature auth): os endpoints de auth são públicos; os routers de
# dado exigem sessão (AUTH-11) — explícito por include, o mapa do que é
# público vive neste arquivo (design). /api/health (liveness, definida
# mais abaixo) fica fora da proteção.
app.include_router(auth_router)
app.include_router(sync_router, dependencies=[Depends(require_session)])
app.include_router(activities_router, dependencies=[Depends(require_session)])
app.include_router(evaluation_router, dependencies=[Depends(require_session)])
app.include_router(potential_router, dependencies=[Depends(require_session)])
app.include_router(health_router, dependencies=[Depends(require_session)])
app.include_router(home_router, dependencies=[Depends(require_session)])
app.include_router(profile_router, dependencies=[Depends(require_session)])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
