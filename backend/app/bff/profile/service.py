"""BFF Service do Profile — composição de tela Perfil via services de domínio.

Reutiliza a lógica do módulo profile antigo para zonas de ritmo (VDOT).
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.heart_rate_zones.dependencies import get_hr_zones_service
from app.domain.heart_rate_zones.schemas import HRZonesOut as DomainHRZonesOut
from app.domain.heart_rate_zones.service import HeartRateZonesService
from app.domain.vdot.dependencies import get_vdot_service
from app.domain.vdot.schemas import VDOTOut
from app.domain.vdot.service import VDOTService
from app.profile import calc, service as profile_service
from app.db.models import VdotZoneConfig


class ProfileBFFService:
    """Composição da tela Perfil via services de domínio."""

    def __init__(
        self,
        hr_zones_service: HeartRateZonesService,
        vdot_service: VDOTService,
        db: Session,
    ):
        self.hr_zones_service = hr_zones_service
        self.vdot_service = vdot_service
        self.db = db

    def get_zones(self, user_id: int) -> dict:
        """Retorna zonas FC + zonas ritmo para o usuário."""
        hr_zones = self.hr_zones_service.get_hr_zones(user_id)
        pace_zones = self._get_pace_zones(user_id)
        return {
            "hr_zones": hr_zones.model_dump(),
            "pace_zones": pace_zones,
        }

    def _get_pace_zones(self, user_id: int) -> dict:
        """Obtém zonas de ritmo no formato legado (PaceZonesOut)."""
        config = (
            self.db.query(VdotZoneConfig)
            .filter(VdotZoneConfig.user_id == user_id)
            .order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc())
            .first()
        )
        if config is None:
            raise ValueError("zonas VDOT não configuradas")

        zones_with_key = {}
        for key, zone in config.zones.items():
            zone_copy = dict(zone)
            zone_copy["key"] = key
            zones_with_key[key] = zone_copy

        return {
            "vdot": config.vdot,
            "source": config.source,
            "test_date": config.test_date,
            "distancia_metros": config.distance_m,
            "tempo_segundos": config.time_s,
            "zones": zones_with_key,
            "equivalencias": config.equivalencias,
        }