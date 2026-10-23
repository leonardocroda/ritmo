"""Motor de veredito V1–V6 (home/calc.py) — função pura, pins literais.

Cenários derivados dos ACs HOME-02..HOME-10 do spec: cada regra V1..V6
com frase/tom exatos, cadeia de prioridade fixa (primeiro casamento
vence — uma frase por dia), sinal ausente neutro (nunca sustenta regra
de bom nem de ruim), nenhum sinal -> None (estado vazio orientando
sync, DISTINTO de V6) e determinismo (mesma entrada, mesmo veredito).
Valores afirmados são literais do spec — nunca constantes
compartilhadas com a implementação (lição L-001).
"""

from datetime import date

from app.home.calc import (
    ACWR_HIGH,
    TAPER_DAYS,
    TSB_FATIGUE,
    TSB_QUALITY,
    FitnessSignal,
    HrvSignal,
    Signals,
    SleepSignal,
    verdict,
)

DAY = date(2026, 10, 23)
FLOOR_S = 25200  # 7h — o mesmo piso do painel Saúde (literal do spec)


def _hrv(status):
    return HrvSignal(value=55.0, status=status, as_of=DAY)


def _sleep(duration_s):
    return SleepSignal(duration_s=duration_s, as_of=DAY)


def _fitness(tsb=0.0, acwr=None):
    return FitnessSignal(tsb=tsb, acwr=acwr, as_of=DAY)


# ---------------------------------------------------------------
# Thresholds (spec §Assumptions: TSB > 0 · TSB < −10 · ACWR > 1,5 ·
# taper ≤ 14 dias)
# ---------------------------------------------------------------


def test_constants_match_spec() -> None:
    """Réguas do motor: os 4 thresholds da tabela do spec."""
    assert TSB_QUALITY == 0
    assert TSB_FATIGUE == -10
    assert ACWR_HIGH == 1.5
    assert TAPER_DAYS == 14


# ---------------------------------------------------------------
# Regras individuais V1–V6 (frase + tom exatos do spec)
# ---------------------------------------------------------------


def test_v1_unbalanced_and_night_below_floor() -> None:
    """HOME-03: HRV UNBALANCED + última noite < piso (7h) -> 'Recuperação
    em dívida', tom alert."""
    v = verdict(Signals(hrv=_hrv("UNBALANCED"), sleep=_sleep(21600)))  # 6h
    assert v is not None
    assert v.phrase == "Recuperação em dívida"
    assert v.tone == "alert"
    assert v.rule == "V1"


def test_v2_unbalanced_without_sleep_aggravant() -> None:
    """HOME-04: HRV UNBALANCED, noite ok -> 'Corpo pedindo leve', attention."""
    v = verdict(Signals(hrv=_hrv("UNBALANCED"), sleep=_sleep(28800)))  # 8h
    assert v is not None
    assert v.phrase == "Corpo pedindo leve"
    assert v.tone == "attention"
    assert v.rule == "V2"


def test_v3_acwr_above_high() -> None:
    """HOME-05: acwr > 1,5 -> 'Carga alta — segure o volume', attention."""
    v = verdict(Signals(fitness=_fitness(tsb=0.0, acwr=1.6)))
    assert v is not None
    assert v.phrase == "Carga alta — segure o volume"
    assert v.tone == "attention"
    assert v.rule == "V3"


def test_v4_tsb_below_fatigue() -> None:
    """HOME-06: tsb < −10 -> 'Acúmulo de fadiga', attention."""
    v = verdict(Signals(fitness=_fitness(tsb=-10.5, acwr=1.2)))
    assert v is not None
    assert v.phrase == "Acúmulo de fadiga"
    assert v.tone == "attention"
    assert v.rule == "V4"


def test_v5_balanced_positive_tsb_night_not_below_floor() -> None:
    """HOME-07: BALANCED + tsb > 0 + noite NÃO abaixo do piso ->
    'Pronto pra qualidade', good."""
    v = verdict(
        Signals(hrv=_hrv("BALANCED"), sleep=_sleep(28800), fitness=_fitness(tsb=5.2))
    )
    assert v is not None
    assert v.phrase == "Pronto pra qualidade"
    assert v.tone == "good"
    assert v.rule == "V5"


def test_v6_dia_comum_when_no_rule_fires() -> None:
    """HOME-08: nenhum sinal dispara regra (incl. hrv null/'coletando')
    -> 'Dia comum, sem urgências', neutral. Há dado (o bloco HRV existe
    com status null) — não é o estado vazio."""
    v = verdict(Signals(hrv=_hrv(None)))
    assert v is not None
    assert v.phrase == "Dia comum, sem urgências"
    assert v.tone == "neutral"
    assert v.rule == "V6"


# ---------------------------------------------------------------
# Prioridade fixa V1→V6 — primeiro casamento vence (HOME-09)
# ---------------------------------------------------------------


def test_priority_v1_beats_v3_v4_v5() -> None:
    """HOME-09: com todos os gatilhos armados, V1 vence e emite UMA frase."""
    v = verdict(
        Signals(
            hrv=_hrv("UNBALANCED"),
            sleep=_sleep(21600),
            fitness=_fitness(tsb=-20.0, acwr=2.0),
        )
    )
    assert v is not None
    assert v.rule == "V1"
    assert v.phrase == "Recuperação em dívida"


def test_priority_v2_beats_v3_v4() -> None:
    """HOME-09: HRV fora (sem agravante de sono) vem antes de carga/fadiga."""
    v = verdict(
        Signals(
            hrv=_hrv("UNBALANCED"),
            sleep=_sleep(28800),
            fitness=_fitness(tsb=-20.0, acwr=2.0),
        )
    )
    assert v is not None
    assert v.rule == "V2"


def test_priority_v3_beats_v4_v5() -> None:
    """HOME-09: carga alta vem antes de fadiga e da janela de qualidade."""
    v = verdict(
        Signals(
            hrv=_hrv("BALANCED"),
            sleep=_sleep(28800),
            fitness=_fitness(tsb=-20.0, acwr=2.0),
        )
    )
    assert v is not None
    assert v.rule == "V3"


# ---------------------------------------------------------------
# Sinal nulo é neutro + estado vazio (HOME-10)
# ---------------------------------------------------------------


def test_null_signals_never_trigger_rules() -> None:
    """HOME-10: sono abaixo do piso SEM HRV não sustenta V1 (nunca frase
    de alerta sem evidência) — cai em V6; forma nula idem."""
    v = verdict(Signals(sleep=_sleep(21600)))
    assert v is not None
    assert v.rule == "V6"
    v2 = verdict(Signals(hrv=_hrv("BALANCED"), sleep=_sleep(21600)))
    assert v2 is not None
    assert v2.rule == "V6"  # V5 exige tsb > 0 — forma nula é neutra


def test_no_signals_returns_none() -> None:
    """HOME-10/estado vazio: banco sem sinal nenhum -> veredito None
    (orienta sync) — distinto de V6."""
    assert verdict(Signals()) is None
    assert verdict(Signals(hrv=None, sleep=None, fitness=None)) is None


def test_determinism_same_input_same_verdict() -> None:
    """HOME-02: mesma consulta, mesmo banco -> mesmo veredito — duas
    chamadas idênticas devolvem o mesmo resultado, sem aleatoriedade."""
    signals = Signals(hrv=_hrv("UNBALANCED"), sleep=_sleep(21600))
    assert verdict(signals) == verdict(signals)


# ---------------------------------------------------------------
# Bordas numéricas das réguas (edge cases do spec)
# ---------------------------------------------------------------


def test_v1_boundary_seven_hours_exactly_is_not_below_floor() -> None:
    """Borda do piso: 7h EXATA não é 'abaixo do piso' — V1 exige sono
    estritamente < 25200s; com 7h exata o casamento é V2."""
    v = verdict(Signals(hrv=_hrv("UNBALANCED"), sleep=_sleep(FLOOR_S)))
    assert v is not None
    assert v.rule == "V2"


def test_v5_blocked_when_night_below_floor() -> None:
    """HOME-07 (negativa): BALANCED + tsb > 0 mas noite abaixo do piso —
    a janela de qualidade NÃO abre; nenhuma regra -> V6."""
    v = verdict(
        Signals(hrv=_hrv("BALANCED"), sleep=_sleep(21600), fitness=_fitness(tsb=5.2))
    )
    assert v is not None
    assert v.rule == "V6"


def test_v5_fires_without_sleep_data() -> None:
    """HOME-10: sono ausente é neutro — não bloqueia V5 (a noite não
    dormiu abaixo do piso por falta de evidência)."""
    v = verdict(Signals(hrv=_hrv("BALANCED"), fitness=_fitness(tsb=5.2)))
    assert v is not None
    assert v.rule == "V5"


def test_thresholds_are_strict() -> None:
    """Bordas dos thresholds: acwr == 1,5 não é V3; tsb == −10 não é V4;
    tsb == 0 não é V5 — todas estritas, caem em V6."""
    v = verdict(Signals(fitness=_fitness(tsb=-10.0, acwr=1.5)))
    assert v is not None
    assert v.rule == "V6"
    v2 = verdict(Signals(hrv=_hrv("BALANCED"), fitness=_fitness(tsb=0.0, acwr=1.2)))
    assert v2 is not None
    assert v2.rule == "V6"
