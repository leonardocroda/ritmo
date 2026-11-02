"""Adaptador SQLAlchemy para ShoeRepository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Shoe as ShoeModel
from app.domain.equipment.domain.entities import Shoe, ShoeRun, DegradationSignal
from app.domain.equipment.ports.repositories import ShoeRepository


class SQLAlchemyShoeRepository(ShoeRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, shoe_id: int, user_id: int) -> Shoe | None:
        model = self.session.execute(
            select(ShoeModel).where(
                ShoeModel.id == shoe_id, ShoeModel.user_id == user_id
            )
        ).scalars().first()
        return self._to_shoe(model) if model else None

    def list(self, user_id: int, status: str | None = None) -> Sequence[Shoe]:
        query = select(ShoeModel).where(ShoeModel.user_id == user_id)
        if status:
            query = query.where(ShoeModel.status == status)
        models = self.session.execute(query.order_by(ShoeModel.created_at.desc())).scalars().all()
        return [self._to_shoe(m) for m in models]

    def save(self, shoe: Shoe) -> Shoe:
        # Placeholder
        return shoe

    def delete(self, shoe_id: int, user_id: int) -> bool:
        model = self.session.execute(
            select(ShoeModel).where(
                ShoeModel.id == shoe_id, ShoeModel.user_id == user_id
            )
        ).scalars().first()
        if model:
            self.session.delete(model)
            return True
        return False

    def get_runs(self, shoe_id: int) -> Sequence[ShoeRun]:
        # Placeholder
        return []

    def get_degradation(self, shoe_id: int) -> tuple[DegradationSignal, ...] | None:
        # Placeholder
        return None

    def _to_shoe(self, m) -> Shoe:
        return Shoe(
            id=m.id,
            user_id=m.user_id,
            name=m.name,
            brand=m.brand,
            model=m.model,
            acquired_date=m.acquired_date,
            initial_km=m.initial_km,
            max_km=m.max_km,
            status=m.status,
            strava_gear_id=m.strava_gear_id,
            created_at=m.created_at,
        )