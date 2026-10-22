"""Cofre tokens_store (T3) — Fernet + banco, único módulo da coluna cifrada.

Cenários derivados dos ACs GTDB-13/14/15: chave validada com fail-fast
(comando de geração na mensagem), ciphertext no banco (nunca plano),
guard otimista do persist-back (GTDB-04: linha mais nova preservada) e
blob ilegível subindo como InvalidToken (chamador trata como "sem
tokens"). Nenhum teste toca a API do Garmin — Postgres real do compose.
"""

import json
from datetime import datetime

import json
from datetime import datetime

import pytest
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import GarminToken, User
from app.garmin.tokens_store import TokenKeyError, get_blob, get_meta, require_key, save_blob
from helpers import TEST_TOKEN_ENCRYPTION_KEY

BLOB = json.dumps(
    {"di_token": "di-token-do-usuario", "di_refresh_token": "r", "di_client_id": "c"}
)
OUTRO_BLOB = json.dumps(
    {"di_token": "di-token-outro", "di_refresh_token": "r2", "di_client_id": "c"}
)


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def fernet() -> Fernet:
    return Fernet(TEST_TOKEN_ENCRYPTION_KEY)


@pytest.fixture()
def outra_fernet() -> Fernet:
    return Fernet(Fernet.generate_key())


def _make_user(db) -> int:
    user = User(display_name="Corredora")
    db.add(user)
    db.flush()
    return user.id


def _updated_at(user_id: int):
    """updated_at fresco do banco (naive — convenção das colunas DateTime)."""
    with SessionLocal() as s:
        return s.execute(
            select(GarminToken.updated_at).where(GarminToken.user_id == user_id)
        ).scalar_one()


# ---------------------------------------------------------------
# require_key (GTDB-14)
# ---------------------------------------------------------------


def test_require_key_accepts_valid_key() -> None:
    """Done-when T3: chave Fernet válida → o cofre fica operante."""
    f = require_key(Settings(_env_file=None, token_encryption_key=TEST_TOKEN_ENCRYPTION_KEY))
    assert isinstance(f, Fernet)
    assert f.decrypt(f.encrypt(b"ok")) == b"ok"


def test_require_key_missing_raises_with_generation_command() -> None:
    """GTDB-14: chave ausente → TokenKeyError apontando o comando de geração."""
    with pytest.raises(TokenKeyError) as exc:
        require_key(Settings(_env_file=None, token_encryption_key=""))
    assert "Fernet.generate_key" in str(exc.value)


def test_require_key_invalid_raises_with_generation_command() -> None:
    """GTDB-14: chave que não é Fernet → mesmo fail-fast com o comando."""
    with pytest.raises(TokenKeyError) as exc:
        require_key(Settings(_env_file=None, token_encryption_key="nao-e-uma-chave"))
    assert "Fernet.generate_key" in str(exc.value)


# ---------------------------------------------------------------
# save_blob + get_blob (GTDB-13)
# ---------------------------------------------------------------


def test_save_blob_writes_ciphertext_and_get_blob_roundtrips(db, fernet) -> None:
    """Done-when T3 + GTDB-13 AC 1: a coluna guarda SOMENTE ciphertext —
    o blob plano é recuperável apenas com a chave (get_blob)."""
    user_id = _make_user(db)

    assert save_blob(db, user_id, BLOB, fernet) is True
    db.commit()

    with SessionLocal() as s:
        row = s.execute(
            select(GarminToken).where(GarminToken.user_id == user_id)
        ).scalar_one()
        assert row.token_encrypted != BLOB  # nunca texto plano
        assert BLOB not in row.token_encrypted
        assert fernet.decrypt(row.token_encrypted.encode()).decode() == BLOB

    loaded = get_blob(db, user_id, fernet)
    assert loaded is not None
    blob, updated_at = loaded
    assert blob == BLOB
    assert updated_at is not None


def test_save_blob_upsert_updates_same_row(db, fernet) -> None:
    """Done-when T3: sem linha cria, com linha ATUALIZA (1:1 — nunca
    segunda linha) e o updated_at avança."""
    user_id = _make_user(db)
    save_blob(db, user_id, BLOB, fernet)
    db.commit()
    first = _updated_at(user_id)

    save_blob(db, user_id, OUTRO_BLOB, fernet)
    db.commit()

    with SessionLocal() as s:
        assert (
            s.execute(select(GarminToken).where(GarminToken.user_id == user_id)).scalar_one().token_encrypted
            != BLOB
        )
    assert _updated_at(user_id) > first
    assert get_blob(db, user_id, fernet)[0] == OUTRO_BLOB


def test_save_blob_guard_accepted_when_row_unchanged(db, fernet) -> None:
    """Done-when T3: guard com expected vigente → grava e o updated_at avança."""
    user_id = _make_user(db)
    save_blob(db, user_id, BLOB, fernet)
    db.commit()
    loaded_at = _updated_at(user_id)

    accepted = save_blob(db, user_id, OUTRO_BLOB, fernet, expected_updated_at=loaded_at)
    db.commit()

    assert accepted is True
    assert get_blob(db, user_id, fernet)[0] == OUTRO_BLOB
    assert _updated_at(user_id) > loaded_at


def test_save_blob_guard_refused_preserves_newer_row(db, fernet) -> None:
    """GTDB-04 AC 2: a linha mudou desde o carregamento (re-login fake) →
    guard recusa (False) e a linha mais nova permanece intacta."""
    user_id = _make_user(db)
    save_blob(db, user_id, BLOB, fernet)
    db.commit()
    loaded_at = _updated_at(user_id)

    # re-login concorrente: outra sessão grava tokens novos
    with SessionLocal() as s:
        row = s.execute(
            select(GarminToken).where(GarminToken.user_id == user_id)
        ).scalar_one()
        row.token_encrypted = fernet.encrypt(OUTRO_BLOB.encode()).decode()
        row.updated_at = datetime(2026, 10, 22, 23, 0, 0)
        s.commit()

    refused = save_blob(db, user_id, BLOB, fernet, expected_updated_at=loaded_at)
    db.commit()

    assert refused is False
    with SessionLocal() as s:
        row = s.execute(
            select(GarminToken).where(GarminToken.user_id == user_id)
        ).scalar_one()
        assert fernet.decrypt(row.token_encrypted.encode()).decode() == OUTRO_BLOB  # preservada


def test_get_blob_none_without_row(db, fernet) -> None:
    """Done-when T3: usuário sem linha → None (canal "sem tokens")."""
    user_id = _make_user(db)
    assert get_blob(db, user_id, fernet) is None


def test_get_blob_with_other_key_raises_invalid_token(db, fernet, outra_fernet) -> None:
    """Done-when T3: ciphertext de outra chave → InvalidToken sobe para o
    chamador tratar como "sem tokens" (estado Reconectar — GTDB-03)."""
    user_id = _make_user(db)
    save_blob(db, user_id, BLOB, fernet)
    db.commit()

    with pytest.raises(InvalidToken):
        get_blob(db, user_id, outra_fernet)


# ---------------------------------------------------------------
# get_meta (GTDB-16/17 — endpoint de status)
# ---------------------------------------------------------------


def test_get_meta_reads_row_without_decrypting(db) -> None:
    """Done-when T3: existência + updated_at SEM decriptar — ciphertext
    ilegível (qualquer chave) não impede o meta."""
    user_id = _make_user(db)
    db.add(GarminToken(user_id=user_id, token_encrypted="nao-e-fernet"))
    db.commit()
    expected = _updated_at(user_id)

    exists, updated_at = get_meta(db, user_id)

    assert exists is True
    assert updated_at == expected
    assert get_meta(db, user_id + 999) == (False, None)  # sem linha


# ---------------------------------------------------------------
# GTDB-15 — nenhum log no cofre
# ---------------------------------------------------------------


def test_tokens_store_has_no_logging_calls() -> None:
    """GTDB-15: o cofre nunca registra nada — o blob é segredo mesmo
    cifrado (inspeção estática, padrão do teste read-only do gateway).
    O comando de geração no texto do TokenKeyError não é log."""
    from pathlib import Path

    source = Path("app/garmin/tokens_store.py").read_text(encoding="utf-8")
    assert "import logging" not in source
    assert "getLogger" not in source
    assert "logger." not in source
    assert "logging." not in source


def test_only_tokens_store_touches_the_encrypted_column() -> None:
    """GTDB-13: tokens_store é o ÚNICO módulo que lê/grava a coluna
    cifrada — nenhum outro módulo de app referencia ``token_encrypted``
    (models.py apenas declara a coluna)."""
    from pathlib import Path

    offenders = []
    for path in Path("app").rglob("*.py"):
        if path.name == "models.py" or path.name == "tokens_store.py":
            continue
        if "token_encrypted" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == []
