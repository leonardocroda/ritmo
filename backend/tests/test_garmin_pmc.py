"""PMC determinística (T7) — CTL/ATL/TSB/ACWR conferidos contra cálculo manual.

Cenários derivados do spec (SYNC-22/23/24). O cálculo manual
(`_manual_pmc`) é uma implementação independente escrita no próprio
teste a partir das fórmulas do spec — nunca um import do módulo
implementado (Independent Test do spec, lição L-001). As âncoras
literais (100 - 20/42 etc.) vêm da conta feita à mão.
"""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, DailyLoad
from app.garmin.pmc import aggregate_daily_loads, recompute


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _activity(day: date, load: float | None, garmin_id: str) -> Activity:
    """Atividade mínima com carga literal — a data é o wall clock local."""
    return Activity(
        user_id=1,
        garmin_id=garmin_id,
        start_time=datetime.combine(day, time(7, 0)),
        activity_type="running",
        name=f"Run {garmin_id}",
        distance_m=5000.0,
        duration_s=1800.0,
        training_load=load,
    )


def _manual_pmc(loads: list[float]) -> list[dict]:
    """Cálculo manual puro (SYNC-22/24): CTL α=1/42, ATL α=1/7, TSB, ACWR.

    A EWMA nasce do primeiro load do dia 1 (semente do design); ACWR só
    quando existem 28 dias completos de carga.
    """
    ctl = atl = loads[0]
    rows = []
    for i, load in enumerate(loads):
        if i > 0:
            ctl = ctl + (load - ctl) / 42
            atl = atl + (load - atl) / 7
        acwr = None
        if i >= 27:
            acwr = sum(loads[i - 6 : i + 1]) / (sum(loads[i - 27 : i + 1]) / 4)
        rows.append({"ctl": ctl, "atl": atl, "tsb": ctl - atl, "acwr": acwr})
    return rows


def _load_rows(db) -> list[DailyLoad]:
    return db.execute(select(DailyLoad).order_by(DailyLoad.date)).scalars().all()


def test_aggregate_sums_training_load_per_day(db):
    """SYNC-22: soma por data local; 2 atividades no mesmo dia somam; gaps ficam 0."""
    db.add(_activity(date(2024, 1, 1), 100.0, "a1"))
    db.add(_activity(date(2024, 1, 6), 100.0, "b1"))
    db.add(_activity(date(2024, 1, 6), 50.0, "b2"))
    db.commit()

    assert aggregate_daily_loads(db, 1) == [
        (date(2024, 1, 1), 100.0),
        (date(2024, 1, 2), 0.0),
        (date(2024, 1, 3), 0.0),
        (date(2024, 1, 4), 0.0),
        (date(2024, 1, 5), 0.0),
        (date(2024, 1, 6), 150.0),
    ]


def test_aggregate_missing_training_load_counts_zero(db):
    """SYNC-24: atividade sem training_load conta carga 0 no dia (não some o dia)."""
    db.add(_activity(date(2024, 1, 1), None, "no-load"))
    db.add(_activity(date(2024, 1, 2), 30.0, "with-load"))
    db.commit()

    assert aggregate_daily_loads(db, 1) == [(date(2024, 1, 1), 0.0), (date(2024, 1, 2), 30.0)]


def test_aggregate_empty_without_activities(db):
    """Sem atividades não existe série — agregado vazio."""
    assert aggregate_daily_loads(db, 1) == []


def test_recompute_matches_manual_calc_3_days(db):
    """SYNC-22 (Independent Test): ≥ 3 dias batem com o cálculo manual puro."""
    db.add(_activity(date(2024, 1, 1), 100.0, "a1"))
    db.add(_activity(date(2024, 1, 2), 80.0, "a2"))
    db.add(_activity(date(2024, 1, 4), 120.0, "a4"))
    db.add(_activity(date(2024, 1, 5), None, "a5"))  # SYNC-24: sem load
    db.commit()

    assert recompute(db, 1, date(2024, 1, 1), date(2024, 1, 5)) == 5
    db.commit()

    rows = _load_rows(db)
    assert [r.date for r in rows] == [date(2024, 1, d) for d in (1, 2, 3, 4, 5)]
    manual = _manual_pmc([100.0, 80.0, 0.0, 120.0, 0.0])
    for row, expected in zip(rows, manual):
        assert row.ctl == pytest.approx(expected["ctl"])
        assert row.atl == pytest.approx(expected["atl"])
        assert row.tsb == pytest.approx(expected["tsb"])
        assert row.acwr is expected["acwr"]  # < 28d de histórico: None

    # Âncoras literais — a conta feita à mão (α=1/42 e 1/7):
    assert rows[0].ctl == 100.0
    assert rows[0].atl == 100.0
    assert rows[0].tsb == 0.0
    assert rows[1].ctl == pytest.approx(100 - 20 / 42)
    assert rows[1].atl == pytest.approx(100 - 20 / 7)
    assert rows[1].tsb == pytest.approx(100 / 42)


def test_recompute_acwr_from_complete_28d_window(db):
    """SYNC-22: ACWR None até 28d completos; depois soma(7d)/(soma(28d)/4)."""
    for i in range(31):
        day = date(2024, 1, 1) + timedelta(days=i)
        load = 200.0 if i == 30 else 50.0
        db.add(_activity(day, load, f"run-{i:02d}"))
    db.commit()

    assert recompute(db, 1, date(2024, 1, 1), date(2024, 1, 31)) == 31
    db.commit()

    rows = _load_rows(db)
    assert rows[26].date == date(2024, 1, 27)
    assert rows[26].acwr is None  # 27 dias de histórico: janela incompleta
    assert rows[27].date == date(2024, 1, 28)
    assert rows[27].acwr == pytest.approx(350 / (1400 / 4))  # carga constante -> 1.0
    assert rows[29].date == date(2024, 1, 30)
    assert rows[29].acwr == pytest.approx(1.0)
    # Dia do pico: soma(7d)=500 (6×50 + 200); soma(28d)=1550 -> 500/(1550/4)
    assert rows[30].date == date(2024, 1, 31)
    assert rows[30].acwr == pytest.approx(500 / 387.5)


def test_recompute_preserves_history_and_seeds_from_last_prior_row(db):
    """SYNC-23: recompute só da janela afetada; linhas anteriores intocadas.

    A semente CTL/ATL vem da última linha anterior à janela — por isso
    os dias recalculados batem com a primeira execução, mesmo começando
    do meio da série.
    """
    db.add(_activity(date(2024, 1, 1), 100.0, "a1"))
    db.add(_activity(date(2024, 1, 2), 80.0, "a2"))
    db.add(_activity(date(2024, 1, 4), 120.0, "a4"))
    db.add(_activity(date(2024, 1, 5), None, "a5"))
    db.commit()
    assert recompute(db, 1, date(2024, 1, 1), date(2024, 1, 5)) == 5
    db.commit()

    first_run = _load_rows(db)
    untouched = [(r.id, r.ctl, r.atl, r.tsb) for r in first_run[:3]]

    # Janela afetada: só os dias 4 e 5 (SYNC-23 — nada antes disso muda)
    assert recompute(db, 1, date(2024, 1, 4), date(2024, 1, 5)) == 2
    db.commit()

    second_run = _load_rows(db)
    assert [(r.id, r.ctl, r.atl, r.tsb) for r in second_run[:3]] == untouched
    assert [r.date for r in second_run] == [r.date for r in first_run]

    # Semente vinda da linha do dia 3 (a última anterior à janela):
    ctl3, atl3 = first_run[2].ctl, first_run[2].atl
    ctl4 = ctl3 + (120 - ctl3) / 42
    atl4 = atl3 + (120 - atl3) / 7
    ctl5 = ctl4 + (0 - ctl4) / 42
    atl5 = atl4 + (0 - atl4) / 7
    assert second_run[3].ctl == pytest.approx(ctl4)
    assert second_run[3].atl == pytest.approx(atl4)
    assert second_run[3].tsb == pytest.approx(ctl4 - atl4)
    assert second_run[4].ctl == pytest.approx(ctl5)
    assert second_run[4].atl == pytest.approx(atl5)
    # Cargas unchanged -> valores idênticos aos da primeira execução
    assert second_run[3].ctl == pytest.approx(first_run[3].ctl)
    assert second_run[4].tsb == pytest.approx(first_run[4].tsb)


def test_recompute_without_activities_writes_nothing(db):
    """Sem série não há o que recalcular — 0 linhas escritas."""
    assert recompute(db, 1, date(2024, 1, 1), date(2024, 1, 5)) == 0
    db.commit()
    assert db.execute(select(func.count()).select_from(DailyLoad)).scalar_one() == 0


def test_recompute_extends_series_to_today_with_zero_days(db):
    """A série vai até `today` mesmo sem atividade — dias sem carga decaem a EWMA."""
    db.add(_activity(date(2024, 1, 1), 100.0, "only"))
    db.commit()

    assert recompute(db, 1, date(2024, 1, 1), date(2024, 1, 4)) == 4
    db.commit()

    rows = _load_rows(db)
    assert [r.date for r in rows] == [date(2024, 1, d) for d in (1, 2, 3, 4)]
    manual = _manual_pmc([100.0, 0.0, 0.0, 0.0])
    for row, expected in zip(rows, manual):
        assert row.ctl == pytest.approx(expected["ctl"])
        assert row.atl == pytest.approx(expected["atl"])
        assert row.acwr is None  # 4 dias de histórico: janela de 28d incompleta
    assert rows[3].ctl == pytest.approx(manual[3]["ctl"])
