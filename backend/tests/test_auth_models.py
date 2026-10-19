"""Modelos de auth — User.email/password_hash + UserSession (T1).

Integração no Postgres do compose: unicidade do email (múltiplos NULL
permitidos — o seed id 1 nasce sem email), cascade usuário→sessões e
unique de token_hash (fundação de AUTH-09/13/14/15).

Users de teste nascem com id explícito (padrão da suite): o init_db
insere o seed 1 com id explícito e a sequência users_pkey fica
desincronizada — insert sem id colide; o fix é a T2 (setval no
init_db), e o register da T6/T7 já dependerá dela.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.engine import SessionLocal, init_db
from app.db.models import User, UserSession

# Expiração arbitrária distante — os testes de modelo não dependem do TTL
EXPIRES_AT = datetime(2027, 11, 16, 12, 0, 0)


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def test_multiple_null_emails_accepted(db) -> None:
    """Done-when T1 (User.email nullable + unique): o seed id 1 nasce sem
    email e múltiplos NULL coexistem na coluna unique (Postgres trata
    NULL ≠ NULL — o CLI vincula o seed depois via AUTH-25)."""
    seed = db.get(User, 1)
    assert seed is not None
    assert seed.email is None

    db.add(User(id=2, display_name="Convidado A"))
    db.add(User(id=3, display_name="Convidado B"))
    db.commit()

    assert db.query(User).filter(User.email.is_(None)).count() == 3


def test_duplicate_email_violates_unique(db) -> None:
    """Done-when T1: email repetido viola a unique — última barreira do
    banco atrás da normalização lowercase do service (AUTH-01/04)."""
    db.add(User(id=2, display_name="Ana", email="ana@example.com"))
    db.commit()

    db.add(User(id=3, display_name="Outra", email="ana@example.com"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_duplicate_token_hash_violates_unique(db) -> None:
    """Done-when T1 (UserSession unique em token_hash, AUTH-15): o mesmo
    hash não pode pertencer a duas sessões — String(64) guarda o hex
    SHA-256 do token, nunca o token."""
    db.add(UserSession(user_id=1, token_hash="a" * 64, expires_at=EXPIRES_AT))
    db.commit()

    db.add(UserSession(user_id=1, token_hash="a" * 64, expires_at=EXPIRES_AT))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_user_delete_cascades_sessions(db) -> None:
    """Done-when T1 (FK CASCADE): deletar o usuário derruba as sessões —
    nenhuma linha órfã em `sessions`."""
    user = User(id=2, display_name="Alvo")
    db.add(user)
    db.flush()
    db.add(UserSession(user_id=user.id, token_hash="b" * 64, expires_at=EXPIRES_AT))
    db.add(UserSession(user_id=user.id, token_hash="c" * 64, expires_at=EXPIRES_AT))
    db.commit()

    db.delete(user)
    db.commit()

    assert db.query(UserSession).count() == 0
