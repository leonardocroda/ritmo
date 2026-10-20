"""API de avaliação como job — 201 pending + worker + GET de status (EVAL-21..25).

User-scope (T6, USR-15/16/12): a avaliação nasce com o ``user_id`` do
usuário da sessão (``session_client`` — sessão real, sem o override do
conftest); atividade/avaliação de outro usuário → 404.

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

from app.auth.security import hash_password
from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Evaluation, Split, User
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


def _seed_run(db, *, user_id: int, activity_type: str = "running") -> Activity:
    activity = Activity(
        user_id=user_id,
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


def test_post_201_pending_e_worker_conclui(session_client, monkeypatch) -> None:
    """EVAL-21/22: a resposta é o pending (201); ao fim do request o
    worker já concluiu — linha done com veredito, tokens e evaluated."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_run(db, user_id=user_id)
        activity_id = activity.id
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{activity_id}/evaluate",
        json={"intent_type": "facil", "intent_text": "era pra ser 30min a 4:15"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["verdict"] == ""
    assert body["verdict_json"] is None
    assert body["model"] == "z-ai/glm-5.3"
    assert body["intent_text"] == "era pra ser 30min a 4:15"

    with SessionLocal() as db:
        row = db.execute(select(Evaluation)).scalar_one()
        assert row.status == "done"
        assert row.verdict == "on_target"
        assert row.tokens_in == 1234 and row.tokens_out == 56
        assert row.user_id == user_id  # USR-15: linha do dono da sessão
    assert len(calls) == 1  # worker: exatamente uma chamada à NIM
    with SessionLocal() as db:
        fresh = db.execute(
            select(Activity).where(Activity.id == activity_id)
        ).scalar_one()
        assert fresh.evaluated is True


def test_post_erro_nim_vira_linha_error(session_client, monkeypatch) -> None:
    """EVAL-23: NIM fora → 201 pending na resposta + linha error com o
    motivo ao fim do request — a tentativa nunca se perde (sem 502/504)."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_run(db, user_id=user_id)
        activity_id = activity.id
    _mock_nim(monkeypatch, error=NimError("NIM HTTP 503"))

    response = client.post(
        f"/api/activities/{activity_id}/evaluate",
        json={"intent_type": "facil", "intent_text": "tento 1"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    with SessionLocal() as db:
        row = db.execute(select(Evaluation)).scalar_one()
        assert row.status == "error"
        assert "NIM HTTP 503" in row.error
        assert row.intent_text == "tento 1"  # a tentativa sobrevive com o motivo
        fresh = db.execute(
            select(Activity).where(Activity.id == activity_id)
        ).scalar_one()
        assert fresh.evaluated is False


def test_get_status_do_polling(session_client, monkeypatch) -> None:
    """EVAL-25: GET leve por id — done com veredito; 404 para id de outro
    treino ou inexistente."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_run(db, user_id=user_id)
        activity_id = activity.id
    _mock_nim(monkeypatch)

    created = client.post(
        f"/api/activities/{activity_id}/evaluate", json={"intent_type": "facil"}
    ).json()

    status = client.get(
        f"/api/activities/{activity_id}/evaluate/{created['id']}"
    )
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    assert body["verdict"] == "on_target"
    assert body["verdict_json"]["headline"] == "Rodagem fácil bem controlada"

    assert (
        client.get(f"/api/activities/{activity_id}/evaluate/999").status_code == 404
    )
    assert (
        client.get(f"/api/activities/999/evaluate/{created['id']}").status_code == 404
    )


# ---------------------------------------------------------------
# T6 (user-scope) — avaliação isolada por usuário da sessão
# ---------------------------------------------------------------


def test_post_404_atividade_de_outro_usuario(session_client, monkeypatch) -> None:
    """USR-16: atividade de outro usuário → 404, sem NIM e sem linha criada."""
    client, _user_id = session_client
    with SessionLocal() as db:
        other = User(display_name="Outra", email="outro@example.com",
                     password_hash=hash_password("senha-segura-123"))
        db.add(other)
        db.flush()
        other_run = _seed_run(db, user_id=other.id)
        db.commit()
        other_activity_id = other_run.id
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{other_activity_id}/evaluate",
        json={"intent_type": "facil"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"
    assert calls == []
    with SessionLocal() as db:
        assert db.execute(select(Evaluation)).scalars().all() == []


def test_get_status_404_avaliacao_de_outro_usuario(session_client) -> None:
    """USR-12: GET de status de avaliação de outro usuário → 404 (o
    polling alheio nunca enxerga nem a existência)."""
    client, _user_id = session_client
    with SessionLocal() as db:
        other = User(display_name="Outra", email="outro@example.com",
                     password_hash=hash_password("senha-segura-123"))
        db.add(other)
        db.flush()
        other_run = _seed_run(db, user_id=other.id)
        db.flush()
        other_eval = Evaluation(
            user_id=other.id,
            activity_id=other_run.id,
            intent_type="facil",
            model="z-ai/glm-5.3",
            prompt_version="v1",
            verdict="",
            status="pending",
        )
        db.add(other_eval)
        db.commit()
        other_eval_id = other_eval.id
        other_activity_id = other_run.id

    response = client.get(
        f"/api/activities/{other_activity_id}/evaluate/{other_eval_id}"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "avaliação não encontrada"


# ---------------------------------------------------------------
# Worker, recovery e superfície de erro (EVAL-21..25)
# ---------------------------------------------------------------


def test_lifespan_recupera_pending_orfa(db, monkeypatch) -> None:
    """EVAL-24: pending criada antes do startup vira error "interrompida"
    quando o lifespan do backend roda (padrão recover_stale_jobs)."""
    settings = Settings(_env_file=None)
    zone_config = load_zone_config(settings.vdot_zones_path)
    user = User(display_name="Corredora")
    db.add(user)
    db.flush()
    activity = _seed_run(db, user_id=user.id)
    _mock_nim(monkeypatch)
    created = service.create_evaluation(
        db, activity.id, user.id, "facil", None, zone_config, settings
    )
    assert created["status"] == "pending"

    with TestClient(app):  # lifespan roda recover_stale_evaluations()
        pass

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "interrompida" in row.error


def test_404_atividade_inexistente(session_client, monkeypatch) -> None:
    """EVAL-09: id inexistente → 404 com mensagem clara."""
    client, _user_id = session_client
    _mock_nim(monkeypatch)
    response = client.post(
        "/api/activities/999/evaluate", json={"intent_type": "facil"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"


def test_422_atividade_nao_corrida(session_client, monkeypatch) -> None:
    """EVAL-10: yoga → 422, sem NIM e sem linha criada."""
    client, user_id = session_client
    with SessionLocal() as db:
        yoga = _seed_run(db, user_id=user_id, activity_type="yoga")
        yoga_id = yoga.id
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{yoga_id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 422
    assert "corridas" in response.json()["detail"]
    assert calls == []
    with SessionLocal() as db:
        assert db.execute(select(Evaluation)).scalars().all() == []


def test_422_intent_type_fora_dos_sete(session_client) -> None:
    """EVAL-11: pydantic rejeita tipo fora do enum antes do handler."""
    client, _user_id = session_client
    response = client.post(
        "/api/activities/1/evaluate", json={"intent_type": "fácil"}
    )
    assert response.status_code == 422


def test_422_intent_text_acima_de_500(session_client) -> None:
    """EVAL-11: texto livre com 501 caracteres → 422."""
    client, _user_id = session_client
    response = client.post(
        "/api/activities/1/evaluate",
        json={"intent_type": "facil", "intent_text": "a" * 501},
    )
    assert response.status_code == 422


def test_503_sem_api_key(session_client, monkeypatch) -> None:
    """EVAL-12: key vazia → 503, sem NIM e nada criado."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_run(db, user_id=user_id)
        activity_id = activity.id
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key=""),
    )

    response = client.post(
        f"/api/activities/{activity_id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 503
    assert "NVIDIA_API_KEY" in response.json()["detail"]
    assert calls == []
    with SessionLocal() as db:
        assert db.execute(select(Evaluation)).scalars().all() == []


def test_503_precede_404_com_key_vazia(session_client, monkeypatch) -> None:
    """Precedência da assumption do spec: key ausente responde 503 ANTES
    da consulta — erro de configuração não depende do dado."""
    client, _user_id = session_client
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key=""),
    )
    response = client.post("/api/activities/999/evaluate", json={"intent_type": "facil"})
    assert response.status_code == 503
    assert "NVIDIA_API_KEY" in response.json()["detail"]


def test_500_zonas_nao_configuradas(session_client, monkeypatch) -> None:
    """EVAL-15: arquivo de zonas inválido → 500 (mesma mensagem do activities)."""
    client, _user_id = session_client
    from app.activities import router as activities_router

    def raise_missing(path):
        raise ZoneConfigError(f"não foi possível carregar {path}")

    monkeypatch.setattr(activities_router, "load_zone_config", raise_missing)
    response = client.post("/api/activities/1/evaluate", json={"intent_type": "facil"})
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"
