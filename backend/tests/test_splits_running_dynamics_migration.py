"""Running dynamics por volta — colunas na `Split` + migração idempotente (T1).

Integração no Postgres do compose: tabela `splits` com as 4 colunas
nullable `ground_contact_time_ms`, `stride_length_cm`,
`vertical_oscillation_cm`, `vertical_ratio`. O init_db migra idempotente
em bases antigas (sem as colunas). Volta sem dado = NULL, nunca zero
inventado.
"""

from datetime import date

import pytest
from sqlalchemy import text

from app.db.engine import SessionLocal, engine, init_db
from app.db.models import Activity, Split, User


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def test_split_model_has_running_dynamics_columns(db) -> None:
    """Done-when T1: `Split` com as 4 colunas de running dynamics
    nullable — volta sem dado fica NULL."""
    activity = Activity(
        user_id=1,
        garmin_id="act_rd_1",
        start_time=date(2024, 1, 15),
        activity_type="running",
        name="Morning Run",
        distance_m=5000.0,
        duration_s=1800.0,
    )
    db.add(activity)
    db.flush()

    split = Split(
        user_id=1,
        activity_id=activity.id,
        idx=1,
        dist_m=1000.0,
        duration_s=360.0,
        pace_s=360.0,
        # running dynamics ausentes -> NULL
    )
    db.add(split)
    db.commit()

    fetched = db.get(Split, split.id)
    assert fetched is not None
    assert fetched.ground_contact_time_ms is None
    assert fetched.stride_length_cm is None
    assert fetched.vertical_oscillation_cm is None
    assert fetched.vertical_ratio is None


def test_split_accepts_running_dynamics_values(db) -> None:
    """Done-when T1: `Split` aceita valores nas 4 colunas de running
    dynamics quando o lapDTO do Garmin os traz."""
    activity = Activity(
        user_id=1,
        garmin_id="act_rd_2",
        start_time=date(2024, 1, 15),
        activity_type="running",
        name="Morning Run",
        distance_m=5000.0,
        duration_s=1800.0,
    )
    db.add(activity)
    db.flush()

    split = Split(
        user_id=1,
        activity_id=activity.id,
        idx=1,
        dist_m=1000.0,
        duration_s=360.0,
        pace_s=360.0,
        ground_contact_time_ms=250,
        stride_length_cm=145.5,
        vertical_oscillation_cm=8.2,
        vertical_ratio=5.8,
    )
    db.add(split)
    db.commit()

    fetched = db.get(Split, split.id)
    assert fetched.ground_contact_time_ms == 250
    assert fetched.stride_length_cm == 145.5
    assert fetched.vertical_oscillation_cm == 8.2
    assert fetched.vertical_ratio == 5.8


def test_init_db_creates_split_running_dynamics_columns(db) -> None:
    """Done-when T1: init_db cria as 4 colunas de running dynamics na
    tabela `splits` em base nova."""
    with engine.begin() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'splits'"
                )
            )
        }
    assert "ground_contact_time_ms" in columns
    assert "stride_length_cm" in columns
    assert "vertical_oscillation_cm" in columns
    assert "vertical_ratio" in columns


def test_init_db_migrates_pre_split_schema(db) -> None:
    """Done-when T1: base criada antes da feature running dynamics tem
    `splits` sem as colunas — o init_db migra idempotente (ALTER TABLE)
    sem quebrar dados existentes. Simulação: derruba as 4 colunas e roda
    init_db de novo."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE splits DROP COLUMN ground_contact_time_ms"))
        conn.execute(text("ALTER TABLE splits DROP COLUMN stride_length_cm"))
        conn.execute(text("ALTER TABLE splits DROP COLUMN vertical_oscillation_cm"))
        conn.execute(text("ALTER TABLE splits DROP COLUMN vertical_ratio"))

    init_db()

    with engine.begin() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'splits'"
                )
            )
        }
    assert "ground_contact_time_ms" in columns
    assert "stride_length_cm" in columns
    assert "vertical_oscillation_cm" in columns
    assert "vertical_ratio" in columns


def test_init_db_rerun_is_idempotent_for_splits(db) -> None:
    """Done-when T1: re-executar init_db não duplica colunas nem dados
    existentes da tabela `splits`."""
    # Cria um split com running dynamics
    activity = Activity(
        user_id=1,
        garmin_id="act_rd_3",
        start_time=date(2024, 1, 15),
        activity_type="running",
        name="Morning Run",
        distance_m=5000.0,
        duration_s=1800.0,
    )
    db.add(activity)
    db.flush()
    split = Split(
        user_id=1,
        activity_id=activity.id,
        idx=1,
        dist_m=1000.0,
        duration_s=360.0,
        ground_contact_time_ms=250,
    )
    db.add(split)
    db.commit()

    init_db()

    fetched = db.get(Split, split.id)
    assert fetched is not None
    assert fetched.ground_contact_time_ms == 250

    # Contagem de splits permanece 1 (não duplicou)
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM splits")).scalar()
    assert count == 1
