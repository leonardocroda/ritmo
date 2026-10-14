"""CLI de re-auth — ``python -m app.garmin.login`` (SYNC-25/26/27).

Pede email via ``input`` e senha via ``getpass``; MFA chega via prompt
quando a lib sinaliza (callback ``prompt_mfa``). Os tokens são gravados
pela própria lib no path de ``GARMINTOKENS`` (o mesmo que o gateway
lê) e o diretório é protegido com ``secure_token_dir``.

A UI nunca pede credenciais — re-auth é CLI (decisão do spec: MFA é
interativo e fluxo web de credenciais é Fase 2.5).
"""

import getpass
from collections.abc import Callable

from garminconnect import Garmin

from app.garmin.token_utils import get_token_path, secure_token_dir


def prompt_mfa() -> str:
    """Código MFA — a lib chama este callback quando o MFA é exigido."""
    return input("Código MFA: ")


def run_login(
    email: str, password: str, mfa_prompt: Callable[[], str] | None = None
) -> str:
    """Login interativo que grava e protege os tokens; devolve o tokenstore.

    Seam de teste: credenciais e prompt injetáveis — nenhum teste toca a
    API real do Garmin (a lib entra stubada via monkeypatch).
    """
    if mfa_prompt is None:
        mfa_prompt = prompt_mfa
    garmin = Garmin(email=email, password=password, prompt_mfa=mfa_prompt)
    tokenstore = get_token_path()
    garmin.login(tokenstore)
    secure_token_dir(tokenstore)
    return tokenstore


def main() -> None:
    email = input("Email Garmin: ")
    password = getpass.getpass("Senha Garmin: ")
    tokenstore = run_login(email, password)
    print(f"Tokens gravados em {tokenstore}")


if __name__ == "__main__":
    main()
