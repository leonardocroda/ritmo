"""Delta de sono e volume semanal ISO (home/calc.py) — pins literais.

Cenários derivados dos ACs HOME-20/21 (delta vs média de 4 semanas,
guarda de divisão por zero) e HOME-14/37 (semanas ISO segunda-feira,
série de 10 semanas, semana corrente parcial) + edges: noites sem
dado fora da média, apenas uma noite, fronteira ISO na virada do ano.
Valores afirmados são literais derivados das fixtures.
"""

from datetime import date

from app.home.calc import sleep_delta, weekly_volume

H8 = 28800.0  # 8h
H7 = 25200.0  # 7h
H7_45 = 27900.0  # 7h45


# ---------------------------------------------------------------
# sleep_delta — última noite vs média das 7 anteriores com dado
# ---------------------------------------------------------------


def test_sleep_delta_normal() -> None:
    """HOME-20: 7 noites de 8h e última de 7h -> −1h vs média."""
    assert sleep_delta([H8] * 7 + [H7]) == -3600.0


def test_sleep_delta_ignores_nights_without_data() -> None:
    """Edge do spec: noites sem dado ficam FORA da média — só 8h e 7h45
    contam (média 7h52,5); última 7h -> −3150s."""
    assert sleep_delta([None, H8, None, H7_45, H7]) == -3150.0


def test_sleep_delta_uses_only_the_last_seven_previous() -> None:
    """HOME-20: média das 7 ANTERIORES — noites mais velhas que a
    janela não arrastam a média (2 noites curtas antigas ignoradas)."""
    durations = [7200.0, 7200.0] + [H8] * 7 + [H7]
    assert sleep_delta(durations) == -3600.0


def test_sleep_delta_single_night_is_none() -> None:
    """Edge: sem noite anterior não há comparação -> None."""
    assert sleep_delta([H8]) is None


def test_sleep_delta_empty_or_missing_last_is_none() -> None:
    """Edge: sem noites (ou a última sem dado) -> None."""
    assert sleep_delta([]) is None
    assert sleep_delta([H8, None]) is None


# ---------------------------------------------------------------
# weekly_volume — semanas ISO (segunda), corrente + 4 completas + série 10
# ---------------------------------------------------------------


def test_weekly_volume_iso_boundary_and_avg4() -> None:
    """HOME-14/20: corrida de DOMINGO pertence à semana da segunda
    anterior; corrente parcial conta; avg4 = média das 4 completas
    (20+30+40+50)/4 = 35km; delta = (10−35)/35 = −71,4%."""
    runs = [
        # semana 21/09: 20km · 28/09: 30km · 05/10: 40km
        (date(2026, 9, 23), 20000.0),
        (date(2026, 9, 30), 30000.0),
        (date(2026, 10, 7), 40000.0),
        # semana 12/10: 45km + 5km do domingo 18/10 = 50km (soma do week)
        (date(2026, 10, 13), 45000.0),
        (date(2026, 10, 18), 5000.0),
        # corrente (seg 19/10): 10km na segunda
        (date(2026, 10, 19), 10000.0),
    ]
    volume = weekly_volume(runs, date(2026, 10, 21))  # quarta

    assert volume["week_km"] == 10.0
    assert volume["avg4_km"] == 35.0
    assert volume["delta_pct"] == -71.4
    assert [(w["week_start"], w["km"]) for w in volume["weeks"]] == [
        (date(2026, 8, 17), 0.0),
        (date(2026, 8, 24), 0.0),
        (date(2026, 8, 31), 0.0),
        (date(2026, 9, 7), 0.0),
        (date(2026, 9, 14), 0.0),
        (date(2026, 9, 21), 20.0),
        (date(2026, 9, 28), 30.0),
        (date(2026, 10, 5), 40.0),
        (date(2026, 10, 12), 50.0),
        (date(2026, 10, 19), 10.0),
    ]


def test_weekly_volume_avg4_zero_delta_none() -> None:
    """HOME-21: média de 4 semanas zerada -> delta None (chip '—') —
    nunca divisão por zero, nunca % inventado."""
    volume = weekly_volume([(date(2026, 10, 21), 5000.0)], date(2026, 10, 21))
    assert volume["week_km"] == 5.0
    assert volume["avg4_km"] == 0.0
    assert volume["delta_pct"] is None


def test_weekly_volume_series_is_exactly_ten_weeks() -> None:
    """HOME-37: série com exatamente as 10 últimas semanas ISO, ASC,
    terminando na corrente; semana sem corrida = 0.0 (não omitida)."""
    volume = weekly_volume([(date(2026, 10, 20), 8000.0)], date(2026, 10, 23))
    weeks = volume["weeks"]
    assert len(weeks) == 10
    assert weeks[-1]["week_start"] == date(2026, 10, 19)  # sexta 23/10 -> seg 19/10
    assert weeks[0]["week_start"] == date(2026, 8, 17)  # 9 semanas antes
    assert weeks[-1]["km"] == 8.0
    assert all(w["km"] == 0.0 for w in weeks[:-1])


def test_weekly_volume_partial_current_week_counts() -> None:
    """Edge (design §Riscos): a corrente é parcial e é o ponto — a
    corrida de hoje entra no week_km."""
    volume = weekly_volume([(date(2026, 10, 23), 12000.0)], date(2026, 10, 23))
    assert volume["week_km"] == 12.0


def test_weekly_volume_iso_year_boundary() -> None:
    """Edge ISO: 31/12 (qui) e 01/01 (sex) pertencem à MESMA semana —
    a segunda 28/12/2026; aritmética segura na virada do ano."""
    volume = weekly_volume(
        [(date(2026, 12, 31), 5000.0), (date(2027, 1, 1), 5000.0)],
        date(2027, 1, 2),
    )
    assert volume["week_km"] == 10.0
    assert volume["weeks"][-1]["week_start"] == date(2026, 12, 28)
