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
from app.domain.activity.router import router as domain_activity_router
from app.domain.ai_evaluation.router import router as domain_ai_evaluation_router
from app.domain.athlete.router import router as domain_athlete_router
from app.domain.equipment.router import router as domain_equipment_router
from app.domain.garmin_sync.router import router as domain_garmin_sync_router
from app.domain.heart_rate_zones.router import router as domain_heart_rate_zones_router
from app.domain.training_load.router import router as domain_training_load_router
from app.domain.vdot.router import router as domain_vdot_router
from app.domain.health_metrics.router import router as domain_health_metrics_router
from app.evaluation.router import router as evaluation_router
from app.evaluation.service import recover_stale_evaluations
from app.garmin.router import router as sync_router
from app.garmin.service import recover_stale_jobs
from app.garmin.tokens_store import require_key
from app.health.router import router as health_router
from app.home.router import router as home_router
from app.potential.router import router as potential_router
from app.profile.router import router as profile_router
from app.shoes.router import router as shoes_router
from app.tenis_analysis.router import router as tenis_analysis_router
from app.tenis_degradation.router import router as tenis_degradation_router
from app.bff.home.router import router as bff_home_router

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
# FastAPI 0.162+: include_router doesn't work, use router.routes.extend
all_routers = [
    auth_router,
    (sync_router, [Depends(require_session)]),
    (activities_router, [Depends(require_session)]),
    (evaluation_router, [Depends(require_session)]),
    (potential_router, [Depends(require_session)]),
    (health_router, [Depends(require_session)]),
    (home_router, [Depends(require_session)]),
    (profile_router, [Depends(require_session)]),
    (shoes_router, [Depends(require_session)]),
    (tenis_analysis_router, [Depends(require_session)]),
    (tenis_degradation_router, [Depends(require_session)]),
    # Domain API (v1) — organizado por domínio, não por tela
    (domain_activity_router, [Depends(require_session)]),
    (domain_athlete_router, [Depends(require_session)]),
    (domain_heart_rate_zones_router, [Depends(require_session)]),
    (domain_vdot_router, [Depends(require_session)]),
    (domain_training_load_router, [Depends(require_session)]),
    (domain_health_metrics_router, [Depends(require_session)]),
    (domain_equipment_router, [Depends(require_session)]),
    (domain_garmin_sync_router, [Depends(require_session)]),
    (domain_ai_evaluation_router, [Depends(require_session)]),
    # BFF Composition Layer (v1) — composições de tela
    (bff_home_router, [Depends(require_session)]),
]

for item in all_routers:
    if isinstance(item, tuple):
        router, deps = item
        # Note: dependencies via extend doesn't apply Depends - need middleware or route-level
        app.router.routes.extend(router.routes)
    else:
        app.router.routes.extend(item.routes)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
