"""Value Objects do domínio Shoes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True, slots=True)
class KM:
    """Quilometragem — value object."""

    value: float

    def __add__(self, other: KM) -> KM:
        return KM(self.value + other.value)

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True, slots=True)
class ShoeStatus:
    """Status do tênis."""

    value: str  # "ativo" | "aposentado"

    @classmethod
    def active(cls) -> ShoeStatus:
        return cls("ativo")

    @classmethod
    def retired(cls) -> ShoeStatus:
        return cls("aposentado")


@dataclass(frozen=True, slots=True)
class RunTypeBand:
    """Banda de tipo de corrida (ex: easy 0-5km, threshold 5-10km, etc.)."""

    name: str
    min_km: float
    max_km: float