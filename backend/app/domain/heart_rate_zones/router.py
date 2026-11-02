"""Router da API de domínio Heart Rate Zones — /api/v1/heart-rate-zones.

FASE DE TRANSIÇÃO (strangler fig — decisão F1 do audit-erros.md): as três
rotas re-registram os handlers legados de `app.profile.router` (que
implementam HRZ-01..22 via `app.profile.service`/`calc`). O domínio novo
(`app/domain/heart_rate_zones/`) tinha update/zonas derivadas como stub
(ERR-11: PUT respondia 200 sem persistir) — assume o router só depois de
passar nos parity tests (Fase 2 do plano).
"""

from fastapi import APIRouter

from app.profile.router import (
    get_hr_zones as legacy_get_hr_zones,
    get_hr_zones_history as legacy_get_hr_zones_history,
    put_hr_zones as legacy_put_hr_zones,
)

router = APIRouter(prefix="/api/v1/heart-rate-zones", tags=["heart-rate-zones"])

router.get("")(legacy_get_hr_zones)
router.put("")(legacy_put_hr_zones)
router.get("/history")(legacy_get_hr_zones_history)
