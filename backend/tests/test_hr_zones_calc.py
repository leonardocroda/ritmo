"""Zonas de FC — matemática pura (T2, feature hr-zones), pinável sem banco.

Defaults por método, guardrails dos bounds e derivação das zonas em bpm
(HRZ-08..11) — mesma postura do health/calc.py (AD-003): funções puras,
zero I/O. Valores afirmados são literais calculados na mão a partir das
fórmulas do spec (HRZ-10: lthr round(pct × fclthr / 100), fcr
fcrest + round(pct × (fcmax − fcrest) / 100), fcmax round(pct × fcmax /
100)) — nunca constantes compartilhadas com a implementação (lições
L-001/L-002). Ex.: fclthr 177 nos defaults lthr 65/80/89/95/100 ->
115,05/141,6/157,53/168,15/177 -> [115, 142, 158, 168, 177+].
"""

import pytest

from app.profile.calc import (
    DEFAULT_BOUNDS,
    BoundsError,
    classify,
    validate_bounds,
    zones_bpm,
)

# Literais do spec (HRZ-08) — defaults por método
LTHR_DEFAULTS = [
    {"low": 65, "high": 80},
    {"low": 80, "high": 89},
    {"low": 89, "high": 95},
    {"low": 95, "high": 100},
    {"low": 100, "high": None},
]
FCR_DEFAULTS = [
    {"low": 50, "high": 60},
    {"low": 60, "high": 70},
    {"low": 70, "high": 80},
    {"low": 80, "high": 90},
    {"low": 90, "high": 100},
]

# Bounds custom válidos do teste independente do spec (lthr, Z5 aberta)
LTHR_CUSTOM = [
    {"low": 64, "high": 79},
    {"low": 79, "high": 88},
    {"low": 88, "high": 94},
    {"low": 94, "high": 99},
    {"low": 99, "high": None},
]


def test_default_bounds_per_method() -> None:
    """HRZ-08: defaults exatamente como o spec — lthr 65/80/89/95/100 com
    Z5 aberta (high null); fcr e fcmax 50/60/70/80/90 fechando em 100."""
    assert DEFAULT_BOUNDS == {
        "lthr": LTHR_DEFAULTS,
        "fcr": FCR_DEFAULTS,
        "fcmax": FCR_DEFAULTS,
    }


def test_validate_bounds_accepts_defaults_and_custom_valid() -> None:
    """HRZ-08/09: os defaults dos 3 métodos são válidos, assim como
    bounds custom com cadeia ascendente íntegra (64/79/88/94/99 no
    lthr, Z5 aberta) — nenhum raise."""
    for method in ("lthr", "fcr", "fcmax"):
        validate_bounds(method, DEFAULT_BOUNDS[method])
    validate_bounds("lthr", LTHR_CUSTOM)


def test_validate_bounds_rejects_wrong_zone_count() -> None:
    """HRZ-09: ≠5 zonas -> BoundsError apontando a contagem recebida."""
    for bounds, count in ((LTHR_DEFAULTS[:4], 4), (LTHR_DEFAULTS + LTHR_DEFAULTS[:1], 6)):
        with pytest.raises(BoundsError) as excinfo:
            validate_bounds("lthr", bounds)
        assert f"recebidas {count}" in str(excinfo.value)


def test_validate_bounds_rejects_z1_low_nonpositive() -> None:
    """HRZ-09: z1.low ≤ 0 -> BoundsError apontando a zona 1."""
    bounds = [dict(z) for z in LTHR_DEFAULTS]
    bounds[0]["low"] = 0
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", bounds)
    assert "zona 1" in str(excinfo.value)


def test_validate_bounds_rejects_broken_chain() -> None:
    """HRZ-09: cadeia não conectada (z[n].high == z[n+1].low) — gap e
    sobreposição apontam a zona seguinte."""
    # gap: Z2.low 81 deixa um buraco entre 80 e 81
    gap = [dict(z) for z in LTHR_DEFAULTS]
    gap[1] = {"low": 81, "high": 89}
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", gap)
    assert "zona 2" in str(excinfo.value)

    # sobreposição: Z2.low 79 invade a Z1
    overlap = [dict(z) for z in LTHR_DEFAULTS]
    overlap[1] = {"low": 79, "high": 89}
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", overlap)
    assert "zona 2" in str(excinfo.value)


def test_validate_bounds_rejects_zone_below_one_point() -> None:
    """HRZ-09: zona <1 ponto (high ≤ low) ou high null no meio da cadeia
    -> BoundsError apontando a zona inválida."""
    flat = [dict(z) for z in LTHR_DEFAULTS]
    flat[2] = {"low": 89, "high": 89}
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", flat)
    assert "zona 3" in str(excinfo.value)

    null_high = [dict(z) for z in LTHR_DEFAULTS]
    null_high[1] = {"low": 80, "high": None}
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", null_high)
    assert "zona 2" in str(excinfo.value)


def test_validate_bounds_lthr_z5_high_must_be_null() -> None:
    """HRZ-09: upper em Z5 do LTHR deve ser None (zona aberta, sem teto
    inventado) -> BoundsError apontando a zona 5."""
    bounds = [dict(z) for z in LTHR_DEFAULTS]
    bounds[4] = {"low": 100, "high": 105}
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", bounds)
    assert "zona 5" in str(excinfo.value)


def test_validate_bounds_fcr_fcmax_z5_high_must_be_100() -> None:
    """HRZ-09: Z5 do fcr/fcmax fecha em 100 — high null ou ≠100 ou span 0
    -> BoundsError apontando a zona 5."""
    for method in ("fcr", "fcmax"):
        for z5 in ({"low": 90, "high": None}, {"low": 90, "high": 99}, {"low": 100, "high": 100}):
            bounds = [dict(z) for z in FCR_DEFAULTS]
            bounds[4] = z5
            with pytest.raises(BoundsError) as excinfo:
                validate_bounds(method, bounds)
            assert "zona 5" in str(excinfo.value), (method, z5)


def test_validate_bounds_reports_first_invalid_point() -> None:
    """HRZ-09: com dois pontos inválidos, o motivo aponta o PRIMEIRO —
    cadeia quebrada na zona 2 vem antes do high indevido na zona 5."""
    bounds = [dict(z) for z in LTHR_DEFAULTS]
    bounds[1] = {"low": 82, "high": 89}  # gap na Z2
    bounds[4] = {"low": 100, "high": 105}  # upper indevido na Z5
    with pytest.raises(BoundsError) as excinfo:
        validate_bounds("lthr", bounds)
    assert "zona 2" in str(excinfo.value)
    assert "zona 5" not in str(excinfo.value)


def test_zones_bpm_lthr_defaults() -> None:
    """HRZ-10: lthr 177 nos defaults -> [115, 142, 158, 168, 177+]
    (round(pct × 177 / 100): 115,05/141,6/157,53/168,15/177) e Z5
    aberta (high None)."""
    zones = zones_bpm("lthr", DEFAULT_BOUNDS["lthr"], {"fclthr": 177})
    assert zones == [
        {"n": 1, "low": 115, "high": 142},
        {"n": 2, "low": 142, "high": 158},
        {"n": 3, "low": 158, "high": 168},
        {"n": 4, "low": 168, "high": 177},
        {"n": 5, "low": 177, "high": None},
    ]


def test_zones_bpm_lthr_custom_bounds() -> None:
    """HRZ-09/10 (teste independente do spec): bounds 64/79/88/94/99 no
    lthr recalculam as zonas — 113,28/139,83/155,76/166,38/175,23."""
    zones = zones_bpm("lthr", LTHR_CUSTOM, {"fclthr": 177})
    assert zones == [
        {"n": 1, "low": 113, "high": 140},
        {"n": 2, "low": 140, "high": 156},
        {"n": 3, "low": 156, "high": 166},
        {"n": 4, "low": 166, "high": 175},
        {"n": 5, "low": 175, "high": None},
    ]


def test_zones_bpm_fcr() -> None:
    """HRZ-10: Karvonen com fcrest 50/fcmax 190 (reserva 140) ->
    50+70/50+84/50+98/50+112/50+126 = [120, 134, 148, 162, 176]; Z5
    fecha em fcmax (190), não em 50+round(1,0×140)."""
    zones = zones_bpm("fcr", DEFAULT_BOUNDS["fcr"], {"fcrest": 50, "fcmax": 190})
    assert zones == [
        {"n": 1, "low": 120, "high": 134},
        {"n": 2, "low": 134, "high": 148},
        {"n": 3, "low": 148, "high": 162},
        {"n": 4, "low": 162, "high": 176},
        {"n": 5, "low": 176, "high": 190},
    ]


def test_zones_bpm_fcmax() -> None:
    """HRZ-10: fcmax 190 nos defaults -> round(pct × 190 / 100) =
    [95, 114, 133, 152, 171]; Z5 fecha em fcmax (190)."""
    zones = zones_bpm("fcmax", DEFAULT_BOUNDS["fcmax"], {"fcmax": 190})
    assert zones == [
        {"n": 1, "low": 95, "high": 114},
        {"n": 2, "low": 114, "high": 133},
        {"n": 3, "low": 133, "high": 152},
        {"n": 4, "low": 152, "high": 171},
        {"n": 5, "low": 171, "high": 190},
    ]


def test_zones_bpm_none_without_required_metric() -> None:
    """HRZ-11: métrica exigida ausente -> zonas None (estado vazio
    honesto, não erro) — lthr sem fclthr; fcr sem fcrest ou sem fcmax;
    fcmax sem fcmax."""
    assert zones_bpm("lthr", DEFAULT_BOUNDS["lthr"], {"fclthr": None}) is None
    assert zones_bpm("lthr", DEFAULT_BOUNDS["lthr"], {}) is None
    assert zones_bpm("fcr", DEFAULT_BOUNDS["fcr"], {"fcmax": 190}) is None
    assert zones_bpm("fcr", DEFAULT_BOUNDS["fcr"], {"fcrest": 50}) is None
    assert zones_bpm("fcmax", DEFAULT_BOUNDS["fcmax"], {"fcmax": None}) is None


def test_classify_boundaries() -> None:
    """HRZ-10: low inclusivo, high exclusivo (low ≤ FC < high); Z5 do
    lthr aberta (qualquer FC ≥ low cai nela, sem teto); abaixo da Z1 ->
    None (guard de segurança)."""
    zones = zones_bpm("lthr", DEFAULT_BOUNDS["lthr"], {"fclthr": 177})

    assert classify(114, zones) is None  # abaixo da Z1 — guard
    assert classify(115, zones) == 1  # low inclusivo
    assert classify(141, zones) == 1  # high exclusivo (141 < 142)
    assert classify(142, zones) == 2
    assert classify(158, zones) == 3
    assert classify(168, zones) == 4
    assert classify(176, zones) == 4
    assert classify(177, zones) == 5  # início da Z5 aberta
    assert classify(220, zones) == 5  # sem teto inventado
