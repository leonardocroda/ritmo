"""Router do BFF Profile — /api/v1/bff/profile/zones"""

from fastapi import APIRouter, Depends

from app.auth.deps import require_session
from app.bff.profile.dependencies import get_profile_bff_service
from app.bff.profile.schemas import ProfileZonesOut
from app.bff.profile.service import ProfileBFFService
from app.db.models import User

router = APIRouter(prefix="/api/v1/bff/profile", tags=["bff:profile"])


@router.get("/zones")
def get_profile_zones(
    user: User = Depends(require_session),
    service: ProfileBFFService = Depends(get_profile_bff_service),
) -> ProfileZonesOut:
    """Composição: Zonas FC + Zonas Ritmo em 1 payload para /perfil."""
    return ProfileZonesOut(**service.get_zones(user.id))