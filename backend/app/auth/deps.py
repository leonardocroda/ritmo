"""Dependência de proteção — cookie → sessão → User ou 401 (AUTH-11).

Todos os routers de dado são incluídos em ``main.py`` com
``dependencies=[Depends(require_session)]`` — o mapa do que é público
fica visível no entrypoint (design auth). A renovação sliding re-seta o
cookie no response injetado: o Max-Age acompanha o novo ``expires_at``,
senão o browser derruba a sessão antes do banco.
"""

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service
from app.core.config import get_settings
from app.db.engine import get_db
from app.db.models import User


def set_session_cookie(response: Response, token: str) -> None:
    """Cookie de sessão HOST-ONLY (sem ``Domain``): HttpOnly + SameSite=Lax
    + Max-Age do TTL; Secure por env (LAN HTTP — Fase 2.5 liga)."""
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


def require_session(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    """Resolve o cookie para o User da sessão; sem sessão válida → 401
    JSON sem nenhum dado (AUTH-11/13). Renovou (sliding) → re-seta o
    cookie no response injetado (AUTH-12)."""
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    user, renewed = service.resolve_session(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="não autenticado"
        )
    if renewed:
        set_session_cookie(response, token)
    return user
