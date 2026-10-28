"""Modelos de tênis — Shoe + Activity.shoe_id + migração idempotente (T1).

Integração no Postgres do compose: tabela `shoes` com unique
`uq_shoe_user_strava` (múltiplos NULL permitidos), FK `Activity.shoe_id`
com `ondelete="SET NULL"` e índice. O init_db migra idempotente em
bases antigas (sem a tabela/coluna).
"""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.engine import SessionLocal, engine, init_db
from app.db.models import Activity, Shoe, User


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def test_shoe_model_complete(db) -> None:
    """Done-when T1: Shoe com todas as colunas do design, unique
    `uq_shoe_user_strava`, created_at default _utcnow."""
    shoe = Shoe(
        user_id=1,
        name="Kayano 30",
        brand="ASICS",
        model="Gel-Kayano 30",
        acquired_date=date(2024, 1, 15),
        initial_km=100.0,
        max_km=800.0,
        status="ativo",
        strava_gear_id="g12345",
    )
    db.add(shoe)
    db.commit()

    fetched = db.get(Shoe, shoe.id)
    assert fetched is not None
    assert fetched.name == "Kayano 30"
    assert fetched.brand == "ASICS"
    assert fetched.model == "Gel-Kayano 30"
    assert fetched.acquired_date == date(2024, 1, 15)
    assert fetched.initial_km == 100.0
    assert fetched.max_km == 800.0
    assert fetched.status == "ativo"
    assert fetched.strava_gear_id == "g12345"
    assert fetched.created_at is not None


def test_unique_shoe_user_strava_allows_multiple_nulls(db) -> None:
    """Done-when T1: unique `uq_shoe_user_strava` permite múltiplos
    NULL em strava_gear_id (Postgres trata NULL ≠ NULL) — tênis criados
    manualmente não têm gear_id."""
    db.add(Shoe(user_id=1, name="Tênis A"))
    db.add(Shoe(user_id=1, name="Tênis B"))
    db.commit()

    assert db.query(Shoe).filter(Shoe.strava_gear_id.is_(None)).count() == 2


def test_unique_shoe_user_strava_blocks_duplicate_gear_id(db) -> None:
    """Done-when T1: `strava_gear_id` duplicado para o mesmo usuário
    viola a unique — upsert no backfill usa isso."""
    db.add(Shoe(user_id=1, name="Tênis A", strava_gear_id="g123"))
    db.commit()

    db.add(Shoe(user_id=1, name="Tênis B", strava_gear_id="g123"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_activity_shoe_id_fk_set_null_index(db) -> None:
    """Done-when T1: `Activity.shoe_id` nullable, FK `shoes.id` com
    `ondelete="SET NULL"`, index."""
    shoe = Shoe(user_id=1, name="Kayano 30")
    db.add(shoe)
    db.flush()

    activity = Activity(
        user_id=1,
        garmin_id="act_1",
        start_time=date(2024, 1, 15),
        activity_type="running",
        name="Morning Run",
        distance_m=5000.0,
        duration_s=1800.0,
        shoe_id=shoe.id,
    )
    db.add(activity)
    db.commit()

    fetched = db.get(Activity, activity.id)
    assert fetched.shoe_id == shoe.id

    # Deletar o tênis zera o shoe_id (SET NULL)
    db.delete(shoe)
    db.commit()
    db.refresh(activity)
    assert activity.shoe_id is None


def test_init_db_creates_shoes_table_and_migrates(db) -> None:
    """Done-when T1: init_db cria a tabela `shoes` e a coluna
    `activities.shoe_id` em base nova — re-run não duplica."""
    with engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
        }
    assert "shoes" in tables

    with engine.begin() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'activities'"
                )
            )
        }
    assert "shoe_id" in columns


def test_init_db_migrates_pre_shoes_schema(db) -> None:
    """Done-when T1: base criada antes da feature tenis tem `activities`
    sem `shoe_id` — o init_db migra idempotente (ALTER + FK + index) sem
    tocar no seed. Simulação: derruba a coluna e roda init_db de novo."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE activities DROP COLUMN shoe_id"))

    init_db()

    with engine.begin() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'activities'"
                )
            )
        }
    assert "shoe_id" in columns

    # FK existe e funciona (SET NULL)
    shoe = Shoe(user_id=1, name="Test")
    db.add(shoe)
    db.flush()
    activity = Activity(
        user_id=1,
        garmin_id="act_mig",
        start_time=date(2024, 1, 15),
        activity_type="running",
        name="Test",
        distance_m=5000.0,
        duration_s=1800.0,
        shoe_id=shoe.id,
    )
    db.add(activity)
    db.commit()

    db.delete(shoe)
    db.commit()
    db.refresh(activity)
    assert activity.shoe_id is None

    # Índice existe
    with engine.begin() as conn:
        indexes = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'activities' AND indexname = 'ix_activities_shoe_id'"
                )
            )
        }
    assert "ix_activities_shoe_id" in indexes


def test_init_db_rerun_is_idempotent_for_shoes(db) -> None:
    """Done-when T1: re-executar init_db não duplica a tabela/coluna e
    o seed de usuário permanece intacto."""
    init_db()

    with engine.begin() as conn:
        # Conta linhas de users (seed 1)
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()

    # Adiciona um tênis manual
    db.add(Shoe(user_id=1, name="Manual"))
    db.commit()

    init_db()

    with engine.begin() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM users")).scalar() == user_count
        assert conn.execute(text("SELECT COUNT(*) FROM shoes")).scalar() == 1