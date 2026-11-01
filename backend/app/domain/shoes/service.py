"""Application Service do domínio Shoes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

from app.domain.shoes.domain.entities import Shoe, ShoeRun, DegradationSignal
from app.domain.shoes.ports.repositories import ShoeRepository
from app.domain.shoes.schemas import (
    ShoeOut, ShoesListOut, ShoeSummaryOut, ShoeCreateIn, ShoeUpdateIn,
    DegradationOut, DegradationSignalOut
)


@dataclass
class ShoesService:
    repo: ShoeRepository

    def list(self, user_id: int, status: str | None = None) -> ShoesListOut:
        shoes = self.repo.list(user_id, status)
        items = [self._to_shoe_out(s) for s in shoes]
        return ShoesListOut(items=items, attribution_30d_pct=None)

    def get(self, shoe_id: int, user_id: int) -> Optional[ShoeOut]:
        shoe = self.repo.get_by_id(shoe_id, user_id)
        return self._to_shoe_out(shoe) if shoe else None

    def create(self, user_id: int, data: ShoeCreateIn) -> ShoeOut:
        # Placeholder - implementar criação real
        raise NotImplementedError

    def update(self, shoe_id: int, user_id: int, data: ShoeUpdateIn) -> Optional[ShoeOut]:
        # Placeholder
        raise NotImplementedError

    def delete(self, shoe_id: int, user_id: int) -> bool:
        return self.repo.delete(shoe_id, user_id)

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
            total_km=0,  # calcular
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
            current_km=0.0,  # calcular
            run_count=0,
            last_use=None,
            life_pct=None,
        )