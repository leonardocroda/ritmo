"""Entidades do domínio Activities — imutáveis, sem dependências de infra."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence

from app.domain.activities.domain.value_objects import (
    Pace,
    HeartRate,
    Cadence,
    ZoneKey,
    ZoneConfigVO,
)


@dataclass(frozen=True, slots=True)
class RunningDynamics:
    """Dinâmicas de corrida por volta — value object imutável."""

    gct_ms: Optional[int] = None
    stride_cm: Optional[float] = None
    vert_osc_cm: Optional[float] = None
    vert_ratio: Optional[float] = None


@dataclass(frozen=True, slots=True)
class Split:
    """Uma volta/lap da atividade — entidade imutável."""

    idx: int
    distance_m: Optional[float]
    duration_s: Optional[float]
    pace: Optional[Pace]
    avg_hr: Optional[HeartRate]
    avg_cadence: Optional[Cadence]
    avg_temperature: Optional[float]
    elevation_m: Optional[float]
    intensity_type: Optional[str]
    zone: Optional[ZoneKey]
    km_label: str
    dynamics: RunningDynamics = field(default_factory=RunningDynamics)

    @property
    def pace_s(self) -> Optional[float]:
        """Pace em s/km para compatibilidade."""
        return float(self.pace) if self.pace else None

    @classmethod
    def from_db(cls, split_model, zone_config: ZoneConfigVO) -> Split:
        """Converte Split do SQLAlchemy para entidade de domínio."""
        pace = None
        if split_model.pace_s and split_model.pace_s > 0:
            pace = Pace.from_seconds_per_km(split_model.pace_s)

        avg_hr = None
        if split_model.avg_hr is not None:
            avg_hr = HeartRate(split_model.avg_hr)

        avg_cadence = None
        if split_model.avg_cadence is not None:
            avg_cadence = Cadence(int(split_model.avg_cadence))

        zone = None
        if pace is not None:
            zone = zone_config.classify_pace(pace.seconds_per_km)

        return cls(
            idx=split_model.idx,
            distance_m=split_model.dist_m,
            duration_s=split_model.duration_s,
            pace=pace,
            avg_hr=avg_hr,
            avg_cadence=avg_cadence,
            avg_temperature=split_model.avg_temperature,
            elevation_m=split_model.elevation_m,
            intensity_type=split_model.intensity_type,
            zone=zone,
            km_label="",  # Preenchido pelo service
            dynamics=RunningDynamics(
                gct_ms=split_model.ground_contact_time_ms,
                stride_cm=split_model.stride_length_cm,
                vert_osc_cm=split_model.vertical_oscillation_cm,
                vert_ratio=split_model.vertical_ratio,
            ),
        )


@dataclass(frozen=True, slots=True)
class Activity:
    """Atividade de corrida — entidade agregada imutável."""

    id: int
    user_id: int
    start_time: datetime
    activity_type: str
    name: Optional[str]
    distance_m: float
    duration_s: float
    avg_hr: Optional[HeartRate]
    max_hr: Optional[HeartRate]
    avg_cadence: Optional[Cadence]
    elevation_gain_m: Optional[float]
    aerobic_te: Optional[float]
    anaerobic_te: Optional[float]
    training_load: Optional[float]
    inferred_type: Optional[str]
    structure: Optional[str]
    splits: tuple[Split, ...] = field(default_factory=tuple)
    evaluated: bool = False
    garmin_id: Optional[str] = None
    shoe_id: Optional[int] = None
    feel: Optional[int] = None
    rpe: Optional[int] = None

    @property
    def pace(self) -> Optional[Pace]:
        """Pace médio da atividade."""
        if self.duration_s > 0 and self.distance_m > 0:
            return Pace.from_seconds_per_meter(self.duration_s / self.distance_m)
        return None

    @property
    def is_running(self) -> bool:
        return self.activity_type in ("running", "trail_running")

    @property
    def distance_km(self) -> float:
        return self.distance_m / 1000

    @property
    def duration_min(self) -> float:
        return self.duration_s / 60

    @classmethod
    def from_db(cls, activity_model, zone_config: ZoneConfigVO, splits: Sequence[Split]) -> Activity:
        """Converte Activity do SQLAlchemy para entidade de domínio."""
        avg_hr = None
        if activity_model.avg_hr is not None:
            avg_hr = HeartRate(activity_model.avg_hr)

        max_hr = None
        if activity_model.max_hr is not None:
            max_hr = HeartRate(activity_model.max_hr)

        avg_cadence = None
        if activity_model.avg_cadence is not None:
            avg_cadence = Cadence(int(activity_model.avg_cadence))

        # Preenche km_label cumulativo nas splits
        cumulative_m = 0.0
        labeled_splits = []
        for split in splits:
            cumulative_m += split.distance_m or 0
            labeled_splits.append(
                Split(
                    idx=split.idx,
                    distance_m=split.distance_m,
                    duration_s=split.duration_s,
                    pace=split.pace,
                    avg_hr=split.avg_hr,
                    avg_cadence=split.avg_cadence,
                    avg_temperature=split.avg_temperature,
                    elevation_m=split.elevation_m,
                    intensity_type=split.intensity_type,
                    zone=split.zone,
                    km_label=f"{cumulative_m / 1000:.1f}".replace(".", ","),
                    dynamics=split.dynamics,
                )
            )

        return cls(
            id=activity_model.id,
            user_id=activity_model.user_id,
            start_time=activity_model.start_time,
            activity_type=activity_model.activity_type,
            name=activity_model.name,
            distance_m=activity_model.distance_m,
            duration_s=activity_model.duration_s,
            avg_hr=avg_hr,
            max_hr=max_hr,
            avg_cadence=avg_cadence,
            elevation_gain_m=activity_model.elevation_gain_m,
            aerobic_te=activity_model.aerobic_te,
            anaerobic_te=activity_model.anaerobic_te,
            training_load=activity_model.training_load,
            inferred_type=activity_model.inferred_type,  # Será recalculado se necessário
            structure=None,  # Será derivado pelo service
            splits=tuple(labeled_splits),
            evaluated=activity_model.evaluated,
            garmin_id=activity_model.garmin_id,
            shoe_id=activity_model.shoe_id,
            feel=activity_model.feel,
            rpe=activity_model.rpe,
        )