"""Rate limiter de login em memória — 5 falhas / 15 min (T5, AUTH-08).

Unit puro: comportamentos do spec auth (assumption travada) afirmados
com literais — 15 min = 900s e limite 5 NUNCA vêm de constantes da
implementação. Timestamps antigos são injetados direto no ``_store``
(exposto por design para a fixture de teste).
"""

import time

import pytest

from app.auth.rate_limit import RateLimitedError, RateLimiter

# Literais do spec (AUTH-08) — janela 15 min, limite 5 falhas
WINDOW_S = 15 * 60
LIMIT = 5


def _record_failures(limiter: RateLimiter, email: str, times: int) -> None:
    for _ in range(times):
        limiter.record_failure(email)


def test_four_failures_pass_check() -> None:
    """Done-when T5: 4 falhas na janela → check NÃO levanta — a 5ª
    tentativa ainda é permitida."""
    limiter = RateLimiter()
    _record_failures(limiter, "alvo@example.com", LIMIT - 1)

    limiter.check("alvo@example.com")  # não levanta


def test_fifth_failure_raises_rate_limited_even_with_correct_password() -> None:
    """Done-when T5 (AUTH-08): a 5ª falha trava o email — check levanta
    RateLimitedError em qualquer tentativa seguinte, MESMO com senha
    correta (o check roda antes de verificar credenciais). A mensagem
    informa tentativas demais e a janela de 15 min (edge case do spec)."""
    limiter = RateLimiter()
    _record_failures(limiter, "alvo@example.com", LIMIT)

    with pytest.raises(RateLimitedError) as exc_info:
        limiter.check("alvo@example.com")

    message = str(exc_info.value)
    assert "15 minutos" in message  # janela acionável (PT-BR)


def test_window_expiry_restores_check() -> None:
    """Done-when T5: janela expirada → check passa de novo — timestamps
    com mais de 15 min saem da contagem (manipulados no _store)."""
    limiter = RateLimiter()
    _record_failures(limiter, "alvo@example.com", LIMIT)
    with pytest.raises(RateLimitedError):
        limiter.check("alvo@example.com")

    # 5 falhas com 15min+1s de idade — fora da janela
    stale = time.monotonic() - (WINDOW_S + 1)
    limiter._store["alvo@example.com"] = [stale] * LIMIT

    limiter.check("alvo@example.com")  # não levanta


def test_reset_on_success_clears_counter() -> None:
    """Done-when T5: login bem-sucedido (reset) zera o contador — o
    email volta a ter as 5 tentativas da janela inteiras."""
    limiter = RateLimiter()
    _record_failures(limiter, "alvo@example.com", LIMIT)
    with pytest.raises(RateLimitedError):
        limiter.check("alvo@example.com")

    limiter.reset("alvo@example.com")

    _record_failures(limiter, "alvo@example.com", LIMIT - 1)
    limiter.check("alvo@example.com")  # 4 falhas pós-reset: ainda livre


def test_emails_are_isolated() -> None:
    """Done-when T5: o lockout é POR EMAIL — 5 falhas de um email não
    travam outro (cada convidado falha sozinho)."""
    limiter = RateLimiter()
    _record_failures(limiter, "travado@example.com", LIMIT)
    with pytest.raises(RateLimitedError):
        limiter.check("travado@example.com")

    limiter.check("outro@example.com")  # não levanta