"""Calc do painel Saúde (health/calc.py) — funções puras, pins literais.

Cenários derivados dos done-when de T2, dos ACs do endpoint
(HLT-04/09/10/11/12), do modelo científico de HRV (hrv-baseline,
HRV-01..HRV-08) e dos edge cases do spec: buckets <6h/≥6h45
cruzados na mesma data, faixa neutra 6h–6h45, truque ±12h perto da
meia-noite, virada de ano ISO, noite sem horário fora da regularidade,
bucket vazio -> médias None. Valores afirmados são literais derivados
das fixtures (lição L-001) — nunca constantes compartilhadas com a
implementação.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.health.calc import (
    ADEQUATE_MIN_S,
    HRV_AVG_DAYS,
    HRV_BASELINE_DAYS,
    HRV_BASELINE_MIN_VALUES,
    HRV_BASELINE_SD_FACTOR,
    REM_BAND,
    SHORT_MAX_S,
    SLEEP_FLOOR_S,
    below_floor,
    dose_response,
    hrv_model,
    local_minute,
    regularity,
    strength_weeks,
    weekday_pattern,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _night(day, duration_s, score=70, hrv=None, bed_min=None, wake_min=None):
    """Noite como o service monta: HRV/score da mesma data e minutos locais."""
    return {
        "date": day,
        "duration_s": duration_s,
        "score": score,
        "hrv": hrv,
        "bed_min": bed_min,
        "wake_min": wake_min,
    }


# ---------------------------------------------------------------
# Réguas do backend (design §Components)
# ---------------------------------------------------------------


def test_constants_match_spec() -> None:
    """Done-when T2: piso 7h, banda REM 21–31%, buckets <6h / ≥6h45."""
    assert SLEEP_FLOOR_S == 25200
    assert REM_BAND == (21.0, 31.0)
    assert SHORT_MAX_S == 21600
    assert ADEQUATE_MIN_S == 24300


# ---------------------------------------------------------------
# dose_response (HLT-09)
# ---------------------------------------------------------------


def test_dose_response_pins_from_real_bank_shape() -> None:
    """Done-when T2 (pins do banco real, §4.5): <6h -> HRV 69,5 / score
    60,2 vs ≥6h45 -> 81,3 / 80,2; mesma noite no cruzamento."""
    short = [
        _night(date(2026, 10, 5), 21000, 60, 68.0),
        _night(date(2026, 10, 6), 20500, 60, 70.0),
        _night(date(2026, 10, 7), 20800, 60, 69.5),
        _night(date(2026, 10, 8), 20200, 60, 70.0),
        _night(date(2026, 10, 9), 20700, 61, 70.0),
    ]
    adequate = [
        _night(date(2026, 9, 20), 27900, 80, 81.0),
        _night(date(2026, 9, 21), 28200, 80, 81.5),
        _night(date(2026, 9, 22), 27600, 80, 81.0),
        _night(date(2026, 9, 23), 28500, 80, 81.5),
        _night(date(2026, 9, 24), 27000, 80, 81.0),
        _night(date(2026, 9, 25), 28800, 80, 81.5),
        _night(date(2026, 9, 26), 29400, 81, 82.0),
        _night(date(2026, 9, 27), 27300, 80, 81.0),
        _night(date(2026, 9, 28), 29100, 81, 81.7),
        _night(date(2026, 9, 29), 28350, 80, 81.0),
    ]

    dose = dose_response(short + adequate)

    assert dose["short"] == {"nights": 5, "avg_hrv": 69.5, "avg_score": 60.2}
    assert dose["adequate"] == {"nights": 10, "avg_hrv": 81.3, "avg_score": 80.2}
    assert dose["neutral_nights"] == 0


def test_dose_response_band_boundaries() -> None:
    """Edge do spec: 6h exata é neutra (short é <6h), 6h45 exata é
    adequate (≥6h45), 6h30 é neutra."""
    nights = [
        _night(date(2026, 10, 1), 21600, 70, 60.0),
        _night(date(2026, 10, 2), 23400, 71, 61.0),
        _night(date(2026, 10, 3), 24300, 80, 75.0),
        _night(date(2026, 10, 4), 21599, 55, 50.0),
    ]

    dose = dose_response(nights)

    assert dose["short"] == {"nights": 1, "avg_hrv": 50.0, "avg_score": 55.0}
    assert dose["adequate"] == {"nights": 1, "avg_hrv": 75.0, "avg_score": 80.0}
    assert dose["neutral_nights"] == 2


def test_dose_response_nights_without_hrv_out_of_comparison() -> None:
    """Edge do spec: o cruzamento exige as duas linhas na mesma data —
    noite <6h ou ≥6h45 sem HRV sai da comparação (nem bucket nem nota);
    na faixa 6h–6h45 conta como neutra."""
    nights = [
        _night(date(2026, 10, 1), 21000, 60, None),
        _night(date(2026, 10, 2), 23400, 70, None),
        _night(date(2026, 10, 3), 27000, 80, None),
    ]

    dose = dose_response(nights)

    assert dose["short"] == {"nights": 0, "avg_hrv": None, "avg_score": None}
    assert dose["adequate"] == {"nights": 0, "avg_hrv": None, "avg_score": None}
    assert dose["neutral_nights"] == 1


def test_dose_response_all_neutral_or_empty_keeps_zeros() -> None:
    """Edge do spec (HLT-11): todas as noites na faixa neutra -> ambos os
    buckets nights=0 e médias null; janela vazia -> zeros honestos."""
    neutral = [
        _night(date(2026, 10, 1), 22000, 70, 60.0),
        _night(date(2026, 10, 2), 23000, 70, None),
    ]

    for nights in (neutral, []):
        dose = dose_response(nights)
        assert dose["short"] == {"nights": 0, "avg_hrv": None, "avg_score": None}
        assert dose["adequate"] == {"nights": 0, "avg_hrv": None, "avg_score": None}
    assert dose_response(neutral)["neutral_nights"] == 2
    assert dose_response([])["neutral_nights"] == 0


def test_dose_response_null_score_not_averaged() -> None:
    """Banco permite noite sem score: ela conta no bucket, mas não entra
    na média (nenhum número inventado); só scores None -> média None."""
    nights = [
        _night(date(2026, 10, 1), 21000, None, 65.0),
        _night(date(2026, 10, 2), 21000, 70, 67.0),
    ]

    dose = dose_response(nights)
    assert dose["short"] == {"nights": 2, "avg_hrv": 66.0, "avg_score": 70.0}

    dose = dose_response([_night(date(2026, 10, 1), 21000, None, 65.0)])
    assert dose["short"] == {"nights": 1, "avg_hrv": 65.0, "avg_score": None}


def test_dose_response_deterministic() -> None:
    """AD-003: mesma entrada -> mesmos valores (teste repete)."""
    nights = [_night(date(2026, 10, 1), 21000, 60, 68.0)]
    assert dose_response(nights) == dose_response(list(nights))


# ---------------------------------------------------------------
# weekday_pattern (HLT-10)
# ---------------------------------------------------------------


def test_weekday_pattern_seven_entries_seg_to_dom() -> None:
    """Done-when T2: 7 entradas seg..dom em ordem; dia vazio -> None/0;
    pin do banco real: sexta com 20664 s = 5,74 h."""
    nights = [
        _night(date(2026, 10, 12), 25200),  # segunda
        _night(date(2026, 10, 9), 20664),  # sexta
        _night(date(2026, 10, 16), 20664),  # sexta
    ]

    pattern = weekday_pattern(nights)

    assert pattern == [
        {"weekday": 0, "avg_duration_s": 25200.0, "nights": 1},
        {"weekday": 1, "avg_duration_s": None, "nights": 0},
        {"weekday": 2, "avg_duration_s": None, "nights": 0},
        {"weekday": 3, "avg_duration_s": None, "nights": 0},
        {"weekday": 4, "avg_duration_s": 20664.0, "nights": 2},
        {"weekday": 5, "avg_duration_s": None, "nights": 0},
        {"weekday": 6, "avg_duration_s": None, "nights": 0},
    ]
    assert round(pattern[4]["avg_duration_s"] / 3600, 2) == 5.74


def test_weekday_pattern_uses_wake_date_weekday() -> None:
    """Premissa do spec: weekday da data de acordar (a noite que virou
    domingo é de domingo) — 2026-10-16 é sexta, 2026-10-18 é domingo."""
    nights = [
        _night(date(2026, 10, 16), 21600),
        _night(date(2026, 10, 18), 21600),
    ]

    pattern = weekday_pattern(nights)
    nights_by_weekday = {e["weekday"]: e["nights"] for e in pattern}
    assert nights_by_weekday[4] == 1  # sexta
    assert nights_by_weekday[6] == 1  # domingo
    assert sum(e["nights"] for e in pattern) == 2


# ---------------------------------------------------------------
# regularity (HLT-04/12)
# ---------------------------------------------------------------


def test_regularity_midnight_trick() -> None:
    """Done-when T2 (design §Riscos): deitar 23:50 e 00:10 têm média
    00:00 — o deslocamento ±12h impede a meia-noite de virar meio-dia."""
    nights = [
        _night(date(2026, 10, 1), 21600, bed_min=1430, wake_min=388),
        _night(date(2026, 10, 2), 21600, bed_min=10, wake_min=392),
    ]

    result = regularity(nights)
    assert result == {"avg_bed_min": 0.0, "avg_wake_min": 390.0}


def test_regularity_averages_local_minutes() -> None:
    """Done-when T2: média dos minutos locais com 1 casa — 22:16 e 22:20
    -> 22:18 (1338)."""
    nights = [
        _night(date(2026, 10, 1), 21600, bed_min=1336, wake_min=388),
        _night(date(2026, 10, 2), 21600, bed_min=1340, wake_min=388),
    ]

    assert regularity(nights) == {"avg_bed_min": 1338.0, "avg_wake_min": 388.0}


def test_regularity_excludes_nights_without_times() -> None:
    """Edge do spec: noite sem bed_time/wake_time fica fora (nenhum
    horário inventado); sem elegíveis -> None."""
    partial = [
        _night(date(2026, 10, 1), 21600, bed_min=1330, wake_min=None),
        _night(date(2026, 10, 2), 21600, bed_min=None, wake_min=400),
        _night(date(2026, 10, 3), 21600, bed_min=1336, wake_min=388),
    ]
    assert regularity(partial) == {"avg_bed_min": 1336.0, "avg_wake_min": 388.0}

    assert regularity([_night(date(2026, 10, 1), 21600, bed_min=1336)]) is None
    assert regularity([]) is None


# ---------------------------------------------------------------
# local_minute (HLT-05 — conversão de fuso)
# ---------------------------------------------------------------


def test_local_minute_gmt_to_local_pin() -> None:
    """Done-when T2: 01:16 GMT naive -> 1336 (22:16 do dia anterior em
    São Paulo) — o GMT armazenado nunca é exibido como local (AC 5)."""
    bed = datetime(2026, 10, 16, 1, 16)
    assert local_minute(bed, SAO_PAULO) == 1336


def test_local_minute_crosses_midnight_and_other_zones() -> None:
    """Edge (design §Riscos): a conversão usa o datetime completo —
    02:59 GMT -> 23:59 do dia anterior local (1439); em UTC o mesmo
    01:16 é 76 (01:16), sem fuso hardcode."""
    assert local_minute(datetime(2026, 10, 16, 2, 59), SAO_PAULO) == 1439
    assert local_minute(datetime(2026, 10, 16, 1, 16), ZoneInfo("UTC")) == 76


# ---------------------------------------------------------------
# below_floor (HLT-04)
# ---------------------------------------------------------------


def test_below_floor_counts_and_pct() -> None:
    """Done-when T2: noites < 7h com pct de 1 casa; nenhuma abaixo ->
    0/0.0; janela vazia -> zeros (não erro)."""
    nights = [
        _night(date(2026, 10, 1), 24000),
        _night(date(2026, 10, 2), 25000),
        _night(date(2026, 10, 3), 26000),
    ]
    assert below_floor(nights) == {"nights": 2, "pct": 66.7}
    assert below_floor([_night(date(2026, 10, 1), 26000)]) == {"nights": 0, "pct": 0.0}
    assert below_floor([]) == {"nights": 0, "pct": 0.0}


# ---------------------------------------------------------------
# strength_weeks (HLT-12)
# ---------------------------------------------------------------


def test_strength_weeks_streak_window_and_current_week() -> None:
    """Done-when T2: streak de semanas completas (≥2 sessões) terminando
    na última completa; weeks_hit/weeks_total na janela; semana corrente
    (1 sessão, em andamento) separada e sem quebrar a streak."""
    sessions = [
        datetime(2026, 9, 15, 7, 0),  # semana de 09-14: 2 sessões
        datetime(2026, 9, 17, 19, 0),
        date(2026, 9, 22),  # semana de 09-21: 2
        date(2026, 9, 24),
        date(2026, 9, 29),  # semana de 09-28: 2
        date(2026, 10, 1),
        date(2026, 10, 6),  # semana de 10-05: 2
        date(2026, 10, 8),
        date(2026, 10, 13),  # semana corrente (10-12): 1, em andamento
    ]

    result = strength_weeks(sessions, date(2026, 10, 16), date(2026, 9, 28))

    assert result == {
        "streak_weeks": 4,
        "weeks_hit": 2,
        "weeks_total": 3,
        "current_week_sessions": 1,
    }


def test_strength_weeks_last_complete_week_below_two_breaks_streak() -> None:
    """Edge do spec: última semana completa com 1 sessão -> streak 0
    (não herda streak antiga); weeks_hit mostra a realidade da janela."""
    sessions = [
        date(2026, 9, 15),  # semana de 09-14: 2
        date(2026, 9, 17),
        date(2026, 9, 22),  # semana de 09-21: 2
        date(2026, 9, 24),
        date(2026, 10, 6),  # última completa (10-05): 1 só
    ]

    result = strength_weeks(sessions, date(2026, 10, 16), date(2026, 9, 21))

    assert result == {
        "streak_weeks": 0,
        "weeks_hit": 1,
        "weeks_total": 4,
        "current_week_sessions": 0,
    }


def test_strength_weeks_streak_exceeds_window() -> None:
    """Done-when T2: a streak conta semanas completas consecutivas mesmo
    antes do início da janela (spec AC 12 — pode exceder a janela)."""
    sessions = []
    for week_start in (date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21),
                       date(2026, 9, 28), date(2026, 10, 5)):
        sessions.append(week_start)
        sessions.append(date.fromordinal(week_start.toordinal() + 2))

    result = strength_weeks(sessions, date(2026, 10, 16), date(2026, 9, 28))

    assert result["streak_weeks"] == 5
    assert result["weeks_hit"] == 2
    assert result["weeks_total"] == 3


def test_strength_weeks_iso_year_boundary() -> None:
    """Edge (design §Riscos): virada de ano ISO — 30/12/2025 e 02/01/2026
    são a MESMA semana ISO (2026-W01, segunda em 29/12); a streak cruza o
    ano sem quebrar."""
    sessions = [
        date(2025, 12, 16),  # semana de 15/12: 2
        date(2025, 12, 18),
        date(2025, 12, 23),  # semana de 22/12: 2
        date(2025, 12, 25),
        date(2025, 12, 30),  # semana ISO 2026-W01: 2 (cruza o ano)
        date(2026, 1, 2),
        date(2026, 1, 6),  # semana corrente (05/01): 1
    ]

    result = strength_weeks(sessions, date(2026, 1, 7), date(2025, 12, 22))

    assert result == {
        "streak_weeks": 3,
        "weeks_hit": 2,
        "weeks_total": 3,
        "current_week_sessions": 1,
    }


# ---------------------------------------------------------------
# hrv_model (hrv-baseline — HRV-01..HRV-08, modelo científico)
# ---------------------------------------------------------------


def test_hrv_model_constants_match_spec() -> None:
    """Done-when T1 (réguas do backend): média móvel de 7 dias, banda =
    janela de 60 dias ± 0,75 DP amostral, threshold de 14 valores."""
    assert HRV_AVG_DAYS == 7
    assert HRV_BASELINE_DAYS == 60
    assert HRV_BASELINE_MIN_VALUES == 14
    assert HRV_BASELINE_SD_FACTOR == 0.75


def test_hrv_model_rolling_avg_fills_capture_gaps() -> None:
    """HRV-02: cada ponto é a média 7d sobre os valores disponíveis — o
    dia sem captura (10-03) é preenchido com a média da janela e a noite
    segue null; janela truncada no início do histórico usa o que existe
    (10-01 = só ela mesma; dias anteriores ficam None)."""
    rows = [
        (date(2026, 10, 1), 60.0),
        (date(2026, 10, 2), 70.0),
        (date(2026, 10, 4), 80.0),
    ]
    model = hrv_model(rows, days=7)

    assert [p["date"] for p in model["points"]] == [
        date(2026, 9, 28) + timedelta(days=i) for i in range(7)
    ]
    by_day = {p["date"]: p for p in model["points"]}
    assert by_day[date(2026, 9, 28)]["avg7"] is None  # janela vazia
    assert by_day[date(2026, 10, 1)]["avg7"] == 60.0  # truncada: só ela
    assert by_day[date(2026, 10, 2)]["avg7"] == 65.0  # (60+70)/2
    assert by_day[date(2026, 10, 3)]["value"] is None  # sem captura
    assert by_day[date(2026, 10, 3)]["avg7"] == 65.0  # preenchida (HRV-02)
    assert by_day[date(2026, 10, 4)]["avg7"] == 70.0  # (60+70+80)/3


def test_hrv_model_day_with_empty_window_has_no_avg() -> None:
    """HRV-03: mais de 7 dias seguidos sem captura -> o dia corrido fica
    sem ponto na linha (avg7 None) — nenhum valor é inventado."""
    rows = [
        (date(2026, 9, 1), 50.0),
        (date(2026, 10, 10), 60.0),
    ]
    model = hrv_model(rows, days=60)

    assert len(model["points"]) == 60
    by_day = {p["date"]: p for p in model["points"]}
    assert by_day[date(2026, 10, 4)]["avg7"] is None
    assert by_day[date(2026, 10, 4)]["value"] is None
    assert by_day[date(2026, 10, 9)]["avg7"] is None  # véspera: janela vazia
    assert by_day[date(2026, 10, 10)]["avg7"] == 60.0  # só ela na janela
    assert by_day[date(2026, 9, 5)]["avg7"] == 50.0  # 09-01 na janela 7d


def test_hrv_model_band_pin_and_threshold() -> None:
    """HRV-04/05: banda pinada à mão — 15 valores 60..88 (passo 2):
    média 74, SQ 1120, var amostral 1120/14 = 80, DP √80; banda =
    74 ± 0,75√80 = (67,291796, 80,708204). Threshold: 13 valores na
    janela -> sem banda; 14 -> banda. Bônus determinístico: tendência de
    alta deixa a média 7d (82) acima da banda -> UNBALANCED (HRV-06)."""
    rows = [
        (date(2026, 9, 16) + timedelta(days=i), 60.0 + 2.0 * i)
        for i in range(15)
    ]
    model = hrv_model(rows, days=20)

    by_day = {p["date"]: p for p in model["points"]}
    assert by_day[date(2026, 9, 28)]["band_low"] is None  # 13 valores
    assert by_day[date(2026, 9, 29)]["band_low"] is not None  # 14 valores
    last = by_day[date(2026, 9, 30)]
    assert round(last["band_low"], 6) == 67.291796
    assert round(last["band_high"], 6) == 80.708204
    assert last["avg7"] == 82.0  # (76+78+80+82+84+86+88)/7
    assert model["current"]["status"] == "UNBALANCED"


def test_hrv_model_status_balanced_on_inclusive_edge() -> None:
    """HRV-06 edge (limites inclusos): 15 valores iguais -> DP 0, banda
    (70, 70), média 7d 70 — igual ao limite é BALANCED, não UNBALANCED."""
    rows = [(date(2026, 9, 16) + timedelta(days=i), 70.0) for i in range(15)]
    model = hrv_model(rows, days=20)

    assert model["current"] == {
        "date": date(2026, 9, 30),
        "value": 70.0,
        "avg7": 70.0,
        "band_low": 70.0,
        "band_high": 70.0,
        "status": "BALANCED",
    }


def test_hrv_model_status_unbalanced_after_suppression() -> None:
    """HRV-06: queda recente — 14 dias a 80 e 7 a 20; média 7d 20 fica
    abaixo da banda (média 60 ± 0,75√840 = 38,262935..81,737065) ->
    UNBALANCED."""
    rows = [
        *((date(2026, 9, 14) + timedelta(days=i), 80.0) for i in range(14)),
        *((date(2026, 9, 28) + timedelta(days=i), 20.0) for i in range(7)),
    ]
    model = hrv_model(rows, days=21)

    current = model["current"]
    assert current["date"] == date(2026, 10, 4)
    assert current["value"] == 20.0
    assert current["avg7"] == 20.0
    assert round(current["band_low"], 6) == 38.262935
    assert round(current["band_high"], 6) == 81.737065
    assert current["status"] == "UNBALANCED"


def test_hrv_model_without_band_status_is_none() -> None:
    """HRV-08: menos de 14 valores na janela do último dia -> banda null
    e status None (o card mostra "coletando linha de base"); a janela de
    exibição continua sendo `days` dias corridos (edge do spec — história
    menor que a janela gera dias corrido vazios, não janela inventada)."""
    rows = [
        (date(2026, 10, 13), 82.0),
        (date(2026, 10, 14), 68.0),
        (date(2026, 10, 15), 75.0),
    ]
    model = hrv_model(rows, days=60)

    assert len(model["points"]) == 60
    assert model["points"][0]["date"] == date(2026, 8, 17)
    assert model["current"] == {
        "date": date(2026, 10, 15),
        "value": 75.0,
        "avg7": 75.0,
        "band_low": None,
        "band_high": None,
        "status": None,
    }
    assert all(p["band_low"] is None for p in model["points"])


def test_hrv_model_window_is_calendar_days_ending_at_latest_data() -> None:
    """HRV-01: a janela termina na última data COM dado (não em hoje) e
    tem `days` dias corridos — dado anterior à janela fica fora dos
    pontos (só alimenta as janelas móveis)."""
    rows = [
        (date(2026, 8, 20), 50.0),
        (date(2026, 10, 15), 70.0),
    ]
    model = hrv_model(rows, days=10)

    assert len(model["points"]) == 10
    assert model["points"][0]["date"] == date(2026, 10, 6)
    assert model["points"][-1]["date"] == date(2026, 10, 15)
    assert [p["value"] for p in model["points"] if p["value"] is not None] == [
        70.0
    ]  # 08-20 fora da exibição
    assert model["points"][-1]["avg7"] == 70.0
