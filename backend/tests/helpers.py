"""Helpers do ambiente de teste — a suite roda no Postgres do compose (AD-007)."""

import sqlalchemy

POSTGRES_UP_HINT = "docker compose up -d postgres"

# Porta não escutada no loopback pode pendurar o SYN por minutos no Windows
# (proxy do Docker/WSL). O probe impõe teto próprio: falha "imediatamente" (INFRA-06).
PROBE_CONNECT_TIMEOUT_S = 3


def ensure_postgres_available(database_url: str) -> None:
    """Falha rápido e claro se o Postgres de testes não estiver acessível (INFRA-06).

    Levanta RuntimeError com a instrução de subida em vez de deixar a suite
    quebrar em erros de conexão espalhados.
    """
    engine = sqlalchemy.create_engine(
        database_url,
        connect_args={"connect_timeout": PROBE_CONNECT_TIMEOUT_S},
    )
    try:
        with engine.connect():
            pass
    except Exception as exc:
        raise RuntimeError(
            f"Postgres de testes inacessível ({database_url}): {exc}. "
            f"Suba o banco antes de rodar a suite: {POSTGRES_UP_HINT}"
        ) from exc
    finally:
        engine.dispose()
