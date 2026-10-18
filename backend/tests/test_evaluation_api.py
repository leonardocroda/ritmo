"""API de avaliação — POST /api/activities/{id}/evaluate (EVAL-09..15).

TestClient + Postgres real; NIM sempre mockada (monkeypatch do módulo
`nim` — nenhum teste chama a API real). Falhas não gravam nada: cada
teste de erro confere no banco 0 linhas de `Evaluation` e `evaluated`
inalterado (Decisão E). `get_settings` do router é fixado por teste
porque o `lru_cache` da app atravessa testes.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Evaluation, Split
from app.evaluation import nim
from app.evaluation.nim import NimError, NimTimeout
from app.main import app
from app.vdot.zones import ZoneConfigError

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


def _mock_nim(monkeypatch, verdict: dict | None = VERDICT,
              error: Exception | None = None, calls: list | None = None):
    def fake(system: str, user: str, settings, transport=None):
        if calls is not None:
            calls.append(system)
        if error is not None:
            raise error
        return verdict, {"prompt_tokens": 1234, "completion_tokens": 56}

    monkeypatch.setattr(nim, "chat_completion", fake)


def _nothing_saved(db, activity_id: int) -> None:
    """Decisão E: falha não deixa linha nem muda evaluated (query fresca)."""
    db.expire_all()
    assert db.execute(select(Evaluation)).scalars().all() == []
    fresh = db.execute(select(Activity).where(Activity.id == activity_id)).scalar_one()
    assert fresh.evaluated is False


def test_200_happy_path_devolve_avaliacao(db, client, monkeypatch) -> None:
    """EVAL-04: 200 com EvaluationOut completo; linha gravada e evaluated true."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch)

    response = client.post(
        f"/api/activities/{activity.id}/evaluate",
        json={"intent_type": "facil", "intent_text": "era pra ser 30min a 4:15"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["activity_id"] == activity.id
    assert body["verdict"] == "on_target"
    assert body["model"] == "z-ai/glm-5.3"
    assert body["prompt_version"] == "v1"
    assert body["tokens_in"] == 1234
    assert body["tokens_out"] == 56
    assert body["verdict_json"]["headline"] == "Rodagem fácil bem controlada"
    assert body["verdict_json"]["execucao_vs_intencao"]["pct_zona_alvo"] == 84.5
    assert body["created_at"] is not None

    db.expire_all()
    assert len(db.execute(select(Evaluation)).scalars().all()) == 1
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is True


def test_404_atividade_inexistente(client, monkeypatch) -> None:
    """EVAL-09: id inexistente → 404 com mensagem clara."""
    _mock_nim(monkeypatch)
    response = client.post(
        "/api/activities/999/evaluate", json={"intent_type": "facil"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"


def test_422_atividade_nao_corrida(db, client, monkeypatch) -> None:
    """EVAL-10: yoga → 422, sem chamar a NIM."""
    yoga = _seed_run(db, activity_type="yoga")
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    response = client.post(
        f"/api/activities/{yoga.id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 422
    assert "corridas" in response.json()["detail"]
    assert calls == []
    _nothing_saved(db, yoga.id)


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
    """EVAL-12: key vazia → 503, sem chamada à NIM e nada gravado."""
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
    _nothing_saved(db, activity.id)


def test_502_nim_error(db, client, monkeypatch) -> None:
    """EVAL-13: NIM com HTTP != 200 → 502, nada gravado."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, error=NimError("NIM HTTP 503"))

    response = client.post(
        f"/api/activities/{activity.id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 502
    assert "Falha na IA" in response.json()["detail"]
    _nothing_saved(db, activity.id)


def test_502_veredito_fora_do_schema(db, client, monkeypatch) -> None:
    """EVAL-14: JSON fora do contrato → 502, veredito nunca inventado."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, verdict={"veredito": "excellent"})

    response = client.post(
        f"/api/activities/{activity.id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 502
    assert "fora do contrato" in response.json()["detail"]
    _nothing_saved(db, activity.id)


def test_504_timeout_da_nim(db, client, monkeypatch) -> None:
    """EVAL-13: NIM não responde → 504, nada gravado."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, error=NimTimeout("read timed out"))

    response = client.post(
        f"/api/activities/{activity.id}/evaluate", json={"intent_type": "facil"}
    )

    assert response.status_code == 504
    assert "demorou demais" in response.json()["detail"]
    _nothing_saved(db, activity.id)


def test_500_zonas_nao_configuradas(client, monkeypatch) -> None:
    """EVAL-15: arquivo de zonas inválido → 500 (mesma mensagem do activities)."""
    from app.activities import router as activities_router

    def raise_missing(path):
        raise ZoneConfigError(f"não foi possível carregar {path}")

    monkeypatch.setattr(activities_router, "load_zone_config", raise_missing)
    response = client.post("/api/activities/1/evaluate", json={"intent_type": "facil"})
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"


def test_503_precede_404_com_key_vazia(client, monkeypatch) -> None:
    """Fix 6 do Verifier (spec-precision): key ausente responde 503 ANTES
    da consulta — erro de configuração não depende do dado. Pin da
    precedência escolhida (assumption do spec)."""
    monkeypatch.setattr(
        "app.evaluation.router.get_settings",
        lambda: Settings(_env_file=None, nvidia_api_key=""),
    )
    response = client.post("/api/activities/999/evaluate", json={"intent_type": "facil"})
    assert response.status_code == 503
    assert "NVIDIA_API_KEY" in response.json()["detail"]
