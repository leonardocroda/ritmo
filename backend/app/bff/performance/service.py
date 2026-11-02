"""BFF Service do Performance — composição do painel via services de domínio.

Wrapper fino que reutiliza o `get_potential` do módulo antigo.
"""

from datetime import date
from zoneinfo import ZoneInfo
from typing import Optional

from sqlalchemy.orm import Session

from app.potential.service import get_potential as get_potential_legacy
from app.vdot.calibration import load_calibration_from_db
from app.vdot.zones import ZoneConfigError
from fastapi import HTTPException


class PerformanceBFFService:
    """Composição do painel Performance via services de domínio."""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, user_id: int) -> dict:
        """Retorna o payload do painel Performance para o usuário."""
        try:
            calibration = load_calibration_from_db(self.db, user_id)
        except ZoneConfigError as exc:
            raise HTTPException(
                status_code=500, detail="zonas VDOT não configuradas"
            ) from exc
        return get_potential_legacy(self.db, user_id, calibration)