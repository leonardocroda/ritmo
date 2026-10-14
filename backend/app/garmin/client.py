"""Gateway do Garmin — único ponto de acesso à API (AD-002).

Aqui, e só aqui, existem: contagem de chamadas, intervalo mínimo,
retry com backoff e teto. O resto do backend nunca importa a lib
`garminconnect` (princípio estrutural do design do garmin-sync).

Fatos verificados da lib (garminconnect==0.3.2, pinada no pyproject):
- `get_rhr_day` existe; `get_rhr_data` não existe nesta versão;
- `get_activities_by_date` pagina internamente de 20 em 20 sem pausa
  entre páginas (rajada) — por isso `get_activities` pagina por conta
  própria via `connectapi`, com 1 contagem + 1 sleep por página.
"""

import time
from collections.abc import Callable
from datetime import date
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from app.core.config import Settings
from app.garmin.token_utils import resolve_token_path, secure_token_dir

PAGE_SIZE = 20
RETRY_BACKOFF_S = (2, 4, 8)  # SYNC-07: backoff exponencial literal do spec


class GarminAuthExpiredError(Exception):
    """Token morto/401 — sem retry; o job vira `error` com reauth_needed."""


class SyncBudgetExceededError(Exception):
    """Teto SYNC_MAX_CALLS atingido — guard rail contra runaway (SYNC-09)."""


class GarminGateway:
    """Todas as chamadas de dados passam por `_call()` — sequência garantida."""

    def __init__(self, garmin: Garmin, settings: Settings) -> None:
        self._garmin = garmin
        self.settings = settings
        self._calls = 0

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "GarminGateway":
        """Login pelo tokenstore existente (SYNC-25) — nunca pede credenciais.

        As ~2 chamadas internas do `login()` são custo fixo documentado:
        ficam fora do contador de chamadas de dados.
        """
        settings = settings or Settings()
        tokenstore = resolve_token_path(settings.garmintokens)
        garmin = Garmin()
        try:
            garmin.login(tokenstore)
        except GarminConnectAuthenticationError as exc:
            raise GarminAuthExpiredError(str(exc)) from exc
        secure_token_dir(tokenstore)
        return cls(garmin, settings)

    @property
    def calls_made(self) -> int:
        return self._calls

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def _call(self, fn: Callable[[], Any]) -> Any:
        """Uma chamada de dados à API do Garmin — o único caminho.

        Ordem imposta: teto conferido ANTES da chamada (SYNC-09); cada
        tentativa conta em `calls_made` (429 também consumiu o servidor —
        auditoria honesta); sucesso dorme o intervalo mínimo (SYNC-03);
        429/erro transitório retenta com backoff 2/4/8s até sync_retry_max
        (SYNC-07); auth expirada nunca retenta (SYNC-25).
        """
        last_exc: Exception | None = None
        for attempt in range(self.settings.sync_retry_max + 1):
            if self._calls >= self.settings.sync_max_calls:
                raise SyncBudgetExceededError(
                    f"Teto de chamadas atingido ({self.settings.sync_max_calls}); "
                    f"feitas {self._calls}."
                )
            self._calls += 1
            try:
                result = fn()
            except GarminConnectAuthenticationError as exc:
                raise GarminAuthExpiredError(str(exc)) from exc
            except (
                GarminConnectTooManyRequestsError,
                GarminConnectConnectionError,
            ) as exc:
                last_exc = exc
                if attempt < self.settings.sync_retry_max:
                    self._sleep(RETRY_BACKOFF_S[min(attempt, len(RETRY_BACKOFF_S) - 1)])
                continue
            self._sleep(self.settings.sync_call_interval_s)
            return result
        raise last_exc  # retries esgotados — o tipo será tratado como falho

    # -- 8 métodos de dados do design -------------------------------------

    def get_activities(self, start: date, end: date) -> list[dict]:
        """Atividades por data com paginação PRÓPRIA (20/pág via connectapi).

        A paginação da lib itera sem pausa entre páginas; aqui cada página
        é 1 contagem + 1 sleep (design: controle total do orçamento).
        """
        activities: list[dict] = []
        offset = 0
        while True:
            page = self._call(
                lambda offset=offset: self._garmin.connectapi(
                    self._garmin.garmin_connect_activities,
                    params={
                        "startDate": start.isoformat(),
                        "endDate": end.isoformat(),
                        "start": str(offset),
                        "limit": str(PAGE_SIZE),
                    },
                )
            )
            if not page:
                return activities
            activities.extend(page)
            if len(page) < PAGE_SIZE:
                return activities
            offset += PAGE_SIZE

    def get_splits(self, activity_id: int) -> dict | None:
        return self._call(lambda: self._garmin.get_activity_splits(str(activity_id)))

    def get_sleep(self, day: date) -> dict | None:
        return self._call(lambda: self._garmin.get_sleep_data(day.isoformat()))

    def get_hrv(self, day: date) -> dict | None:
        return self._call(lambda: self._garmin.get_hrv_data(day.isoformat()))

    def get_rhr(self, day: date) -> dict | None:
        return self._call(lambda: self._garmin.get_rhr_day(day.isoformat()))

    def get_stress(self, day: date) -> dict | None:
        return self._call(lambda: self._garmin.get_stress_data(day.isoformat()))

    def get_body_battery(self, start: date, end: date) -> list[dict]:
        return self._call(
            lambda: self._garmin.get_body_battery(start.isoformat(), end.isoformat())
        )

    def get_personal_records(self) -> dict:
        return self._call(self._garmin.get_personal_record)
