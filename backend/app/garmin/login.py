"""CLI de login por usuário — ``python -m app.garmin.login --user <email>``.

Conecta a conta Garmin de um usuário JÁ CADASTRADO no Ritmo (feature
garmin-tokens-db, AD-014): onboarding de convidado é operador-assistida
— o convidado nunca digita a senha Garmin no site. Credenciais no
terminal (senha via getpass; MFA via prompt quando a lib sinaliza) e
tokens gravados CIFRADOS na linha do usuário no banco (upsert —
re-login substitui; GTDB-07).

Nada vai para arquivo: ``GARMINTOKENS`` é removida do env do processo e
o ``login`` é chamado SEM tokenstore — a lib usaria o arquivo como
fallback e o convidado herdaria os tokens do operador (risco do
design). O banco é a única fonte (GTDB-19). Falhas do login são
traduzidas para mensagens FIXAS: nenhum fragmento de token/blob na
saída (GTDB-15). A UI nunca pede credenciais — re-auth é CLI.
"""

import argparse
import getpass
import json
import os
import sys
from collections.abc import Callable

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import User
from app.garmin.tokens_store import require_key, save_blob


class LoginError(Exception):
    """Falha de pré-condição do login — mensagem segura, sem token (GTDB-15)."""


def prompt_mfa() -> str:
    """Código MFA — a lib chama este callback quando o MFA é exigido."""
    return input("Código MFA: ")


def run_login(
    db: Session,
    user_id: int,
    email: str,
    password: str,
    mfa_prompt: Callable[[], str] | None = None,
) -> None:
    """Login de credenciais + gravação CIFRADA na linha do usuário (upsert).

    Seam de teste: db, credenciais e prompt injetáveis — nenhum teste
    toca a API real do Garmin (a lib entra stubada via monkeypatch).
    Falha do login levanta ANTES da gravação: tokens existentes ficam
    intactos (GTDB-09). Sessão sem ``di_token`` (dumps jwt_web-only) →
    ``LoginError`` — nada gravado (nenhum blob inútil no banco).
    """
    if mfa_prompt is None:
        mfa_prompt = prompt_mfa
    # Nunca resumir de arquivo/env: o login de um convidado salvaria os
    # tokens do operador na linha dele (risco registrado no design)
    os.environ.pop("GARMINTOKENS", None)
    garmin = Garmin(email=email, password=password, prompt_mfa=mfa_prompt)
    garmin.login(None)  # sem tokenstore — o banco é a única fonte
    blob = garmin.client.dumps()
    if not json.loads(blob).get("di_token"):
        raise LoginError("sessão sem token DI — refaça o login")
    save_blob(db, user_id, blob, require_key(get_settings()))
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Conecta a conta Garmin de um usuário do Ritmo (tokens cifrados no banco)."
    )
    parser.add_argument("--user", required=True, help="email do usuário cadastrado no Ritmo")
    args = parser.parse_args()
    email = args.user.strip().lower()  # mesma normalização do auth (service)
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            print(
                f"Erro: usuário {email} não encontrado — cadastre-o antes de conectar o Garmin.",
                file=sys.stderr,
            )
            sys.exit(1)
        password = getpass.getpass(f"Senha Garmin de {email}: ")
        try:
            run_login(db, user.id, email, password)
        except LoginError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            sys.exit(1)
        except GarminConnectTooManyRequestsError:
            print(
                "Erro: muitas tentativas de login no Garmin — aguarde alguns minutos e repita.",
                file=sys.stderr,
            )
            sys.exit(1)
        except (GarminConnectAuthenticationError, GarminConnectConnectionError):
            print(
                "Erro: login Garmin falhou — confira o email, a senha e o código MFA.",
                file=sys.stderr,
            )
            sys.exit(1)
    print(f"Tokens Garmin de {email} gravados no banco (cifrados).")


if __name__ == "__main__":
    main()
