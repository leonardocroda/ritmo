"""Ponte transitória strangler — rotas /api/v1/tenis/{analysis,degradation}.

ERR-02/ERR-03 (audit-erros.md): o frontend migrou para /api/v1/tenis/...
mas os routers legados seguem em /api/tenis/... — 404 em análise
comparativa e degradação. Em vez de reverter o frontend, re-registramos
os PRÓPRIOS handlers legados sob o prefixo novo (uma única implementação,
zero duplicação). Remover na Fase 2 quando o domínio equipment servir
análise/degradação nativamente (junto com este arquivo e seus includes
no main.py).
"""

from fastapi import APIRouter

from app.tenis_analysis.router import (
    analysis_compare as legacy_analysis_compare,
    analysis_shoe_detail as legacy_analysis_shoe_detail,
    analysis_shoes as legacy_analysis_shoes,
)
from app.tenis_degradation.router import (
    degradation_shoe as legacy_degradation_shoe,
)

tenis_analysis_bridge_router = APIRouter(prefix="/api/v1/tenis/analysis", tags=["equipment"])

tenis_analysis_bridge_router.get("/shoes")(legacy_analysis_shoes)
tenis_analysis_bridge_router.get("/shoes/{shoe_id}")(legacy_analysis_shoe_detail)
tenis_analysis_bridge_router.get("/compare")(legacy_analysis_compare)

tenis_degradation_bridge_router = APIRouter(prefix="/api/v1/tenis/degradation", tags=["equipment"])

tenis_degradation_bridge_router.get("/{shoe_id}")(legacy_degradation_shoe)
