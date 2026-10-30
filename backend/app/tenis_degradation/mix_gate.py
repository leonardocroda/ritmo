"""Gate de mix de tipos de treino para degradação.

Agrupa corridas por tipo de treino × banda de pace (mesma convenção da
análise comparativa). Nunca compara tipos diferentes (evita confounding
de seleção). Grupos sem pares válidos são omitidos.

Reusa _band_for_pace e _type_label de tenis_analysis.profile.
"""

from collections import defaultdict

from app.tenis_analysis.profile import _band_for_pace, _type_label

RUNNING_TYPES = ("running", "trail_running")


def group_by_type_band(runs: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """Agrupa runs por (tipo de treino, banda de pace).

    Só inclui runs running/trail_running. Retorna dicionário
    (tipo, banda) -> lista de runs.
    """
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for run in runs:
        tipo = run.get("inferred_type") or run.get("activity_type") or "outro"
        tipo = _type_label(tipo)
        if tipo not in RUNNING_TYPES and tipo not in ("running", "trail_running"):
            # inferred_type já é o tipo de treino (facil/tempo/etc), não activity_type.
            # Se não for um tipo reconhecido, usa "outro".
            pass
        banda = _band_for_pace(run.get("pace_s")) or "sem_pace"
        buckets[(tipo, banda)].append(run)
    return dict(buckets)


def filter_valid_groups(
    groups: dict[tuple[str, str], list[dict]], min_pairs: int = 1
) -> dict[tuple[str, str], list[dict]]:
    """Remove grupos com menos de min_pairs corridas."""
    return {k: v for k, v in groups.items() if len(v) >= min_pairs}
