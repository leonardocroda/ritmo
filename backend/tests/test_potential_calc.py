"""Calc do painel Performance (ex-Potencial) (potential/calc.py) — funções puras, pins literais.

Cenários derivados dos done-when de T6/T7, dos ACs do endpoint
(POT-07/08/09/10/14) e dos edge cases do spec: dedup prova×PR na
mesma data, PR sem data fora da timeline, PR/prova inválidos fora,
âncora Riegel no 5K, média só das presentes, sinal do decay. As
entradas são SimpleNamespace com os mesmos atributos das linhas do
banco; valores afirmados são literais (lição L-001), derivados da
forma fechada de Daniels (T1) — nunca constantes compartilhadas com a
implementação.
"""

from datetime import date, datetime
from types import SimpleNamespace

from app.potential.calc import (
    CANONICAL,
    decay,
    demonstrated,
    predictions,
    riegel_time,
    timeline_points,
)
from app.vdot.calibration import Calibration


def _pr(event, value, pr_date=None):
    return SimpleNamespace(event=event, value=value, pr_date=pr_date)


def _race(name, start, distance_m, duration_s):
    return SimpleNamespace(
        name=name, start_time=start, distance_m=distance_m, duration_s=duration_s
    )


# Fixture real (sondas de 15/10/2026 + design §Contrato): os 4 PRs
# canônicos datados + 1K/LONGEST_RUN fora + prova de Londrina na data
# da maratona (dedup) + prova 10K solta + teste de calibração vigente.
CALIBRATION = Calibration(
    vdot=50.2,
    source="10K em 41:15",
    test_date=date(2026, 10, 3),
    distance_m=10012,
    time_s=2475,
)

REAL_PRS = [
    _pr("FASTEST_10K", 2425.0, date(2024, 10, 5)),
    _pr("FASTEST_5K", 1163.8299560546875, date(2026, 4, 26)),
    _pr("FASTEST_HALF_MARATHON", 5409.188, date(2026, 5, 3)),
    _pr("FASTEST_MARATHON", 13925.76, date(2026, 7, 5)),
    _pr("FASTEST_1K", 180.0, date(2026, 2, 1)),  # não canônico
    _pr("LONGEST_RUN", 32000.0, date(2026, 3, 15)),  # distância, não tempo
]

REAL_RACES = [
    _race(
        "Londrina Corrida",  # mesma data do PR da maratona -> dedup
        datetime(2026, 7, 5, 7, 10, 53),
        42300.0,
        14083.0,
    ),
    _race("Corrida de Aniversário", datetime(2025, 6, 15, 7, 0, 0), 10000.0, 2500.0),
]


def test_canonical_distances_match_spec() -> None:
    """Done-when T6: as 4 distâncias canônicas do spec, em metros."""
    assert CANONICAL == {
        "5K": 5000,
        "10K": 10000,
        "HALF_MARATHON": 21097.5,
        "MARATHON": 42195,
    }


def test_riegel_time_pins_anchored_on_5k() -> None:
    """Done-when T6: Riegel 1.06 ancorado no 5K (1163,83 s @ 5000 m) —
    10K ≈ 2426,5 · meia ≈ 5353,8 · maratona ≈ 11162,4 (cálculo manual)."""
    assert round(riegel_time(1163.83, 5000, 10000), 1) == 2426.5
    assert round(riegel_time(1163.83, 5000, 21097.5), 1) == 5353.8
    assert round(riegel_time(1163.83, 5000, 42195), 1) == 11162.4


def test_riegel_time_uses_given_exponent() -> None:
    """O expoente é parâmetro (default 1.06 do spec), não constante interna."""
    assert riegel_time(1163.83, 5000, 10000) == riegel_time(1163.83, 5000, 10000, 1.06)
    assert riegel_time(1163.83, 5000, 10000, 1.05) != riegel_time(1163.83, 5000, 10000, 1.06)


def test_timeline_points_real_fixture_chronological() -> None:
    """Done-when T6: timeline com os dados reais — PRs canônicos datados +
    prova solta + teste de calibração, em ordem de data; vdot de cada ponto
    = calculate_vdot (pins 51,32/49,52/51,62/50,88/39,48/50,18)."""
    points = timeline_points(REAL_PRS, REAL_RACES, CALIBRATION)
    assert [(p["date"], p["source"], p["label"]) for p in points] == [
        (date(2024, 10, 5), "pr", "10K 40:25"),
        (date(2025, 6, 15), "prova", "Corrida de Aniversário"),
        (date(2026, 4, 26), "pr", "5K 19:23"),
        (date(2026, 5, 3), "pr", "Meia 1:30:09"),
        (date(2026, 7, 5), "pr", "Maratona 3:52:05"),
        (date(2026, 10, 3), "teste", "10K em 41:15"),
    ]
    assert [round(p["vdot"], 2) for p in points] == [51.32, 49.52, 51.62, 50.88, 39.48, 50.18]
    assert [(p["distance_m"], p["time_s"]) for p in points] == [
        (10000, 2425.0),
        (10000, 2500.0),
        (5000, 1163.8299560546875),
        (21097.5, 5409.188),
        (42195, 13925.76),
        (10012, 2475),
    ]


def test_timeline_points_dedup_race_on_pr_date() -> None:
    """POT-09 (premissa do spec): prova na mesma data de um PR canônico não
    vira ponto — o PR certificado (3:52:05) prevalece sobre a atividade com
    GPS que continuou após a chegada; prova em data livre permanece."""
    points = timeline_points(REAL_PRS, REAL_RACES, CALIBRATION)
    dates_sources = [(p["date"], p["source"]) for p in points]
    assert (date(2026, 7, 5), "prova") not in dates_sources
    assert (date(2026, 7, 5), "pr") in dates_sources
    assert (date(2025, 6, 15), "prova") in dates_sources  # data livre: ponto válido


def test_timeline_points_excludes_pr_without_date_and_non_canonical() -> None:
    """Edge do spec: PR sem data não vira ponto (não há como plotar);
    1K/LONGEST_RUN ficam fora (Out of Scope — não são marcadores aeróbicos)."""
    prs = [
        _pr("FASTEST_5K", 1163.83),  # sem data
        _pr("FASTEST_1K", 180.0, date(2026, 2, 1)),
        _pr("LONGEST_RUN", 32000.0, date(2026, 3, 15)),
    ]
    points = timeline_points(prs, [], CALIBRATION)
    assert [p["source"] for p in points] == ["teste"]
    assert points[0]["label"] == "10K em 41:15"


def test_timeline_points_excludes_invalid_pr_efforts() -> None:
    """Edge do spec: distance_m/time_s 0 ou negativo -> fora da timeline e do
    demonstrado (VDOT indefinido), sem crash."""
    prs = [
        _pr("FASTEST_5K", 0, date(2026, 1, 1)),
        _pr("FASTEST_10K", -2425.0, date(2026, 1, 2)),
        _pr("FASTEST_HALF_MARATHON", None, date(2026, 1, 3)),
        _pr("FASTEST_MARATHON", 13925.76, date(2026, 7, 5)),
    ]
    points = timeline_points(prs, [], CALIBRATION)
    assert [p["source"] for p in points] == ["pr", "teste"]
    assert points[0]["label"] == "Maratona 3:52:05"


def test_timeline_points_excludes_invalid_race_efforts() -> None:
    """Mesma validade do PR para provas: corrida sem distância (esteira) ou
    sem duração não vira ponto (VDOT indefinido)."""
    races = [
        _race("Esteira", datetime(2026, 2, 1, 6, 0, 0), 0.0, 1800.0),
        _race("Sem duração", datetime(2026, 2, 2, 6, 0, 0), 10000.0, None),
        _race("Prova válida", datetime(2026, 2, 3, 6, 0, 0), 10000.0, 2500.0),
    ]
    points = timeline_points([], races, CALIBRATION)
    assert [p["label"] for p in points] == ["Prova válida", "10K em 41:15"]


def test_demonstrated_max_vdot_and_empty_list() -> None:
    """Done-when T6: demonstrado = maior VDOT (fixture real -> 51,62 do 5K);
    lista vazia -> None (nenhum número inventado)."""
    points = timeline_points(REAL_PRS, REAL_RACES, CALIBRATION)
    assert round(demonstrated(points), 2) == 51.62
    assert demonstrated([]) is None


def test_timeline_points_deterministic() -> None:
    """Done-when T6 (AD-003): mesma entrada -> mesmos valores (teste repete)."""
    first = timeline_points(REAL_PRS, REAL_RACES, CALIBRATION)
    second = timeline_points(REAL_PRS, REAL_RACES, CALIBRATION)
    assert first == second


# Fixtures de predições (sonda real de 15/10/2026): tempos do preditor
# do Garmin por evento canônico; None/ausente = evento não sincronizado.
REAL_GARMIN = {"5K": 1165.0, "10K": 2447.0, "HALF_MARATHON": 5437.0, "MARATHON": 11989.0}


def test_predictions_with_all_estimates_present() -> None:
    """POT-10 (done-when T7): 4 distâncias com Garmin + Riegel (âncora 5K) +
    equivalência VDOT + média honesta das 3 + PR com data (pins do design)."""
    rows = predictions(REAL_GARMIN, 1163.8299560546875, 50.2, REAL_PRS)

    assert list(rows.keys()) == ["5K", "10K", "HALF_MARATHON", "MARATHON"]
    # Riegel ancorado no 5K: a âncora projeta a si mesma; demais distâncias
    assert rows["5K"]["riegel_s"] == 1163.8
    assert rows["10K"]["riegel_s"] == 2426.5
    assert rows["HALF_MARATHON"]["riegel_s"] == 5353.8
    assert rows["MARATHON"]["riegel_s"] == 11162.4
    # Equivalência do VDOT corrente (50.2)
    assert rows["5K"]["vdot_s"] == 1191.9
    assert rows["10K"]["vdot_s"] == 2471.1
    assert rows["HALF_MARATHON"]["vdot_s"] == 5472.3
    assert rows["MARATHON"]["vdot_s"] == 11401.4
    # Garmin da sonda real
    assert rows["5K"]["garmin_s"] == 1165.0
    assert rows["10K"]["garmin_s"] == 2447.0
    assert rows["HALF_MARATHON"]["garmin_s"] == 5437.0
    assert rows["MARATHON"]["garmin_s"] == 11989.0
    # Média honesta das 3 presentes (ex.: 5K = (1165 + 1163.8 + 1191.9) / 3)
    assert rows["5K"]["average_s"] == 1173.6
    assert rows["10K"]["average_s"] == 2448.2
    assert rows["HALF_MARATHON"]["average_s"] == 5421.0
    assert rows["MARATHON"]["average_s"] == 11517.6
    # PR histórico com data
    assert rows["5K"]["pr_s"] == 1163.8
    assert rows["5K"]["pr_date"] == date(2026, 4, 26)
    assert rows["MARATHON"]["pr_s"] == 13925.8
    assert rows["MARATHON"]["pr_date"] == date(2026, 7, 5)


def test_predictions_without_5k_anchor_riegel_null_everywhere() -> None:
    """Edge do spec (POT-10): sem PR de 5K -> riegel_s None em TODAS as
    distâncias (âncora ausente, não substituída por 10K/maratona) e a média
    honesta usa só as presentes."""
    rows = predictions(dict(REAL_GARMIN), None, 50.2, REAL_PRS)

    assert all(row["riegel_s"] is None for row in rows.values())
    # média = (garmin + vdot) / 2 — ex. 10K = (2447 + 2471.1) / 2
    assert rows["10K"]["average_s"] == 2459.1
    assert rows["5K"]["average_s"] == 1178.5  # (1165 + 1191.9) / 2
    # PR de outras distâncias continuam exibidos
    assert rows["10K"]["pr_s"] == 2425.0
    assert rows["10K"]["pr_date"] == date(2024, 10, 5)


def test_predictions_absent_garmin_out_of_average() -> None:
    """Edge do spec (POT-10): predição não sincronizada (None ou evento
    ausente) -> "—" e a média honesta usa Riegel + VDOT (nunca conta o
    ausente)."""
    garmin = dict(REAL_GARMIN, **{"10K": None})
    del garmin["MARATHON"]  # evento nem veio no payload
    rows = predictions(garmin, 1163.83, 50.2, [])

    assert rows["10K"]["garmin_s"] is None
    assert rows["10K"]["average_s"] == 2448.8  # (2426.5 + 2471.1) / 2
    assert rows["MARATHON"]["garmin_s"] is None
    assert rows["MARATHON"]["average_s"] == 11281.9  # (11162.4 + 11401.4) / 2
    # sem PR nenhum: colunas de PR vazias
    assert rows["5K"]["pr_s"] is None
    assert rows["5K"]["pr_date"] is None


def test_predictions_invalid_anchor_time_does_not_project() -> None:
    """Edge do spec: âncora 0/negativa não projeta (esforço inválido não
    existe) — riegel_s NULL, mesma postura de não ter PR de 5K."""
    rows = predictions(REAL_GARMIN, 0, 50.2, REAL_PRS)
    assert all(row["riegel_s"] is None for row in rows.values())
    rows = predictions(REAL_GARMIN, -1163.83, 50.2, REAL_PRS)
    assert all(row["riegel_s"] is None for row in rows.values())


def test_decay_real_fixture_marathon_biggest_gap() -> None:
    """POT-14 (done-when T7): decay com o fixture real — 4 linhas na ordem
    canônica; sinal pinado (real mais lento -> delta negativo = gap); a
    maratona tem o maior gap (execução), 5K é overperform (positivo)."""
    rows = decay(REAL_PRS, 50.2)
    assert [row["event"] for row in rows] == ["5K", "10K", "HALF_MARATHON", "MARATHON"]
    by_event = {row["event"]: row for row in rows}
    assert by_event["5K"] == {"event": "5K", "real_pace_s": 232.8, "ideal_pace_s": 238.4, "delta_pct": 2.3}
    assert by_event["10K"] == {"event": "10K", "real_pace_s": 242.5, "ideal_pace_s": 247.1, "delta_pct": 1.9}
    assert by_event["HALF_MARATHON"] == {
        "event": "HALF_MARATHON", "real_pace_s": 256.4, "ideal_pace_s": 259.4, "delta_pct": 1.2,
    }
    assert by_event["MARATHON"] == {
        "event": "MARATHON", "real_pace_s": 330.0, "ideal_pace_s": 270.2, "delta_pct": -22.1,
    }
    biggest_gap = min(rows, key=lambda row: row["delta_pct"])
    assert biggest_gap["event"] == "MARATHON"  # maior gap negativo (POT-29)


def test_decay_excludes_distances_without_pr() -> None:
    """Spec (POT-14): distância sem PR canônico fica de fora — nenhum número
    inventado; 1K/LONGEST_RUN nunca entram (não canônicos)."""
    rows = decay([REAL_PRS[0], *REAL_PRS[4:]], 50.2)  # só 10K + não canônicos
    assert [row["event"] for row in rows] == ["10K"]


def test_decay_empty_without_canonical_prs() -> None:
    """Spec: sem PR canônico -> decay [] (estado vazio, não erro)."""
    assert decay([], 50.2) == []
    assert decay([_pr("FASTEST_1K", 180.0, date(2026, 2, 1))], 50.2) == []


def test_decay_invalid_pr_effort_excluded() -> None:
    """Edge do spec: PR com tempo 0/None não vira linha do decay (pace
    indefinido) — sem crash e sem número inventado."""
    prs = [
        _pr("FASTEST_5K", 0, date(2026, 1, 1)),
        _pr("FASTEST_10K", None, date(2026, 1, 2)),
        _pr("FASTEST_MARATHON", 13925.76, date(2026, 7, 5)),
    ]
    rows = decay(prs, 50.2)
    assert [row["event"] for row in rows] == ["MARATHON"]
