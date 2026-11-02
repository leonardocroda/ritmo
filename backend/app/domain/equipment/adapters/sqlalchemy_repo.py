"""Adaptador SQLAlchemy para ShoeRepository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Activity, Shoe as ShoeModel
from app.domain.equipment.domain.entities import Shoe, ShoeRun, DegradationSignal
from app.domain.equipment.ports.repositories import ShoeRepository
from app.garmin.mappers import RUNNING_TYPES


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

    def create(self, shoe: Shoe) -> Shoe:
        model = ShoeModel(
            user_id=shoe.user_id,
            name=shoe.name,
            brand=shoe.brand,
            model=shoe.model,
            acquired_date=shoe.acquired_date,
            initial_km=shoe.initial_km,
            max_km=shoe.max_km,
            status=shoe.status,
            strava_gear_id=shoe.strava_gear_id,
        )
        self.session.add(model)
        self.session.flush()
        return self._to_shoe(model)

    def update(self, shoe: Shoe) -> Shoe:
        model = self.session.execute(
            select(ShoeModel).where(
                ShoeModel.id == shoe.id, ShoeModel.user_id == shoe.user_id
            )
        ).scalars().first()
        if not model:
            raise ValueError("Shoe not found")
        
        model.name = shoe.name
        model.brand = shoe.brand
        model.model = shoe.model
        model.acquired_date = shoe.acquired_date
        model.initial_km = shoe.initial_km
        model.max_km = shoe.max_km
        model.status = shoe.status
        model.strava_gear_id = shoe.strava_gear_id
        
        self.session.flush()
        return self._to_shoe(model)

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
        return []

    def get_degradation(self, shoe_id: int) -> tuple[DegradationSignal, ...] | None:
        return None

    def set_activity_shoe(
        self, activity_id: int, user_id: int, shoe_id: Optional[int]
    ) -> Optional[Shoe]:
        activity = self.session.execute(
            select(Activity).where(
                Activity.id == activity_id, Activity.user_id == user_id
            )
        ).scalars().first()
        if not activity:
            return None

        if activity.activity_type not in RUNNING_TYPES:
            return None

        if shoe_id is not None:
            shoe = self.session.execute(
                select(ShoeModel).where(
                    ShoeModel.id == shoe_id, ShoeModel.user_id == user_id
                )
            ).scalars().first()
            if not shoe:
                return None

        activity.shoe_id = shoe_id
        self.session.flush()

        if shoe_id is None:
            return None

        shoe = self.session.get(ShoeModel, shoe_id)
        return Shoe(
            id=shoe.id,
            user_id=shoe.user_id,
            name=shoe.name,
            brand=shoe.brand,
            model=shoe.model,
            acquired_date=shoe.acquired_date,
            initial_km=shoe.initial_km,
            max_km=shoe.max_km,
            status=shoe.status,
            strava_gear_id=shoe.strava_gear_id,
            created_at=shoe.created_at,
        )

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