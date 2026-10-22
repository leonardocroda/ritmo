"""CLI de importação run-once — ``python -m app.garmin.import_tokens [--path <p>]``.

Migra o tokenstore legado de ARQUIVO (era garmin_mcp: ``~/.garminconnect``,
layout do ``dump()`` da lib 0.3.2) para a linha do usuário 1, já CIFRADO
(GTDB-10) — transição sem re-login/MFA. Run-once por omissão: se o
usuário 1 já tem tokens, RECUSA com orientação para o login CLI (nunca
reimportar token velho sobre token novo — GTDB-11). Arquivo ausente,
ilegível ou sem ``di_token`` → erro claro, nenhuma gravação (GTDB-12).

Único leitor legítimo do arquivo legado (GTDB-19); roda no HOST — o
container não vê o home do operador sem o mount, que morre nesta feature.
"""

import argparse
import json
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import DEFAULT_USER_ID, GarminToken
from app.garmin.token_utils import resolve_token_path
from app.garmin.tokens_store import require_key, save_blob


class ImportTokensError(Exception):
    """Falha de pré-condição da importação — mensagem segura, sem token."""


def import_legacy(path: str, db: Session, fernet: Fernet) -> None:
    """Lê o tokenstore legado e grava CIFRADO na linha do usuário 1.

    ``path`` pode ser o diretório (``<path>/garmin_tokens.json`` — layout
    do ``dump()`` da lib) ou o arquivo direto. JSON sem ``di_token`` ou
    linha existente do usuário 1 → ``ImportTokensError`` ANTES de qualquer
    gravação (GTDB-11/12).
    """
    file = Path(resolve_token_path(path))
    if file.is_dir():
        file = file / "garmin_tokens.json"
    if not file.is_file():
        raise ImportTokensError(
            f"tokenstore legado não encontrado em {file} — confira o --path."
        )
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ImportTokensError(f"arquivo legado ilegível ({file}): {exc}") from exc
    if not isinstance(data, dict) or not data.get("di_token"):
        raise ImportTokensError(
            "JSON sem di_token — tokenstore legado inválido; refaça o login CLI."
        )
    existing = db.query(GarminToken).filter(GarminToken.user_id == DEFAULT_USER_ID).one_or_none()
    if existing is not None:
        raise ImportTokensError(
            "usuário 1 já tem tokens no banco — use "
            "python -m app.garmin.login --user <email> para renovar "
            "(importação é run-once)."
        )
    save_blob(db, DEFAULT_USER_ID, file.read_text(encoding="utf-8"), fernet)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importa o tokenstore legado (~/.garminconnect) para o usuário 1, cifrado."
    )
    parser.add_argument(
        "--path",
        default="~/.garminconnect",
        help="diretório do tokenstore legado ou o garmin_tokens.json direto",
    )
    args = parser.parse_args()
    fernet = require_key(get_settings())
    with SessionLocal() as db:
        try:
            import_legacy(args.path, db, fernet)
        except ImportTokensError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            sys.exit(1)
    print("Tokens legados importados e cifrados para o usuário 1.")


if __name__ == "__main__":
    main()
