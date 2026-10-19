"""Endpoints de auth — os 4 de auth; logout/me protegidos (feature auth).

Mapeamento service → HTTP: as exceções de domínio já carregam as
mensagens exatas do spec (403/401/409); o limiter vira 429; o cookie é
setado/deletado aqui (mecânica em ``deps.set_session_cookie``).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.deps import require_session, set_session_cookie
from app.auth.rate_limit import RateLimitedError, RateLimiter
from app.auth.schemas import LoginIn, MeOut, RegisterIn
from app.core.config import get_settings
from app.db.engine import get_db
from app.db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Limiter compartilhado entre requests (worker único, em memória) — a
# fixture de teste zera ``_store`` para não vazar estado (risco do design)
limiter = RateLimiter()


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=MeOut)
def register(
    payload: RegisterIn, response: Response, db: Session = Depends(get_db)
) -> MeOut:
    """Cadastro por convite + auto-login (201 + cookie)."""
    settings = get_settings()
    try:
        user, token = service.register(db, payload, settings.invite_code)
    except (service.InviteDisabledError, service.InviteInvalidError) as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except service.EmailTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    set_session_cookie(response, token)
    return MeOut(id=user.id, email=user.email, display_name=user.display_name)


@router.post("/login", response_model=MeOut)
def login(
    payload: LoginIn, response: Response, db: Session = Depends(get_db)
) -> MeOut:
    """Login email+senha (200 + cookie); erro único 401; lockout 429."""
    try:
        user, token = service.login(db, payload.email, payload.password, limiter)
    except RateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except service.InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    set_session_cookie(response, token)
    return MeOut(id=user.id, email=user.email, display_name=user.display_name)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_session)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    """Revoga a sessão corrente, limpa o cookie e responde 204 (AUTH-09)."""
    settings = get_settings()
    service.revoke(db, request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(require_session)) -> MeOut:
    """Quem está logado — 200 {id, email, display_name} (AUTH-10)."""
    return MeOut(id=user.id, email=user.email, display_name=user.display_name)
