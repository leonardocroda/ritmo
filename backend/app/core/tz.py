"""Fuso do app — resolvedor único (extraído do health router, T4).

APP_TIMEZONE é a única fonte (config 100% env vars); valor inválido ->
default + logger.warning (edge do spec: o painel segue funcional no
fuso default, sem crash). Todos os pontos que precisam de datas no
fuso do app (Saúde, Home) delegam aqui — uma resposta por pergunta.
"""

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "America/Sao_Paulo"


def app_tz() -> ZoneInfo:
    """Fuso do app: APP_TIMEZONE; inválida -> default + warning."""
    name = get_settings().app_timezone
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(
            "APP_TIMEZONE inválida (%s) — usando %s", name, DEFAULT_TIMEZONE
        )
        return ZoneInfo(DEFAULT_TIMEZONE)
