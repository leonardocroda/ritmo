"""Tipo inferido + estrutura derivada — funções puras (design).

Calculados em tempo de leitura, nunca persistidos (premissa do spec):
recalibrar zonas re-classifica sem re-sync. A prioridade das regras é
a da tabela de premissas do spec, em ordem estrita:

prova (eventType race) > intervalado (>=2 grupos interval/repetition
separados por recuperação) > limiar (bloco >=3 voltas threshold somando
>=2000m) > tempo (bloco >=3 marathon somando >=2000m) > progressivo
(2ª metade <= 92% do pace da 1ª) > longão (>=16000m) > fácil.

Voltas sem pace/zona não contam para blocos (edge do spec). Grupos
consideram recuperação por zona (easy/marathon) OU intensityType
REST/RECOVERY/WALK.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.activities.metrics import _half_pace, split_halves

# Limiar do longão (premissa do spec: corredor de ~52km/semana, longão típico 16-24km)
LONG_RUN_MIN_M = 16000

# Zonas de esforço do intervalado e zonas/intensidades de recuperação (spec)
WORK_ZONES = frozenset({"interval", "repetition"})
RECOVERY_ZONES = frozenset({"easy", "marathon"})
RECOVERY_INTENSITIES = frozenset({"REST", "RECOVERY", "WALK"})

# Blocos de limiar/tempo (spec: >=3 voltas consecutivas somando >=2000m)
BLOCK_MIN_LAPS = 3
BLOCK_MIN_METERS = 2000

# Fator do progressivo (premissa do spec: pace da 2ª metade <= 92% do da 1ª)
PROGRESSIVE_MAX_RATIO = 0.92

# Rótulos PT-BR por intensityType (design: "Aquecimento 2,0km + Corrida
# 7,1km + Desaquecimento 2,0km"); tipos fora do mapa passam com a chave crua.
INTENSITY_LABELS = {
    "WARMUP": "Aquecimento",
    "ACTIVE": "Corrida",
    "COOLDOWN": "Desaquecimento",
    "REST": "Descanso",
    "RECOVERY": "Recuperação",
    "WALK": "Caminhada",
    "INTERVAL": "Intervalo",
}


@dataclass(frozen=True)
class ClassifiedSplit:
    """Volta já classificada — o que o tipo inferido e a estrutura precisam."""

    dist_m: float | None
    duration_s: float | None
    pace_s: float | None
    intensity_type: str | None
    zone: str | None


def _is_race(raw_json: dict | None) -> bool:
    """Prova: eventType.typeKey=="race" (ou eventTypeDTO) no raw_json."""
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
    """Grupos de voltas consecutivas em zona interval/repetition separados
    por recuperação; voltas sem pace/zona não contam nem separam (spec)."""
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


def _has_block(classified: Sequence[ClassifiedSplit], zone: str) -> bool:
    """Bloco de >=3 voltas consecutivas na zona somando >=2000m (spec)."""
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
    if _has_block(classified, "threshold"):
        return "limiar"
    if _has_block(classified, "marathon"):
        return "tempo"
    if _is_progressive(classified):
        return "progressivo"
    if distance_m >= LONG_RUN_MIN_M:
        return "longao"
    return "facil"


def derive_structure(classified: Sequence[ClassifiedSplit]) -> str | None:
    """Soma passos consecutivos por intensityType ("Aquecimento 2,0km + …").

    Todas as voltas do mesmo tipo -> rótulo único ("Corrida", spec);
    nenhuma volta com intensity_type -> None (payload omite).
    """
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
