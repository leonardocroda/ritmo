"""Router da API de domínio Activity — /api/v1/activities.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): este
router DELEGA aos handlers legados de `app.activities` e `app.evaluation`,
que são a implementação completa e provada. O domínio novo
(`app/domain/activity/`) assume este router quando passar nos parity
tests (Fase 2/4 do plano) — até lá, nenhuma tela depende dele.

Trocar a delegação por `Depends(get_activity_service)` ANTES de o
domínio ter paridade com o legado foi exatamente o erro que gerou
os ERR-06..10 do audit.
"""

from fastapi import APIRouter, Depends  # noqa: F401 (Depends documenta o contrato)

from app.activities.router import (
    get_activity as legacy_get_activity,
    list_activities as legacy_list_activities,
)
from app.evaluation.router import (
    evaluate_activity as legacy_evaluate_activity,
    get_evaluation_status as legacy_get_evaluation_status,
)
from app.auth.deps import require_session  # noqa: F401 (documenta o contrato)

router = APIRouter(prefix="/api/v1/activities", tags=["activity"])

# Lista + detalhe: mesma implementação do /api/activities legado.
router.get("")(legacy_list_activities)
router.get("/{activity_id}")(legacy_get_activity)

# Avaliar com IA (ERR-01): mesmos handlers do router legado
# (/api/activities/{id}/evaluate), agora também em /api/v1 — a URL que
# o frontend já chama. 201 pending + polling no GET.
router.post("/{activity_id}/evaluate", status_code=201)(legacy_evaluate_activity)
router.get("/{activity_id}/evaluate/{evaluation_id}")(legacy_get_evaluation_status)
