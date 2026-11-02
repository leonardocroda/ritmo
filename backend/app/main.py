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
from app.bff.health.router import router as bff_health_router
from app.bff.performance.router import router as bff_performance_router
from app.bff.activities.router import router as bff_activities_router
from app.bff.profile.router import router as bff_profile_router
from app.bff.shoes.router import router as bff_shoes_router
from app.domain.equipment.bridge_tenis import (
    tenis_analysis_bridge_router,
    tenis_degradation_bridge_router,
)

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
#
# ERR-14 (audit-erros.md): o include com `dependencies=` é o único mecanismo
# que aplica o require_session no nível do router — o `routes.extend` usado
# na primeira tentativa do refactor DESCARTAVA essas dependências (o que
# só não abriu buraco porque os endpoints antigos repetem a dependência
# inline). Nunca trocar include_router por extend aqui.
app.include_router(auth_router)
app.include_router(sync_router, dependencies=[Depends(require_session)])
app.include_router(activities_router, dependencies=[Depends(require_session)])
app.include_router(evaluation_router, dependencies=[Depends(require_session)])
app.include_router(potential_router, dependencies=[Depends(require_session)])
app.include_router(health_router, dependencies=[Depends(require_session)])
app.include_router(home_router, dependencies=[Depends(require_session)])
app.include_router(profile_router, dependencies=[Depends(require_session)])
app.include_router(shoes_router, dependencies=[Depends(require_session)])
app.include_router(tenis_analysis_router, dependencies=[Depends(require_session)])
app.include_router(tenis_degradation_router, dependencies=[Depends(require_session)])
# Domain API (v1) — organizado por domínio, não por tela
app.include_router(domain_activity_router, dependencies=[Depends(require_session)])
app.include_router(domain_athlete_router, dependencies=[Depends(require_session)])
app.include_router(domain_heart_rate_zones_router, dependencies=[Depends(require_session)])
app.include_router(domain_vdot_router, dependencies=[Depends(require_session)])
app.include_router(domain_training_load_router, dependencies=[Depends(require_session)])
app.include_router(domain_health_metrics_router, dependencies=[Depends(require_session)])
app.include_router(domain_equipment_router, dependencies=[Depends(require_session)])
app.include_router(domain_garmin_sync_router, dependencies=[Depends(require_session)])
app.include_router(domain_ai_evaluation_router, dependencies=[Depends(require_session)])
# Ponte transitória strangler: rotas /api/v1/tenis/{analysis,degradation}
# delegam aos handlers legados até o domínio equipment implementar a
# análise nativamente (Fase 2 do audit-erros.md). Remover junto.
app.include_router(tenis_analysis_bridge_router, dependencies=[Depends(require_session)])
app.include_router(tenis_degradation_bridge_router, dependencies=[Depends(require_session)])
# BFF Composition Layer (v1) — composições de tela
app.include_router(bff_home_router, dependencies=[Depends(require_session)])
app.include_router(bff_health_router, dependencies=[Depends(require_session)])
app.include_router(bff_performance_router, dependencies=[Depends(require_session)])
app.include_router(bff_activities_router, dependencies=[Depends(require_session)])
app.include_router(bff_profile_router, dependencies=[Depends(require_session)])
app.include_router(bff_shoes_router, dependencies=[Depends(require_session)])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
