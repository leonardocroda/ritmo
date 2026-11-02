"""Garmin Sync domain package.

FASE DE TRANSIÇÃO: o SyncService orquestra o sync completo usando o
gateway legado (`app.garmin.GarminGateway`). Os stubs TokenStore /
GarminAPIClient da primeira versão foram removidos (ERR-15 do
audit-erros.md) — tokens cifrados são tocados exclusivamente por
`app.garmin.tokens_store` (GTDB-13).
"""

from app.domain.garmin_sync.domain.entities import GarminActivity, GarminSleep, GarminHRV, SyncStatus
from app.domain.garmin_sync.service import SyncService
from app.domain.garmin_sync.dependencies import get_sync_service
from app.domain.garmin_sync.schemas import SyncJobOut, SyncCreatedOut, LatestJobOut
from app.domain.garmin_sync.router import router

__all__ = [
    "GarminActivity", "GarminSleep", "GarminHRV", "SyncStatus",
    "SyncService",
    "get_sync_service",
    "SyncJobOut", "SyncCreatedOut", "LatestJobOut",
    "router",
]
