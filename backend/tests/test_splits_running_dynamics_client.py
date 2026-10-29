"""Typed splits do client Garmin — funções do gateway (T3).

Unit, sem DB, sem chamada real ao Garmin: injeta um objeto `garmin` fake
no `GarminGateway` e verifica retorno, orçamento de chamadas e backoff.
"""

from types import SimpleNamespace

import pytest

from app.garmin.client import GarminGateway
from garminconnect import GarminConnectTooManyRequestsError


class _FakeGarmin:
    """Imita o client garminconnect para get_activity_splits."""

    def __init__(self, side_effects=None):
        self._calls = 0
        self.side_effects = side_effects or []

    def get_activity_splits(self, activity_id: str):
        self._calls += 1
        if self.side_effects and self._calls <= len(self.side_effects):
            raise self.side_effects[self._calls - 1]
        return {"lapDTOs": [{"lapIndex": 1, "distance": 1000.0}]}


def _gateway(garmin, calls_made=0, retry_max=3, interval_s=0) -> GarminGateway:
    settings = SimpleNamespace(
        sync_max_calls=1500,
        sync_call_interval_s=interval_s,
        sync_retry_max=retry_max,
    )
    gw = GarminGateway(garmin=garmin, settings=settings, tokens_loaded_at=None)
    gw._calls = calls_made
    return gw


def test_get_activity_splits_typed_returns_lapdto(monkeypatch) -> None:
    """Done-when T3: retorna os lapDTOs completos da atividade."""
    monkeypatch.setattr(GarminGateway, "_sleep", lambda self, s: None)
    garmin = _FakeGarmin()
    gw = _gateway(garmin)
    result = gw.get_activity_splits_typed(12345)
    assert result == {"lapDTOs": [{"lapIndex": 1, "distance": 1000.0}]}
    assert garmin._calls == 1


def test_get_activity_splits_typed_counts_call(monkeypatch) -> None:
    """Done-when T3: conta 1 chamada no orçamento (calls_made)."""
    monkeypatch.setattr(GarminGateway, "_sleep", lambda self, s: None)
    garmin = _FakeGarmin()
    gw = _gateway(garmin, calls_made=10)
    gw.get_activity_splits_typed(12345)
    assert gw.calls_made == 11


def test_get_activity_splits_typed_429_then_success(monkeypatch) -> None:
    """Done-when T3: 429 → backoff (2,4,8) ×3 retries, depois sucesso."""
    monkeypatch.setattr(GarminGateway, "_sleep", lambda self, s: None)
    garmin = _FakeGarmin(side_effects=[GarminConnectTooManyRequestsError()] * 2)
    gw = _gateway(garmin, retry_max=2)
    result = gw.get_activity_splits_typed(12345)
    assert result == {"lapDTOs": [{"lapIndex": 1, "distance": 1000.0}]}
    assert garmin._calls == 3  # 2 falhas + 1 sucesso


def test_get_activity_splits_typed_429_persistent_domain_error(monkeypatch) -> None:
    """Done-when T3: 429 persistente → erro de domínio após 3 retries."""
    monkeypatch.setattr(GarminGateway, "_sleep", lambda self, s: None)
    garmin = _FakeGarmin(side_effects=[GarminConnectTooManyRequestsError()] * 4)
    gw = _gateway(garmin, retry_max=2)
    with pytest.raises(GarminConnectTooManyRequestsError):
        gw.get_activity_splits_typed(12345)
    assert garmin._calls == 3  # retry_max + 1


def test_get_activity_splits_typed_no_splits(monkeypatch) -> None:
    """Done-when T3: atividade sem splits → None/vazio sem erro."""
    monkeypatch.setattr(GarminGateway, "_sleep", lambda self, s: None)
    garmin = _FakeGarmin()
    garmin.get_activity_splits = lambda aid: None
    gw = _gateway(garmin)
    result = gw.get_activity_splits_typed(12345)
    assert result is None
