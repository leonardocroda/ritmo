"""Seed da The Best Açaí (T7) — o countdown precisa de uma prova real.

Cenários derivados dos ACs HOME-22/23: `init_db` semeia a meia
(2026-11-08, 21097.5m, goal null) quando o usuário 1 não tem prova
nenhuma; re-executar não duplica; prova de outro usuário não bloqueia
o seed (guard é por usuário); o countdown calcula `days_left`
dinamicamente (nunca cravado); sem prova -> countdown None. Depois
desta task TODO teste tem a prova no banco (conftest recria o schema)
— as leituras são user-scoped, então só o usuário 1 a enxerga.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.auth.security import hash_password
from app.db.engine import SessionLocal, init_db
from app.db.models import DEFAULT_USER_ID, Race, User
from app.home import service as home_service

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
MEIA_DAY = date(2026, 11, 8)  # The Best Açaí — data fixa do seed


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada
    teste) — o seed da meia já entra com ele."""
    init_db()
    with SessionLocal() as session:
        yield session


def _seed_foreign_race(db) -> None:
    """Prova de OUTRO usuário (id via sequência) — não pode bloquear o
    seed do usuário 1."""
    other = User(
        display_name="Outra",
        email="outra@example.com",
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(other)
    db.flush()
    db.add(Race(user_id=other.id, name="Maratona dela", date=date(2026, 12, 6),
                distance_m=42195.0))
    db.commit()


# ---------------------------------------------------------------
# HOME-23: seed idempotente
# ---------------------------------------------------------------


def test_seed_creates_meia_on_empty_db(db) -> None:
    """HOME-23: init_db em banco zerado cria a meia do usuário 1 com os
    valores da decisão do spec."""
    meia = db.execute(
        select(Race).where(Race.user_id == DEFAULT_USER_ID)
    ).scalar_one_or_none()

    assert meia is not None
    assert meia.name == "The Best Açaí"
    assert meia.date == MEIA_DAY
    assert meia.distance_m == 21097.5
    assert meia.goal_time_s is None


def test_seed_idempotent_double_init(db) -> None:
    """HOME-23: rodar o init_db de novo NÃO duplica o seed."""
    init_db()

    assert db.query(Race).filter(Race.user_id == DEFAULT_USER_ID).count() == 1


def test_seed_per_user_guard_respects_other_users_race(db) -> None:
    """HOME-23 (guard por usuário): prova de outro usuário não bloqueia
    o seed — o guard é 'races vazio PARA O USUÁRIO 1'."""
    _seed_foreign_race(db)
    init_db()

    assert db.query(Race).filter(Race.user_id == DEFAULT_USER_ID).count() == 1
    assert db.query(Race).filter(Race.name == "Maratona dela").count() == 1


# ---------------------------------------------------------------
# HOME-22: countdown alimentado pelo seed
# ---------------------------------------------------------------


def test_countdown_days_left_is_dynamic(db) -> None:
    """HOME-22: a meia semeada alimenta o countdown do payload com
    days_left = prova − hoje, calculado em tempo de teste (nunca o 16
    cravado do exemplo do spec — hoje é o relógio, não uma constante)."""
    today = datetime.now(SAO_PAULO).date()
    expected_days = (MEIA_DAY - today).days

    countdown = home_service.get_home(db, DEFAULT_USER_ID, SAO_PAULO)["countdown"]

    assert countdown == {
        "name": "The Best Açaí",
        "date": MEIA_DAY,
        "days_left": expected_days,
    }


def test_countdown_null_without_any_race(db) -> None:
    """HOME-22 (edge 'sem prova'): o arranjo limpa `races` (nota de
    ambiente do tasks.md) -> countdown None no payload."""
    db.execute(Race.__table__.delete())  # DELETE FROM races
    db.commit()

    assert home_service.get_home(db, DEFAULT_USER_ID, SAO_PAULO)["countdown"] is None
