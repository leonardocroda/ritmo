"""Application Service do domínio Garmin — Sync, Import."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.domain.garmin.ports.client import GarminClient, TokenStore
from app.domain.garmin.schemas import SyncJobOut, SyncCreatedOut, LatestJobOut


@dataclass
class SyncService:
    client: GarminClient
    token_store: TokenStore

    async def start_sync(self, user_id: int, window_days: int = 3) -> SyncCreatedOut:
        # Placeholder - implementar sync real
        return SyncCreatedOut(id=1, status="pending")

    def get_latest_job(self, user_id: int) -> LatestJobOut:
        return LatestJobOut(job=None)

    def get_job(self, job_id: int, user_id: int) -> Optional[SyncJobOut]:
        return None