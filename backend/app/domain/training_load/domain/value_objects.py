"""Value Objects do domínio Performance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence


@dataclass(frozen=True, slots=True)
class VDOT:
    """VDOT — value object imutável."""

    value: float

    @classmethod
    def from_time_distance(cls, time_s: float, distance_m: float) -> VDOT:
        """Calcula VDOT aproximado a partir de tempo e distância (Jack Daniels)."""
        # Fórmula simplificada - usar tabela real em produção
        vdot = (distance_m / 1000) / (time_s / 60) * 100  # placeholder
        return cls(vdot)

    def predict_time(self, distance_m: float) -> float:
        """Prediz tempo para distância (placeholder)."""
        return distance_m / 1000 * (100 / self.value) * 60


@dataclass(frozen=True, slots=True)
class RaceTime:
    """Tempo de prova — value object."""

    seconds: float
    event: str

    @property
    def formatted(self) -> str:
        h = int(self.seconds // 3600)
        m = int((self.seconds % 3600) // 60)
        s = int(self.seconds % 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


@dataclass(frozen=True, slots=True)
class EventDistance:
    """Distância de evento padrão."""

    key: str
    meters: float
    label: str

    @classmethod
    def standard_events(cls) -> Sequence[EventDistance]:
        return (
            cls("5K", 5000, "5 km"),
            cls("10K", 10000, "10 km"),
            cls("HALF_MARATHON", 21097.5, "Meia Maratona"),
            cls("MARATHON", 42195, "Maratona"),
        )