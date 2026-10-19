"""API de auth + proteção dos routers (T7) — TestClient no Postgres real.

A proteção REAL é exercida aqui: o fixture ``client`` limpa o override
do conftest (que mantém a suite pré-auth verde no interim do spec).
Cookie host-only (sem Domain), flags HttpOnly/SameSite/Max-Age, CORS
com origem exata + credenciais, sliding re-setando o cookie e a
sequência pós-T2 (2 registros sem colisão). Mensagens 4xx afirmadas
como no spec — literais, nunca constantes da implementação.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.deps import require_session
from app.auth.router import limiter as auth_limiter
from app.core.config import get_settings
from app.db.engine import SessionLocal, init_db
from app.db.models import UserSession
from app.main import app

INVITE = "SEGREDO"
PASSWORD = "senha-segura-123"
COOKIE = "ritmo_session"
# 30d em segundos — Max-Age do cookie (design auth)
MAX_AGE_30D = 2592000


def _naive_now() -> datetime:
    """Agora em naive UTC — convenção das colunas DateTime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    """SHA-256 hex recomputado no teste (independente da implementação)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@pytest.fixture()
def client():
    """TestClient com a proteção REAL — sem o override do conftest.

    O lifespan recria o schema e semeia o usuário 1 (o conftest derruba
    antes de cada teste)."""
    app.dependency_overrides.pop(require_session, None)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _zero_limiter():
    """Estado do limiter não vaza entre testes (risco do design auth)."""
    auth_limiter._store.clear()
    yield
    auth_limiter._store.clear()


@pytest.fixture()
def invite_on(monkeypatch):
    """INVITE_CODE no env — o default da Settings é vazio (desabilitado)."""
    monkeypatch.setattr(get_settings(), "invite_code", INVITE)


def _register(client, email="ana@example.com", password=PASSWORD,
              display_name="Convidada", invite_code=INVITE):
    return client.post(
        "/api/auth/register",
        json={
            "display_name": display_name,
            "email": email,
            "password": password,
            "invite_code": invite_code,
        },
    )


# ---------------------------------------------------------------
# register — 201 + cookie + auto-login; 403/409/422 (AUTH-01..05)
# ---------------------------------------------------------------


def test_register_201_sets_host_only_cookie_and_autologin(client, invite_on) -> None:
    """Done-when T7 (AUTH-01): 201 com {id, email, display_name}, cookie
    HttpOnly + SameSite=Lax + Max-Age=30d, host-only (sem Domain) e
    Secure ausente (LAN HTTP) — e a sessão já vale no /me (auto-login)."""
    response = _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 1
    assert body["email"] == "ana@example.com"
    assert body["display_name"] == "Convidada"

    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"Max-Age={MAX_AGE_30D}" in cookie
    assert "Domain=" not in cookie  # host-only: vale para :3000 e :8000
    assert "Secure" not in cookie  # LAN HTTP — Fase 2.5 liga

    me_response = client.get("/api/auth/me")  # cookie persistido pelo client
    assert me_response.status_code == 200


def test_register_invite_disabled_responds_403(client) -> None:
    """Done-when T7 (AUTH-02): INVITE_CODE vazio (default) → 403 com a
    mensagem exata do spec, independentemente do payload."""
    response = _register(client)

    assert response.status_code == 403
    assert response.json()["detail"] == "registro desabilitado"


def test_register_wrong_invite_code_responds_403(client, invite_on) -> None:
    """Done-when T7 (AUTH-03): código diferente do env → 403 específica."""
    response = _register(client, invite_code="errado")

    assert response.status_code == 403
    assert response.json()["detail"] == "código de convite inválido"


def test_register_duplicate_email_case_variant_responds_409(client, invite_on) -> None:
    """Done-when T7 (AUTH-04): repetir o email (variante maiúscula) →
    409 com a mensagem do spec — unicidade pós-normalização."""
    assert _register(client).status_code == 201

    response = _register(client, email="ANA@EXAMPLE.COM", display_name="Outra")

    assert response.status_code == 409
    assert response.json()["detail"] == "email já cadastrado"


def test_register_invalid_fields_respond_422_per_field(client, invite_on) -> None:
    """Done-when T7 (AUTH-05): senha <8, email malformado, nome vazio e
    nome >120 → 422 apontando o campo violado com mensagem específica."""
    cases = [
        ({"password": "curta"}, "password", "8 caracteres"),
        ({"email": "sem-arroba"}, "email", "email inválido"),
        ({"display_name": "   "}, "display_name", "nome é obrigatório"),
        ({"display_name": "n" * 121}, "display_name", "120 caracteres"),
    ]
    for overrides, field, message in cases:
        response = _register(client, **overrides)
        assert response.status_code == 422, overrides
        errors = response.json()["detail"]
        assert errors[0]["loc"][-1] == field, overrides
        assert message in errors[0]["msg"], overrides


# ---------------------------------------------------------------
# login — 200 + flags; 401 genérica única; 429 no lockout (AUTH-06..08)
# ---------------------------------------------------------------


def test_login_200_sets_cookie_with_flags(client, invite_on) -> None:
    """Done-when T7 (AUTH-06): credenciais válidas → 200 com o corpo
    {id, email, display_name} e Set-Cookie com os flags do design."""
    assert _register(client).status_code == 201

    response = client.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["display_name"] == "Convidada"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"Max-Age={MAX_AGE_30D}" in cookie


def test_login_401_generic_single_message_both_branches(client, invite_on) -> None:
    """Done-when T7 (AUTH-07): senha errada OU email inexistente → a
    MESMA 401 com a mensagem única — nunca revelar qual campo falhou."""
    assert _register(client).status_code == 201

    wrong_password = client.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": "senha-errada"}
    )
    unknown_email = client.post(
        "/api/auth/login",
        json={"email": "desconhecida@example.com", "password": PASSWORD},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == "email ou senha inválidos"
    assert unknown_email.json()["detail"] == "email ou senha inválidos"


def test_login_429_after_five_failures_even_with_correct_password(
    client, invite_on
) -> None:
    """Done-when T7 (AUTH-08): 5 falhas → a 6ª tentativa responde 429
    MESMO com a senha correta; mensagem acionável com a janela de 15 min."""
    assert _register(client).status_code == 201
    for _ in range(5):
        attempt = client.post(
            "/api/auth/login",
            json={"email": "ana@example.com", "password": "senha-errada"},
        )
        assert attempt.status_code == 401

    locked = client.post(
        "/api/auth/login", json={"email": "ana@example.com", "password": PASSWORD}
    )

    assert locked.status_code == 429
    assert "15 minutos" in locked.json()["detail"]


# ---------------------------------------------------------------
# logout e me — proteção + revogação (AUTH-09/10/11)
# ---------------------------------------------------------------


def test_logout_204_revokes_session_and_clears_cookie(client, invite_on) -> None:
    """Done-when T7 (AUTH-09): 204, linha apagada do banco, cookie
    expirado no response e a sessão morta não resolve mais no /me."""
    assert _register(client).status_code == 201
    token = client.cookies[COOKIE]
    assert client.get("/api/auth/me").status_code == 200

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert "Max-Age=0" in response.headers["set-cookie"]  # cookie limpo
    with SessionLocal() as db:
        rows = (
            db.query(UserSession)
            .filter(UserSession.token_hash == _token_hash(token))
            .count()
        )
    assert rows == 0  # sessão revogada no banco
    assert client.get("/api/auth/me").status_code == 401


def test_protected_operations_without_session_respond_401(client) -> None:
    """Done-when T7 (AUTH-11): logout e /me são protegidos — sem cookie,
    401 JSON sem nenhum dado."""
    logout = client.post("/api/auth/logout")
    me = client.get("/api/auth/me")

    assert logout.status_code == 401
    assert me.status_code == 401
    assert me.json() == {"detail": "não autenticado"}


def test_me_200_returns_id_email_display_name(client, invite_on) -> None:
    """Done-when T7 (AUTH-10): com sessão → 200 com exatamente as três
    chaves do contrato."""
    assert _register(client).status_code == 201

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 1
    assert body["email"] == "ana@example.com"
    assert body["display_name"] == "Convidada"
    assert set(body.keys()) == {"id", "email", "display_name"}


# ---------------------------------------------------------------
# Proteção dos routers existentes + health público + preflight
# ---------------------------------------------------------------


def test_data_routers_401_without_cookie_and_200_with(client, invite_on) -> None:
    """Done-when T7 (AUTH-11/13): TODOS os routers de dado respondem 401
    sem cookie; com sessão, /api/activities volta a 200; /api/health
    (liveness) segue público."""
    for path in (
        "/api/activities",
        "/api/health/summary",
        "/api/potential",
        "/api/sync/jobs/latest",
    ):
        assert client.get(path).status_code == 401, path
    assert client.get("/api/health").status_code == 200  # público

    assert _register(client).status_code == 201
    assert client.get("/api/activities").status_code == 200  # com sessão


def test_cors_exact_origin_with_credentials_and_preflight_exempt(client) -> None:
    """Done-when T7 (AUTH-28 + assumption): preflight OPTIONS é isento de
    sessão e responde com a origem EXATA + allow-credentials; origem fora
    da lista não recebe headers CORS."""
    preflight = client.options(
        "/api/activities",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200  # isento de sessão
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert preflight.headers["access-control-allow-credentials"] == "true"

    simple = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert simple.headers["access-control-allow-origin"] == "http://localhost:3000"

    stranger = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in stranger.headers


# ---------------------------------------------------------------
# Sliding (AUTH-12) e sequência pós-T2 (AUTH-27)
# ---------------------------------------------------------------


def test_sliding_renews_expires_at_and_sets_cookie(client, invite_on) -> None:
    """Done-when T7 (AUTH-12): request com a sessão no limiar (≤15d)
    renova expires_at para ~30d no BANCO e devolve Set-Cookie (o cookie
    acompanha o sliding)."""
    assert _register(client).status_code == 201
    token = client.cookies[COOKIE]
    with SessionLocal() as db:
        row = (
            db.query(UserSession)
            .filter(UserSession.token_hash == _token_hash(token))
            .one()
        )
        row.expires_at = _naive_now() + timedelta(days=15)  # no limiar
        db.commit()

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert f"{COOKIE}=" in response.headers["set-cookie"]  # re-setado
    with SessionLocal() as db:
        renewed = (
            db.query(UserSession)
            .filter(UserSession.token_hash == _token_hash(token))
            .one()
        )
    remaining = renewed.expires_at - _naive_now()
    assert timedelta(days=29) < remaining <= timedelta(days=30)  # ~30d


def test_two_registers_in_a_row_get_distinct_ids_above_one(client, invite_on) -> None:
    """Done-when T7 (AUTH-27 via API): 2 registros seguidos → ids > 1 e
    distintos — a sequência reajustada pela T2 não colide."""
    first = _register(client, email="primeira@example.com")
    second = _register(client, email="segunda@example.com")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] > 1
    assert second.json()["id"] > 1
    assert second.json()["id"] != first.json()["id"]