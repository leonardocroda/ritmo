"""Perfil de tênis por tipo × banda de pace — funções puras (T1).

Unit, sem DB. Valida build_shoe_profile e build_all_shoes_profiles.
"""

from app.tenis_analysis.profile import build_all_shoes_profiles, build_shoe_profile


def _run(pace_s, inferred_type="running", distance_m=5000.0, avg_hr=160, avg_cadence=175.0):
    return {
        "distance_m": distance_m,
        "duration_s": pace_s * distance_m / 1000 if pace_s else 300,
        "pace_s": pace_s,
        "avg_hr": avg_hr,
        "avg_cadence": avg_cadence,
        "inferred_type": inferred_type,
    }


def test_profile_groups_by_type_and_band() -> None:
    """Done-when T1: perfil agrupa por tipo de treino × banda de pace."""
    runs = [
        _run(330, "facil"),   # 5:30/km -> facil
        _run(300, "facil"),   # 5:00/km -> facil
        _run(270, "tempo"),   # 4:30/km -> tempo
        _run(240, "limiar"),  # 4:00/km -> limiar
        _run(210, "intervalado"),  # 3:30/km -> repeticao (banda 180-240)
    ]
    profile = build_shoe_profile(runs)
    assert profile["total_runs"] == 5

    by_key = {(g["tipo"], g["banda"]): g for g in profile["groups"]}
    # tipo vem de inferred_type, banda do pace (primeiro match, mais rapido primeiro)
    assert ("facil", "tempo") in by_key          # 330,300 -> tipo facil, banda tempo
    assert by_key[("facil", "tempo")]["n_corridas"] == 2
    assert ("tempo", "limiar") in by_key         # 270 -> tipo tempo, banda limiar
    assert ("limiar", "limiar") in by_key        # 240 -> tipo limiar, banda limiar
    assert ("intervalado", "intervalado") in by_key  # 210 -> tipo intervalado, banda intervalado


def test_profile_no_pace_bruto_agregado_sem_fatiamento() -> None:
    """Done-when T1: grupos sempre têm tipo e banda; nada é agregado bruto."""
    runs = [_run(300, "facil"), _run(270, "tempo")]
    profile = build_shoe_profile(runs)
    # Cada grupo tem tipo E banda preenchidos
    for g in profile["groups"]:
        assert g["tipo"] is not None
        assert g["banda"] is not None
    # Não existe um grupo "agregado bruto" sem tipo×banda


def test_profile_empty_runs() -> None:
    """Done-when T1: sem corridas -> perfil vazio."""
    profile = build_shoe_profile([])
    assert profile["total_runs"] == 0
    assert profile["total_km"] == 0.0
    assert profile["groups"] == []


def test_profile_km_and_averages() -> None:
    """Done-when T1: km totais e médias por grupo."""
    runs = [
        _run(300, "facil", distance_m=5000.0, avg_hr=150, avg_cadence=170.0),
        _run(300, "facil", distance_m=5000.0, avg_hr=160, avg_cadence=180.0),
    ]
    profile = build_shoe_profile(runs)
    assert profile["total_km"] == 10.0
    g = profile["groups"][0]
    assert g["n_corridas"] == 2
    assert g["km_totais"] == 10.0
    assert g["pace_medio_s"] == 300.0
    assert g["fc_media"] == 155.0
    assert g["cadencia_media"] == 175.0


def test_profile_all_shoes() -> None:
    """Done-when T1: build_all_shoes_profiles devolve um perfil por tênis."""
    data = {
        1: [_run(300, "facil")],
        2: [_run(270, "tempo")],
    }
    result = build_all_shoes_profiles(data)
    assert set(result.keys()) == {1, 2}
    assert result[1]["total_runs"] == 1
    assert result[2]["total_runs"] == 1
