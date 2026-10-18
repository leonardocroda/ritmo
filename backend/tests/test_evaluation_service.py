"""Orquestração e persistência da avaliação — NIM mockada (EVAL-04/06/19).

A NIM é sempre um monkeypatch do módulo `nim` (nenhum teste chama a API
real). Falhas não gravam NADA (Decisão E): cada teste de falha faz o
rollback que o `get_db` do FastAPI faria ao fechar a sessão e confere o
banco por query fresca — nem linha, nem `evaluated` alterado.
"""

from datetime import date, datetime

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
DAY = date(2024, 1, 15)
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


def _seed_yoga(db) -> Activity:
    return _seed_run(db, activity_type="yoga", laps=0)


def _mock_nim(monkeypatch, verdict: dict | None = VERDICT, usage: dict | None = None,
              error: Exception | None = None, capture: dict | None = None,
              calls: list | None = None):
    """Troca a chamada NIM por um duble; capture registra (system, user),
    calls conta cada chamada (Fix 3 do Verifier: pin da chamada única)."""
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


def test_happy_path_persiste_todos_campos(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-04/06: avalia, persiste TUDO (model, prompt_version, tokens,
    payload, veredito) e marca evaluated — o retorno espelha a linha."""
    activity = _seed_run(db)
    capture: dict = {}
    calls: list = []
    _mock_nim(monkeypatch, capture=capture, calls=calls)

    result = service.evaluate(db, activity.id, "facil", "era pra ser 30min a 4:15",
                              zone_config, settings)

    # EVAL-03: exatamente UMA chamada à NIM por avaliação (Fix 3 —
    # duplicar a chamada no service falha aqui)
    assert len(calls) == 1

    assert result["model"] == "z-ai/glm-5.3"
    assert result["prompt_version"] == PROMPT_VERSION == "v1"
    assert result["verdict"] == "on_target"
    assert result["tokens_in"] == 1234
    assert result["tokens_out"] == 56
    assert result["activity_id"] == activity.id
    assert result["verdict_json"]["headline"] == "Rodagem fácil bem controlada"

    row = db.execute(select(Evaluation)).scalar_one()
    assert row.payload_json["intencao"] == {"tipo": "facil", "texto": "era pra ser 30min a 4:15"}
    assert row.payload_json["zona_alvo"]["pct_zona_alvo"] == 84.5
    assert row.model == "z-ai/glm-5.3"
    assert row.prompt_version == "v1"
    assert row.tokens_in == 1234 and row.tokens_out == 56

    db.expire_all()
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is True

    # O prompt vigente e o payload determinístico são o que vai à NIM (AD-003)
    import json

    assert capture["system"] == SYSTEM_PROMPT_V1
    sent = json.loads(capture["user"])
    assert sent["intencao"]["texto"] == "era pra ser 30min a 4:15"
    assert sent["zona_alvo"]["pct_zona_alvo"] == 84.5


def test_sanitiza_eco_pct_zona_alvo(db, settings, zone_config, monkeypatch) -> None:
    """AD-03 sem brecha: o pct gravado é o do Python, nunca o eco do LLM."""
    activity = _seed_run(db)
    echo_errado = {
        **VERDICT,
        "execucao_vs_intencao": {"pct_zona_alvo": 61.0, "principais_desvios": []},
    }
    _mock_nim(monkeypatch, verdict=echo_errado)

    result = service.evaluate(db, activity.id, "facil", None, zone_config, settings)
    # 4 voltas easy de 300s + 1 repetition de 220s → 84,5% (cálculo Python)
    assert result["verdict_json"]["execucao_vs_intencao"]["pct_zona_alvo"] == 84.5

    # Progressivo: sem zona alvo → null, mesmo que o LLM ecoe número
    _mock_nim(monkeypatch, verdict=echo_errado)
    result_progressivo = service.evaluate(
        db, activity.id, "progressivo", None, zone_config, settings
    )
    assert result_progressivo["verdict_json"]["execucao_vs_intencao"]["pct_zona_alvo"] is None


def test_reavaliacao_adiciona_linha_nova(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-19: re-avaliar cria linha nova; a primeira fica intacta;
    list_evaluations ordena mais recente primeiro (EVAL-17/18)."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch)

    first = service.evaluate(db, activity.id, "facil", "primeira", zone_config, settings)
    second = service.evaluate(db, activity.id, "facil", "segunda", zone_config, settings)

    rows = db.execute(select(Evaluation).order_by(Evaluation.id)).scalars().all()
    assert len(rows) == 2
    assert rows[0].intent_text == "primeira"  # nada sobrescrito
    assert rows[1].intent_text == "segunda"

    evaluations = service.list_evaluations(db, activity.id)
    assert [e["id"] for e in evaluations] == [second["id"], first["id"]]
    assert evaluations[0]["intent_text"] == "segunda"


def test_falha_nim_nada_gravado(db, settings, zone_config, monkeypatch) -> None:
    """Decisão E: NimError → nenhuma linha, evaluated inalterado."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, error=NimError("NIM HTTP 503"))

    with pytest.raises(NimError):
        service.evaluate(db, activity.id, "facil", None, zone_config, settings)

    db.rollback()  # o get_db do FastAPI fecha a sessão sem commit
    db.expire_all()
    assert db.execute(select(Evaluation)).scalars().all() == []
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is False


def test_veredito_invalido_nada_gravado(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-14: veredito fora do schema → ValueError, nada gravado."""
    activity = _seed_run(db)
    invalido = {k: v for k, v in VERDICT.items() if k != "headline"}
    _mock_nim(monkeypatch, verdict=invalido)

    with pytest.raises(ValueError):
        service.evaluate(db, activity.id, "facil", None, zone_config, settings)

    db.rollback()
    db.expire_all()
    assert db.execute(select(Evaluation)).scalars().all() == []
    fresh = db.execute(select(Activity).where(Activity.id == activity.id)).scalar_one()
    assert fresh.evaluated is False


def test_activity_inexistente_retorna_none(db, settings, zone_config) -> None:
    """EVAL-09: id inexistente → None (404 no router)."""
    assert service.evaluate(db, 999, "facil", None, zone_config, settings) is None


def test_nao_corrida_rejeitada_sem_chamar_nim(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-10: yoga → ActivityNotRunning e zero chamadas à NIM."""
    yoga = _seed_yoga(db)
    calls: list = []

    def fail_if_called(system, user, settings_, transport=None):
        calls.append(1)
        raise AssertionError("NIM não deve ser chamada para não-corrida")

    monkeypatch.setattr(nim, "chat_completion", fail_if_called)

    with pytest.raises(service.ActivityNotRunning):
        service.evaluate(db, yoga.id, "facil", None, zone_config, settings)
    assert calls == []


def test_list_evaluations_vazio_sem_avaliacoes(db, settings) -> None:
    """EVAL-17: sem avaliações → lista vazia (estado vazio, não erro)."""
    activity = _seed_run(db)
    assert service.list_evaluations(db, activity.id) == []


def test_trail_running_aceita_avaliacao(db, settings, zone_config, monkeypatch) -> None:
    """EVAL-10 (Fix 4 do Verifier): trail_running É corrida — avalia
    normalmente; remover "trail_running" de RUNNING_TYPES falha aqui."""
    trail = _seed_run(db, activity_type="trail_running")
    _mock_nim(monkeypatch)

    result = service.evaluate(db, trail.id, "facil", None, zone_config, settings)

    assert result is not None
    assert result["activity_id"] == trail.id
    assert result["verdict"] == "on_target"
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.activity_id == trail.id
    db.expire_all()
    fresh = db.execute(select(Activity).where(Activity.id == trail.id)).scalar_one()
    assert fresh.evaluated is True


def test_usage_zeros_persiste_tokens_zero(db, settings, zone_config, monkeypatch) -> None:
    """Edge do spec (Fix 5 do Verifier): usage sem tokens → a avaliação
    persiste com tokens 0 (custo desconhecido, não avaliação perdida)."""
    activity = _seed_run(db)
    _mock_nim(monkeypatch, usage={"prompt_tokens": 0, "completion_tokens": 0})

    result = service.evaluate(db, activity.id, "facil", None, zone_config, settings)

    assert result["tokens_in"] == 0
    assert result["tokens_out"] == 0
    row = db.execute(select(Evaluation)).scalar_one()
    assert row.tokens_in == 0
    assert row.tokens_out == 0
