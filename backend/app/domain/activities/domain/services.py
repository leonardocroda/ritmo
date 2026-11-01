"""Serviços puros do domínio Activities — sem I/O, sem dependências externas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

from app.domain.activities.domain.entities import Activity, Split
from app.domain.activities.domain.value_objects import ZoneConfigVO, ZoneKey


# Limites inclusivos do gate (spec: corridas >=8km com >=4 voltas)
MIN_DISTANCE_M = 8000
MIN_SPLITS = 4
MIN_CADENCE_LAPS_PER_HALF = 2


@dataclass(frozen=True, slots=True)
class ConsistencyMetrics:
    """Métricas de consistência de uma corrida."""

    first_half_pace_s: Optional[float]
    second_half_pace_s: Optional[float]
    balance_delta_s: Optional[float]
    balance_delta_pct: Optional[float]
    first_half_hr: Optional[float]
    second_half_hr: Optional[float]
    hr_drift_bpm: Optional[float]
    decoupling_pct: Optional[float]
    cadence_fade_spm: Optional[float]


def _valid_pace(split) -> bool:
    """Pace válido: distância e duração > 0. Funciona com Split ou ClassifiedSplit."""
    dist = getattr(split, 'distance_m', None) or getattr(split, 'dist_m', None)
    dur = getattr(split, 'duration_s', None)
    return bool(dist and dist > 0 and dur and dur > 0)


def _half_pace(splits: Sequence) -> Optional[float]:
    """Pace da metade (s/km): tempo total / distância total das voltas com pace válido."""
    distance = sum(
        (getattr(s, 'distance_m', None) or getattr(s, 'dist_m', None) or 0)
        for s in splits if _valid_pace(s)
    )
    duration = sum(
        getattr(s, 'duration_s', None) or 0
        for s in splits if _valid_pace(s)
    )
    if distance <= 0 or duration <= 0:
        return None
    return duration / distance * 1000


def _extract_numeric(value) -> float | None:
    """Extrai valor numérico de value objects (HeartRate, Cadence, Pace) ou retorna o próprio valor."""
    if value is None:
        return None
    if hasattr(value, 'bpm'):  # HeartRate
        return float(value.bpm)
    if hasattr(value, 'spm'):  # Cadence
        return float(value.spm)
    if hasattr(value, 'seconds_per_km'):  # Pace
        return float(value.seconds_per_km)
    return float(value)


def _weighted_mean(splits: Sequence[Split], attr: str) -> Optional[float]:
    """Média ponderada pela duração de um campo opcional; None sem dados."""
    weighted = [
        (_extract_numeric(getattr(s, attr)), s.duration_s)
        for s in splits
        if getattr(s, attr) is not None and s.duration_s and s.duration_s > 0
    ]
    total_weight = sum(w for _, w in weighted)
    if total_weight <= 0:
        return None
    return sum(v * w for v, w in weighted) / total_weight


def _count_with(splits: Sequence[Split], attr: str) -> int:
    return sum(1 for s in splits if getattr(s, attr) is not None)


def _decoupling(
    pace_first: Optional[float],
    pace_second: Optional[float],
    hr_first: Optional[float],
    hr_second: Optional[float],
) -> Optional[float]:
    """Variação % do razão FC-média/pace-médio entre metades."""
    if pace_first is None or pace_second is None or hr_first is None or hr_second is None:
        return None
    if pace_first <= 0 or hr_first <= 0:
        return None
    ratio_first = hr_first / pace_first
    ratio_second = hr_second / pace_second
    return round((ratio_second - ratio_first) / ratio_first * 100, 1)


def split_halves(splits: Sequence) -> tuple[list, list]:
    """Divide as voltas em (1ª metade, 2ª metade) por distância acumulada.

    A volta que atinge >=50% da distância total fecha a 1ª metade e fica nela.
    Funciona com Split ou ClassifiedSplit (duck typing: distance_m/dist_m).
    """
    total = sum(
        getattr(s, 'distance_m', None) or getattr(s, 'dist_m', None) or 0
        for s in splits
    )
    target = total / 2
    first: list = []
    second: list = []
    accumulated = 0.0
    closed = False
    for split in splits:
        if closed:
            second.append(split)
            continue
        first.append(split)
        accumulated += getattr(split, 'distance_m', None) or getattr(split, 'dist_m', None) or 0
        if total > 0 and accumulated >= target:
            closed = True
    return first, second


class ConsistencyCalculator:
    """Calculadora pura de métricas de consistência — sem I/O, determinística."""

    def calculate(self, activity: Activity, splits: Sequence[Split]) -> Optional[ConsistencyMetrics]:
        """Calcula métricas de consistência para uma atividade.

        Returns None se a atividade não atende ao gate (distância < 8km ou < 4 voltas).
        """
        if activity.distance_m < MIN_DISTANCE_M or len(splits) < MIN_SPLITS:
            return None

        first, second = split_halves(splits)
        pace_first = _half_pace(first)
        pace_second = _half_pace(second)
        hr_first = _weighted_mean(first, "avg_hr")
        hr_second = _weighted_mean(second, "avg_hr")

        # Converte HeartRate para float se presente
        hr_first_val = float(hr_first) if hr_first is not None else None
        hr_second_val = float(hr_second) if hr_second is not None else None

        metrics = ConsistencyMetrics(
            first_half_pace_s=pace_first,
            second_half_pace_s=pace_second,
            balance_delta_s=(
                pace_second - pace_first
                if pace_first is not None and pace_second is not None
                else None
            ),
            balance_delta_pct=(
                round((pace_second - pace_first) / pace_first * 100, 1)
                if pace_first is not None and pace_second is not None
                else None
            ),
            first_half_hr=hr_first_val,
            second_half_hr=hr_second_val,
            hr_drift_bpm=(
                hr_second_val - hr_first_val
                if hr_first_val is not None and hr_second_val is not None
                else None
            ),
            decoupling_pct=_decoupling(pace_first, pace_second, hr_first_val, hr_second_val),
            cadence_fade_spm=None,
        )

        # Fade de cadência só com >= 2 voltas com cadência em cada metade
        if (
            _count_with(first, "avg_cadence") >= MIN_CADENCE_LAPS_PER_HALF
            and _count_with(second, "avg_cadence") >= MIN_CADENCE_LAPS_PER_HALF
        ):
            cadence_first = _weighted_mean(first, "avg_cadence")
            cadence_second = _weighted_mean(second, "avg_cadence")
            if cadence_first is not None and cadence_second is not None:
                metrics = ConsistencyMetrics(
                    first_half_pace_s=metrics.first_half_pace_s,
                    second_half_pace_s=metrics.second_half_pace_s,
                    balance_delta_s=metrics.balance_delta_s,
                    balance_delta_pct=metrics.balance_delta_pct,
                    first_half_hr=metrics.first_half_hr,
                    second_half_hr=metrics.second_half_hr,
                    hr_drift_bpm=metrics.hr_drift_bpm,
                    decoupling_pct=metrics.decoupling_pct,
                    cadence_fade_spm=cadence_second - cadence_first,
                )

        return metrics


# --- Classificação de zonas ---

# Zonas de esforço do intervalado e zonas/intensidades de recuperação
WORK_ZONES = frozenset({ZoneKey("interval"), ZoneKey("repetition")})
RECOVERY_ZONES = frozenset({ZoneKey("easy"), ZoneKey("marathon")})
RECOVERY_INTENSITIES = frozenset({"REST", "RECOVERY", "WALK"})

# Blocos de limiar/tempo (spec: >=3 voltas consecutivas somando >=2000m)
BLOCK_MIN_LAPS = 3
BLOCK_MIN_METERS = 2000

# Fator do progressivo (spec: pace da 2ª metade <= 92% do da 1ª)
PROGRESSIVE_MAX_RATIO = 0.92

# Rótulos PT-BR por intensityType
INTENSITY_LABELS = {
    "WARMUP": "Aquecimento",
    "ACTIVE": "Corrida",
    "COOLDOWN": "Desaquecimento",
    "REST": "Descanso",
    "RECOVERY": "Recuperação",
    "WALK": "Caminhada",
    "INTERVAL": "Intervalo",
}


@dataclass(frozen=True, slots=True)
class ClassifiedSplit:
    """Volta já classificada — o que o tipo inferido e a estrutura precisam."""

    dist_m: Optional[float]
    duration_s: Optional[float]
    pace_s: Optional[float]
    intensity_type: Optional[str]
    zone: Optional[ZoneKey]


def _is_race(raw_json: dict | None) -> bool:
    """Prova: eventType.typeKey=='race' (ou eventTypeDTO) no raw_json."""
    raw = raw_json or {}
    event = raw.get("eventType") or {}
    event_dto = raw.get("eventTypeDTO") or {}
    return event.get("typeKey") == "race" or event_dto.get("typeKey") == "race"


def _is_work(split: ClassifiedSplit) -> bool:
    return split.zone in WORK_ZONES


def _is_recovery(split: ClassifiedSplit) -> bool:
    if split.zone in RECOVERY_ZONES:
        return True
    return (split.intensity_type or "") in RECOVERY_INTENSITIES


def _count_work_groups(classified: Sequence[ClassifiedSplit]) -> int:
    """Grupos de voltas consecutivas em zona interval/repetition separados por recuperação."""
    groups = 0
    in_group = False
    for split in classified:
        if _is_work(split):
            if not in_group:
                groups += 1
                in_group = True
        elif _is_recovery(split):
            in_group = False
    return groups


def _has_block(classified: Sequence[ClassifiedSplit], zone: ZoneKey) -> bool:
    """Bloco de >=3 voltas consecutivas na zona somando >=2000m."""
    run_laps = 0
    run_meters = 0.0
    for split in classified:
        if split.zone == zone:
            run_laps += 1
            run_meters += split.dist_m or 0
            if run_laps >= BLOCK_MIN_LAPS and run_meters >= BLOCK_MIN_METERS:
                return True
        else:
            run_laps = 0
            run_meters = 0.0
    return False


def _is_progressive(classified: Sequence[ClassifiedSplit]) -> bool:
    """Pace médio da 2ª metade <= 92% do da 1ª (metades por distância acumulada)."""
    first, second = split_halves(classified)
    pace_first = _half_pace(first)
    pace_second = _half_pace(second)
    if pace_first is None or pace_second is None:
        return False
    return pace_second <= pace_first * PROGRESSIVE_MAX_RATIO


LONG_RUN_MIN_M = 16000


def infer_type(
    raw_json: dict | None,
    classified: Sequence[ClassifiedSplit],
    distance_m: float,
) -> str:
    """Tipo do treino pela ordem de prioridade do spec (ASCII na API)."""
    if _is_race(raw_json):
        return "prova"
    if _count_work_groups(classified) >= 2:
        return "intervalado"
    if _has_block(classified, ZoneKey("threshold")):
        return "limiar"
    if _has_block(classified, ZoneKey("marathon")):
        return "tempo"
    if _is_progressive(classified):
        return "progressivo"
    if distance_m >= LONG_RUN_MIN_M:
        return "longao"
    return "facil"


def derive_structure(classified: Sequence[ClassifiedSplit]) -> str | None:
    """Soma passos consecutivos por intensityType ("Aquecimento 2,0km + …")."""
    groups: list[list] = []  # [intensity_type, dist_m acumulada]
    for split in classified:
        intensity = split.intensity_type
        if intensity is None:
            continue
        if groups and groups[-1][0] == intensity:
            groups[-1][1] += split.dist_m or 0
        else:
            groups.append([intensity, split.dist_m or 0])
    if not groups:
        return None
    if len(groups) == 1:
        return INTENSITY_LABELS.get(groups[0][0], groups[0][0])
    parts = [
        f"{INTENSITY_LABELS.get(intensity, intensity)} "
        f"{f'{meters / 1000:.1f}'.replace('.', ',')}km"
        for intensity, meters in groups
    ]
    return " + ".join(parts)


def classify_splits(splits: Sequence[Split], zone_config: ZoneConfigVO) -> list[ClassifiedSplit]:
    """Converte splits do domínio para ClassifiedSplit com zona classificada."""
    classified = []
    for split in splits:
        classified.append(
            ClassifiedSplit(
                dist_m=split.distance_m,
                duration_s=split.duration_s,
                pace_s=float(split.pace) if split.pace else None,
                intensity_type=split.intensity_type,
                zone=split.zone,
            )
        )
    return classified