"""CLI de login por usuário (T6) — unidade com a lib stubada (GTDB-07/08/09/15).

Nenhum teste toca a API real do Garmin. O stub reproduz o contrato do
login real da garminconnect 0.3.2 no cenário do banco: ``login(None)``
(sem tokenstore — a lib aceitaria ``GARMINTOKENS`` como fallback), MFA
via callback quando sinalizado e ``client.dumps()`` devolvendo o blob
DI — que o CLI valida e grava CIFRADO na linha do usuário (upsert).
"""

import json
import os
import sys

import pytest
from cryptography.fernet import Fernet
from garminconnect import GarminConnectAuthenticationError
from sqlalchemy import select

import app.garmin.login as login_module
from app.db.engine import SessionLocal, init_db
from app.db.models import GarminToken, User
from app.garmin.login import LoginError, main, run_login
from app.garmin.tokens_store import save_blob
from helpers import TEST_TOKEN_ENCRYPTION_KEY

BLOB = json.dumps(
    {"di_token": "di-token-fake", "di_refresh_token": "refresh-fake", "di_client_id": "cid"}
)
BLOB_SEM_DI = json.dumps({"di_token": None, "di_refresh_token": "r", "di_client_id": "c"})
OLD_BLOB = json.dumps(
    {"di_token": "di-token-antigo", "di_refresh_token": "r0", "di_client_id": "cid"}
)


class FakeGarmin:
    """Stub da lib: registra o contrato e simula MFA + dumps do login real."""

    def __init__(
        self,
        email=None,
        password=None,
        prompt_mfa=None,
        mfa_required=False,
        blob=BLOB,
        fail=None,
    ) -> None:
        self.email = email
        self.password = password
        self.prompt_mfa = prompt_mfa
        self.mfa_required = mfa_required
        self.mfa_code = None
        self.blob = blob
        self.fail = fail
        self.login_args: list = []
        self.client = FakeClient(blob)

    def login(self, tokenstore=None):
        self.login_args.append(tokenstore)
        if self.fail is not None:
            raise self.fail
        if self.mfa_required:
            self.mfa_code = self.prompt_mfa()


class FakeClient:
    """`garmin.client` — dumps() devolve o blob DI configurado."""

    def __init__(self, blob: str) -> None:
        self._blob = blob

    def dumps(self) -> str:
        return self._blob


def stub_garmin(monkeypatch, mfa_required=False, blob=BLOB, fail=None):
    """Troca a classe Garmin do módulo por uma fábrica; devolve as instâncias."""
    created: list[FakeGarmin] = []

    def factory(email=None, password=None, prompt_mfa=None, **kwargs):
        fake = FakeGarmin(
            email,
            password,
            prompt_mfa=prompt_mfa,
            mfa_required=mfa_required,
            blob=blob,
            fail=fail,
        )
        created.append(fake)
        return fake

    monkeypatch.setattr(login_module, "Garmin", factory)
    return created


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _make_user(email: str = "bruno@example.com") -> int:
    with SessionLocal() as s:
        user = User(display_name="Bruno", email=email)
        s.add(user)
        s.commit()
        return user.id


def _rows() -> list[GarminToken]:
    with SessionLocal() as s:
        return s.execute(select(GarminToken)).scalars().all()


def test_valid_login_without_mfa_writes_encrypted_row(db, monkeypatch):
    """GTDB-07: credenciais chegam à lib e os tokens são gravados
    CIFRADOS na linha do usuário — a coluna nunca guarda texto plano."""
    user_id = _make_user()
    created = stub_garmin(monkeypatch)
    fernet = Fernet(TEST_TOKEN_ENCRYPTION_KEY)

    run_login(db, user_id, "bruno@example.com", "s3nh4", mfa_prompt=lambda: "000000")

    fake = created[0]
    assert fake.email == "bruno@example.com"
    assert fake.password == "s3nh4"
    assert fake.prompt_mfa is not None
    rows = _rows()
    assert len(rows) == 1
    assert rows[0].user_id == user_id
    assert rows[0].token_encrypted != BLOB  # cifrado, nunca plano
    assert fernet.decrypt(rows[0].token_encrypted.encode()).decode() == BLOB


def test_valid_login_with_mfa_replaces_existing_row(db, monkeypatch):
    """GTDB-07 (upsert) + MFA: a lib sinaliza MFA, o código do prompt
    alimenta o login e o re-login SUBSTITUI a linha existente."""
    user_id = _make_user()
    fernet = Fernet(TEST_TOKEN_ENCRYPTION_KEY)
    with SessionLocal() as s:
        save_blob(s, user_id, OLD_BLOB, fernet)
        s.commit()
    created = stub_garmin(monkeypatch, mfa_required=True)

    run_login(db, user_id, "bruno@example.com", "s3nh4", mfa_prompt=lambda: "654321")

    fake = created[0]
    assert fake.mfa_code == "654321"  # o código do prompt foi para a lib
    rows = _rows()
    assert len(rows) == 1  # 1:1 — substituiu, não duplicou
    assert fernet.decrypt(rows[0].token_encrypted.encode()).decode() == BLOB


def test_garmintokens_popped_and_login_without_tokenstore(db, monkeypatch, tmp_path):
    """GTDB-19 + risco do design: GARMINTOKENS removida do env ANTES do
    login e `login(None)` — o convidado nunca herda o tokenstore do
    operador (a lib usaria a env como fallback de login(None))."""
    monkeypatch.setenv("GARMINTOKENS", str(tmp_path / "tokens-do-operador"))
    user_id = _make_user()
    created = stub_garmin(monkeypatch)

    run_login(db, user_id, "bruno@example.com", "s3nh4", mfa_prompt=lambda: "000000")

    fake = created[0]
    assert "GARMINTOKENS" not in os.environ
    assert fake.login_args == [None]  # sem tokenstore — o banco é a única fonte
    assert len(_rows()) == 1


def test_unknown_email_main_exits_without_writing(db, monkeypatch, capsys):
    """GTDB-08: email inexistente → mensagem clara, exit != 0, nenhuma
    gravação (nem lib instanciada — o usuário resolve antes do login)."""
    monkeypatch.setattr(sys, "argv", ["login", "--user", "fantasma@example.com"])
    monkeypatch.setattr(login_module.getpass, "getpass", lambda *a, **k: "s3nh4")
    created = stub_garmin(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0
    assert "fantasma@example.com" in capsys.readouterr().err
    assert created == []  # nem chegou ao login
    assert _rows() == []


def test_login_failure_keeps_existing_tokens(db, monkeypatch):
    """GTDB-09: credenciais/MFA/rate limit falham → erro sobe e os tokens
    existentes do usuário permanecem INALTERADOS."""
    user_id = _make_user()
    fernet = Fernet(TEST_TOKEN_ENCRYPTION_KEY)
    with SessionLocal() as s:
        save_blob(s, user_id, OLD_BLOB, fernet)
        s.commit()
        old_ct = s.execute(
            select(GarminToken.token_encrypted).where(GarminToken.user_id == user_id)
        ).scalar_one()
    stub_garmin(monkeypatch, fail=GarminConnectAuthenticationError("Authentication failed (401)"))

    with pytest.raises(GarminConnectAuthenticationError):
        run_login(db, user_id, "bruno@example.com", "errada", mfa_prompt=lambda: "000000")

    with SessionLocal() as s:
        assert (
            s.execute(
                select(GarminToken.token_encrypted).where(GarminToken.user_id == user_id)
            ).scalar_one()
            == old_ct
        )


def test_session_without_di_token_errors_and_writes_nothing(db, monkeypatch):
    """Risco do design (dumps jwt_web-only): sessão sem `di_token` →
    erro "sem token DI" e NADA gravado (nenhum blob inútil no banco)."""
    user_id = _make_user()
    stub_garmin(monkeypatch, blob=BLOB_SEM_DI)

    with pytest.raises(LoginError, match="sem token DI"):
        run_login(db, user_id, "bruno@example.com", "s3nh4", mfa_prompt=lambda: "000000")

    assert _rows() == []


def test_main_translates_lib_failure_without_blob_fragment(db, monkeypatch, capsys):
    """GTDB-15: a falha da lib é traduzida para mensagem FIXA — nenhum
    fragmento de token/blob vaza na saída de erro do CLI."""
    _make_user()
    monkeypatch.setattr(sys, "argv", ["login", "--user", "bruno@example.com"])
    monkeypatch.setattr(login_module.getpass, "getpass", lambda *a, **k: "s3nh4")
    stub_garmin(
        monkeypatch,
        fail=GarminConnectAuthenticationError(f"401 com fragmento {BLOB}"),
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code != 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "di-token-fake" not in output
    assert BLOB not in output


def test_main_resolves_user_with_normalized_email(db, monkeypatch):
    """Mesmo critério do auth (trim + lowercase): `--user` em qualquer
    caixa resolve o usuário cadastrado."""
    user_id = _make_user("bruno@example.com")
    created = stub_garmin(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["login", "--user", "  BRUNO@Example.COM "])
    monkeypatch.setattr(login_module.getpass, "getpass", lambda *a, **k: "s3nh4")

    main()  # não levanta — sai 0

    fake = created[0]
    assert fake.email == "bruno@example.com"  # normalizado para a lib
    assert [row.user_id for row in _rows()] == [user_id]
