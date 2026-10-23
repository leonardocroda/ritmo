"""Recomendações R1–R5 (home/calc.py) — função pura, pins literais.

Cenários derivados dos ACs HOME-25..HOME-30 do spec: cada recomendação
com texto/why exatos, taper disparando INDEPENDENTE do veredito
(≤14 dias da próxima prova), cap de 3 por prioridade fixa, ordenação
R1>R2>R3>R4>R5 e estado vazio (sem veredito) sem recomendação — nada
para basear. Valores afirmados são literais do spec.
"""

from app.home.calc import Recommendation, recommendations


# ---------------------------------------------------------------
# R1–R3 e R5: casamento 1:1 com a regra do veredito
# ---------------------------------------------------------------


def test_r1_quality_window_from_v5() -> None:
    """HOME-26: V5 -> 'Boa janela pra sessão de qualidade', why
    'HRV · sono · forma', tom good."""
    recs = recommendations("V5", None)
    assert len(recs) == 1
    r = recs[0]
    assert r.text == "Boa janela pra sessão de qualidade"
    assert r.why == "HRV · sono · forma"
    assert r.tone == "good"


def test_r2_recovery_from_v1() -> None:
    """HOME-27: V1 -> 'Priorize recuperação hoje — leve ou descanso',
    why 'HRV · sono' — tom espelha a severidade da regra (alert)."""
    recs = recommendations("V1", None)
    assert len(recs) == 1
    r = recs[0]
    assert r.text == "Priorize recuperação hoje — leve ou descanso"
    assert r.why == "HRV · sono"
    assert r.tone == "alert"


def test_r2_recovery_from_v2() -> None:
    """HOME-27: V2 -> mesma recomendação, tom attention (sem o
    agravante de sono da V1)."""
    recs = recommendations("V2", None)
    assert len(recs) == 1
    assert recs[0].text == "Priorize recuperação hoje — leve ou descanso"
    assert recs[0].tone == "attention"


def test_r3_hold_volume_from_v3() -> None:
    """HOME-28: V3 -> 'Segure o volume nesta semana', why 'ACWR · forma'."""
    recs = recommendations("V3", None)
    assert len(recs) == 1
    r = recs[0]
    assert r.text == "Segure o volume nesta semana"
    assert r.why == "ACWR · forma"
    assert r.tone == "attention"


def test_r3_hold_volume_from_v4() -> None:
    """HOME-28: V4 (fadiga) pede a mesma ação de segurar o volume."""
    recs = recommendations("V4", None)
    assert len(recs) == 1
    assert recs[0].text == "Segure o volume nesta semana"


def test_r5_dia_comum_from_v6() -> None:
    """HOME-30: V6 -> 'Siga o leve de hoje' com copy de apoio 'Tudo
    dentro da faixa' — why None: nenhuma regra específica sustenta."""
    recs = recommendations("V6", None)
    assert len(recs) == 1
    r = recs[0]
    assert r.text == "Siga o leve de hoje"
    assert r.support == "Tudo dentro da faixa"
    assert r.why is None
    assert r.tone == "neutral"


# ---------------------------------------------------------------
# R4: taper ≤14 dias, independente do veredito (HOME-29)
# ---------------------------------------------------------------


def test_r4_taper_fires_with_v1() -> None:
    """HOME-29: prova a 10 dias dispara o taper JUNTO com a recomendação
    da regra — independente do veredito; why carrega o N dinâmico."""
    recs = recommendations("V1", 10)
    assert [r.text for r in recs] == [
        "Priorize recuperação hoje — leve ou descanso",
        "Semana de prova — redução progressiva (taper)",
    ]
    taper = recs[1]
    assert taper.why == "prova em 10 dias"
    assert taper.tone == "attention"


def test_r4_taper_with_v6_orders_before_r5() -> None:
    """HOME-25/HOME-29: dia comum + prova em 5 dias -> taper antes do
    'Siga o leve de hoje' (prioridade fixa R4 > R5)."""
    recs = recommendations("V6", 5)
    assert len(recs) == 2
    assert recs[0].text == "Semana de prova — redução progressiva (taper)"
    assert recs[1].text == "Siga o leve de hoje"


def test_r4_taper_boundary_fourteen_and_zero() -> None:
    """HOME-29: faltam exatamente 14 dias dispara (≤14); dia da prova
    (0) também — why com o N do payload."""
    for days, expected in ((14, "prova em 14 dias"), (0, "prova em 0 dias")):
        recs = recommendations("V6", days)
        assert any(r.why == expected for r in recs), days


def test_r4_taper_requires_race_within_fourteen() -> None:
    """HOME-29 (negativa): sem prova (None) ou prova em 15 dias -> sem
    taper; V6 sozinho devolve só o R5."""
    assert [r.text for r in recommendations("V6", None)] == ["Siga o leve de hoje"]
    assert [r.text for r in recommendations("V6", 15)] == ["Siga o leve de hoje"]


# ---------------------------------------------------------------
# Shape, cap 3 e estado vazio (HOME-25)
# ---------------------------------------------------------------


def test_each_recommendation_carries_the_four_fields() -> None:
    """HOME-25: cada recomendação é {text, support, why, tone} — nada
    de campo extra, nada faltando."""
    for rule in ("V1", "V2", "V3", "V4", "V5", "V6"):
        for countdown in (None, 3, 10, 15):
            for r in recommendations(rule, countdown):
                assert set(r.__dataclass_fields__) == {"text", "support", "why", "tone"}


def test_cap_three_never_exceeded() -> None:
    """HOME-25: 1–3 recomendações, nunca mais de 3, para qualquer
    combinação de regra e countdown."""
    for rule in ("V1", "V2", "V3", "V4", "V5", "V6"):
        for countdown in (None, 0, 5, 14, 15, 30):
            recs = recommendations(rule, countdown)
            assert 1 <= len(recs) <= 3, (rule, countdown, len(recs))


def test_no_verdict_no_recommendations() -> None:
    """Estado vazio (HOME-34 no payload): sem veredito não há o que
    recomendar — a Home orienta sync, não prescreve."""
    assert recommendations(None, None) == []
