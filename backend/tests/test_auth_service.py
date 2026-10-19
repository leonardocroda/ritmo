"""Service de sessão — register/login/sliding/revoke/prune (T6).

Integração no Postgres do compose: os fluxos do design auth afirmados
contra o banco real — exceções de domínio com as mensagens exatas do
spec, erro genérico único de login, lockout mesmo com senha correta,
sliding com borda inclusa (≤15d), prune lazy no login e revoke
idempotente. Payloads duck-typed (SimpleNamespace) — o RegisterIn da
T7 satisfaz o mesmo contrato de atributos. Hashes esperados são
recomputados no teste com hashlib (nunca constantes da implementação).
"""

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.auth import service
from app.auth.rate_limit import RateLimitedError, RateLimiter
from app.db.engine import SessionLocal, init_db
from app.db.models import User, UserSession

INVITE = "SEGREDO"
PASSWORD = "senha-segura-123"


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _payload(**overrides) -> SimpleNamespace:
    """Payload de registro duck-typed (mesmos atributos do RegisterIn)."""
    data = {
        "display_name": "Convidada",
        "email": "ana@example.com",
        "password": PASSWORD,
        "invite_code": INVITE,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _naive_now() -> datetime:
    """Agora em naive UTC — mesma convenção das colunas DateTime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    """SHA-256 hex recomputado no teste (independente da implementação)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------
# register — convite, normalização e unicidade (AUTH-01..05 base)
# ---------------------------------------------------------------


def test_register_with_valid_invite_creates_user_and_session(db) -> None:
    """Done-when T6 (AUTH-01): convite válido → user + sessão; o banco
    guarda o HASH do token devolvido (nunca o token cru) e o id vem da
    sequência corrigida (>1 — setval da T2)."""
    user, token = service.register(db, _payload(), INVITE)

    assert user.id > 1
    assert user.email == "ana@example.com"
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")

    row = db.query(UserSession).filter(UserSession.user_id == user.id).one()
    assert row.token_hash == _token_hash(token)  # hash do token cru...
    assert row.token_hash != token  # ...nunca o token (AUTH-15)
    remaining = row.expires_at - _naive_now()
    assert timedelta(days=30) - remaining < timedelta(minutes=5)  # TTL 30d


def test_register_normalizes_email_trim_lowercase(db) -> None:
    """Edge do spec (complementa AUTH-01): maiúsculas/espaços são
    normalizados (trim + lowercase) ANTES da unicidade."""
    user, _ = service.register(db, _payload(email="  Ana@Example.COM "), INVITE)

    assert user.email == "ana@example.com"


def test_register_invite_disabled_raises(db) -> None:
    """Done-when T6 (AUTH-02): INVITE_CODE vazio/ausente → registro
    desabilitado, independentemente do payload (mensagem exata do spec)."""
    with pytest.raises(service.InviteDisabledError, match="registro desabilitado"):
        service.register(db, _payload(), "")


def test_register_wrong_invite_code_raises(db) -> None:
    """Done-when T6 (AUTH-03): código diferente do env → código de
    convite inválido (mensagem exata do spec)."""
    with pytest.raises(service.InviteInvalidError, match="código de convite inválido"):
        service.register(db, _payload(invite_code="errado"), INVITE)


def test_register_duplicate_email_case_variant_raises(db) -> None:
    """Done-when T6 (AUTH-04): email já cadastrado pega a variante em
    maiúsculas — unicidade depois da normalização."""
    service.register(db, _payload(), INVITE)

    with pytest.raises(service.EmailTakenError, match="email já cadastrado"):
        service.register(
            db, _payload(display_name="Outra", email="ANA@EXAMPLE.COM"), INVITE
        )


# ---------------------------------------------------------------
# login — genérico, lockout e prune lazy (AUTH-06/07/08/16 base)
# ---------------------------------------------------------------


def test_login_success_creates_session_and_normalizes_email(db) -> None:
    """Done-when T6 (AUTH-06): credenciais válidas → token cru devolvido
    e nova linha em sessions; email com maiúsculas/espaços encontra a
    conta (mesma normalização do register)."""
    user, _ = service.register(db, _payload(), INVITE)

    logged, token = service.login(db, "ANA@Example.COM ", PASSWORD, RateLimiter())

    assert logged.id == user.id
    rows = db.query(UserSession).filter(UserSession.user_id == user.id).all()
    assert len(rows) == 2  # a do register + a do login (simultâneas OK)
    assert _token_hash(token) in {r.token_hash for r in rows}


def test_login_generic_error_in_both_branches(db) -> None:
    """Done-when T6 (AUTH-07): senha errada OU email inexistente → a
    MESMA exceção genérica com a mensagem única do spec — nunca revelar
    qual campo falhou."""
    service.register(db, _payload(), INVITE)
    limiter = RateLimiter()

    with pytest.raises(service.InvalidCredentialsError, match="email ou senha inválidos"):
        service.login(db, "ana@example.com", "senha-errada", limiter)

    with pytest.raises(service.InvalidCredentialsError, match="email ou senha inválidos"):
        service.login(db, "desconhecida@example.com", "senha-errada", limiter)


def test_login_lockout_even_with_correct_password(db) -> None:
    """Done-when T6 (AUTH-08): 5 falhas registradas → login levanta
    RateLimitedError ANTES de verificar a senha correta (429 na T7)."""
    service.register(db, _payload(), INVITE)
    limiter = RateLimiter()
    for _ in range(5):
        limiter.record_failure("ana@example.com")

    with pytest.raises(RateLimitedError):
        service.login(db, "ana@example.com", PASSWORD, limiter)


def test_login_prunes_expired_sessions_of_user(db) -> None:
    """Done-when T6 (AUTH-16): login bem-sucedido remove as sessões
    EXPIRADAS do mesmo usuário — as válidas (e a nova) permanecem."""
    user = User(
        display_name="Ana",
        email="ana@example.com",
        password_hash=service.hash_password(PASSWORD),
    )
    db.add(user)
    db.flush()
    now = _naive_now()
    db.add(UserSession(user_id=user.id, token_hash="a" * 64,
                       expires_at=now - timedelta(hours=1)))  # expirada
    db.add(UserSession(user_id=user.id, token_hash="b" * 64,
                       expires_at=now + timedelta(days=10)))  # válida
    db.commit()

    service.login(db, "ana@example.com", PASSWORD, RateLimiter())

    hashes = {s.token_hash for s in db.query(UserSession).all()}
    assert "a" * 64 not in hashes  # expirada removida
    assert "b" * 64 in hashes  # válida preservada
    assert len(hashes) == 2  # válida + a sessão nova do login


# ---------------------------------------------------------------
# resolve_session — lookup, sliding (borda inclusa) e renovação
# ---------------------------------------------------------------


def _seed_session(db, email: str, token: str, expires_at: datetime) -> User:
    """Usuário + sessão com expires_at controlado pelo teste."""
    user = User(display_name="Corredora", email=email)
    db.add(user)
    db.flush()
    db.add(UserSession(user_id=user.id, token_hash=_token_hash(token),
                       expires_at=expires_at))
    db.commit()
    return user


def test_resolve_valid_token_returns_user_without_renewal(db) -> None:
    """Done-when T6 (AUTH-09/13 base): token válido → user; sessão nova
    (30d restantes > 15d) NÃO renova."""
    user, token = service.register(db, _payload(), INVITE)

    resolved, renewed = service.resolve_session(db, token)

    assert resolved is not None
    assert resolved.id == user.id
    assert renewed is False


def test_resolve_missing_invalid_or_expired_token_returns_none(db) -> None:
    """Done-when T6 (AUTH-11/13): token ausente, desconhecido ou com
    expires_at no passado → (None, False) — sem exceção."""
    _seed_session(db, "velha@example.com", "expirado",
                  _naive_now() - timedelta(minutes=1))

    assert service.resolve_session(db, None) == (None, False)
    assert service.resolve_session(db, "nunca-existiu") == (None, False)
    assert service.resolve_session(db, "expirado") == (None, False)


def test_resolve_renews_at_threshold_boundary_inclusive(db) -> None:
    """Done-when T6 (AUTH-12): restam EXATAMENTE 15 dias (borda inclusa)
    → renova para now + 30d e sinaliza — a renovação persiste no banco."""
    expires = _naive_now() + timedelta(days=15)
    user = _seed_session(db, "ana@example.com", "na-borda", expires)

    resolved, renewed = service.resolve_session(db, "na-borda")

    assert resolved is not None and resolved.id == user.id
    assert renewed is True
    row = db.query(UserSession).filter(UserSession.token_hash == _token_hash("na-borda")).one()
    remaining = row.expires_at - _naive_now()
    assert timedelta(days=30) - remaining < timedelta(minutes=5)  # ~30d


def test_resolve_skips_renewal_above_threshold(db) -> None:
    """Done-when T6 (AUTH-12): restam >15 dias (15d + 1s) → sem
    renovação — expires_at permanece intocado (escrita só no limiar)."""
    expires = _naive_now() + timedelta(days=15, seconds=1)
    _seed_session(db, "ana@example.com", "folgada", expires)

    _, renewed = service.resolve_session(db, "folgada")

    assert renewed is False
    row = db.query(UserSession).filter(UserSession.token_hash == _token_hash("folgada")).one()
    assert row.expires_at == expires


# ---------------------------------------------------------------
# revoke — delete idempotente (AUTH-09 base)
# ---------------------------------------------------------------


def test_revoke_revokes_and_is_idempotent(db) -> None:
    """Done-when T6 (AUTH-09/13): revoke derruba a sessão (resolve →
    None) e token inexistente não levanta (logout repetido é inofensivo)."""
    user, token = service.register(db, _payload(), INVITE)
    assert user.id > 1

    service.revoke(db, token)
    assert service.resolve_session(db, token) == (None, False)

    service.revoke(db, "nunca-existiu")  # idempotente — sem exceção