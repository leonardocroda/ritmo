"""CLI set_password — bootstrap e suporte (T8, AUTH-25/26).

Unit com seam: ``run_set_password`` recebe email/senha prontos; o
``main()`` interativo é exercido com monkeypatch de ``input`` e
``getpass`` — nenhum teste toca I/O real. Os 3 caminhos do done-when:
vincula o seed (display_name preservado), reseta conta existente e
cria conta nova quando o seed já tem email.
"""

import pytest

from app.auth.security import hash_password, verify_password
from app.auth.set_password import main, run_set_password
from app.db.engine import SessionLocal, init_db
from app.db.models import User


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def test_binds_seed_user_preserving_display_name(db) -> None:
    """AUTH-25 (caminho 1): email inédito + seed sem email → vincula ao
    id 1, normaliza lowercase e preserva o display_name do seed."""
    user = run_set_password("Leonardo@Example.COM ", "senha-forte-123")

    assert user.id == 1
    assert user.email == "leonardo@example.com"
    assert user.display_name == "Leonardo"
    assert user.password_hash is not None
    assert verify_password("senha-forte-123", user.password_hash)


def test_resets_existing_password_without_touching_name(db) -> None:
    """AUTH-26: email de conta existente → só o hash muda (nova senha
    verifica, antiga não) e o display_name fica intacto."""
    with SessionLocal() as session:
        session.add(
            User(
                id=2,
                display_name="Ana",
                email="ana@example.com",
                password_hash=hash_password("antiga-123"),
            )
        )
        session.commit()

    user = run_set_password("ana@example.com", "nova-senha-456")

    assert user.display_name == "Ana"
    assert verify_password("nova-senha-456", user.password_hash)
    assert not verify_password("antiga-123", user.password_hash)


def test_creates_new_account_when_seed_claimed(db) -> None:
    """AUTH-25 (caminho 2): email inédito + seed já vinculado → cria
    conta nova (id > 1) com display_name = parte local do email."""
    with SessionLocal() as session:
        seed = session.get(User, 1)
        seed.email = "leonardo@example.com"
        seed.password_hash = hash_password("senha-forte-123")
        session.commit()

    user = run_set_password("Bruno@Example.com", "outra-senha-789")

    assert user.id != 1
    assert user.email == "bruno@example.com"
    assert user.display_name == "bruno"
    assert verify_password("outra-senha-789", user.password_hash)


def test_main_interactive_binds_seed(db, monkeypatch, capsys) -> None:
    """main() interativo (input + getpass mockados) exercendo o caminho
    de bootstrap: o seed sai com email e senha definidos."""
    respostas = iter(["leonardo@example.com", "senha-forte-123"])
    monkeypatch.setattr("builtins.input", lambda *args: next(respostas))
    monkeypatch.setattr("app.auth.set_password.getpass", lambda *args: next(respostas))

    main()

    assert "leonardo@example.com" in capsys.readouterr().out
    with SessionLocal() as session:
        seed = session.get(User, 1)
        assert seed.email == "leonardo@example.com"
        assert verify_password("senha-forte-123", seed.password_hash)
