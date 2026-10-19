"""Rate limiter de login em memória (feature auth — AUTH-08).

5 falhas por email em 15 minutos → ``RateLimitedError`` (o router
responde 429). Contador em memória: reinicia no restart do backend —
aceitável no MVP (assumption do spec auth); interface trocável por
Redis na Fase 2.5. ``_store`` é exposto para a fixture de teste zerar/
manipular estado (mesmo padrão do ``_clean_database``).
"""

import threading
import time

# Literais do spec auth (AUTH-08): 5 falhas por email em 15 minutos
WINDOW_S = 15 * 60
MAX_FAILURES = 5


class RateLimitedError(Exception):
    """Email com ≥5 falhas de login na janela — o router responde 429.

    Mensagem acionável em PT-BR (edge case do spec): informa tentativas
    demais e a janela de 15 minutos.
    """


class RateLimiter:
    """Contador de falhas de login por email, em memória, thread-safe.

    Fluxo do service (T6): ``check`` ANTES de tentar autenticar (trava
    mesmo com senha correta), ``record_failure`` a cada senha errada,
    ``reset`` no sucesso.
    """

    def __init__(self) -> None:
        # email -> timestamps (monotonic) das falhas na janela corrente;
        # exposto por design para a fixture de teste
        self._store: dict[str, list[float]] = {}
        # Worker único (uvicorn, 1 container) — o lock é higiene barata
        # para o dia em que houver mais de uma thread
        self._lock = threading.Lock()

    def check(self, email: str) -> None:
        """Levanta RateLimitedError se o email já tem ≥5 falhas na janela."""
        now = time.monotonic()
        with self._lock:
            failures = self._recent_failures(email, now)
            if len(failures) >= MAX_FAILURES:
                raise RateLimitedError(
                    "Muitas tentativas de login. Aguarde 15 minutos antes "
                    "de tentar novamente."
                )

    def record_failure(self, email: str) -> None:
        """Registra uma falha de login do email na janela corrente."""
        now = time.monotonic()
        with self._lock:
            failures = self._recent_failures(email, now)
            failures.append(now)
            self._store[email] = failures

    def reset(self, email: str) -> None:
        """Login bem-sucedido zera o contador do email."""
        with self._lock:
            self._store.pop(email, None)

    def _recent_failures(self, email: str, now: float) -> list[float]:
        """Falhas do email ainda dentro da janela de 15 min (poda lazy)."""
        recent = [
            ts for ts in self._store.get(email, []) if now - ts < WINDOW_S
        ]
        self._store[email] = recent
        return recent
