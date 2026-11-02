"""Router da API de domínio Health Metrics — /api/v1/health-metrics.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md):
/summary re-registra o handler do BFF health (que delega ao service
legado `app.health.service` — implementação completa e testada). A
primeira versão usava uma re-implementação nova sem testes. O endpoint
/signals foi removido: não tinha implementação provada nem consumidor
(a Home compõe sinais no BFF home).
"""

from fastapi import APIRouter

from app.bff.health.router import get_health_summary as legacy_bff_health_summary

router = APIRouter(prefix="/api/v1/health-metrics", tags=["health-metrics"])

router.get("/summary")(legacy_bff_health_summary)
