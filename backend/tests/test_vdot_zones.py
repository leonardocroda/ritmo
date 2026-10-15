"""Zonas VDOT (T3) — load, classify e meta como funções puras.

Os cortes afirmados são os literais do spec com VDOT 50.2
(4:41 / 4:29 / 4:07 / 3:45 por km — lição L-001): pace mais lento que
o cut -> zona mais lenta; pace mais rápido -> zona mais rápida. Os
midpoints exatos são calculados no teste a partir dos valores
calibrados do JSON (fonte de verdade), nunca de constantes do módulo.
"""

import json
from pathlib import Path

import pytest

from app.vdot.zones import ZoneConfigError, load_zone_config

REAL_ZONES_PATH = Path(__file__).parents[1] / "data" / "vdot_zones.json"


def _speed(pace_s_per_km: float) -> float:
    """Pace (s/km) -> velocidade (m/s) — a conversão que o service faz."""
    return 1000 / pace_s_per_km


@pytest.fixture(scope="module")
def config():
    return load_zone_config(REAL_ZONES_PATH)


# ---------------------------------------------------------------
# load_zone_config
# ---------------------------------------------------------------


def test_load_zone_config_reads_calibrated_file(config) -> None:
    """T2/T3: o JSON calibrado (VDOT 50.2) carrega com as 5 zonas."""
    assert [z.key for z in config.meta()] == [
        "easy",
        "marathon",
        "threshold",
        "interval",
        "repetition",
    ]


def test_load_zone_config_missing_file_raises(tmp_path) -> None:
    """Done-when: arquivo ausente -> ZoneConfigError."""
    with pytest.raises(ZoneConfigError):
        load_zone_config(tmp_path / "nao_existe.json")


def test_load_zone_config_invalid_json_raises(tmp_path) -> None:
    """Done-when: JSON inválido -> ZoneConfigError."""
    bad = tmp_path / "vdot_zones.json"
    bad.write_text("{nao é json", encoding="utf-8")
    with pytest.raises(ZoneConfigError):
        load_zone_config(bad)


def test_load_zone_config_missing_zones_raises(tmp_path) -> None:
    """Edge: JSON válido mas sem as zonas -> ZoneConfigError."""
    bad = tmp_path / "vdot_zones.json"
    bad.write_text(json.dumps({"vdot": 50.2}), encoding="utf-8")
    with pytest.raises(ZoneConfigError):
        load_zone_config(bad)


# ---------------------------------------------------------------
# classify — cortes exatos de midpoint (spec: 4:41/4:29/4:07/3:45)
# ---------------------------------------------------------------


def test_classify_easy_marathon_cut_is_441(config) -> None:
    """Cut easy/marathon = 4:41/km: 4:41 (281s) ainda é easy, 4:40 (280s) já é marathon."""
    assert config.classify(_speed(281)) == "easy"
    assert config.classify(_speed(280)) == "marathon"


def test_classify_marathon_threshold_cut_is_429(config) -> None:
    """Cut marathon/threshold = 4:29/km: 4:29 (269s) ainda é marathon, 4:28 (268s) já é threshold."""
    assert config.classify(_speed(269)) == "marathon"
    assert config.classify(_speed(268)) == "threshold"


def test_classify_threshold_interval_cut_is_407(config) -> None:
    """Cut threshold/interval = 4:07/km: 4:07 (247s) ainda é threshold, 4:06 (246s) já é interval."""
    assert config.classify(_speed(247)) == "threshold"
    assert config.classify(_speed(246)) == "interval"


def test_classify_interval_repetition_cut_is_345(config) -> None:
    """Cut interval/repetition = 3:45/km: 3:45 (225s) ainda é interval, 3:44 (224s) já é repetition."""
    assert config.classify(_speed(225)) == "interval"
    assert config.classify(_speed(224)) == "repetition"


def test_classify_below_first_cut_is_easy_above_last_is_repetition(config) -> None:
    """Spec: abaixo do primeiro cut -> easy (5:30 = 330s); acima do último -> repetition (3:30 = 210s)."""
    assert config.classify(_speed(330)) == "easy"
    assert config.classify(_speed(210)) == "repetition"


def test_classify_exact_cut_belongs_to_faster_zone(config) -> None:
    """Borda exata do midpoint pertence à zona mais rápida (abaixo do primeiro é estrito).

    Os midpoints são calculados no teste a partir dos valores calibrados
    do JSON — mesma fórmula da premissa do spec, valores da fonte de verdade.
    """
    zones = json.loads(REAL_ZONES_PATH.read_text(encoding="utf-8"))["zones"]
    cuts = (
        (zones["easy"]["ms_max"] + zones["marathon"]["ms"]) / 2,
        (zones["marathon"]["ms"] + zones["threshold"]["ms_min"]) / 2,
        (zones["threshold"]["ms_max"] + zones["interval"]["ms_min"]) / 2,
        (zones["interval"]["ms_max"] + zones["repetition"]["ms"]) / 2,
    )
    assert config.classify(cuts[0]) == "marathon"
    assert config.classify(cuts[1]) == "threshold"
    assert config.classify(cuts[2]) == "interval"
    assert config.classify(cuts[3]) == "repetition"


def test_classify_invalid_pace_returns_none(config) -> None:
    """Spec: volta sem pace válido (distância/duração ≤ 0) -> zone=null."""
    assert config.classify(None) is None
    assert config.classify(0) is None
    assert config.classify(-3.5) is None


# ---------------------------------------------------------------
# meta — rótulo, faixa e cor (legenda do gráfico)
# ---------------------------------------------------------------


def test_meta_returns_five_zones_with_label_range_and_color(config) -> None:
    """Contrato do design: chave/rótulo/faixa exibível/cor por zona.

    Faixas normalizadas do JSON calibrado ("A/km-B/km" -> "A–B/km");
    cores do design (verde/azul/laranja/vermelho/roxo).
    """
    metas = {z.key: z for z in config.meta()}
    assert metas["easy"].label == "Easy"
    assert metas["easy"].pace_range == "5:51–4:53/km"
    assert metas["easy"].color == "#22c55e"
    assert metas["marathon"].label == "Maratona"
    assert metas["marathon"].pace_range == "4:30/km"
    assert metas["marathon"].color == "#3b82f6"
    assert metas["threshold"].label == "Limiar"
    assert metas["threshold"].pace_range == "4:14–4:27/km"
    assert metas["threshold"].color == "#f97316"
    assert metas["interval"].label == "Intervalado"
    assert metas["interval"].pace_range == "3:59–3:49/km"
    assert metas["interval"].color == "#ef4444"
    assert metas["repetition"].label == "Repetição"
    assert metas["repetition"].pace_range == "3:40/km"
    assert metas["repetition"].color == "#a855f7"


def test_interval_color_differs_from_hr_line_color(config) -> None:
    """TRN-17: a cor reservada à linha de FC (#f8fafc, design) não colide
    com a cor da zona interval (vermelho) — o vermelho é da zona de pace."""
    interval_color = next(z.color for z in config.meta() if z.key == "interval")
    assert interval_color != "#f8fafc"
