"""Perfil de tênis fatiado por tipo de treino × banda de pace.

Funções puras: recebem uma lista de dicionários (já lidos do banco) e
devolvem o perfil agregado. Nunca expõem pace bruto agregado sem
fatiamento — o confounding de seleção (Adizero → tiro, Kayano → rodagem)
invalida comparações brutas.

Cada run dict esperado (campos lidos do banco):
    id, distance_m, duration_s, pace_s, avg_hr, max_hr, avg_cadence,
    inferred_type, start_time, shoe_id
"""

from collections import defaultdict

# Faixas de pace (s por km) por banda. Valores coerentes com as zonas
# VDOT do vdot_zones.json do usuário (VDOT 50.2). Editáveis se o usuário
# quiser ajustar.
PACE_BANDS_S_KM: list[tuple[str, float, float]] = [
    ("repeticao", 0, 180),   # 3:00/km ou mais rápido
    ("intervalado", 180, 240),  # 3:00–4:00/km
    ("limiar", 240, 300),   # 4:00–5:00/km
    ("tempo", 300, 360),    # 5:00–6:00/km
    ("facil", 360, 999),    # 6:00/km ou mais lento
    ("longao", 360, 999),   # 6:00/km ou mais lento (longão)
    ("progressivo", 360, 999),  # qualquer pace lento (julgado por distribuição)
    ("prova", 0, 999),      # qualquer pace (julgado por PRs)
    ("outro", 0, 999),      # sem tipo claro
]


def _band_for_pace(pace_s: float | None) -> str | None:
    """Retorna a banda de pace para um pace_s, ou None se não classificar."""
    if pace_s is None or pace_s <= 0:
        return None
    for band, low, high in PACE_BANDS_S_KM:
        if low <= pace_s < high:
            return band
    # pace acima de 7:00/km (maior que a última banda fácil) -> fácil
    return "facil"


def _type_label(inferred_type: str | None) -> str:
    """Normaliza o tipo de treino para rótulo do perfil."""
    if not inferred_type:
        return "outro"
    return inferred_type.strip().lower()


def build_shoe_profile(runs: list[dict]) -> dict:
    """Perfil de um tênis fatiado por tipo de treino × banda de pace.

    Args:
        runs: lista de dicts com campos do banco (pace_s, inferred_type,
              distance_m, duration_s, avg_hr, avg_cadence, etc.).

    Returns:
        dict com:
          - total_runs: int
          - total_km: float
          - groups: list de {tipo, banda, pace_medio_s, fc_media,
                            cadencia_media, n_corridas, km_totais}
    """
    total_runs = len(runs)
    total_km = sum((r.get("distance_m") or 0) for r in runs) / 1000.0

    # Agrupa por (tipo, banda)
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for run in runs:
        tipo = _type_label(run.get("inferred_type"))
        banda = _band_for_pace(run.get("pace_s"))
        buckets[(tipo, banda)].append(run)

    groups = []
    for (tipo, banda), bucket_runs in sorted(buckets.items()):
        paces = [r["pace_s"] for r in bucket_runs if r.get("pace_s")]
        fcs = [r["avg_hr"] for r in bucket_runs if r.get("avg_hr")]
        cads = [r["avg_cadence"] for r in bucket_runs if r.get("avg_cadence")]
        kms = sum((r.get("distance_m") or 0) for r in bucket_runs) / 1000.0

        groups.append(
            {
                "tipo": tipo,
                "banda": banda or "sem_pace",
                "pace_medio_s": round(sum(paces) / len(paces), 1) if paces else None,
                "fc_media": round(sum(fcs) / len(fcs), 1) if fcs else None,
                "cadencia_media": round(sum(cads) / len(cads), 1) if cads else None,
                "n_corridas": len(bucket_runs),
                "km_totais": round(kms, 2),
            }
        )

    return {
        "total_runs": total_runs,
        "total_km": round(total_km, 2),
        "groups": groups,
    }


def build_all_shoes_profiles(shoes_runs: dict[int, list[dict]]) -> dict[int, dict]:
    """Perfil de vários tênis de uma só vez.

    Args:
        shoes_runs: mapeia shoe_id -> lista de runs desse tênis.

    Returns:
        mapeia shoe_id -> perfil (mesmo formato de build_shoe_profile).
    """
    return {shoe_id: build_shoe_profile(runs) for shoe_id, runs in shoes_runs.items()}
