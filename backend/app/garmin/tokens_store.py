"""Cofre dos tokens Garmin — Fernet + banco (feature garmin-tokens-db).

ÚNICO módulo que toca a coluna cifrada (GTDB-13): cifra, decripta, lê e
grava o blob — nenhuma chamada de log aqui (GTDB-15), o blob é segredo
mesmo cifrado. Blob que não decripta (chave trocada/perdida) sobe como
``InvalidToken``: os chamadores tratam como "sem tokens" (estado
"Reconectar", GTDB-03) — nunca crash do sync.

Funções de escrita NÃO comitam: o chamador controla a transação (padrão
de `upserts.py` — o service decide a fronteira; os CLIs comitam no fim).
"""

from datetime import datetime

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import GarminToken

# Mensagem única de fail-fast (GTDB-14): ausente e inválida apontam a
# MESMA correção — gerar a chave e definir no ambiente
_KEY_HELP = (
    "TOKEN_ENCRYPTION_KEY ausente ou inválida — gere uma chave com "
    'python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())" '
    "e defina no .env (ou no ambiente do compose)."
)


class TokenKeyError(Exception):
    """Chave de criptografia ausente/inválida — o backend não sobe (GTDB-14)."""


def require_key(settings: Settings) -> Fernet:
    """Valida presença e formato da chave; devolve o Fernet pronto.

    Fail-fast (GTDB-14): chave ausente ou que não instancia Fernet
    levanta ``TokenKeyError`` com o comando de geração no texto.
    """
    raw = settings.token_encryption_key
    if not raw:
        raise TokenKeyError(_KEY_HELP)
    try:
        return Fernet(raw)
    except (TypeError, ValueError) as exc:
        raise TokenKeyError(_KEY_HELP) from exc


def get_blob(db: Session, user_id: int, fernet: Fernet) -> tuple[str, datetime] | None:
    """Blob decriptado + ``updated_at`` da linha — None sem linha (GTDB-01).

    O ``updated_at`` volta como foi carregado: é o valor que o guard
    otimista do persist-back compara (GTDB-04). Ciphertext de outra
    chave levanta ``InvalidToken`` — o chamador decide.
    """
    row = db.execute(
        select(GarminToken).where(GarminToken.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        return None
    blob = fernet.decrypt(row.token_encrypted.encode("utf-8")).decode("utf-8")
    return blob, row.updated_at


def save_blob(
    db: Session,
    user_id: int,
    blob: str,
    fernet: Fernet,
    expected_updated_at: datetime | None = None,
) -> bool:
    """Upsert CIFRADO do blob (GTDB-13) — nunca texto plano na coluna.

    Sem ``expected_updated_at``: cria a linha ou atualiza a existente
    (re-login legítimo). Com ele: UPDATE otimista ``WHERE updated_at =
    :expected`` (GTDB-04) — ``False`` significa que a linha mudou desde
    o carregamento (ex.: re-login CLI durante o sync) e a versão mais
    nova foi PRESERVADA. ``synchronize_session=False`` evita sincronizar
    o objeto da identity map: no sync, o commit seguinte do job não pode
    ressuscitar o ciphertext antigo sobre a linha recusada.
    """
    ciphertext = fernet.encrypt(blob.encode("utf-8")).decode("utf-8")
    if expected_updated_at is None:
        row = db.execute(
            select(GarminToken).where(GarminToken.user_id == user_id)
        ).scalar_one_or_none()
        if row is None:
            db.add(GarminToken(user_id=user_id, token_encrypted=ciphertext))
        else:
            row.token_encrypted = ciphertext  # onupdate avança updated_at
        return True
    result = db.execute(
        update(GarminToken)
        .where(
            GarminToken.user_id == user_id,
            GarminToken.updated_at == expected_updated_at,
        )
        .values(token_encrypted=ciphertext)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount > 0


def get_meta(db: Session, user_id: int) -> tuple[bool, datetime | None]:
    """(existe, updated_at) sem decriptar — endpoint de status (GTDB-16/17)."""
    updated_at = db.execute(
        select(GarminToken.updated_at).where(GarminToken.user_id == user_id)
    ).scalar_one_or_none()
    return (updated_at is not None, updated_at)
