"""Gateway do Garmin — único ponto de acesso à API (AD-002).

Aqui, e só aqui, existem: contagem de chamadas, intervalo mínimo,
retry com backoff e teto. O resto do backend nunca importa a lib
`garminconnect` (princípio estrutural do design do garmin-sync).

Fatos verificados da lib (garminconnect==0.3.2, pinada no pyproject):
- `get_rhr_day` existe; `get_rhr_data` não existe nesta versão;
- `get_activities_by_date` pagina internamente de 20 em 20 sem pausa
  entre páginas (rajada) — por isso `get_activities` pagina por conta
  própria via `connectapi`, com 1 contagem + 1 sleep por página;
- `get_user_settings` não existe nesta versão: o endpoint user-settings
  (payload `userData`) é o `get_user_profile` — e, constatado em UAT real
  (21/10/2026), `userData` NÃO traz `maxHeartRate` (a Garmin não o armazena
  no perfil); a FC máx auto-detectada vive no endpoint de zonas de FC
  `/biometric-service/heartRateZones/v2` (chave `maxHeartRateUsed` do
  esporte RUNNING), lido aqui via `connectapi` genérico;
- `get_lactate_threshold(latest=True)` faz 2 requests internos (power +
  HR) — o orçamento conta os dois (fase physio do hr-zones).
"""

import time
from collections.abc import Callable
from datetime import date, timedelta
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
BATTERY_MAX_RANGE_DAYS = 28  # T15 real: a API devolve 400 "date range is too big" acima disso
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

    # -- 11 métodos de dados do design ------------------------------------

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
        """Body battery da janela, fatiada em blocos de <= 28 dias.

        Descoberta da primeira sync real (T15): ranges maiores tomam 400
        ("date range is too big"). Cada bloco é 1 chamada contada com o
        seu intervalo — a sequência permanece (SYNC-03).
        """
        rows: list[dict] = []
        block_start = start
        while block_start <= end:
            block_end = min(block_start + timedelta(days=BATTERY_MAX_RANGE_DAYS - 1), end)
            rows.extend(
                self._call(
                    lambda bs=block_start, be=block_end: self._garmin.get_body_battery(
                        bs.isoformat(), be.isoformat()
                    )
                )
            )
            block_start = block_end + timedelta(days=1)
        return rows

    def get_personal_records(self) -> dict:
        return self._call(self._garmin.get_personal_record)

    def get_race_predictions(self) -> dict:
        """Preditor de prova (snapshot latest) — 1 chamada (POT-01)."""
        return self._call(self._garmin.get_race_predictions)

    # SPEC_DEVIATION (fix UAT 21/10/2026): o design apontava o fcmax em
    # `userData.maxHeartRate` (user settings) — o payload real da conta NÃO
    # tem essa chave (a Garmin não armazena FC máx no perfil; calcula). A
    # FC máx auto-detectada (como o LTHR) vive no endpoint de zonas de FC
    # `/biometric-service/heartRateZones/v2` (`maxHeartRateUsed` do esporte
    # RUNNING; confirmado em runtime: 199 detectado, 220-idade daria 192).
    # A lib 0.3.2 não envelopa o endpoint — leitura via `connectapi`.
    def get_heart_rate_zones(self) -> list:
        """Zonas de FC v2 do perfil — `maxHeartRateUsed` do esporte RUNNING
        (fallback DEFAULT) é a fonte do fcmax auto-detectado (fase physio
        do hr-zones). Read-only, como o resto do gateway."""
        return self._call(
            lambda: self._garmin.connectapi(
                "/biometric-service/heartRateZones/v2?generateDefaults=false"
            )
        )

    def get_lactate_threshold(self) -> dict:
        """LTHR auto-detectado (latest) — 1 `_call` que na API custa 2
        chamadas internas da lib (power + HR): o contador soma as duas
        (orçamento honesto — o servidor consumiu os dois requests)."""
        result = self._call(lambda: self._garmin.get_lactate_threshold(latest=True))
        self._calls += 1  # 2ª chamada interna da lib (power): burst, sem pausa
        return result
