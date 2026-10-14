"""CLI de re-auth — unidade com a lib stubada.

Nenhum teste toca a API real do Garmin. O stub reproduz os efeitos do
`login` real da garminconnect 0.3.2: sinaliza MFA chamando `prompt_mfa`
quando exigido e grava ("dump") um marcador de token no tokenstore
recebido — é esse dump que faz os tokens pararem no path de
GARMINTOKENS, o mesmo que o gateway lê (SYNC-25/26/27).
"""

import getpass
from pathlib import Path

import app.garmin.login as login_module
from app.garmin.login import main, run_login


class FakeGarmin:
    """Stub da lib: registra o contrato e simula MFA + dump do login real."""

    def __init__(
        self, email=None, password=None, prompt_mfa=None, mfa_required=False, **kwargs
    ) -> None:
        self.email = email
        self.password = password
        self.prompt_mfa = prompt_mfa
        self.mfa_required = mfa_required
        self.mfa_code = None
        self.tokenstore = None

    def login(self, tokenstore=None):
        self.tokenstore = tokenstore
        if self.mfa_required:
            self.mfa_code = self.prompt_mfa()
        # dump real: a lib grava os tokens no tokenstore após o login
        store = Path(tokenstore)
        store.mkdir(parents=True, exist_ok=True)
        (store / "garmin_ui_token").write_text("dump", encoding="utf-8")
        return None, None


def stub_garmin(monkeypatch, mfa_required=False):
    """Troca a classe Garmin do módulo por uma fábrica; devolve as instâncias."""
    created: list[FakeGarmin] = []

    def factory(email=None, password=None, prompt_mfa=None, **kwargs):
        fake = FakeGarmin(
            email, password, prompt_mfa=prompt_mfa, mfa_required=mfa_required
        )
        created.append(fake)
        return fake

    monkeypatch.setattr(login_module, "Garmin", factory)
    return created


def spy_secure_dir(monkeypatch):
    """Registra os paths protegidos em vez de depender de chmod (Windows)."""
    recorded: list[str] = []
    monkeypatch.setattr(
        login_module, "secure_token_dir", lambda path: recorded.append(path)
    )
    return recorded


def test_direct_flow_passes_credentials_and_mfa_prompt(monkeypatch, tmp_path):
    """Fluxo direto (sem MFA): credenciais e prompt chegam à lib; a lib
    não sinaliza MFA — o prompt nunca é invocado."""
    monkeypatch.setenv("GARMINTOKENS", str(tmp_path / "tokens"))
    created = stub_garmin(monkeypatch)
    spy_secure_dir(monkeypatch)
    asked: list[str] = []

    def no_mfa() -> str:
        asked.append("MFA não deveria ser pedido no fluxo direto")
        return "000000"

    run_login("corredor@test.com", "s3nh4", mfa_prompt=no_mfa)

    fake = created[0]
    assert fake.email == "corredor@test.com"
    assert fake.password == "s3nh4"
    assert fake.prompt_mfa is no_mfa  # o prompt é injetado na lib
    assert asked == []


def test_mfa_flow_prompts_code_when_lib_signals(monkeypatch, tmp_path):
    """Fluxo MFA: a lib sinaliza chamando prompt_mfa; o código digitado
    alimenta o login, que segue até o dump e a proteção."""
    monkeypatch.setenv("GARMINTOKENS", str(tmp_path / "tokens"))
    created = stub_garmin(monkeypatch, mfa_required=True)
    secured = spy_secure_dir(monkeypatch)

    run_login("corredor@test.com", "s3nh4", mfa_prompt=lambda: "654321")

    fake = created[0]
    assert fake.mfa_code == "654321"  # o código do prompt foi para a lib
    assert fake.tokenstore == str(tmp_path / "tokens")
    assert secured == [str(tmp_path / "tokens")]


def test_login_dumps_tokens_at_garmintokens_path(monkeypatch, tmp_path):
    """Dump no path: os tokens caem exatamente em GARMINTOKENS (o path
    que o gateway lê) e o diretório é protegido com secure_token_dir."""
    token_dir = str(tmp_path / "tokens")
    monkeypatch.setenv("GARMINTOKENS", token_dir)
    created = stub_garmin(monkeypatch)
    secured = spy_secure_dir(monkeypatch)

    result = run_login("corredor@test.com", "s3nh4", mfa_prompt=lambda: "000000")

    fake = created[0]
    assert result == token_dir
    assert fake.tokenstore == token_dir  # o dump da lib acontece neste path
    assert (tmp_path / "tokens" / "garmin_ui_token").exists()
    assert secured == [token_dir]


def test_main_reads_email_via_input_and_password_via_getpass(monkeypatch, tmp_path):
    """Criterion da task: a CLI pede email via input e senha via getpass
    e ambos chegam à lib."""
    monkeypatch.setenv("GARMINTOKENS", str(tmp_path / "tokens"))
    created = stub_garmin(monkeypatch)
    secured = spy_secure_dir(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda prompt="": "corredor@test.com")
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "s3nh4")

    main()

    fake = created[0]
    assert fake.email == "corredor@test.com"
    assert fake.password == "s3nh4"
    assert secured == [str(tmp_path / "tokens")]
