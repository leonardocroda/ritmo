"""Value Objects do domínio Activities — imutáveis, sem dependências externas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class Pace:
    """Ritmo em segundos por km — value object imutável."""

    seconds_per_km: float

    @classmethod
    def from_seconds_per_meter(cls, seconds_per_meter: float) -> Pace:
        """Cria Pace a partir de s/m (o que o banco guarda)."""
        return cls(seconds_per_meter * 1000)

    @classmethod
    def from_seconds_per_km(cls, seconds_per_km: float) -> Pace:
        """Cria Pace diretamente em s/km."""
        return cls(seconds_per_km)

    def to_seconds_per_meter(self) -> float:
        """Converte para s/m (para persistência)."""
        return self.seconds_per_km / 1000

    def format_min_km(self) -> str:
        """Formata como 'min:seg/km' (ex.: '5:30')."""
        total_seconds = int(self.seconds_per_km)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def __float__(self) -> float:
        return float(self.seconds_per_km)

    def __lt__(self, other: Pace) -> bool:
        return self.seconds_per_km < other.seconds_per_km

    def __le__(self, other: Pace) -> bool:
        return self.seconds_per_km <= other.seconds_per_km


@dataclass(frozen=True, slots=True)
class HeartRate:
    """Frequência cardíaca em bpm — value object imutável."""

    bpm: int

    def __int__(self) -> int:
        return self.bpm

    def __lt__(self, other: HeartRate) -> bool:
        return self.bpm < other.bpm


@dataclass(frozen=True, slots=True)
class Cadence:
    """Cadência em passos por minuto — value object imutável."""

    spm: int

    def __int__(self) -> int:
        return self.spm


class ZoneKey(str):
    """Chave de zona de esforço — string tipada com valores válidos."""

    VALID = frozenset({"easy", "marathon", "threshold", "interval", "repetition"})

    def __new__(cls, value: str) -> ZoneKey:
        if value not in cls.VALID:
            raise ValueError(f"Zona inválida: {value}. Válidas: {cls.VALID}")
        return super().__new__(cls, value)


@dataclass(frozen=True, slots=True)
class ZoneConfigVO:
    """Configuração de zonas para classificação — value object."""

    vdot: float
    pace_zones: dict[ZoneKey, tuple[Optional[float], Optional[float]]]  # (min_s_km, max_s_km)
    hr_zones: dict[int, tuple[Optional[int], Optional[int]]]  # zona -> (min_bpm, max_bpm)

    def classify_pace(self, pace_s_km: Optional[float]) -> Optional[ZoneKey]:
        """Classifica um pace (s/km) na zona correspondente."""
        if pace_s_km is None:
            return None
        for zone, (min_pace, max_pace) in self.pace_zones.items():
            if min_pace is not None and pace_s_km < min_pace:
                continue
            if max_pace is not None and pace_s_km > max_pace:
                continue
            return zone
        return None

    def classify_hr(self, hr_bpm: Optional[int]) -> Optional[int]:
        """Classifica uma FC (bpm) na zona correspondente."""
        if hr_bpm is None:
            return None
        for zone_num, (min_hr, max_hr) in self.hr_zones.items():
            if min_hr is not None and hr_bpm < min_hr:
                continue
            if max_hr is not None and hr_bpm > max_hr:
                continue
            return zone_num
        return None


@dataclass(frozen=True, slots=True)
class ActivityFilter:
    """Filtro para listagem de atividades."""

    activity_type: str = "running"  # "running" | "all"
    limit: int = 30
    offset: int = 0

    def __post_init__(self):
        if self.activity_type not in ("running", "all"):
            raise ValueError(f"activity_type inválido: {self.activity_type}")
        if not 1 <= self.limit <= 100:
            raise ValueError("limit deve estar entre 1 e 100")
        if self.offset < 0:
            raise ValueError("offset deve ser >= 0")