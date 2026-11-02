"""Application Service do domínio Shoes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select

from app.domain.equipment.domain.entities import Shoe, ShoeRun, DegradationSignal
from app.domain.equipment.ports.repositories import ShoeRepository
from app.domain.equipment.schemas import (
    ShoeOut, ShoesListOut, ShoeSummaryOut, ShoeCreateIn, ShoeUpdateIn,
    DegradationOut, DegradationSignalOut
)
from app.garmin.mappers import RUNNING_TYPES


@dataclass
class ShoesService:
    repo: ShoeRepository

    def list(self, user_id: int, status: str | None = None) -> ShoesListOut:
        shoes = self.repo.list(user_id, status)
        items = [self._to_shoe_out(s) for s in shoes]
        attribution_30d_pct = self._calculate_attribution_30d_pct(user_id)
        return ShoesListOut(items=items, attribution_30d_pct=attribution_30d_pct)

    def get(self, shoe_id: int, user_id: int) -> Optional[ShoeOut]:
        shoe = self.repo.get_by_id(shoe_id, user_id)
        return self._to_shoe_out(shoe) if shoe else None

    def create(self, user_id: int, data: ShoeCreateIn) -> ShoeOut:
        shoe = Shoe(
            user_id=user_id,
            name=data.name.strip(),
            brand=data.brand,
            model=data.model,
            acquired_date=data.acquired_date,
            initial_km=data.initial_km,
            max_km=data.max_km,
            status=data.status,
            strava_gear_id=data.strava_gear_id,
        )
        created = self.repo.create(shoe)
        return self._to_shoe_out(created)

    def update(self, shoe_id: int, user_id: int, data: ShoeUpdateIn) -> Optional[ShoeOut]:
        shoe = self.repo.get_by_id(shoe_id, user_id)
        if not shoe:
            return None

        if data.name is not None:
            name = data.name.strip() if data.name else ""
            if not name:
                raise ValueError("name: nome é obrigatório")
            shoe.name = name
        if data.brand is not None:
            shoe.brand = data.brand
        if data.model is not None:
            shoe.model = data.model
        if data.acquired_date is not None:
            shoe.acquired_date = data.acquired_date
        if data.initial_km is not None:
            if data.initial_km < 0:
                raise ValueError("initial_km: deve ser >= 0")
            shoe.initial_km = data.initial_km
        if data.max_km is not None:
            shoe.max_km = data.max_km
        if data.status is not None:
            if data.status not in ("ativo", "aposentado"):
                raise ValueError("status: deve ser 'ativo' ou 'aposentado'")
            shoe.status = data.status
        if data.strava_gear_id is not None:
            shoe.strava_gear_id = data.strava_gear_id

        updated = self.repo.update(shoe)
        return self._to_shoe_out(updated)

    def set_activity_shoe(
        self, activity_id: int, user_id: int, shoe_id: Optional[int]
    ) -> Optional[ShoeSummaryOut]:
        return self.repo.set_activity_shoe(activity_id, user_id, shoe_id)

    def get_degradation(self, shoe_id: int, user_id: int) -> Optional[DegradationOut]:
        shoe = self.repo.get_by_id(shoe_id, user_id)
        if not shoe:
            return None

        signals = self.repo.get_degradation(shoe_id)
        if not signals:
            return DegradationOut(
                shoe_id=shoe_id,
                total_km=0,
                n_runs=0,
                signals=[],
                insufficient=True,
            )

        return DegradationOut(
            shoe_id=shoe_id,
            total_km=0,
            n_runs=0,
            signals=[
                DegradationSignalOut(
                    signal=s.signal,
                    label=s.label,
                    initial=s.initial,
                    final=s.final,
                    delta=s.delta,
                    unit=s.unit,
                    direction=s.direction,
                    confidence=s.confidence,
                )
                for s in signals
            ],
        )

    def _calculate_attribution_30d_pct(self, user_id: int) -> Optional[float]:
        return None

    def _to_shoe_out(self, shoe: Shoe) -> ShoeOut:
        return ShoeOut(
            id=shoe.id,
            name=shoe.name,
            brand=shoe.brand,
            model=shoe.model,
            acquired_date=shoe.acquired_date,
            initial_km=shoe.initial_km,
            max_km=shoe.max_km,
            status=shoe.status,
            strava_gear_id=shoe.strava_gear_id,
            created_at=shoe.created_at,
            current_km=0.0,
            run_count=0,
            last_use=None,
            life_pct=None,
        )