"""BFF Service do Activities — composição da tela Treinos.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): delega
ao service legado `app.activities.service` (implementação completa:
inferred_type por splits, zonas por velocidade, consistência, contexto,
avaliações). A primeira versão deste BFF apontava para o domínio novo
inacabado — ERR-06..10 do audit-erros.md. O domínio
`app/domain/activity/` assume quando passar nos parity tests.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.activities import service as activities_service
from app.activities.router import ActivityDetailOut, ActivityListOut
from app.vdot.zones import ZoneConfig, load_zone_config_from_db


class ActivitiesBFFService:
    """Composição da tela Treinos via service legado."""

    def __init__(self, db: Session):
        self.db = db

    def list_activities(
        self, user_id: int, activity_type: str, limit: int, offset: int
    ) -> ActivityListOut:
        zone_config = self._zone_config(user_id)
        data = activities_service.list_activities(
            self.db, user_id, activity_type, limit, offset, zone_config
        )
        return ActivityListOut(**data)

    def get_detail(self, activity_id: int, user_id: int) -> ActivityDetailOut | None:
        zone_config = self._zone_config(user_id)
        return activities_service.get_activity_detail(
            self.db, activity_id, user_id, zone_config
        )

    def _zone_config(self, user_id: int) -> ZoneConfig:
        """Mesmo contrato do legado: sem config -> 500 zonas VDOT não configuradas."""
        return load_zone_config_from_db(self.db, user_id)
