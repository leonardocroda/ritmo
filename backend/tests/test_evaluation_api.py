"""API de avaliação — POST cria o job pending (EVAL-21, T16).

TestClient + Postgres real; NIM sempre mockada (nenhum teste chama a
API real). Na T16 o POST é transitório: cria o pending e responde 200
— o dispatch do worker, o 201 e o GET de status entram na T17.
Validações síncronas (404/422×3/503/500) continuam HTTP e nada criam;
falhas da NIM/veredito são do worker (linhas error, testadas no
service). `get_settings` do router é fixado por teste porque o
`lru_cache` da app atravessa testes.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Evaluation, Split
from app.evaluation import nim
from app.main import app
from app.vdot.zones import ZoneConfigError


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("LTHR_BPM", "VDOT_ZONES_PATH", "NVIDIA_API_KEY", "NVIDIA_MODEL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _fixed_settings(monkeypatch):
    """Router sempre com key de teste — o lru_cache da app não vaza entre testes."""
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key="test-key"),
    )


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _seed_run(db, *, activity_type: str = "running") -> Activity:
    activity = Activity(
        garmin_id=f"api-{activity_type}-{datetime.now().timestamp()}",
        start_time=datetime(2024, 1, 15, 7, 0, 0),
        activity_type=activity_type,
        name="Easy Run" if activity_type == "running" else "Ioga",
        distance_m=5000.0 if activity_type == "running" else 0.0,
        duration_s=1420.0 if activity_type == "running" else 1800.0,
        avg_hr=145 if activity_type == "running" else 61,
    )
    db.add(activity)
    db.flush()
    if activity_type == "running":
        for idx in range(1, 6):
            duration = 300.0 if idx <= 4 else 220.0
            db.add(
                Split(
                    activity_id=activity.id,
                    idx=idx,
                    dist_m=1000.0,
                    duration_s=duration,
                    pace_s=duration,
                )
            )
    db.commit()
    return activity


def _mock_nim(monkeypatch, calls: list | None = None):
    """NIM dublê que conta chamadas — o POST da T16 não pode chamar."""

    def fake(system: str, user: str, settings, transport=None):
        if calls is not None:
            calls.append(system)
        raise AssertionError("NIM não deve ser chamada no request path")

    monkeypatch.setattr(nim, "chat_completion", fake)


def test_post_cria_pending_sem_chamar_nim(db, client, monkeypatch) -> None:
    """EVAL-21: POST cria pending com payload, responde o registro e
    NUNCA chama a NIM no request path (pino por count)."""
    activity = _seed_run(db)
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{activity.id}/evaluate",
        json={"intent_type": "facil", "intent_text": "era pra ser 30min a 4:15"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["activity_id"] == activity.id
    assert body["status"] == "pending"
    assert body["verdict"] == ""
    assert body["verdict_json"] is None
    assert body["model"] == "z-ai/glm-5.3"
    assert body["intent_text"] == "era pra ser 30min a 4:15"
    assert calls == []

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "pending"
    assert row.payload_json["intencao"]["tipo"] == "facil"
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is False


def test_404_atividade_inexistente(client, monkeypatch) -> None:
    """EVAL-09: id inexistente → 404 com mensagem clara."""
    _mock_nim(monkeypatch)
    response = client.post(
        "/api/activities/999/evaluate", json={"intent_type": "facil"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"


def test_422_atividade_nao_corrida(db, client, monkeypatch) -> None:
    """EVAL-10: yoga → 422, sem NIM e sem linha criada."""
    yoga = _seed_run(db, activity_type="yoga")
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{yoga.id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 422
    assert "corridas" in response.json()["detail"]
    assert calls == []
    db.expire_all()
    assert db.execute(select(Evaluation)).scalars().all() == []


def test_422_intent_type_fora_dos_sete(client) -> None:
    """EVAL-11: pydantic rejeita tipo fora do enum antes do handler."""
    response = client.post(
        "/api/activities/1/evaluate", json={"intent_type": "fácil"}
    )
    assert response.status_code == 422


def test_422_intent_text_acima_de_500(client) -> None:
    """EVAL-11: texto livre com 501 caracteres → 422."""
    response = client.post(
        "/api/activities/1/evaluate",
        json={"intent_type": "facil", "intent_text": "a" * 501},
    )
    assert response.status_code == 422


def test_503_sem_api_key(db, client, monkeypatch) -> None:
    """EVAL-12: key vazia → 503, sem NIM e nada criado."""
    activity = _seed_run(db)
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key=""),
    )

    response = client.post(
        f"/api/activities/{activity.id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 503
    assert "NVIDIA_API_KEY" in response.json()["detail"]
    assert calls == []
    db.expire_all()
    assert db.execute(select(Evaluation)).scalars().all() == []


def test_503_precede_404_com_key_vazia(client, monkeypatch) -> None:
    """Precedência da assumption do spec: key ausente responde 503 ANTES
    da consulta — erro de configuração não depende do dado."""
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key=""),
    )
    response = client.post("/api/activities/999/evaluate", json={"intent_type": "facil"})
    assert response.status_code == 503
    assert "NVIDIA_API_KEY" in response.json()["detail"]


def test_500_zonas_nao_configuradas(client, monkeypatch) -> None:
    """EVAL-15: arquivo de zonas inválido → 500 (mesma mensagem do activities)."""
    from app.activities import router as activities_router

    def raise_missing(path):
        raise ZoneConfigError(f"não foi possível carregar {path}")

    monkeypatch.setattr(activities_router, "load_zone_config", raise_missing)
    response = client.post("/api/activities/1/evaluate", json={"intent_type": "facil"})
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"
