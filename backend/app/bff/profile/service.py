"""BFF Service do Profile — composição de tela Perfil via services de domínio.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): delega
aos builders de payload do router legado `app.profile` (HRZ-01..22 +
PaceZonesOut), que são a implementação completa. A versão anterior
montava zonas FC com o service de domínio stub (zonas derivadas sempre
null — ERR-11 no contexto do BFF).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.profile.router import hr_zones_payload, pace_zones_payload


class ProfileBFFService:
    """Composição da tela Perfil via builders legados."""

    def __init__(self, db: Session):
        self.db = db

    def get_zones(self, user_id: int) -> dict:
        """Retorna zonas FC + zonas ritmo para o usuário."""
        return {
            "hr_zones": hr_zones_payload(self.db, user_id).model_dump(mode="json"),
            "pace_zones": pace_zones_payload(self.db, user_id).model_dump(mode="json"),
        }
