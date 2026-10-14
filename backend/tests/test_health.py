"""Smoke tests da Fase 0: API sobe, schema é criado, usuário default existe."""

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.engine import SessionLocal
from app.db.models import DEFAULT_USER_ID, User
from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Ritmo"


def test_schema_created() -> None:
    """O lifespan cria todas as tabelas do plano (seção 5)."""
    with TestClient(app):
        table_names = set(inspect(SessionLocal().bind).get_table_names())

    expected = {
        "users",
        "activities",
        "splits",
        "sleep",
        "hrv",
        "rhr",
        "body_battery",
        "stress",
        "load",
        "vdot_tests",
        "zones",
        "evaluations",
        "races",
        "patterns",
        "sync_jobs",
        "personal_records",
        "sync_state",
    }
    assert expected <= table_names, f"Faltando: {expected - table_names}"


def test_default_user_seeded() -> None:
    """Usuário único default (Fase 1: user_id em toda query)."""
    with TestClient(app):
        with SessionLocal() as db:
            user = db.execute(select(User).where(User.id == DEFAULT_USER_ID)).scalar_one_or_none()
            assert user is not None
            assert user.display_name == "Leonardo"
