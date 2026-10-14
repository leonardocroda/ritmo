"""Gateway do Garmin — unidade com a lib stubada e time.sleep monkeypatchado.

Nenhum teste toca a API real do Garmin. Os valores afirmados são os
literais do spec (SYNC-03/07/09/25): intervalo 1,0s, backoff 2/4/8s,
teto conferido antes da chamada, sem retry em auth, paginação própria
de 20 em 20 (lição L-001: literais, nunca constantes compartilhadas).
"""

from datetime import date
from typing import Any

import pytest
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from app.core.config import Settings
from app.garmin import client as client_module
from app.garmin.client import (
    GarminAuthExpiredError,
    GarminGateway,
    SyncBudgetExceededError,
)


def make_settings(**overrides) -> Settings:
    """Settings com os parâmetros de gateway pinados nos literais do spec."""
    values = {"sync_call_interval_s": 1.0, "sync_max_calls": 1500, "sync_retry_max": 3}
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeGarmin:
    """Stub da lib: registra chamadas e scripta falhas/páginas.

    Deliberadamente não tem `get_rhr_data` (não existe na 0.3.2) e o
    `get_activities_by_date` registra qualquer uso da paginação
    interna da lib, proibida pelo design.
    """

    garmin_connect_activities = "/activitylist-service/activities/search/activities"

    def __init__(self, failures: list | None = None, pages: list | None = None) -> None:
        self.failures = list(failures or [])
        self.pages = list(pages or [])
        self.calls: dict[str, list] = {}

    def _record(self, name: str, *args: Any) -> None:
        self.calls.setdefault(name, []).append(args)

    def _gate(self) -> None:
        if self.failures:
            raise self.failures.pop(0)

    def login(self, tokenstore=None):
        self._record("login", tokenstore)
        self._gate()
        return None, None

    def connectapi(self, path, **kwargs):
        self._record("connectapi", path, kwargs)
        self._gate()
        return self.pages.pop(0) if self.pages else []

    def get_activities_by_date(self, *args, **kwargs):
        self._record("get_activities_by_date", *args)
        return "PAGINACAO_INTERNA_PROIBIDA"

    def get_activity_splits(self, activity_id):
        self._record("get_activity_splits", activity_id)
        self._gate()
        return {"splits": "payload"}

    def get_sleep_data(self, cdate):
        self._record("get_sleep_data", cdate)
        self._gate()
        return {"sleep": "payload"}

    def get_hrv_data(self, cdate):
        self._record("get_hrv_data", cdate)
        self._gate()
        return {"hrv": "payload"}

    def get_rhr_day(self, cdate):
        self._record("get_rhr_day", cdate)
        self._gate()
        return {"rhr": "payload"}

    def get_stress_data(self, cdate):
        self._record("get_stress_data", cdate)
        self._gate()
        return {"stress": "payload"}

    def get_body_battery(self, startdate, enddate=None):
        self._record("get_body_battery", startdate, enddate)
        self._gate()
        return [{"battery": "payload"}]

    def get_personal_record(self):
        self._record("get_personal_record")
        self._gate()
        return {"records": "payload"}


@pytest.fixture
def sleeps(monkeypatch):
    """time.sleep monkeypatchado — registra os intervalos em vez de dormir."""
    recorded: list[float] = []
    monkeypatch.setattr(client_module.time, "sleep", lambda s: recorded.append(s))
    return recorded


def test_from_settings_login_via_tokenstore(monkeypatch, tmp_path, sleeps):
    """SYNC-25: from_settings faz login pelo tokenstore, fora do contador."""
    token_dir = str(tmp_path / "tokens")
    fake = FakeGarmin()
    monkeypatch.setattr(client_module, "Garmin", lambda: fake)
    gateway = GarminGateway.from_settings(make_settings(garmintokens=token_dir))
    assert isinstance(gateway, GarminGateway)
    assert fake.calls["login"] == [(token_dir,)]
    assert gateway.calls_made == 0  # login é custo fixo, não é chamada de dados


def test_from_settings_auth_error_maps_to_reauth(monkeypatch, tmp_path):
    """SYNC-25: 401 no login vira GarminAuthExpiredError."""
    fake = FakeGarmin(failures=[GarminConnectAuthenticationError("error 401")])
    monkeypatch.setattr(client_module, "Garmin", lambda: fake)
    with pytest.raises(GarminAuthExpiredError):
        GarminGateway.from_settings(make_settings(garmintokens=str(tmp_path / "tokens")))


def test_call_counts_and_sleeps_interval(sleeps):
    """SYNC-03: cada chamada de dados conta 1 e dorme o intervalo mínimo."""
    gateway = GarminGateway(FakeGarmin(), make_settings())
    result = gateway.get_sleep(date(2026, 10, 13))
    assert result == {"sleep": "payload"}
    assert gateway.calls_made == 1
    assert sleeps == [1.0]


def test_sequential_calls_each_count_and_sleep(sleeps):
    """SYNC-03: sequência de chamadas — uma contagem e um sleep por chamada."""
    gateway = GarminGateway(FakeGarmin(), make_settings())
    day = date(2026, 10, 13)
    gateway.get_sleep(day)
    gateway.get_hrv(day)
    gateway.get_rhr(day)
    assert gateway.calls_made == 3
    assert sleeps == [1.0, 1.0, 1.0]


def test_retry_backoff_2_4_then_success(sleeps):
    """SYNC-07: 429 retenta com backoff exato 2s/4s; sucesso dorme o intervalo."""
    fake = FakeGarmin(
        failures=[
            GarminConnectTooManyRequestsError("429"),
            GarminConnectTooManyRequestsError("429"),
        ]
    )
    gateway = GarminGateway(fake, make_settings())
    result = gateway.get_stress(date(2026, 10, 13))
    assert result == {"stress": "payload"}
    assert gateway.calls_made == 3  # cada tentativa é uma chamada feita
    assert sleeps == [2, 4, 1.0]


def test_retry_exhausted_after_3_retries_raises_last(sleeps):
    """SYNC-07: esgota 1 tentativa + 3 retries (backoff 2/4/8) e re-levanta."""
    fake = FakeGarmin(failures=[GarminConnectTooManyRequestsError("429")] * 4)
    gateway = GarminGateway(fake, make_settings())
    with pytest.raises(GarminConnectTooManyRequestsError):
        gateway.get_stress(date(2026, 10, 13))
    assert gateway.calls_made == 4
    assert sleeps == [2, 4, 8]


def test_connection_error_is_retryable(sleeps):
    """SYNC-07: erro transitório de conexão também retenta."""
    fake = FakeGarmin(failures=[GarminConnectConnectionError("boom")])
    gateway = GarminGateway(fake, make_settings())
    result = gateway.get_hrv(date(2026, 10, 13))
    assert result == {"hrv": "payload"}
    assert gateway.calls_made == 2
    assert sleeps == [2, 1.0]


def test_auth_error_on_data_call_never_retries(sleeps):
    """SYNC-25: auth expirada em chamada de dados → reauth, sem retry e sem sleep."""
    fake = FakeGarmin(failures=[GarminConnectAuthenticationError("401")] * 5)
    gateway = GarminGateway(fake, make_settings())
    with pytest.raises(GarminAuthExpiredError):
        gateway.get_sleep(date(2026, 10, 13))
    assert gateway.calls_made == 1
    assert sleeps == []


def test_budget_ceiling_blocks_before_call(sleeps):
    """SYNC-09: atingido o teto, a chamada é bloqueada ANTES de chegar à API."""
    fake = FakeGarmin()
    gateway = GarminGateway(fake, make_settings(sync_max_calls=2))
    gateway.get_sleep(date(2026, 10, 13))
    gateway.get_hrv(date(2026, 10, 13))
    with pytest.raises(SyncBudgetExceededError):
        gateway.get_rhr(date(2026, 10, 13))
    assert gateway.calls_made == 2
    assert fake.calls.get("get_rhr_day", []) == []  # a API nem foi chamada
    assert sleeps == [1.0, 1.0]


def test_get_activities_paginates_own_20_by_page(sleeps):
    """Design: paginação própria via connectapi — 1 contagem + 1 sleep por página."""
    page1 = [{"activityId": i} for i in range(20)]
    page2 = [{"activityId": 100 + i} for i in range(5)]
    fake = FakeGarmin(pages=[page1, page2])
    gateway = GarminGateway(fake, make_settings())
    result = gateway.get_activities(date(2026, 4, 17), date(2026, 10, 14))
    assert len(result) == 25
    assert result[0] == {"activityId": 0}
    assert result[-1] == {"activityId": 104}
    assert gateway.calls_made == 2
    assert sleeps == [1.0, 1.0]
    assert fake.calls.get("get_activities_by_date", []) == []  # paginação interna proibida
    path, kwargs = fake.calls["connectapi"][0]
    assert path == fake.garmin_connect_activities
    assert kwargs["params"] == {
        "startDate": "2026-04-17",
        "endDate": "2026-10-14",
        "start": "0",
        "limit": "20",
    }
    _, kwargs2 = fake.calls["connectapi"][1]
    assert kwargs2["params"]["start"] == "20"
    assert kwargs2["params"]["limit"] == "20"


def test_get_activities_single_short_page_stops(sleeps):
    """Página com menos de 20 itens encerra a paginação sem probe extra."""
    page = [{"activityId": i} for i in range(3)]
    fake = FakeGarmin(pages=[page])
    gateway = GarminGateway(fake, make_settings())
    result = gateway.get_activities(date(2026, 10, 11), date(2026, 10, 14))
    assert result == page
    assert gateway.calls_made == 1
    assert len(fake.calls["connectapi"]) == 1


def test_get_battery_chunks_range_over_28_days(sleeps):
    """T15 real: a API limita o range de body battery ("date range is
    too big") — janela de 61 dias vira 3 blocos de <= 28 dias, cada um
    contado com o seu intervalo (sequência preservada, SYNC-03)."""
    fake = FakeGarmin()
    gateway = GarminGateway(fake, make_settings())
    result = gateway.get_body_battery(date(2026, 8, 15), date(2026, 10, 14))
    assert fake.calls["get_body_battery"] == [
        ("2026-08-15", "2026-09-11"),
        ("2026-09-12", "2026-10-09"),
        ("2026-10-10", "2026-10-14"),
    ]
    assert gateway.calls_made == 3
    assert sleeps == [1.0, 1.0, 1.0]
    assert len(result) == 3  # 1 linha por bloco no stub


def test_gateway_exposes_eight_data_methods(sleeps):
    """Design: os 8 métodos de dados, cada um exatamente 1 chamada via _call()."""
    fake = FakeGarmin()
    gateway = GarminGateway(fake, make_settings())
    day = date(2026, 10, 13)

    assert gateway.get_activities(day, day) == []
    assert gateway.get_splits(9876543210) == {"splits": "payload"}
    assert gateway.get_sleep(day) == {"sleep": "payload"}
    assert gateway.get_hrv(day) == {"hrv": "payload"}
    assert gateway.get_rhr(day) == {"rhr": "payload"}
    assert gateway.get_stress(day) == {"stress": "payload"}
    assert gateway.get_body_battery(day, day) == [{"battery": "payload"}]
    assert gateway.get_personal_records() == {"records": "payload"}

    assert gateway.calls_made == 8
    assert fake.calls["get_activity_splits"] == [("9876543210",)]
    assert fake.calls["get_sleep_data"] == [("2026-10-13",)]
    assert fake.calls["get_hrv_data"] == [("2026-10-13",)]
    assert fake.calls["get_rhr_day"] == [("2026-10-13",)]
    assert fake.calls["get_stress_data"] == [("2026-10-13",)]
    assert fake.calls["get_body_battery"] == [("2026-10-13", "2026-10-13")]
    assert fake.calls["get_personal_record"] == [()]
