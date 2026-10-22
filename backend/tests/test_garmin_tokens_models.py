"""Modelo GarminToken (T1) — 1:1 com usuário, unique + FK CASCADE (GTDB-02).

Integração no Postgres do compose (padrão test_auth_models): unique de
``user_id`` (uma linha de tokens por usuário) e cascade usuário→tokens
(deletar o usuário apaga os tokens). ``updated_at`` com onupdate é a
âncora do guard otimista do persist-back (GTDB-04).
"""

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.engine import SessionLocal, init_db
from app.db.models import GarminToken, User


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _make_user(db, display_name: str = "Alvo") -> User:
    user = User(display_name=display_name)
    db.add(user)
    db.flush()
    return user


def test_duplicate_user_id_violates_unique(db) -> None:
    """Done-when T1: dois tokens para o mesmo usuário violam a unique —
    exatamente uma linha de tokens por usuário (GTDB-02)."""
    user = _make_user(db)
    db.add(GarminToken(user_id=user.id, token_encrypted="gAAAA" + "x" * 32))
    db.commit()

    db.add(GarminToken(user_id=user.id, token_encrypted="gAAAA" + "y" * 32))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_delete_cascades_tokens(db) -> None:
    """Done-when T1 (FK CASCADE): deletar o usuário apaga a linha de
    tokens — nenhuma linha órfã em `garmin_tokens`."""
    user = _make_user(db)
    db.add(GarminToken(user_id=user.id, token_encrypted="gAAAA" + "z" * 32))
    db.commit()

    db.delete(user)
    db.commit()

    assert db.query(GarminToken).count() == 0


def test_updated_at_advances_on_update(db) -> None:
    """Done-when T1: ``updated_at`` com onupdate avança quando a linha é
    atualizada — é o valor que o guard do persist-back compara (GTDB-04)."""
    user = _make_user(db)
    db.add(
        GarminToken(
            user_id=user.id,
            token_encrypted="gAAAAantigo",
            updated_at=datetime(2026, 1, 1, 12, 0, 0),
        )
    )
    db.commit()

    row = db.execute(select(GarminToken)).scalar_one()
    row.token_encrypted = "gAAAArenovado"
    db.commit()
    db.expire_all()

    reloaded = db.execute(select(GarminToken)).scalar_one()
    assert reloaded.updated_at > datetime(2026, 1, 1, 12, 0, 0)
