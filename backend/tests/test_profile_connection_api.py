"""API do status da conexão Garmin (T9, feature garmin-tokens-db) — HTTP
no Postgres real via `session_client` (padrão hr-zones).

Rotas em escopo (matriz): os 3 estados (GTDB-16 — not_connected,
reauth_needed, connected), a emenda GTDB-16 (tokens atualizados APÓS o
job falho → connected) e 401 sem sessão (GTDB-17, padrão do include no
main). O endpoint NUNCA decripta o blob: a resposta só tem `state` +
`tokens_updated_at` — os testes afirmam o shape FECHADO (dicionário
inteiro), então nenhum fragmento de blob escaparia.
"""

from datetime import datetime

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.db.engine import SessionLocal
from app.db.models import GarminToken, SyncJob
from app.main import app
from helpers import TEST_TOKEN_ENCRYPTION_KEY

# Datetimes naive deterministas (colunas TIMESTAMP são naive): a ordem
# relativa tokens × fim do job é o que a derivação compara.
TOKEN_TS = datetime(2026, 10, 22, 10, 0, 0)
TOKEN_ISO = "2026-10-22T10:00:00"
JOB_TS = datetime(2026, 10, 22, 11, 0, 0)

# A coluna guarda SÓ ciphertext (GTDB-13) — o endpoint lê metadados, mas
# a semente respeita a invariante da coluna.
BLOB = Fernet(TEST_TOKEN_ENCRYPTION_KEY).encrypt(b'{"di_token": "f"}').decode("utf-8")


def _seed_tokens(db, user_id: int, updated_at: datetime) -> None:
    db.add(
        GarminToken(
            user_id=user_id,
            token_encrypted=BLOB,
            created_at=updated_at,
            updated_at=updated_at,
        )
    )


def _seed_job(
    db,
    user_id: int,
    *,
    status: str,
    stats: dict | None,
    finished_at: datetime | None,
) -> None:
    db.add(
        SyncJob(
            user_id=user_id,
            status=status,
            stats_json=stats,
            finished_at=finished_at,
        )
    )


def _get(client) -> dict:
    res = client.get("/api/profile/garmin-connection")
    assert res.status_code == 200
    return res.json()


# ---------------------------------------------------------------
# Os 3 estados (GTDB-16)
# ---------------------------------------------------------------


def test_not_connected_without_tokens(session_client) -> None:
    """GTDB-16: sem linha de tokens → not_connected (e sem data)."""
    client, _user_id = session_client
    assert _get(client) == {"state": "not_connected", "tokens_updated_at": None}


def test_connected_with_tokens_and_healthy_job(session_client) -> None:
    """GTDB-16: linha de tokens e último job sem reauth pendente →
    connected (a perna "caso contrário"), com a data dos tokens."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_tokens(db, user_id, TOKEN_TS)
        _seed_job(
            db, user_id, status="done", stats={"reauth_needed": False}, finished_at=JOB_TS
        )
        db.commit()
    assert _get(client) == {
        "state": "connected",
        "tokens_updated_at": TOKEN_ISO,
    }


def test_reauth_needed_after_failed_job(session_client) -> None:
    """GTDB-16: último job error com reauth_needed=true (SYNC-25) e
    tokens NÃO atualizados depois do fim do job → reauth_needed."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_tokens(db, user_id, TOKEN_TS)  # 10:00, antes do fim do job (11:00)
        _seed_job(
            db, user_id, status="error", stats={"reauth_needed": True}, finished_at=JOB_TS
        )
        db.commit()
    assert _get(client) == {
        "state": "reauth_needed",
        "tokens_updated_at": TOKEN_ISO,
    }


def test_connected_when_tokens_updated_after_failed_job(session_client) -> None:
    """GTDB-16 emendado: tokens atualizados APÓS o job falho (re-login
    CLI) → volta a exibir connected."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_tokens(db, user_id, JOB_TS)  # 11:00, depois do fim do job (10:00)
        _seed_job(
            db, user_id, status="error", stats={"reauth_needed": True}, finished_at=TOKEN_TS
        )
        db.commit()
    assert _get(client)["state"] == "connected"


# ---------------------------------------------------------------
# Auth (GTDB-17 — padrão do include)
# ---------------------------------------------------------------


def test_requires_session_401() -> None:
    """GTDB-17: sem sessão → 401 (o include no main protege o router)."""
    with TestClient(app) as client:
        res = client.get("/api/profile/garmin-connection")
        assert res.status_code == 401
