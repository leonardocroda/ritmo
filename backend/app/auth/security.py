"""Primitivas criptográficas de auth (feature auth — AUTH-06/15).

Funções puras: hash/verify de senha (argon2id) e geração/hash do token
de sessão. O banco guarda SOMENTE o hash SHA-256 do token — coluna
``token_hash`` String(64) hex; o token cru vive apenas no cookie.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# argon2id (default da lib) — custo adequado para LAN entre amigos
_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash argon2id da senha — formato PHC ``$argon2id$...`` (String(255))."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """True se a senha confere; mismatch vira False (login genérico 401)."""
    try:
        _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    return True


def new_session_token() -> str:
    """Token opaco de sessão — 32 bytes aleatórios (~43 chars base64url)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex de 64 chars — o ÚNICO formato que vai ao banco (AUTH-15)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
