"""Router do BFF Performance — /api/v1/bff/performance"""

from fastapi import APIRouter, Depends

from app.auth.deps import require_session
from app.bff.performance.dependencies import get_performance_bff_service
from app.bff.performance.schemas import PerformanceOut
from app.db.models import User

router = APIRouter(prefix="/api/v1/bff/performance", tags=["bff:performance"])


@router.get("")
def get_performance(
    user: User = Depends(require_session),
    service: PerformanceBFFService = Depends(get_performance_bff_service),
) -> PerformanceOut:
    """O painel inteiro em 1 payload — os 5 blocos, com o `pmc` de
    volta (AD-017 reverte a CLR-03).

    Query param não declarado é ignorado: 200 sem efeito no payload.
    O carregamento da calibração acontece no corpo do handler —
    banco sem config -> 500 "zonas VDOT não configuradas".
    Toda leitura filtra pelo usuário da sessão (user-scope)."""
    return PerformanceOut(**service.get_summary(user.id))