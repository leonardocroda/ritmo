"""Endpoint de leitura de alerta de degradação por tênis.

Tudo leitura pura do banco (AD-002), zero Garmin. Isolamento por user_id.
O corpo vive em `service.degradation_payload` — o mesmo payload é servido
pela ponte /api/v1/tenis/degradation e pela BFF shoes (uma única
implementação, ERR-03/ERR-12).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_session
from app.db.engine import get_db
from app.db.models import User
from app.tenis_degradation.service import degradation_payload

router = APIRouter(prefix="/api/tenis/degradation")


@router.get("/{shoe_id}")
def degradation_shoe(
    shoe_id: int,
    user: User = Depends(require_session),
    db: Session = Depends(get_db),
) -> dict:
    """Sinais de degradação de um tênis (baseline ~100 km vs ~50 km)."""
    return degradation_payload(db, user.id, shoe_id)
