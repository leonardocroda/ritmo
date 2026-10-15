"""Tipo inferido + estrutura (T5) — um teste por regra + prioridade + edges.

Fixtures de laps são ClassifiedSplit com zonas atribuídas à mão (a
função é pura — recebe as voltas já classificadas). O treino de
strides segue os dados reais da sonda ("Londrina - Strides": voltas
de 100m ACTIVE em pace de repetition com recuperação REST). Literais
afirmados vêm do spec/design (lição L-001).
"""

from app.activities.infer import ClassifiedSplit, derive_structure, infer_type

RACE_RAW = {"eventType": {"typeKey": "race", "typeId": 1}}
RACE_DTO_RAW = {"eventTypeDTO": {"typeKey": "race", "typeId": 1}}


def _lap(dist_m: float, pace_s: float | None, zone: str | None,
         intensity: str | None = "ACTIVE") -> ClassifiedSplit:
    duration = pace_s * dist_m / 1000 if pace_s is not None and dist_m else None
    return ClassifiedSplit(
        dist_m=dist_m,
        duration_s=duration,
        pace_s=pace_s,
        intensity_type=intensity,
        zone=zone,
    )


def _easy_laps(count: int, dist_m: float = 1000, pace_s: float = 300) -> list[ClassifiedSplit]:
    return [_lap(dist_m, pace_s, "easy") for _ in range(count)]


# ---------------------------------------------------------------
# prova — maior prioridade
# ---------------------------------------------------------------


def test_prova_beats_every_other_rule() -> None:
    """Prioridade: eventType race -> prova mesmo com 2 grupos intervalados e 17km."""
    laps = [
        _lap(500, 220, "interval"),
        _lap(200, 330, "easy"),
        _lap(500, 220, "interval"),
        _lap(16000, 300, "easy"),
    ]
    assert infer_type(RACE_RAW, laps, 17000) == "prova"


def test_prova_also_via_event_type_dto() -> None:
    """Design: eventType.typeKey=="race" OU eventTypeDTO.typeKey=="race"."""
    assert infer_type(RACE_DTO_RAW, _easy_laps(4), 4000) == "prova"


def test_without_raw_json_no_race() -> None:
    """raw_json None -> não é prova (segue as regras de pace/zona)."""
    assert infer_type(None, _easy_laps(4), 4000) == "facil"


# ---------------------------------------------------------------
# intervalado — grupos separados por recuperação
# ---------------------------------------------------------------


def test_intervalado_two_groups_separated_by_easy_zone() -> None:
    """2 grupos interval/easy: [easy, interval, easy, interval, easy]."""
    laps = [
        _lap(1000, 300, "easy"),
        _lap(500, 220, "interval"),
        _lap(300, 330, "easy"),
        _lap(500, 220, "interval"),
        _lap(1000, 300, "easy"),
    ]
    assert infer_type(None, laps, 3300) == "intervalado"


def test_intervalado_recovery_by_intensity_type_rest() -> None:
    """Spec: recuperação também é intensityType REST/RECOVERY/WALK (zona None aqui)."""
    laps = [
        _lap(500, 220, "repetition"),
        _lap(200, None, None, "REST"),  # volta sem pace: só a intensidade sinaliza
        _lap(500, 220, "repetition"),
    ]
    assert infer_type(None, laps, 1200) == "intervalado"


def test_single_interval_group_is_not_intervalado() -> None:
    """1 grupo só não é intervalado (spec exige >=2) — sem outros blocos -> facil."""
    laps = [
        _lap(1000, 300, "easy"),
        _lap(1000, 240, "interval"),
        _lap(1000, 240, "interval"),
        _lap(1000, 240, "interval"),
        _lap(1000, 300, "easy"),
    ]
    assert infer_type(None, laps, 5000) == "facil"


# ---------------------------------------------------------------
# limiar / tempo — blocos de 3 voltas >= 2000m
# ---------------------------------------------------------------


def test_limiar_block_of_3_threshold_laps_over_2000m() -> None:
    laps = [
        _lap(1000, 300, "easy"),
        _lap(700, 260, "threshold"),
        _lap(700, 260, "threshold"),
        _lap(700, 260, "threshold"),
        _lap(1000, 300, "easy"),
    ]
    assert infer_type(None, laps, 4100) == "limiar"


def test_limiar_block_needs_2000m() -> None:
    """3 voltas threshold de 600m = 1800m < 2000m -> não é limiar."""
    laps = [
        _lap(600, 250, "threshold"),
        _lap(600, 250, "threshold"),
        _lap(600, 250, "threshold"),
        _lap(1000, 250, "easy"),
    ]
    assert infer_type(None, laps, 2800) == "facil"


def test_tempo_block_of_3_marathon_laps_over_2000m() -> None:
    laps = [
        _lap(1000, 300, "easy"),
        _lap(800, 270, "marathon"),
        _lap(800, 270, "marathon"),
        _lap(800, 270, "marathon"),
        _lap(1000, 300, "easy"),
    ]
    assert infer_type(None, laps, 4400) == "tempo"


# ---------------------------------------------------------------
# progressivo — 2ª metade <= 92% do pace da 1ª
# ---------------------------------------------------------------


def test_progressivo_second_half_92pct_faster() -> None:
    """4 voltas 5:00/km + 4 voltas 4:30/km (ratio 0,90 <= 0,92) e sem blocos."""
    laps = _easy_laps(4, pace_s=300) + _easy_laps(4, pace_s=270)
    assert infer_type(None, laps, 8000) == "progressivo"


def test_progressivo_boundary_is_inclusive_at_92pct() -> None:
    """Edge: exatamente 92% (276 <= 0,92×300) é progressivo; 277 não é."""
    at_boundary = _easy_laps(4, pace_s=300) + _easy_laps(4, pace_s=276)
    above_boundary = _easy_laps(4, pace_s=300) + _easy_laps(4, pace_s=277)
    assert infer_type(None, at_boundary, 8000) == "progressivo"
    assert infer_type(None, above_boundary, 8000) == "facil"


# ---------------------------------------------------------------
# longão / fácil
# ---------------------------------------------------------------


def test_longao_at_16000m_inclusive() -> None:
    """Edge: >=16000m é longão (inclusivo); 15999m é fácil."""
    laps = _easy_laps(8, dist_m=2000, pace_s=300)
    assert infer_type(None, laps, 16000) == "longao"
    assert infer_type(None, laps, 15999) == "facil"


def test_tempo_beats_longao() -> None:
    """Prioridade: bloco marathon vence mesmo com 17km de distância."""
    laps = _easy_laps(8, dist_m=2000, pace_s=300) + [
        _lap(800, 270, "marathon"),
        _lap(800, 270, "marathon"),
        _lap(800, 270, "marathon"),
    ]
    assert infer_type(None, laps, 17000) == "tempo"


def test_intervalado_beats_limiar() -> None:
    """Prioridade: 2 grupos interval vencem mesmo com bloco threshold >=2000m."""
    laps = [
        _lap(700, 260, "threshold"),
        _lap(700, 260, "threshold"),
        _lap(700, 260, "threshold"),
        _lap(300, 330, "easy"),
        _lap(500, 220, "interval"),
        _lap(300, 330, "easy"),
        _lap(500, 220, "interval"),
    ]
    assert infer_type(None, laps, 4000) == "intervalado"


def test_facil_is_the_fallback() -> None:
    """Corrida fácil: sem prova, sem grupos, sem blocos, pace estável, 5km."""
    assert infer_type(None, _easy_laps(5), 5000) == "facil"


# ---------------------------------------------------------------
# edges — voltas sem pace/zona e strides reais da sonda
# ---------------------------------------------------------------


def test_lap_without_zone_breaks_threshold_block() -> None:
    """Voltas sem pace/zona não contam para blocos: [threshold, None, threshold,
    threshold] não forma bloco de 3 consecutivas."""
    laps = [
        _lap(800, 250, "threshold"),
        _lap(200, None, None),  # volta sem pace válido
        _lap(800, 250, "threshold"),
        _lap(800, 250, "threshold"),
        _lap(1000, 250, "easy"),
    ]
    assert infer_type(None, laps, 3600) == "facil"


def _strides_laps() -> list[ClassifiedSplit]:
    """Sonda 14/10/2026 ("Londrina - Strides"): 4 tiros de 100m ACTIVE em
    pace de repetition separados por 200m REST easy + aquecimento/desaquecimento."""
    laps = [_lap(2000, 300, "easy")]
    for _ in range(4):
        laps.append(_lap(100, 220, "repetition"))
        laps.append(_lap(200, 330, "easy", "REST"))
    laps.append(_lap(1000, 300, "easy"))
    return laps


def test_strides_probe_workout_is_intervalado() -> None:
    """Dados reais da sonda: 4 grupos de repetition com recuperação -> intervalado."""
    assert infer_type(None, _strides_laps(), 4200) == "intervalado"


# ---------------------------------------------------------------
# derive_structure — soma passos consecutivos por intensity_type
# ---------------------------------------------------------------


def test_structure_sums_consecutive_steps_by_type() -> None:
    """Exato do design: "Aquecimento 2,0km + Corrida 7,1km + Desaquecimento 2,0km"."""
    laps = [
        _lap(2000, 300, "easy", "WARMUP"),
        _lap(7100, 300, "easy", "ACTIVE"),
        _lap(2000, 300, "easy", "COOLDOWN"),
    ]
    assert derive_structure(laps) == "Aquecimento 2,0km + Corrida 7,1km + Desaquecimento 2,0km"


def test_structure_single_type_is_bare_label() -> None:
    """Spec: todas as voltas do mesmo tipo -> rótulo único, sem distância."""
    assert derive_structure(_easy_laps(4)) == "Corrida"


def test_structure_split_by_recovery_step() -> None:
    """Passo de descanso interrompe a soma: corrida, descanso, corrida."""
    laps = [
        _lap(3000, 300, "easy", "ACTIVE"),
        _lap(200, None, None, "REST"),
        _lap(3000, 300, "easy", "ACTIVE"),
    ]
    assert derive_structure(laps) == "Corrida 3,0km + Descanso 0,2km + Corrida 3,0km"


def test_structure_none_without_intensity_types() -> None:
    """T7: structure derivada só quando há intensity_type."""
    laps = [ClassifiedSplit(1000, 300, 300.0, None, "easy") for _ in range(4)]
    assert derive_structure(laps) is None
