"""Ritmo API — entrypoint FastAPI.

Fase 0: health check + criação do schema + usuário default.
As features da Fase 1 (sync Garmin, painéis, avaliação IA) entram pelo
workflow spec-driven (.opencode/skills/tlc-spec-driven): uma feature,
um spec validado, tasks atômicas, commits atômicos.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.activities.router import router as activities_router
from app.core.config import get_settings
from app.db.engine import init_db
from app.garmin.router import router as sync_router
from app.garmin.service import recover_stale_jobs
from app.health.router import router as health_router
from app.potential.router import router as potential_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    recover_stale_jobs()  # SYNC-02: nenhum 409 eterno após restart
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

app.include_router(sync_router)
app.include_router(activities_router)
app.include_router(potential_router)
app.include_router(health_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
