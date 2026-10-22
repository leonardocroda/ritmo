"""CLI de importação do tokenstore legado (T7) — GTDB-10/11/12.

Unit com o legado FAKE em tmp_path (nenhum arquivo real do usuário): o
``garmin_tokens.json`` é exatamente o layout do ``dump()`` da lib 0.3.2
(dir com o arquivo dentro, ou arquivo direto). Recusa se o usuário 1 já
tem tokens (nunca reimporta token velho sobre token novo) e grava
CIFRADO na linha dele.
"""

import json
import sys

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.db.engine import SessionLocal, init_db
from app.db.models import DEFAULT_USER_ID, GarminToken
from app.garmin.import_tokens import ImportTokensError, import_legacy, main
from app.garmin.tokens_store import save_blob
from helpers import TEST_TOKEN_ENCRYPTION_KEY

BLOB = json.dumps(
    {"di_token": "di-token-legado", "di_refresh_token": "refresh-legado", "di_client_id": "cid"}
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


def _token_row() -> GarminToken | None:
    with SessionLocal() as s:
        return s.execute(
            select(GarminToken).where(GarminToken.user_id == DEFAULT_USER_ID)
        ).scalar_one_or_none()


def test_import_from_dir_with_garmin_tokens_json(db, fernet, tmp_path):
    """GTDB-10 (dir): ``<path>/garmin_tokens.json`` — layout do dump() da
    lib — é importado e CIFRADO na linha do usuário 1."""
    (tmp_path / "garmin_tokens.json").write_text(BLOB, encoding="utf-8")

    import_legacy(str(tmp_path), db, fernet)

    row = _token_row()
    assert row is not None
    assert row.user_id == DEFAULT_USER_ID
    assert row.token_encrypted != BLOB  # cifrado, nunca plano
    assert fernet.decrypt(row.token_encrypted.encode()).decode() == BLOB


def test_import_from_direct_file(db, fernet, tmp_path):
    """GTDB-10 (arquivo direto): ``--path`` apontando para o próprio
    ``garmin_tokens.json`` também importa."""
    file = tmp_path / "garmin_tokens.json"
    file.write_text(BLOB, encoding="utf-8")

    import_legacy(str(file), db, fernet)

    row = _token_row()
    assert row is not None
    assert fernet.decrypt(row.token_encrypted.encode()).decode() == BLOB


def test_import_refuses_when_user1_already_has_tokens(db, fernet, tmp_path, monkeypatch, capsys):
    """GTDB-11: linha existente → recusa com orientação para o login CLI,
    exit != 0 e a linha INTACTA (nunca reimportar token velho sobre novo)."""
    with SessionLocal() as s:
        save_blob(s, DEFAULT_USER_ID, BLOB, fernet)
        s.commit()
        old_ct = s.execute(
            select(GarminToken.token_encrypted).where(GarminToken.user_id == DEFAULT_USER_ID)
        ).scalar_one()
    (tmp_path / "garmin_tokens.json").write_text(BLOB, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["import_tokens", "--path", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0
    assert "login" in capsys.readouterr().err  # orienta o login CLI
    with SessionLocal() as s:
        assert (
            s.execute(
                select(GarminToken.token_encrypted).where(
                    GarminToken.user_id == DEFAULT_USER_ID
                )
            ).scalar_one()
            == old_ct
        )


def test_import_missing_file_errors_without_writing(db, fernet, tmp_path, monkeypatch, capsys):
    """GTDB-12: arquivo ausente → erro claro, exit != 0, nenhuma gravação."""
    monkeypatch.setattr(sys, "argv", ["import_tokens", "--path", str(tmp_path / "vazio")])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0
    assert "não encontrado" in capsys.readouterr().err
    assert _token_row() is None


def test_import_json_without_di_token_errors_without_writing(
    db, fernet, tmp_path, monkeypatch, capsys
):
    """GTDB-12: JSON sem `di_token` (legado inválido) → erro claro, nada
    gravado — o banco nunca recebe um blob inútil."""
    (tmp_path / "garmin_tokens.json").write_text(
        json.dumps({"di_refresh_token": "r"}), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["import_tokens", "--path", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0
    assert "di_token" in capsys.readouterr().err
    assert _token_row() is None


def test_import_malformed_json_errors_without_writing(db, fernet, tmp_path, monkeypatch, capsys):
    """GTDB-12: arquivo legado ILEGÍVEL (JSON truncado — o branch
    ``except (OSError, ValueError)``) → erro claro, exit != 0 e nenhuma
    gravação — o banco nunca recebe um blob corrompido."""
    (tmp_path / "garmin_tokens.json").write_text(
        '{"di_token": "di-token-legado"', encoding="utf-8"  # '{' sem fechar
    )
    monkeypatch.setattr(sys, "argv", ["import_tokens", "--path", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0
    assert "ilegível" in capsys.readouterr().err
    assert _token_row() is None


def test_main_default_path_is_home_garminconnect(db, fernet, tmp_path, monkeypatch):
    """GTDB-10: sem ``--path`` o default é ``~/.garminconnect`` (expansão
    de ~ via resolve_token_path) — o run-once da operação."""
    home = tmp_path / "home"
    legacy = home / ".garminconnect"
    legacy.mkdir(parents=True)
    (legacy / "garmin_tokens.json").write_text(BLOB, encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))  # expanduser: HOME tem prioridade onde existir
    monkeypatch.setenv("USERPROFILE", str(home))  # ...e USERPROFILE no Windows
    monkeypatch.setattr(sys, "argv", ["import_tokens"])

    main()  # não levanta — sai 0

    row = _token_row()
    assert row is not None
    assert fernet.decrypt(row.token_encrypted.encode()).decode() == BLOB
