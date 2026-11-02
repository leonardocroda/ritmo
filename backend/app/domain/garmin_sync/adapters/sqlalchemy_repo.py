"""Adaptadores SQLAlchemy para repositórios do domínio Garmin Sync."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import GarminToken
from app.domain.garmin_sync.ports.client import TokenStore, GarminClient


class SQLAlchemyTokenStore(TokenStore):
    def __init__(self, session: Session):
        self.session = session

    def get_tokens(self, user_id: int) -> dict | None:
        model = self.session.query(GarminToken).filter(GarminToken.user_id == user_id).first()
        if model:
            # Deserializar tokens do banco
            return {"access_token": model.token_encrypted}  # Simplificado
        return None

    def save_tokens(self, user_id: int, tokens: dict) -> None:
        model = self.session.query(GarminToken).filter(GarminToken.user_id == user_id).first()
        if not model:
            model = GarminToken(user_id=user_id)
            self.session.add(model)
        model.token_encrypted = tokens.get("access_token", "")
        self.session.commit()

    def delete_tokens(self, user_id: int) -> None:
        model = self.session.query(GarminToken).filter(GarminToken.user_id == user_id).first()
        if model:
            self.session.delete(model)
            self.session.commit()


class GarminAPIClient:
    def __init__(self, token_store: TokenStore):
        self.token_store = token_store

    async def fetch_activities(self, after):
        return []

    async def fetch_splits(self, activity_id):
        return []

    async def fetch_sleep(self, start, end):
        return []

    async def fetch_hrv(self, start, end):
        return []

    async def fetch_rhr(self, start, end):
        return []

    async def fetch_stress(self, start, end):
        return []