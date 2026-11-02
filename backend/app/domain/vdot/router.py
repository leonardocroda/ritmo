"""Router da API de domínio VDOT — /api/v1/vdot.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): re-expõe
o handler legado `GET /api/profile/pace-zones` (shape PaceZonesOut — o
contrato da tela Zonas de Ritmo). A primeira versão deste router devolvia
o payload do painel Performance (ERR-04: shape errado derrubava a página).
O payload de Performance vive no BFF: /api/v1/bff/performance.
"""

from fastapi import APIRouter

from app.profile.router import get_pace_zones as legacy_get_pace_zones

router = APIRouter(prefix="/api/v1/vdot", tags=["vdot"])

router.get("")(legacy_get_pace_zones)
