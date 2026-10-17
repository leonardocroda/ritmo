"""Router do sync (T10) — POST cria o job, GETs expõem o estado (SYNC-01/02/05).

TestClient executa o background task de forma síncrona: depois do POST
o job já terminou `done` com stats (FakeGateway — nenhum Garmin real).
"Hoje" congelado em 2026-10-14; valores afirmados são literais do
spec/design (lição L-001).
"""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.engine import SessionLocal
from app.db.models import DEFAULT_USER_ID, SyncJob
from app.garmin import service
from app.garmin.client import GarminAuthExpiredError
from app.garmin.service import create_job
from app.main import app
from fake_garmin import FakeGateway

TODAY = date(2026, 10, 14)
STATS_KEYS = {
    "step",
    "message",
    "activities_new",
    "activities_updated",
    "splits",
    "sleep_days",
    "hrv_days",
    "rhr_days",
    "battery_days",
    "stress_days",
    "records",
    "predictions",
    "calls_made",
    "duration_s",
    "warnings",
    "reauth_needed",
}


@pytest.fixture(autouse=True)
def _frozen_today(monkeypatch):
    monkeypatch.setattr(service, "_today", lambda: TODAY)


@pytest.fixture()
def client(monkeypatch):
    """TestClient com FakeGateway — o lifespan recria o schema do teste."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    with TestClient(app) as test_client:
        yield test_client


def test_post_creates_job_and_runs_sync_to_done(client):
    """SYNC-01: 201 {id, status}; o background roda e o job termina done."""
    response = client.post("/api/sync")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    job_id = body["id"]

    job = client.get(f"/api/sync/jobs/{job_id}").json()
    assert job["id"] == job_id
    assert job["status"] == "done"  # background síncrono no TestClient
    assert job["error"] is None
    assert job["started_at"] is not None
    assert job["finished_at"] is not None
    stats = job["stats"]
    assert stats["message"] == "Sync concluído."
    assert stats["activities_new"] == 12
    assert stats["calls_made"] == 499  # inclui a 1 chamada do passo de predições (POT-01)


def test_post_conflict_409_with_running_job_state(client):
    """SYNC-02: job corrente ativo -> 409 com id/status/started_at dele."""
    with SessionLocal() as db:
        active = create_job(db, DEFAULT_USER_ID)
        active.status = "running"
        active.started_at = datetime(2026, 10, 14, 12, 0, 0)
        db.commit()
        active_id = active.id

    response = client.post("/api/sync")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["id"] == active_id
    assert detail["status"] == "running"
    assert detail["started_at"] == "2026-10-14T12:00:00"


def test_get_job_404_when_missing(client):
    response = client.get("/api/sync/jobs/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "job não encontrado"


def test_latest_job_null_when_never_synced(client):
    """Sem sync nenhum: {job: null} — a UI nasce sem estado."""
    response = client.get("/api/sync/jobs/latest")
    assert response.status_code == 200
    assert response.json() == {"job": None}


def test_latest_returns_last_job_with_stats(client):
    """Dois syncs: latest é o segundo (incremental), qualquer status serve."""
    client.post("/api/sync")
    client.post("/api/sync")

    body = client.get("/api/sync/jobs/latest").json()
    assert body["job"]["id"] == 2
    assert body["job"]["status"] == "done"
    assert body["job"]["stats"]["activities_updated"] == 4  # janela incremental


def test_job_out_and_stats_schema_exact(client):
    """Design: JobOut {id, status, started_at, finished_at, error, stats} +
    stats_json com todos os contadores, calls_made, duration_s, message,
    warnings e reauth_needed (SYNC-05/06)."""
    client.post("/api/sync")
    job = client.get("/api/sync/jobs/latest").json()["job"]

    assert set(job.keys()) == {"id", "status", "started_at", "finished_at", "error", "stats"}
    assert set(job["stats"].keys()) == STATS_KEYS
    assert job["stats"]["warnings"] == []
    assert job["stats"]["reauth_needed"] is False


def test_error_job_exposed_via_api(client, monkeypatch):
    """SYNC-14/05 via API: job error visível com mensagem e stats."""

    class FailingActivities(FakeGateway):
        def get_activities(self, start, end):
            self._record("activities", start, end)
            raise RuntimeError("atividades indisponíveis (retries esgotados)")

    monkeypatch.setattr(service, "GarminGateway", FailingActivities)
    job_id = client.post("/api/sync").json()["id"]

    job = client.get(f"/api/sync/jobs/{job_id}").json()
    assert job["status"] == "error"
    assert job["error"] == "atividades indisponíveis (retries esgotados)"
    assert job["stats"]["activities_new"] == 0
    assert job["stats"]["reauth_needed"] is False


def test_reauth_error_exposed_via_api(client, monkeypatch):
    """SYNC-25 via API: job error com reauth_needed: true no stats."""

    class ReauthGateway(FakeGateway):
        @classmethod
        def from_settings(cls, settings=None):
            raise GarminAuthExpiredError("Sessão Garmin expirada (401)")

    monkeypatch.setattr(service, "GarminGateway", ReauthGateway)
    job_id = client.post("/api/sync").json()["id"]

    job = client.get(f"/api/sync/jobs/{job_id}").json()
    assert job["status"] == "error"
    assert job["error"] == "Sessão Garmin expirada (401)"
    assert job["stats"]["reauth_needed"] is True
