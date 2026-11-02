"""BFF Service do Home — composição do painel via services de domínio.

Wrapper fino que reutiliza o `get_home` do módulo antigo (ele já orquestra
os serviços de domínio: activities, health, training_load, performance).
"""

from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.home.service import get_home as get_home_legacy


class HomeBFFService:
    """Composição do painel Home via services de domínio."""

    def __init__(self, db: Session):
        self.db = db

    def get_today(self, user_id: int, tz: ZoneInfo) -> dict:
        """Retorna o payload do painel Home para o usuário."""
        return get_home_legacy(self.db, user_id, tz)