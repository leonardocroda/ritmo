"""Calc do painel Potencial (potential/calc.py) — funções puras, pins literais.

Cenários derivados dos done-when de T6 e dos ACs do endpoint
(POT-07/08/09) + edge cases do spec: dedup prova×PR na mesma data, PR
sem data fora da timeline, PR/prova inválidos fora. As entradas são
SimpleNamespace com os mesmos atributos das linhas do banco; valores
afirmados são literais (lição L-001), derivados da forma fechada de
Daniels (T1) — nunca constantes compartilhadas com a implementação.
"""

from datetime import date, datetime
from types import SimpleNamespace

from app.potential.calc import CANONICAL, demonstrated, riegel_time, timeline_points
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
