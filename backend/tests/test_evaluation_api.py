"""API de avaliação como job — 201 pending + worker + GET de status (EVAL-21..25).

TestClient + Postgres real; NIM sempre mockada (nenhum teste chama a
API real). O TestClient executa o BackgroundTask dentro do ciclo do
request: a RESPOSTA é o pending (capturada antes do worker) e, quando
`post()` retorna, a linha já foi concluída pelo worker — os dois
estados são afirmados na mesma chamada. Falha da NIM vira linha
`error` com o motivo (não existe mais 502/504 HTTP para NIM — EVAL-23).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Evaluation, Split
from app.evaluation import service
from app.evaluation.nim import NimError
from app.main import app
from app.vdot.zones import ZoneConfigError, load_zone_config

VERDICT = {
    "veredito": "on_target",
    "headline": "Rodagem fácil bem controlada",
    "execucao_vs_intencao": {"pct_zona_alvo": 84.5, "principais_desvios": []},
    "o_que_funcionou": ["pacing estável"],
    "corrigir_prox_vez": [],
    "contexto_relevante": [],
    "confianca": "alta",
}


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


def _mock_nim(monkeypatch, *, verdict: dict | None = VERDICT,
              error: Exception | None = None, calls: list | None = None):
    """NIM dublê: devolve veredito/usage, ou levanta; `calls` conta chamadas."""

    def fake(system: str, user: str, settings, transport=None):
        if calls is not None:
            calls.append(system)
        if error is not None:
            raise error
        return verdict, {"prompt_tokens": 1234, "completion_tokens": 56}

    monkeypatch.setattr("app.evaluation.nim.chat_completion", fake)


def test_post_201_pending_e_worker_conclui(db, client, monkeypatch) -> None:
    """EVAL-21/22: a resposta é o pending (201); ao fim do request o
    worker já concluiu — linha done com veredito, tokens e evaluated."""
    activity = _seed_run(db)
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{activity.id}/evaluate",
        json={"intent_type": "facil", "intent_text": "era pra ser 30min a 4:15"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["verdict"] == ""
    assert body["verdict_json"] is None
    assert body["model"] == "z-ai/glm-5.3"
    assert body["intent_text"] == "era pra ser 30min a 4:15"

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "done"
    assert row.verdict == "on_target"
    assert row.tokens_in == 1234 and row.tokens_out == 56
    assert len(calls) == 1  # worker: exatamente uma chamada à NIM
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is True


def test_post_erro_nim_vira_linha_error(db, client, monkeypatch) -> None:
    """EVAL-23: NIM fora → 201 pending na resposta + linha error com o
    motivo ao fim do request — a tentativa nunca se perde (sem 502/504)."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, error=NimError("NIM HTTP 503"))

    response = client.post(
        f"/api/activities/{activity.id}/evaluate",
        json={"intent_type": "facil", "intent_text": "tento 1"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "NIM HTTP 503" in row.error
    assert row.intent_text == "tento 1"  # a tentativa sobrevive com o motivo
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is False


def test_get_status_do_polling(db, client, monkeypatch) -> None:
    """EVAL-25: GET leve por id — done com veredito; 404 para id de outro
    treino ou inexistente."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch)

    created = client.post(
        f"/api/activities/{activity.id}/evaluate", json={"intent_type": "facil"}
    ).json()

    status = client.get(
        f"/api/activities/{activity.id}/evaluate/{created['id']}"
    )
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    assert body["verdict"] == "on_target"
    assert body["verdict_json"]["headline"] == "Rodagem fácil bem controlada"

    assert (
        client.get(f"/api/activities/{activity.id}/evaluate/999").status_code == 404
    )
    assert (
        client.get(f"/api/activities/999/evaluate/{created['id']}").status_code == 404
    )


def test_lifespan_recupera_pending_orfa(db, monkeypatch) -> None:
    """EVAL-24: pending criada antes do startup vira error "interrompida"
    quando o lifespan do backend roda (padrão recover_stale_jobs)."""
    settings = Settings(_env_file=None)
    zone_config = load_zone_config(settings.vdot_zones_path)
    activity = _seed_run(db)
    _mock_nim(monkeypatch)
    created = service.create_evaluation(
        db, activity.id, "facil", None, zone_config, settings
    )
    assert created["status"] == "pending"

    with TestClient(app):  # lifespan roda recover_stale_evaluations()
        pass

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "interrompida" in row.error


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
