"""Router do BFF Home — /api/v1/bff/home/today"""

from fastapi import APIRouter, Depends

from app.auth.deps import require_session
from app.bff.home.dependencies import get_home_bff_service
from app.bff.home.schemas import HomeTodayOut
from app.core.tz import app_tz
from app.db.models import User

router = APIRouter(prefix="/api/v1/bff/home", tags=["bff:home"])


@router.get("/today")
def get_home_today(
    user: User = Depends(require_session),
    service: HomeBFFService = Depends(get_home_bff_service),
) -> HomeTodayOut:
    """O dia em um payload: veredito, sinais, strip, roteamento e
    recomendações. Toda leitura filtra pelo usuário da sessão."""
    return HomeTodayOut(**service.get_today(user.id, app_tz()))