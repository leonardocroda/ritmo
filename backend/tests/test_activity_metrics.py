"""Métricas de consistência (T4) — funções puras com valores conferidos à mão.

Cada fixture é um longão sintético cujos números saem de aritmética
manual (Independent Test do spec): os valores afirmados são literais
do teste, nunca constantes compartilhadas com a implementação
(lição L-001) e sem aproximações (lição L-002).
"""

from types import SimpleNamespace

from app.activities.metrics import consistency_metrics, split_halves


def _lap(dist_m: float, duration_s: float, avg_hr: float | None = None,
         avg_cadence: float | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        dist_m=dist_m,
        duration_s=duration_s,
        avg_hr=avg_hr,
        avg_cadence=avg_cadence,
    )


def _negative_split_laps() -> list[SimpleNamespace]:
    """8×1000m: 1ª metade 5:00/km (FC 140, cad 172), 2ª metade 4:50/km (FC 140, cad 170)."""
    first = [_lap(1000, 300, 140, 172) for _ in range(4)]
    second = [_lap(1000, 290, 140, 170) for _ in range(4)]
    return first + second


def _drift_laps() -> list[SimpleNamespace]:
    """8×1000m: 4:40/km FC 140 -> 4:50/km FC 145 — razão FC/pace constante (0,5)."""
    first = [_lap(1000, 280, 140, 170) for _ in range(4)]
    second = [_lap(1000, 290, 145, 170) for _ in range(4)]
    return first + second


# ---------------------------------------------------------------
# split_halves — divisão por distância acumulada
# ---------------------------------------------------------------


def test_split_halves_even_laps_close_at_half() -> None:
    """4 voltas de 2000m: acumulado bate 4000m na 2ª volta (>=50% fecha)."""
    laps = [_lap(2000, 480) for _ in range(4)]
    first, second = split_halves(laps)
    assert len(first) == 2
    assert len(second) == 2
    assert first[1] is laps[1]
    assert second[0] is laps[2]


def test_split_halves_crossing_lap_stays_in_first() -> None:
    """3000+1000+2000+2000: a volta que atravessa os 4000m fica na 1ª metade."""
    laps = [_lap(3000, 900), _lap(1000, 300), _lap(2000, 600), _lap(2000, 600)]
    first, second = split_halves(laps)
    assert [lap.dist_m for lap in first] == [3000, 1000]
    assert [lap.dist_m for lap in second] == [2000, 2000]


def test_split_halves_single_lap_over_half_goes_alone_to_first() -> None:
    """1ª volta de 5000m já cobre >50% dos 8000m: sozinha na 1ª metade."""
    laps = [_lap(5000, 1500), _lap(1000, 300), _lap(1000, 300), _lap(1000, 300)]
    first, second = split_halves(laps)
    assert len(first) == 1
    assert len(second) == 3


# ---------------------------------------------------------------
# consistency_metrics — gate 8000m / 4 voltas (inclusivos)
# ---------------------------------------------------------------


def test_consistency_none_below_8000m() -> None:
    """Spec: distance_m < 8000 -> consistency=null mesmo com >=4 voltas."""
    assert consistency_metrics(_negative_split_laps(), 7999.9) is None


def test_consistency_none_below_4_laps() -> None:
    """Spec: <4 voltas -> consistency=null mesmo com >=8000m (3×3000m)."""
    laps = [_lap(3000, 900, 140, 170) for _ in range(3)]
    assert consistency_metrics(laps, 9000) is None


def test_consistency_gate_is_inclusive() -> None:
    """Edge do spec: exatamente 8000m com 4 voltas -> tabela aparece."""
    result = consistency_metrics(_negative_split_laps(), 8000)
    assert result is not None
    assert result["first_half_pace_s"] == 300.0


# ---------------------------------------------------------------
# consistency_metrics — valores conferidos à mão
# ---------------------------------------------------------------


def test_consistency_negative_split_values() -> None:
    """8×1000m, 5:00->4:50 com FC estável 140:
    pace 300->290, Δ -10s (-3,3%), drift 0, decoupling 3,4%, fade -2spm."""
    result = consistency_metrics(_negative_split_laps(), 8000)
    assert result == {
        "first_half_pace_s": 300.0,
        "second_half_pace_s": 290.0,
        "balance_delta_s": -10.0,
        "balance_delta_pct": -3.3,  # (290-300)/300*100
        "first_half_hr": 140.0,
        "second_half_hr": 140.0,
        "hr_drift_bpm": 0.0,
        "decoupling_pct": 3.4,  # (140/290)/(140/300): 300/290 = +3,448% -> 3,4
        "cadence_fade_spm": -2.0,  # 170 - 172
    }


def test_consistency_drift_with_constant_ratio_gives_zero_decoupling() -> None:
    """8×1000m, FC 140->145 enquanto pace 280->290: razão FC/pace constante,
    decoupling 0,0% apesar do drift de +5bpm."""
    result = consistency_metrics(_drift_laps(), 8000)
    assert result["first_half_pace_s"] == 280.0
    assert result["second_half_pace_s"] == 290.0
    assert result["balance_delta_s"] == 10.0
    assert result["balance_delta_pct"] == 3.6  # 10/280*100 = 3,571 -> 3,6
    assert result["first_half_hr"] == 140.0
    assert result["second_half_hr"] == 145.0
    assert result["hr_drift_bpm"] == 5.0
    assert result["decoupling_pct"] == 0.0  # (145/290) = (140/280)
    assert result["cadence_fade_spm"] == 0.0


def test_consistency_rest_lap_without_pace_excluded_from_averages() -> None:
    """Volta de recuperação (0m/30s, sem FC) não entra nas médias de pace;
    entra na divisão de metades por distância acumulada (fica na 1ª)."""
    laps = [
        _lap(1000, 300, 140),
        _lap(1000, 300, 140),
        _lap(1000, 300, 140),
        _lap(0, 30, None),  # volta de recuperação sem pace/FC
        _lap(1000, 290, 140),
        _lap(1000, 290, 140),
        _lap(1000, 290, 140),
        _lap(1000, 290, 140),
    ]
    result = consistency_metrics(laps, 8000)
    # 1ª metade: voltas 1-5 (acumulado 4000 >= 3500 = 50% dos 7000m de voltas)
    # pace 1ª = (300*3 + 290)/4000*1000 = 297,5 | 2ª = 870/3000*1000 = 290,0
    assert result["first_half_pace_s"] == 297.5
    assert result["second_half_pace_s"] == 290.0
    assert result["balance_delta_s"] == -7.5
    assert result["balance_delta_pct"] == -2.5
    assert result["hr_drift_bpm"] == 0.0
    assert result["decoupling_pct"] == 2.6  # (140/290)/(140/297,5) = +2,586%


# ---------------------------------------------------------------
# omission rules — nenhum número inventado
# ---------------------------------------------------------------


def test_consistency_cadence_fade_omitted_without_enough_cadence_laps() -> None:
    """Spec: <2 voltas com cadência em alguma metade -> campo OMITIDO."""
    laps = _negative_split_laps()
    laps[2].avg_cadence = None  # 1ª metade fica com 3 voltas com cadência
    laps[5].avg_cadence = None
    laps[6].avg_cadence = None
    laps[7].avg_cadence = None  # 2ª metade fica com 1 volta -> gate falha
    result = consistency_metrics(laps, 8000)
    assert result is not None
    assert "cadence_fade_spm" not in result


def test_consistency_hr_fields_null_when_no_hr() -> None:
    """Sem FC nas voltas: campos de FC null, decoupling null, pace intacto."""
    laps = _negative_split_laps()
    for lap in laps:
        lap.avg_hr = None
        lap.avg_cadence = None
    result = consistency_metrics(laps, 8000)
    assert result is not None
    assert result["first_half_pace_s"] == 300.0
    assert result["second_half_pace_s"] == 290.0
    assert result["balance_delta_s"] == -10.0
    assert result["first_half_hr"] is None
    assert result["second_half_hr"] is None
    assert result["hr_drift_bpm"] is None
    assert result["decoupling_pct"] is None


def test_consistency_is_deterministic() -> None:
    """AD-003/TRN-23: mesma entrada -> mesmos valores (teste repete e compara)."""
    laps = _negative_split_laps()
    assert consistency_metrics(laps, 8000) == consistency_metrics(laps, 8000)
