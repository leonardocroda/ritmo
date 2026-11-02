"""Adaptador SQLAlchemy para ZoneConfigProvider."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import VdotZoneConfig as VdotZoneConfigModel
from app.vdot.zones import ZoneConfig, load_zone_config_from_db as load_vdot_from_db
from app.domain.activity.domain.value_objects import ZoneConfigVO, ZoneKey, HeartRate
from app.domain.activity.ports.zone_config import ZoneConfigProvider


class DBZoneConfigProvider(ZoneConfigProvider):
    """Provedor de configuração de zonas via banco de dados."""

    def __init__(self, session: Session):
        self.session = session
        self._cache: dict[int, ZoneConfigVO] = {}

    def get_for_user(self, user_id: int) -> ZoneConfigVO:
        if user_id in self._cache:
            return self._cache[user_id]

        # Carrega VDOT do banco - usa o modelo diretamente para ter acesso ao vdot
        model = self.session.query(VdotZoneConfigModel).filter(
            VdotZoneConfigModel.user_id == user_id
        ).order_by(VdotZoneConfigModel.valid_from.desc(), VdotZoneConfigModel.id.desc()).first()

        if model is None:
            # Fallback para o loader padrão (levanta ZoneConfigError se não existir)
            vdot_config = load_vdot_from_db(self.session, user_id)
            vo = self._vdot_to_vo(vdot_config, vdot=None)
        else:
            vdot_config = load_vdot_from_db(self.session, user_id)
            vo = self._vdot_to_vo(vdot_config, vdot=model.vdot)

        self._cache[user_id] = vo
        return vo

    def invalidate_cache(self, user_id: int) -> None:
        self._cache.pop(user_id, None)

    def _vdot_to_vo(self, vdot_config: ZoneConfig, vdot: float | None = None) -> ZoneConfigVO:
        """Converte ZoneConfig (VDOT) para ZoneConfigVO (domínio)."""
        pace_zones = {}
        for zone_key_str, zone_data in vdot_config._zones.items():
            zone_key = ZoneKey(zone_key_str)
            pace_range = zone_data.get("pace_range", "")
            # Parse "4:30-5:00" -> (min, max) em s/km
            min_pace, max_pace = self._parse_pace_range(pace_range)
            pace_zones[zone_key] = (min_pace, max_pace)

        hr_zones = {}
        # Se tiver config de HR, converte
        # Por enquanto vazio - HR zones são separadas

        return ZoneConfigVO(
            vdot=vdot or 0.0,
            pace_zones=pace_zones,
            hr_zones=hr_zones,
        )

    def _parse_pace_range(self, pace_range: str) -> tuple[Optional[float], Optional[float]]:
        """Parse '4:30-5:00' -> (min, max) em s/km."""
        if not pace_range or "-" not in pace_range:
            return (None, None)
        try:
            min_str, max_str = pace_range.split("-")
            return (self._parse_pace(min_str), self._parse_pace(max_str))
        except (ValueError, AttributeError):
            return (None, None)

    def _parse_pace(self, pace_str: str) -> Optional[float]:
        """Parse '4:30' -> 270.0."""
        pace_str = pace_str.strip().replace(",", ".")
        if ":" not in pace_str:
            return None
        parts = pace_str.split(":")
        if len(parts) != 2:
            return None
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except ValueError:
            return None