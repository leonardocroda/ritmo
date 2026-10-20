"""Isolamento A×B (T8, USR-08..12) — ponta a ponta no Postgres real.

Usuário X e Y com sessões próprias no mesmo banco: cada endpoint de
leitura devolve só o dado do dono; toda gravação vincula ao dono da
sessão; recurso alheio -> 404; sem sessão -> 401. Um único TestClient
troca o cookie entre X e Y (o conftest semeia X; Y nasce aqui) — dois
dispositivos, mesmo banco. NIM e Garmin sempre mockados (nenhum teste
chama API real).
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.auth.security import hash_password
from app.auth.service import create_session
from app.core.config import Settings
from app.db.engine import SessionLocal
from app.db.models import Activity, DailyLoad, Evaluation, Sleep, SyncJob, User
from app.garmin import service as garmin_service
from fake_garmin import FakeGateway

TODAY = date(2026, 10, 14)


@pytest.fixture(autouse=True)
def _frozen_today(monkeypatch):
    """Sync determinístico — mesma âncora do FakeGateway (14/10/2026)."""
    monkeypatch.setattr(garmin_service, "_today", lambda: TODAY)


@pytest.fixture(autouse=True)
def _clean_eval_env(monkeypatch):
    for var in ("LTHR_BPM", "VDOT_ZONES_PATH", "NVIDIA_API_KEY", "NVIDIA_MODEL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _eval_settings(monkeypatch):
    """Router de avaliação sempre com key de teste (padrão test_evaluation_api)."""
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key="test-key"),
    )


def _mock_nim_ok(monkeypatch) -> None:
    def fake(system: str, user: str, settings, transport=None):
        return {
            "veredito": "on_target",
            "headline": "ok",
            "execucao_vs_intencao": {"pct_zona_alvo": 80.0, "principais_desvios": []},
            "o_que_funcionou": [],
            "corrigir_prox_vez": [],
            "contexto_relevante": [],
            "confianca": "alta",
        }, {"prompt_tokens": 1, "completion_tokens": 1}

    monkeypatch.setattr("app.evaluation.nim.chat_completion", fake)


def _seed_other_user(db) -> tuple[User, str]:
    """Usuário Y + sessão própria (token para trocar o cookie)."""
    other = User(
        display_name="Outra",
        email="outra@example.com",
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(other)
    db.flush()
    token = create_session(db, other.id)
    db.commit()
    return other, token


def _seed_run(db, user_id: int, garmin_id: str) -> Activity:
    activity = Activity(
        user_id=user_id,
        garmin_id=garmin_id,
        start_time=datetime(2026, 10, 13, 7, 0, 0),
        activity_type="running",
        name="Easy Run",
        distance_m=5000.0,
        duration_s=1500.0,
        avg_hr=145,
    )
    db.add(activity)
    db.commit()
    return activity


# ---------------------------------------------------------------
# Leitura: X não enxerga Y em nenhum painel (USR-01..04/08)
# ---------------------------------------------------------------


def test_activities_list_and_detail_isolated(session_client) -> None:
    """USR-01/02/08: X lista só X; Y lista só Y; detalhe alheio -> 404."""
    client, user_id = session_client
    with SessionLocal() as db:
        other, other_token = _seed_other_user(db)
        own = _seed_run(db, user_id, "iso-x1")
        alien = _seed_run(db, other.id, "iso-y1")
        db.commit()
        own_id, alien_id, other_id = own.id, alien.id, other.id

    # X: só a própria corrida
    body_x = client.get("/api/activities").json()
    assert body_x["total"] == 1
    assert [item["id"] for item in body_x["items"]] == [own_id]

    # detalhe da corrida de Y na sessão de X -> 404
    response = client.get(f"/api/activities/{alien_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"

    # troca o cookie para Y: só a corrida de Y; detalhe de X -> 404
    client.cookies.set("ritmo_session", other_token)
    body_y = client.get("/api/activities").json()
    assert body_y["total"] == 1
    assert [item["id"] for item in body_y["items"]] == [alien_id]
    assert client.get(f"/api/activities/{own_id}").status_code == 404
    assert other_id != user_id


def test_health_summary_isolated(session_client) -> None:
    """USR-03/08: a noite de Y não entra no painel de X (nem vice-versa)."""
    client, user_id = session_client
    with SessionLocal() as db:
        other, other_token = _seed_other_user(db)
        db.add(Sleep(user_id=user_id, date=date(2026, 10, 13),
                     duration_s=28800.0, score=80))  # X: 8h adequada
        db.add(Sleep(user_id=other.id, date=date(2026, 10, 14),
                     duration_s=14400.0, score=30))  # Y: 4h curta
        db.commit()

    body_x = client.get("/api/health/summary").json()
    assert [p["date"] for p in body_x["sleep"]["points"]] == ["2026-10-13"]
    assert body_x["sleep"]["below_floor"] == {"nights": 0, "pct": 0.0}

    client.cookies.set("ritmo_session", other_token)
    body_y = client.get("/api/health/summary").json()
    assert [p["date"] for p in body_y["sleep"]["points"]] == ["2026-10-14"]
    assert body_y["sleep"]["below_floor"] == {"nights": 1, "pct": 100.0}


def test_potential_pmc_isolated(session_client) -> None:
    """USR-04/08: a curva PMC de X carrega só as linhas de X."""
    client, user_id = session_client
    with SessionLocal() as db:
        other, other_token = _seed_other_user(db)
        db.add(DailyLoad(user_id=user_id, date=date(2026, 10, 15),
                         ctl=22.0, atl=28.0, tsb=-6.0, acwr=1.42))
        db.add(DailyLoad(user_id=other.id, date=date(2026, 10, 15),
                         ctl=90.0, atl=95.0, tsb=-5.0, acwr=2.0))
        db.commit()

    body_x = client.get("/api/potential").json()
    assert body_x["pmc"]["points"] == [
        {"date": "2026-10-15", "ctl": 22.0, "atl": 28.0, "tsb": -6.0, "acwr": 1.42},
    ]

    client.cookies.set("ritmo_session", other_token)
    body_y = client.get("/api/potential").json()
    assert body_y["pmc"]["points"] == [
        {"date": "2026-10-15", "ctl": 90.0, "atl": 95.0, "tsb": -5.0, "acwr": 2.0},
    ]


# ---------------------------------------------------------------
# Gravação: sync e avaliação nascem com o dono da sessão (USR-09..16)
# ---------------------------------------------------------------


def test_sync_job_and_data_isolated(session_client, monkeypatch) -> None:
    """USR-13/14/10: POST de sync como X cria job de X, grava dados de X —
    e Y continua com banco vazio."""
    client, user_id = session_client
    monkeypatch.setattr(garmin_service, "GarminGateway", FakeGateway)
    with SessionLocal() as db:
        other, other_token = _seed_other_user(db)

    response = client.post("/api/sync")
    assert response.status_code == 201
    job_id = response.json()["id"]

    with SessionLocal() as db:
        job = db.get(SyncJob, job_id)
        assert job.user_id == user_id  # USR-13: job do dono da sessão
        assert job.status == "done"  # FakeGateway síncrono no TestClient

    # dados sincronizados pertencem a X; Y não enxerga nada
    body_x = client.get("/api/activities", params={"activity_type": "all"}).json()
    assert body_x["total"] == 12  # backfill do FakeGateway

    client.cookies.set("ritmo_session", other_token)
    body_y = client.get("/api/activities", params={"activity_type": "all"}).json()
    assert body_y["total"] == 0
    assert client.get("/api/sync/jobs/latest").json() == {"job": None}


def test_sync_latest_job_isolated(session_client, monkeypatch) -> None:
    """USR-05/10: o polling de X devolve o job de X — o job de Y não vaza."""
    client, user_id = session_client
    monkeypatch.setattr(garmin_service, "GarminGateway", FakeGateway)
    with SessionLocal() as db:
        other, other_token = _seed_other_user(db)
        # job encerrado de Y (anterior ao sync de X)
        alien_job = garmin_service.create_job(db, other.id)
        alien_job.status = "error"
        alien_job.error = "alheio"
        db.commit()
        alien_job_id = alien_job.id

    assert client.post("/api/sync").status_code == 201

    latest_x = client.get("/api/sync/jobs/latest").json()["job"]
    assert latest_x["id"] != alien_job_id
    with SessionLocal() as db:
        own = db.get(SyncJob, latest_x["id"])
        assert own.user_id == user_id
    # GET direto do job alheio -> 404
    assert client.get(f"/api/sync/jobs/{alien_job_id}").status_code == 404


def test_evaluation_scoped_to_session_user(session_client, monkeypatch) -> None:
    """USR-15/16/08: avaliação nasce com user_id de X; atividade de Y -> 404;
    a avaliação de X não aparece no detalhe visto por Y."""
    client, user_id = session_client
    _mock_nim_ok(monkeypatch)
    with SessionLocal() as db:
        other, other_token = _seed_other_user(db)
        own = _seed_run(db, user_id, "iso-x2")
        alien = _seed_run(db, other.id, "iso-y2")
        db.commit()
        own_id, alien_id = own.id, alien.id

    # avalia a própria corrida: 201 + linha com user_id de X
    response = client.post(
        f"/api/activities/{own_id}/evaluate", json={"intent_type": "facil"}
    )
    assert response.status_code == 201
    evaluation_id = response.json()["id"]
    with SessionLocal() as db:
        row = db.get(Evaluation, evaluation_id)
        assert row.user_id == user_id  # USR-15

    # atividade de Y -> 404, sem linha nova
    alien_response = client.post(
        f"/api/activities/{alien_id}/evaluate", json={"intent_type": "facil"}
    )
    assert alien_response.status_code == 404
    with SessionLocal() as db:
        assert len(db.execute(select(Evaluation)).scalars().all()) == 1

    # Y abre o detalhe da própria corrida: a avaliação de X não vaza
    client.cookies.set("ritmo_session", other_token)
    detail_y = client.get(f"/api/activities/{alien_id}").json()
    assert detail_y["evaluations"] == []
    # e o polling da avaliação de X -> 404 para Y
    polling = client.get(f"/api/activities/{own_id}/evaluate/{evaluation_id}")
    assert polling.status_code == 404


# ---------------------------------------------------------------
# Fronteira: sem sessão, 401 em todo endpoint de dado (USR-07/17)
# ---------------------------------------------------------------


def test_data_endpoints_401_without_session(session_client) -> None:
    """USR-07/17: sem cookie -> 401 JSON em todos os endpoints de dado."""
    client, _user_id = session_client
    client.cookies.delete("ritmo_session")

    for path in (
        "/api/activities",
        "/api/activities/1",
        "/api/health/summary",
        "/api/potential",
        "/api/sync/jobs/latest",
        "/api/sync/jobs/1",
    ):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.json() == {"detail": "não autenticado"}
    sync = client.post("/api/sync")
    assert sync.status_code == 401
    evaluate = client.post("/api/activities/1/evaluate", json={"intent_type": "facil"})
    assert evaluate.status_code == 401
