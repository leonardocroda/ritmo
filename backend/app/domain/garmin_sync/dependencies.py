"""FastAPI Dependencies para Garmin Sync."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.domain.garmin_sync.ports.client import GarminClient, TokenStore
from app.domain.garmin_sync.service import SyncService


# Placeholder adapters
class SQLAlchemyTokenStore:
    def __init__(self, db: Session): pass
    def get_tokens(self, user_id: int): return None
    def save_tokens(self, user_id: int, tokens: dict): pass
    def delete_tokens(self, user_id: int): pass


class GarminAPIClient:
    def __init__(self, token_store: TokenStore): pass
    async def fetch_activities(self, after): return []
    async def fetch_splits(self, activity_id): return []
    async def fetch_sleep(self, start, end): return []
    async def fetch_hrv(self, start, end): return []
    async def fetch_rhr(self, start, end): return []
    async def fetch_stress(self, start, end): return []


def get_token_store(db: Session = Depends(get_db)) -> TokenStore:
    return SQLAlchemyTokenStore(db)


def get_garmin_client(token_store: TokenStore = Depends(get_token_store)) -> GarminClient:
    return GarminAPIClient(token_store)


def get_sync_service(
    client: GarminClient = Depends(get_garmin_client),
    token_store: TokenStore = Depends(get_token_store),
) -> SyncService:
    return SyncService(client, token_store)