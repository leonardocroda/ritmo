"""Calibração vigente — banco de dados (VdotZoneConfig) como fonte única.

O painel Performance (ex-Potencial) lê o VDOT corrente do banco via
`load_calibration_from_db`. Ausente/inválido -> `ZoneConfigError`.
"""

from dataclasses import dataclass
from datetime import date

from app.vdot.zones import ZoneConfigError


@dataclass(frozen=True)
class Calibration:
    """A calibração vigente: VDOT corrente + o teste que o gerou."""

    vdot: float
    source: str
    test_date: date
    distance_m: float
    time_s: float


def load_calibration_from_db(db, user_id: int) -> Calibration:
    """Carrega a calibração vigente do banco de dados (VdotZoneConfig).

    Levanta ZoneConfigError se não houver configuração para o usuário
    (mesmo comportamento do loader baseado em arquivo).
    """
    # Import local para evitar dependência circular
    from app.db.models import VdotZoneConfig

    config = (
        db.query(VdotZoneConfig)
        .filter(VdotZoneConfig.user_id == user_id)
        .order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc())
        .first()
    )
    if not config:
        raise ZoneConfigError("zonas VDOT não configuradas")

    return Calibration(
        vdot=config.vdot,
        source=config.source,
        test_date=config.test_date,
        distance_m=config.distance_m,
        time_s=config.time_s,
    )
