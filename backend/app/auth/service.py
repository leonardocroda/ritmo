"""Service de sessão — regras de negócio do auth (feature auth).

Registro por convite, login (erro genérico + limiter + prune lazy),
criação/resolução de sessão com renewal sliding e revoke idempotente.
Exceções de domínio carregam as mensagens EXATAS do spec — o router
(T7) só mapeia para o status HTTP (403/401/409/429). O banco guarda
apenas o hash SHA-256 do token (AUTH-15); o token cru vive no cookie.
"""

import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.rate_limit import RateLimiter
from app.auth.security import hash_password, hash_token, new_session_token, verify_password
from app.core.config import get_settings
from app.db.models import User, UserSession

settings = get_settings()


class InviteDisabledError(Exception):
    """INVITE_CODE ausente/vazio — registro desabilitado (AUTH-02 → 403)."""


class InviteInvalidError(Exception):
    """Código enviado difere de INVITE_CODE (AUTH-03 → 403)."""


class EmailTakenError(Exception):
    """Email (pós-normalização) já pertence a uma conta (AUTH-04 → 409)."""


class InvalidCredentialsError(Exception):
    """Erro ÚNICO de login — email inexistente ou senha errada recebem a
    mesma mensagem genérica (AUTH-07 → 401), nunca revelar o campo."""

    def __init__(self) -> None:
        super().__init__("email ou senha inválidos")


def _utcnow_naive() -> datetime:
    """Agora em naive UTC — convenção das colunas DateTime (sem tz), como
    em garmin/service.py: psycopg grava o wall-clock UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalized(email: str) -> str:
    """Trim + lowercase — unicidade e lookup case-insensitive (spec)."""
    return email.strip().lower()


def register(db: Session, payload, invite_from_env: str) -> tuple[User, str]:
    """Cria conta (convite válido, email inédito) + sessão de auto-login.

    ``payload`` é duck-typed (RegisterIn da T7): display_name, email,
    password e invite_code. Validação de formato (senha <8, email
    malformado) é do schema — 422 no router. Devolve o token CRU; o
    router seta o cookie.
    """
    # AUTH-02: env vazio/ausente desabilita o registro, antes de tudo
    if not invite_from_env:
        raise InviteDisabledError("registro desabilitado")

    # AUTH-03: comparação constant-time (higiene de timing, custo zero)
    sent = (payload.invite_code or "").encode("utf-8")
    expected = invite_from_env.encode("utf-8")
    if not hmac.compare_digest(sent, expected):
        raise InviteInvalidError("código de convite inválido")

    email = _normalized(payload.email)
    if db.query(User).filter(User.email == email).first() is not None:
        raise EmailTakenError("email já cadastrado")

    user = User(
        display_name=payload.display_name,
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()  # user.id via users_id_seq (setval da T2 — nunca colide)
    token = create_session(db, user.id)
    db.commit()
    return user, token


def login(db: Session, email: str, password: str, limiter: RateLimiter) -> tuple[User, str]:
    """Autentica email+senha; devolve (user, token cru) da sessão nova.

    Lockout ANTES da verificação (AUTH-08: 5 falhas/15min travam mesmo
    com senha correta); falha registra no limiter; sucesso reseta e
    pod as sessões expiradas do usuário (prune lazy — AUTH-16).
    """
    normalized = _normalized(email)
    limiter.check(normalized)

    user = db.query(User).filter(User.email == normalized).first()
    if user is None or user.password_hash is None:
        limiter.record_failure(normalized)
        raise InvalidCredentialsError()
    if not verify_password(password, user.password_hash):
        limiter.record_failure(normalized)
        raise InvalidCredentialsError()

    limiter.reset(normalized)

    # AUTH-16: prune lazy — housekeeping sem cron, no login do próprio usuário
    now = _utcnow_naive()
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.expires_at <= now,
    ).delete(synchronize_session=False)

    token = create_session(db, user.id)
    db.commit()
    return user, token


def create_session(db: Session, user_id: int) -> str:
    """Insere a sessão (hash SHA-256 + expires_at = now + TTL) e devolve
    o token cru — quem chama controla o commit."""
    token = new_session_token()
    db.add(
        UserSession(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=_utcnow_naive() + timedelta(days=settings.session_ttl_days),
        )
    )
    db.flush()
    return token


def resolve_session(db: Session, token: str | None) -> tuple[User | None, bool]:
    """Resolve o cookie para (user, renovou).

    Hash → lookup com ``expires_at > now``; ausente/desconhecido/expirado
    → (None, False) (AUTH-11/13). Sliding (AUTH-12): restam ≤15 dias
    (borda INCLUSA) → ``expires_at = now + 30d``, persistido aqui mesmo
    (a sessão do request é fechada sem commit pelo get_db).
    """
    if not token:
        return None, False

    now = _utcnow_naive()
    session_row = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == hash_token(token),
            UserSession.expires_at > now,
        )
        .first()
    )
    if session_row is None:
        return None, False

    renewed = False
    remaining = session_row.expires_at - now
    if remaining <= timedelta(days=settings.session_renew_threshold_days):
        session_row.expires_at = now + timedelta(days=settings.session_ttl_days)
        db.commit()
        renewed = True

    user = db.get(User, session_row.user_id)
    return user, renewed


def revoke(db: Session, token: str | None) -> None:
    """Remove a sessão pelo token — idempotente (logout repetido/cookie
    morto não levanta)."""
    if not token:
        return
    db.query(UserSession).filter(UserSession.token_hash == hash_token(token)).delete(
        synchronize_session=False
    )
    db.commit()
