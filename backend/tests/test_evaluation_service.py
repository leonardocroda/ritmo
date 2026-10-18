"""Orquestração da avaliação como job — NIM mockada (EVAL-21..24).

Fluxo emendado (18/10): `create_evaluation` grava o pending (zero NIM no
request path — pino por count) e `run_evaluation` é o worker que conclui
a linha. A NIM é sempre um monkeypatch do módulo `nim` (nenhum teste
chama a API real). Falhas do worker PRESERVAM a tentativa: linha
``error`` com o motivo (decisão do usuário: perder a espera é o problema).
"""

from datetime import date, datetime
import json

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Evaluation, Split
from app.evaluation import nim, service
from app.evaluation.nim import NimError
from app.evaluation.prompt import PROMPT_VERSION, SYSTEM_PROMPT_V1
from app.vdot.zones import load_zone_config

EASY_PACE_S = 300.0
REPETITION_PACE_S = 220.0
START = datetime(2024, 1, 15, 7, 0, 0)

VERDICT = {
    "veredito": "on_target",
    "headline": "Rodagem fácil bem controlada",
    "execucao_vs_intencao": {"pct_zona_alvo": 92.0, "principais_desvios": []},
    "o_que_funcionou": ["pacing estável"],
    "corrigir_prox_vez": [],
    "contexto_relevante": [],
    "confianca": "alta",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("LTHR_BPM", "VDOT_ZONES_PATH", "NVIDIA_API_KEY", "NVIDIA_MODEL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture()
def zone_config(settings: Settings):
    return load_zone_config(settings.vdot_zones_path)


def _seed_run(db, *, activity_type: str = "running", laps: int = 5) -> Activity:
    is_run = activity_type in ("running", "trail_running")
    activity = Activity(
        garmin_id=f"svc-{activity_type}-{laps}-{datetime.now().timestamp()}",
        start_time=START,
        activity_type=activity_type,
        name="Easy Run" if is_run else "Ioga",
        distance_m=5000.0 if is_run else 0.0,
        duration_s=1420.0 if is_run else 1800.0,
        avg_hr=145 if is_run else 61,
    )
    db.add(activity)
    db.flush()
    if is_run:
        for idx in range(1, laps + 1):
            duration = 300.0 if idx <= laps - 1 else REPETITION_PACE_S
            db.add(
                Split(
                    activity_id=activity.id,
                    idx=idx,
                    dist_m=1000.0,
                    duration_s=duration,
                    pace_s=duration * 1000 / 1000.0,
                )
            )
    db.commit()
    return activity


def _mock_nim(monkeypatch, verdict: dict | None = VERDICT, usage: dict | None = None,
              error: Exception | None = None, capture: dict | None = None,
              calls: list | None = None):
    """Troca a chamada NIM por um duble; capture registra (system, user),
    calls conta cada chamada."""
    usage = usage or {"prompt_tokens": 1234, "completion_tokens": 56}

    def fake(system: str, user: str, settings, transport=None):
        if calls is not None:
            calls.append(system)
        if capture is not None:
            capture["system"] = system
            capture["user"] = user
        if error is not None:
            raise error
        return verdict, usage

    monkeypatch.setattr(nim, "chat_completion", fake)


def test_create_evaluation_pending_sem_chamar_nim(
    db, settings, zone_config, monkeypatch
) -> None:
    """EVAL-21: o request path cria pending com payload montado e NUNCA
    chama a NIM (pino por count); evaluated ainda false."""
    activity = _seed_run(db)
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    created = service.create_evaluation(
        db, activity.id, "facil", "era pra ser 30min a 4:15", zone_config, settings
    )

    assert created["status"] == "pending"
    assert created["verdict"] == ""
    assert created["verdict_json"] is None
    assert created["model"] == "z-ai/glm-5.3"
    assert created["prompt_version"] == PROMPT_VERSION == "v1"
    assert created["intent_text"] == "era pra ser 30min a 4:15"
    assert calls == []

    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "pending"
    assert row.payload_json["intencao"] == {
        "tipo": "facil",
        "texto": "era pra ser 30min a 4:15",
    }
    assert row.payload_json["zona_alvo"]["pct_zona_alvo"] == 84.5

    db.expire_all()
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is False


def test_worker_conclui_done_com_veredito_sanitizado(
    db, settings, zone_config, monkeypatch
) -> None:
    """EVAL-22: worker happy path → done com veredito, tokens, eco
    sanitizado com o número Python (AD-003) e evaluated=true."""
    activity = _seed_run(db)
    echo_errado = {
        **VERDICT,
        "execucao_vs_intencao": {"pct_zona_alvo": 61.0, "principais_desvios": []},
    }
    capture: dict = {}
    calls: list = []
    _mock_nim(monkeypatch, verdict=echo_errado, capture=capture, calls=calls)

    created = service.create_evaluation(db, activity.id, "facil", None, zone_config, settings)
    service.run_evaluation(created["id"])

    assert len(calls) == 1  # exatamente uma chamada à NIM
    assert capture["system"] == SYSTEM_PROMPT_V1  # prompt vigente é o que vai
    sent = json.loads(capture["user"])
    assert sent["intencao"]["tipo"] == "facil"

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "done"
    assert row.verdict == "on_target"
    assert row.tokens_in == 1234 and row.tokens_out == 56
    # 4 voltas easy de 300s + 1 repetition de 220s → 84,5% (Python, não o eco)
    assert row.verdict_json["execucao_vs_intencao"]["pct_zona_alvo"] == 84.5
    assert row.verdict_json["headline"] == "Rodagem fácil bem controlada"
    assert row.error is None

    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is True


def test_worker_progressivo_pct_nulo(db, settings, zone_config, monkeypatch) -> None:
    """Progressivo sem zona alvo → pct null mesmo que o LLM ecoe número."""
    activity = _seed_run(db)
    echo_errado = {
        **VERDICT,
        "execucao_vs_intencao": {"pct_zona_alvo": 61.0, "principais_desvios": []},
    }
    _mock_nim(monkeypatch, verdict=echo_errado)

    created = service.create_evaluation(db, activity.id, "progressivo", None, zone_config, settings)
    service.run_evaluation(created["id"])

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.verdict_json["execucao_vs_intencao"]["pct_zona_alvo"] is None


def test_worker_erro_nim_preserva_a_tentativa(
    db, settings, zone_config, monkeypatch
) -> None:
    """EVAL-23: NIM fora → linha error com o motivo (nada se perde);
    worker não levanta; evaluated segue false."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, error=NimError("NIM HTTP 503"))

    created = service.create_evaluation(db, activity.id, "facil", "tento 1", zone_config, settings)
    service.run_evaluation(created["id"])  # não levanta

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "NIM HTTP 503" in row.error
    assert row.verdict == ""
    assert row.intent_text == "tento 1"  # a tentativa sobrevive

    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is False


def test_worker_veredito_invalido_vira_error(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-23/14: veredito fora do schema → linha error com o motivo —
    veredito nunca é inventado."""
    activity = _seed_run(db)
    invalido = {k: v for k, v in VERDICT.items() if k != "headline"}
    _mock_nim(monkeypatch, verdict=invalido)

    created = service.create_evaluation(db, activity.id, "facil", None, zone_config, settings)
    service.run_evaluation(created["id"])

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "fora do schema" in row.error
    assert row.verdict == ""


def test_worker_excecao_inesperada_vira_error(db, settings, zone_config, monkeypatch) -> None:
    """Guarda do worker: exceção inesperada também vira linha error —
    nada derruba o processo nem deixa a linha presa em pending."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, error=RuntimeError("boom inesperado"))

    created = service.create_evaluation(db, activity.id, "facil", None, zone_config, settings)
    service.run_evaluation(created["id"])  # não levanta

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "erro inesperado" in row.error


def test_worker_linha_nao_pending_e_noop(db, settings, zone_config, monkeypatch) -> None:
    """Re-run do worker em linha done é no-op: sem segunda chamada à NIM."""
    activity = _seed_run(db)
    calls: list = []
    _mock_nim(monkeypatch, calls=calls)

    created = service.create_evaluation(db, activity.id, "facil", None, zone_config, settings)
    service.run_evaluation(created["id"])
    service.run_evaluation(created["id"])  # no-op

    assert len(calls) == 1
    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "done"


def test_recover_stale_pending_vira_interrompida(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-24: restart com pending órfã → error "interrompida"
    (padrão recover_stale_jobs do sync)."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch)

    created = service.create_evaluation(db, activity.id, "facil", None, zone_config, settings)
    service.recover_stale_evaluations()

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "error"
    assert "interrompida" in row.error


def test_create_inexistente_retorna_none(db, settings, zone_config) -> None:
    """EVAL-09: id inexistente → None (404 no router)."""
    assert service.create_evaluation(db, 999, "facil", None, zone_config, settings) is None


def test_create_nao_corrida_sem_chamar_nim(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-10: yoga → ActivityNotRunning e zero chamadas à NIM."""
    yoga = _seed_run(db, activity_type="yoga", laps=0)
    calls: list = []

    def fail_if_called(system, user, settings_, transport=None):
        calls.append(1)
        raise AssertionError("NIM não deve ser chamada para não-corrida")

    monkeypatch.setattr(nim, "chat_completion", fail_if_called)

    with pytest.raises(service.ActivityNotRunning):
        service.create_evaluation(db, yoga.id, "facil", None, zone_config, settings)
    assert calls == []


def test_create_trail_running_aceito(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-10: trail_running É corrida — pending criado e worker conclui."""
    trail = _seed_run(db, activity_type="trail_running")
    _mock_nim(monkeypatch)

    created = service.create_evaluation(db, trail.id, "facil", None, zone_config, settings)
    service.run_evaluation(created["id"])

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "done"
    assert row.activity_id == trail.id
    fresh = db.execute(select(Activity).where(Activity.id == trail.id)).scalar_one()
    assert fresh.evaluated is True


def test_worker_usage_zeros_persiste_tokens_zero(
    db, settings, zone_config, monkeypatch
) -> None:
    """Edge do spec: usage sem tokens → avaliação done com tokens 0."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, usage={"prompt_tokens": 0, "completion_tokens": 0})

    created = service.create_evaluation(db, activity.id, "facil", None, zone_config, settings)
    service.run_evaluation(created["id"])

    db.expire_all()
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.status == "done"
    assert row.tokens_in == 0 and row.tokens_out == 0


def test_list_evaluations_ordenado_e_com_status(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-17/18/19: mais recente primeiro, append-only, status no contrato."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch)

    first = service.create_evaluation(db, activity.id, "facil", "primeira", zone_config, settings)
    service.run_evaluation(first["id"])
    second = service.create_evaluation(db, activity.id, "facil", "segunda", zone_config, settings)
    service.run_evaluation(second["id"])

    evaluations = service.list_evaluations(db, activity.id)
    assert [e["id"] for e in evaluations] == [second["id"], first["id"]]
    assert evaluations[0]["intent_text"] == "segunda"
    assert evaluations[0]["status"] == "done"
    assert evaluations[0]["verdict"] == "on_target"
    assert len(db.execute(select(Evaluation)).scalars().all()) == 2  # nunca sobrescreve


def test_list_evaluations_vazio_sem_avaliacoes(db, settings) -> None:
    """EVAL-17: sem avaliações → lista vazia (estado vazio, não erro)."""
    activity = _seed_run(db)
    assert service.list_evaluations(db, activity.id) == []
