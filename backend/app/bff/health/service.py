"""BFF Service do Health — composição do painel via services de domínio.

Wrapper fino que reutiliza o `get_health` do módulo antigo.
"""

from datetime import date
from zoneinfo import ZoneInfo
from typing import Optional

from sqlalchemy.orm import Session

from app.health.service import get_health as get_health_legacy


class HealthBFFService:
    """Composição do painel Health via services de domínio."""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self, user_id: int, days: int, tz: ZoneInfo
    ) -> dict:
        """Retorna o payload do painel Health para o usuário."""
        return get_health_legacy(self.db, user_id, days, tz)