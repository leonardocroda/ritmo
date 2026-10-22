"""Router do sync (T10) — POST cria o job, GETs expõem o estado (SYNC-01/02/05).

User-scope (T5, USR-13/12): o job nasce com o user_id do usuário da
sessão (``session_client`` — sessão real, sem o override do conftest) e
os GETs só enxergam jobs do próprio usuário; job alheio -> 404.

TestClient executa o background task de forma síncrona: depois do POST
o job já terminou `done` com stats (FakeGateway — nenhum Garmin real).
"Hoje" congelado em 2026-10-14; valores afirmados são literais do
spec/design (lição L-001).
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.auth.security import hash_password
from app.db.engine import SessionLocal
from app.db.models import SyncJob, User, UserHrMetric
from app.garmin import service
from app.garmin.client import GarminAuthExpiredError
from app.garmin.service import create_job
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
def sync_client(monkeypatch, session_client):
    """session_client (sessão real) com FakeGateway — nenhum Garmin real."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    client, user_id = session_client
    return client, user_id


def test_post_creates_job_for_session_user_and_runs_to_done(sync_client):
    """SYNC-01 + USR-13: 201 {id, status}; o job nasce com user_id do
    usuário da sessão e o background termina done."""
    client, user_id = sync_client
    response = client.post("/api/sync")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    job_id = body["id"]

    with SessionLocal() as db:
        job = db.get(SyncJob, job_id)
        assert job.user_id == user_id  # USR-13: gravou com o dono da sessão

    job = client.get(f"/api/sync/jobs/{job_id}").json()
    assert job["id"] == job_id
    assert job["status"] == "done"  # background síncrono no TestClient
    assert job["error"] is None
    assert job["started_at"] is not None
    assert job["finished_at"] is not None
    stats = job["stats"]
    assert stats["message"] == "Sync concluído."
    assert stats["activities_new"] == 12
    assert stats["calls_made"] == 502  # 499 das fases + 3 da physio (1 settings + 2 LTHR)


def test_post_conflict_409_with_running_job_state(sync_client):
    """SYNC-02: job corrente ativo DO USUÁRIO -> 409 com id/status/started_at dele."""
    client, user_id = sync_client
    with SessionLocal() as db:
        active = create_job(db, user_id)
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


def test_get_job_404_when_missing(sync_client):
    client, _user_id = sync_client
    response = client.get("/api/sync/jobs/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "job não encontrado"


def test_get_job_404_for_other_users_job(sync_client):
    """USR-12: job de outro usuário -> 404 (nunca vaza a existência nem o estado)."""
    client, _user_id = sync_client
    with SessionLocal() as db:
        other = User(display_name="Outra", email="outro@example.com",
                     password_hash=hash_password("senha-segura-123"))
        db.add(other)
        db.flush()
        other_job = create_job(db, other.id)
        db.commit()
        other_job_id = other_job.id

    response = client.get(f"/api/sync/jobs/{other_job_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "job não encontrado"


def test_latest_job_null_when_never_synced(sync_client):
    """Sem sync nenhum: {job: null} — a UI nasce sem estado."""
    client, _user_id = sync_client
    response = client.get("/api/sync/jobs/latest")
    assert response.status_code == 200
    assert response.json() == {"job": None}


def test_latest_returns_last_job_with_stats(sync_client):
    """Dois syncs: latest é o segundo (incremental), qualquer status serve."""
    client, _user_id = sync_client
    client.post("/api/sync")
    client.post("/api/sync")

    body = client.get("/api/sync/jobs/latest").json()
    assert body["job"]["id"] == 2
    assert body["job"]["status"] == "done"
    assert body["job"]["stats"]["activities_updated"] == 4  # janela incremental


def test_job_out_and_stats_schema_exact(sync_client):
    """Design: JobOut {id, status, started_at, finished_at, error, stats} +
    stats_json com todos os contadores, calls_made, duration_s, message,
    warnings e reauth_needed (SYNC-05/06)."""
    client, _user_id = sync_client
    client.post("/api/sync")
    job = client.get("/api/sync/jobs/latest").json()["job"]

    assert set(job.keys()) == {"id", "status", "started_at", "finished_at", "error", "stats"}
    assert set(job["stats"].keys()) == STATS_KEYS
    assert job["stats"]["warnings"] == []
    assert job["stats"]["reauth_needed"] is False


def test_error_job_exposed_via_api(sync_client, monkeypatch):
    """SYNC-14/05 via API: job error visível com mensagem e stats."""

    class FailingActivities(FakeGateway):
        def get_activities(self, start, end):
            self._record("activities", start, end)
            raise RuntimeError("atividades indisponíveis (retries esgotados)")

    monkeypatch.setattr(service, "GarminGateway", FailingActivities)
    client, _user_id = sync_client
    job_id = client.post("/api/sync").json()["id"]

    job = client.get(f"/api/sync/jobs/{job_id}").json()
    assert job["status"] == "error"
    assert job["error"] == "atividades indisponíveis (retries esgotados)"
    assert job["stats"]["activities_new"] == 0
    assert job["stats"]["reauth_needed"] is False


def test_reauth_error_exposed_via_api(sync_client, monkeypatch):
    """SYNC-25 via API: job error com reauth_needed: true no stats."""

    class ReauthGateway(FakeGateway):
        @classmethod
        def from_user(cls, db, user_id, settings=None):
            raise GarminAuthExpiredError("Sessão Garmin expirada (401)")

    monkeypatch.setattr(service, "GarminGateway", ReauthGateway)
    client, _user_id = sync_client
    job_id = client.post("/api/sync").json()["id"]

    job = client.get(f"/api/sync/jobs/{job_id}").json()
    assert job["status"] == "error"
    assert job["error"] == "Sessão Garmin expirada (401)"
    assert job["stats"]["reauth_needed"] is True


def test_sync_physio_metrics_created_for_session_user(sync_client):
    """HRZ-05 via API: o sync popula as 3 métricas do usuário da sessão
    (user-scope) com fonte garmin — e o +3 de chamadas vem no stats."""
    client, user_id = sync_client
    client.post("/api/sync")

    with SessionLocal() as db:
        rows = (
            db.execute(
                select(UserHrMetric).where(UserHrMetric.user_id == user_id)
            )
            .scalars()
            .all()
        )
        by_kind = {row.kind: row for row in rows}
        assert set(by_kind) == {"fcmax", "fcrest", "fclthr"}
        assert by_kind["fcmax"].value_bpm == 190
        assert by_kind["fclthr"].value_bpm == 172
        assert by_kind["fcrest"].value_bpm == 42
        assert all(row.source == "garmin" for row in rows)

    job = client.get("/api/sync/jobs/latest").json()["job"]
    assert job["status"] == "done"
    assert job["stats"]["calls_made"] == 502  # 499 + 3 da fase physio
    assert job["stats"]["warnings"] == []
