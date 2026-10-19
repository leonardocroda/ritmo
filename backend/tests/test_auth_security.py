"""Primitivas de segurança de auth — argon2id + token de sessão (T4).

Unit puro: hash/verify de senha, unicidade do token de sessão e o hash
SHA-256 hex de 64 chars — o ÚNICO formato que chega ao banco (AUTH-15;
o token cru vive só no cookie). Valores afirmados derivam do design
(auth): nenhum constante compartilhada com a implementação.
"""

import re

from app.auth.security import (
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)

# Token fixo só para pinar o determinismo do hash_token (nunca é o
# formato de produção — esse nasce de new_session_token)
FIXED_TOKEN = "token-de-teste-fixo-0123456789abcdef"


def test_hash_password_roundtrip_verifies_true() -> None:
    """Done-when T4 (AUTH-06): hash/verify funciona — a senha correta
    confere contra o hash argon2id (formato PHC $argon2id$)."""
    hashed = hash_password("senha-segura-123")

    assert hashed.startswith("$argon2id$")  # algoritmo do design, não bcrypt
    assert verify_password("senha-segura-123", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    """Done-when T4: senha errada → verify False (sem exceção vazando)."""
    hashed = hash_password("senha-segura-123")

    assert verify_password("senha-errada", hashed) is False


def test_verify_password_rejects_wrong_against_any_hash() -> None:
    """Done-when T4 (edge): cada hash valida só a sua senha — hash de uma
    senha não verifica outra (mesmo que ambas sejam 'fortes')."""
    hashed = hash_password("primeira-senha")

    assert verify_password("segunda-senha", hashed) is False


def test_new_session_tokens_are_distinct() -> None:
    """Done-when T4 (AUTH-09/15): tokens de sessão distintos a cada
    chamada — entropia de 32 bytes nunca repete em duas gerações."""
    tokens = {new_session_token() for _ in range(10)}

    assert len(tokens) == 10


def test_new_session_token_shape_is_url_safe_43_chars() -> None:
    """Done-when T4: token_urlsafe(32) → ~43 chars, sem padding nem
    caracteres fora do base64url (cabe em cookie header sem encode)."""
    token = new_session_token()

    assert len(token) == 43
    assert re.fullmatch(r"[A-Za-z0-9_-]+", token)


def test_hash_token_is_deterministic_64_hex_and_never_the_token() -> None:
    """Done-when T4 (AUTH-15): hash_token é determinístico, devolve 64
    hex minúsculos (String(64) do modelo) e NUNCA devolve o próprio
    token — o banco não pode reconstituir a sessão a partir do dump."""
    first = hash_token(FIXED_TOKEN)
    second = hash_token(FIXED_TOKEN)

    assert first == second  # determinístico — lookup por igualdade
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert first != FIXED_TOKEN