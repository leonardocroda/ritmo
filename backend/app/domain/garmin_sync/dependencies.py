"""FastAPI Dependencies para Garmin Sync.

O SyncService usa o gateway legado (`app.garmin.GarminGateway`) — os
placeholders "TokenStore"/"GarminAPIClient" da primeira versão eram
stubs injetados e jamais usados (código morto perigoso, ERR-15) e foram
removidos. Tokens cifrados são tocados exclusivamente por
`app.garmin.tokens_store` (GTDB-13).
"""

from __future__ import annotations

from fastapi import Depends

from app.domain.garmin_sync.service import SyncService


def get_sync_service() -> SyncService:
    return SyncService()
