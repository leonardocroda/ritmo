"""Painel Potencial (T8/T9 + panel-clarity T10) — service direto + HTTP,
no Postgres real.

T8: chamadas diretas a `get_potential` com seeds (o domínio lê
exclusivamente o banco próprio — AD-002; nenhuma chamada Garmin).
T9: TestClient cobrindo a superfície HTTP (500/estados vazios).
T10 (panel-clarity): `pmc` e `days` saem do contrato (CLR-03/04) — os
asserts de PMC migraram 1:1 para test_health_api.py (T1/T2 da feature);
o espaço do param morto não herda validação nova.
Valores afirmados são literais derivados das fixtures com a forma
fechada de Daniels (T1) — nunca constantes compartilhadas com a
implementação (lições L-001/L-002).
"""

from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, DailyLoad, PersonalRecord, RacePrediction
from app.main import app
from app.potential import router as potential_router
from app.potential import service
from app.vdot.calibration import Calibration
from app.vdot.zones import ZoneConfigError

# Calibração vigente (campos reais do vdot_zones.json — design §Contrato)
CALIBRATION = Calibration(
    vdot=50.2,
    source="10K em 41:15",
    test_date=date(2026, 10, 3),
    distance_m=10012,
    time_s=2475,
)

# PRs canônicos reais (valores do banco — mesmos pins de test_potential_calc)
REAL_PRS = [
    ("FASTEST_10K", 2425.0, date(2024, 10, 5)),
    ("FASTEST_5K", 1163.8299560546875, date(2026, 4, 26)),
    ("FASTEST_HALF_MARATHON", 5409.188, date(2026, 5, 3)),
    ("FASTEST_MARATHON", 13925.76, date(2026, 7, 5)),
    ("FASTEST_1K", 180.0, date(2026, 2, 1)),  # não canônico (Out of Scope)
]

# Predições da sonda real de 15/10/2026 (design §Contrato)
REAL_GARMIN = [
    ("5K", 1165.0),
    ("10K", 2447.0),
    ("HALF_MARATHON", 5437.0),
    ("MARATHON", 11989.0),
]


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    """TestClient: o lifespan recria o schema do teste (conftest derruba antes)."""
    with TestClient(app) as test_client:
        yield test_client


def _seed_prs(db) -> None:
    for event, value, pr_date in REAL_PRS:
        db.add(PersonalRecord(event=event, value=value, pr_date=pr_date, raw_json={}))


def _seed_garmin_predictions(db, *, day: date = date(2026, 10, 15)) -> None:
    for event, time_s in REAL_GARMIN:
        db.add(RacePrediction(event=event, time_s=time_s, date=day, raw_json={}))


def _seed_load(db, day: date, ctl: float, atl: float, tsb: float,
               acwr: float | None = None) -> None:
    db.add(DailyLoad(date=day, ctl=ctl, atl=atl, tsb=tsb, acwr=acwr))


def _seed_activity(db, *, garmin_id: str, start: datetime, name: str = "Morning Run",
                   activity_type: str = "running", distance_m: float = 10000.0,
                   duration_s: float = 2500.0, raw_json: dict | None = None) -> None:
    db.add(
        Activity(
            garmin_id=garmin_id,
            start_time=start,
            activity_type=activity_type,
            name=name,
            distance_m=distance_m,
            duration_s=duration_s,
            raw_json=raw_json,
        )
    )


# ---------------------------------------------------------------
# T8 — service.get_potential (chamadas diretas com seeds)
# ---------------------------------------------------------------


def test_get_potential_full_payload_from_seeds(db) -> None:
    """Done-when T8: os 4 blocos montados a partir do banco — pins do
    design §Contrato (PRs reais + predições da sonda + prova deduplicada)."""
    _seed_prs(db)
    _seed_garmin_predictions(db)
    # Maratona de Londrina: prova E PR na mesma data -> só o PR vira ponto
    _seed_activity(
        db, garmin_id="1", start=datetime(2026, 7, 5, 7, 10, 53),
        name="Londrina Corrida", distance_m=42300.0, duration_s=14083.0,
        raw_json={"eventType": {"typeKey": "race", "typeId": 1}},
    )
    # Prova em data livre: vira ponto da timeline
    _seed_activity(
        db, garmin_id="2", start=datetime(2025, 6, 15, 7, 0, 0),
        name="Corrida de Aniversário", distance_m=10000.0, duration_s=2500.0,
        raw_json={"eventType": {"typeKey": "race", "typeId": 1}},
    )
    _seed_activity(
        db, garmin_id="3", start=datetime(2026, 4, 22, 7, 0, 0),
        raw_json={"vO2MaxValue": 54.0},
    )
    db.commit()

    payload = service.get_potential(db, CALIBRATION)

    # Bloco vdot: corrente da calibração; demonstrado = 5K com o evento na origem
    assert payload["vdot"]["current"] == {
        "vdot": 50.2,
        "source": "10K em 41:15",
        "test_date": date(2026, 10, 3),
    }
    demonstrated = payload["vdot"]["demonstrated"]
    assert round(demonstrated["vdot"], 2) == 51.62
    assert demonstrated["source"] == "FASTEST_5K"
    assert demonstrated["date"] == date(2026, 4, 26)
    assert payload["vdot"]["gap_pct"] == 97.3  # 50.2 / 51.6193 × 100 (exato)

    timeline = payload["vdot"]["timeline"]
    assert [(p["date"], p["source"], p["label"]) for p in timeline] == [
        (date(2024, 10, 5), "pr", "10K 40:25"),
        (date(2025, 6, 15), "prova", "Corrida de Aniversário"),
        (date(2026, 4, 26), "pr", "5K 19:23"),
        (date(2026, 5, 3), "pr", "Meia 1:30:09"),
        (date(2026, 7, 5), "pr", "Maratona 3:52:05"),  # prova deduplicada
        (date(2026, 10, 3), "teste", "10K em 41:15"),
    ]

    # Bloco predictions: 3 estimativas + PR com data (pins do design)
    assert payload["predictions"]["5K"] == {
        "garmin_s": 1165.0,
        "riegel_s": 1163.8,
        "vdot_s": 1191.9,
        "average_s": 1173.6,
        "pr_s": 1163.8,
        "pr_date": date(2026, 4, 26),
    }
    assert payload["predictions"]["MARATHON"] == {
        "garmin_s": 11989.0,
        "riegel_s": 11162.4,
        "vdot_s": 11401.4,
        "average_s": 11517.6,
        "pr_s": 13925.8,
        "pr_date": date(2026, 7, 5),
    }

    # Bloco decay: sinal do gap — maratona é o maior (negativo = execução)
    by_event = {row["event"]: row for row in payload["decay"]}
    assert by_event["MARATHON"] == {
        "event": "MARATHON",
        "real_pace_s": 330.0,
        "ideal_pace_s": 270.2,
        "delta_pct": -22.1,
    }

    # vo2max do relógio (sem linhas em load neste teste — nada de pmc no
    # payload: CLR-03; os pins de janela/current/null moram no health)
    assert payload["vo2max"] == {
        "points": [{"date": date(2026, 4, 22), "value": 54.0}],
    }


def test_vo2max_points_filtered_and_ordered_from_raw_json(db) -> None:
    """Done-when T8 (POT-13): pontos do raw_json.vO2MaxValue das corridas
    (running/trail_running — filtro em Python, AD-001), start_time ASC com
    desempate id ASC (determinismo do spec); campo ausente/não-corrida fora."""
    _seed_activity(db, garmin_id="10", start=datetime(2026, 4, 23, 7, 0),
                   raw_json={"vO2MaxValue": 55.0})
    _seed_activity(db, garmin_id="11", start=datetime(2026, 4, 22, 7, 0),
                   raw_json={"vO2MaxValue": 54.0})
    _seed_activity(db, garmin_id="12", start=datetime(2026, 4, 21, 7, 0),
                   activity_type="cycling", raw_json={"vO2MaxValue": 60.0})
    _seed_activity(db, garmin_id="13", start=datetime(2026, 4, 20, 7, 0),
                   raw_json={"distance": 5000})  # corrida sem o campo
    # Empate de start_time: a ordem segue id ASC (estável entre leituras)
    _seed_activity(db, garmin_id="14", start=datetime(2026, 4, 26, 7, 0),
                   raw_json={"vO2MaxValue": 55.5})
    _seed_activity(db, garmin_id="15", start=datetime(2026, 4, 26, 7, 0),
                   activity_type="trail_running", raw_json={"vO2MaxValue": 56.0})
    db.commit()

    payload = service.get_potential(db, CALIBRATION)
    assert payload["vo2max"] == {
        "points": [
            {"date": date(2026, 4, 22), "value": 54.0},
            {"date": date(2026, 4, 23), "value": 55.0},
            {"date": date(2026, 4, 26), "value": 55.5},
            {"date": date(2026, 4, 26), "value": 56.0},
        ],
    }


def test_vo2max_null_without_watch_data(db) -> None:
    """Done-when T8 (POT-13): nenhuma corrida com vO2MaxValue -> vo2max=None
    (spec AC 7 — bloco null, não lista vazia)."""
    _seed_activity(db, garmin_id="20", start=datetime(2026, 4, 22, 7, 0), raw_json={})
    db.commit()
    payload = service.get_potential(db, CALIBRATION)
    assert payload["vo2max"] is None


def test_get_potential_without_user_data_keeps_empty_states(db) -> None:
    """Done-when T8: sem PRs/predições/provas -> decay=[], timeline só com o
    teste de calibração (demonstrado = o próprio teste), colunas de PR null,
    Riegel null (sem âncora de 5K) — nenhum número inventado."""
    payload = service.get_potential(db, CALIBRATION)

    (point,) = payload["vdot"]["timeline"]
    assert point["source"] == "teste"
    assert point["label"] == "10K em 41:15"
    assert point["distance_m"] == 10012
    assert point["time_s"] == 2475
    assert round(point["vdot"], 2) == 50.18
    assert payload["vdot"]["demonstrated"] == {
        "vdot": point["vdot"], "source": "10K em 41:15", "date": date(2026, 10, 3),
    }
    assert payload["vdot"]["gap_pct"] == 100.0  # 50.2 / 50.1830 × 100 (exato)

    assert payload["predictions"]["5K"] == {
        "garmin_s": None,
        "riegel_s": None,
        "vdot_s": 1191.9,  # equivalência do VDOT corrente existe mesmo sem dados
        "average_s": 1191.9,  # média honesta = única estimativa presente
        "pr_s": None,
        "pr_date": None,
    }
    assert payload["decay"] == []
    assert payload["vo2max"] is None


def test_potential_domain_never_imports_garmin_gateway() -> None:
    """POT-15 (Success Criteria, verificável por código): nenhum import do
    gateway Garmin em nenhum módulo do domínio potential/ — leitura 100%
    do banco próprio (AD-002)."""
    domain = Path(service.__file__).parent
    modules = sorted(domain.glob("*.py"))
    assert modules  # o domínio existe
    for module in modules:
        source = module.read_text(encoding="utf-8")
        assert "from app.garmin" not in source, module.name
        assert "import app.garmin" not in source, module.name


# ---------------------------------------------------------------
# T10 (panel-clarity) — service sem pmc (CLR-03)
# ---------------------------------------------------------------


def test_service_payload_omits_pmc_even_with_load_rows(db) -> None:
    """Done-when T10 (CLR-03): payload só com os 4 blocos — a exclusão é
    do contrato, não do dado vazio: com linhas de `load` no banco a chave
    continua ausente (a curva de carga mora no health, T1/T2). Ordem das
    chaves pinada — o espelho do router e do cliente seguem a posição."""
    _seed_load(db, date(2026, 10, 13), 20.0, 25.0, -5.0, 1.31)
    _seed_load(db, date(2026, 10, 14), 21.0, 27.0, -6.0, 1.40)
    _seed_load(db, date(2026, 10, 15), 22.0, 28.0, -6.0, 1.42)
    db.commit()

    payload = service.get_potential(db, CALIBRATION)
    assert list(payload.keys()) == ["vdot", "predictions", "vo2max", "decay"]


# ---------------------------------------------------------------
# T9 — GET /api/potential (TestClient + superfície HTTP)
# ---------------------------------------------------------------


def _seed_full_panel(db) -> None:
    """Painel completo: PRs reais + predições da sonda + linhas de load
    (que não viram bloco — CLR-03) + vo2max."""
    _seed_prs(db)
    _seed_garmin_predictions(db)
    _seed_load(db, date(2026, 10, 14), 21.0, 27.0, -6.0, 1.40)
    _seed_load(db, date(2026, 10, 15), 22.0, 28.0, -6.0, 1.42)
    _seed_activity(
        db, garmin_id="30", start=datetime(2026, 4, 22, 7, 0, 0),
        raw_json={"vO2MaxValue": 54.0},
    )


def test_api_happy_path_200_full_payload(client) -> None:
    """POT-11: 200 com o payload completo em JSON — datas ISO e os pins
    do design atravessando o HTTP (sem `pmc` — CLR-03; janela/current do
    bloco são pinados no health, T1/T2 da panel-clarity)."""
    with SessionLocal() as db:
        _seed_full_panel(db)
        db.commit()

    response = client.get("/api/potential")
    assert response.status_code == 200
    body = response.json()

    assert body["vdot"]["current"] == {
        "vdot": 50.2, "source": "10K em 41:15", "test_date": "2026-10-03",
    }
    assert body["vdot"]["demonstrated"] == {
        "vdot": pytest.approx(51.6193, abs=1e-3),
        "source": "FASTEST_5K",
        "date": "2026-04-26",
    }
    assert body["vdot"]["gap_pct"] == 97.3
    assert [(p["date"], p["source"]) for p in body["vdot"]["timeline"]] == [
        ("2024-10-05", "pr"),
        ("2026-04-26", "pr"),
        ("2026-05-03", "pr"),
        ("2026-07-05", "pr"),
        ("2026-10-03", "teste"),
    ]
    assert body["vdot"]["timeline"][0]["label"] == "10K 40:25"

    assert body["predictions"]["5K"] == {
        "garmin_s": 1165.0, "riegel_s": 1163.8, "vdot_s": 1191.9,
        "average_s": 1173.6, "pr_s": 1163.8, "pr_date": "2026-04-26",
    }
    assert list(body["predictions"].keys()) == ["5K", "10K", "HALF_MARATHON", "MARATHON"]

    assert body["vo2max"] == {"points": [{"date": "2026-04-22", "value": 54.0}]}
    by_event = {row["event"]: row for row in body["decay"]}
    assert by_event["MARATHON"]["delta_pct"] == -22.1


def test_api_payload_omits_pmc_even_with_load_rows(client) -> None:
    """Done-when T10 (CLR-03): 200 com o payload de 4 blocos mesmo com
    linhas em `load` — a exclusão é do contrato, não do dado vazio (a
    curva de carga mora no health). Ordem das chaves pinada no JSON."""
    with SessionLocal() as db:
        _seed_load(db, date(2026, 10, 15), 22.0, 28.0, -6.0, 1.42)
        db.commit()

    response = client.get("/api/potential")
    assert response.status_code == 200
    assert list(response.json().keys()) == [
        "vdot", "predictions", "vo2max", "decay",
    ]


def test_api_dead_days_param_returns_identical_payload(client) -> None:
    """Done-when T10 (CLR-04): `?days=90` (param morto do cliente antigo)
    -> 200 com payload idêntico ao da chamada sem param — o painel cheio
    (com `load` semeados) mostraria qualquer efeito de janela."""
    with SessionLocal() as db:
        _seed_full_panel(db)
        db.commit()

    plain = client.get("/api/potential")
    with_days = client.get("/api/potential", params={"days": 90})
    assert plain.status_code == 200
    assert with_days.status_code == 200
    assert with_days.json() == plain.json()


def test_api_dead_days_param_space_has_no_validation(client) -> None:
    """Edge do spec (CLR-04): o espaço do param morto não herda validação
    nova — os valores que eram 422 no contrato antigo (0, -1, 366) agora
    são query ignorada: 200 com payload idêntico. Os bounds vivos de
    `days` são os do health (7–365 — test_health_api)."""
    baseline = client.get("/api/potential").json()
    for params in ({"days": 0}, {"days": -1}, {"days": 366}):
        response = client.get("/api/potential", params=params)
        assert response.status_code == 200, params
        assert response.json() == baseline, params


def test_api_missing_zones_file_responds_500(client, monkeypatch) -> None:
    """POT-16: vdot_zones.json ausente/inválido -> 500 com a mensagem exata
    (a mesma do workouts-list — sem VDOT corrente não há painel)."""
    def raise_missing(path):
        raise ZoneConfigError(f"não foi possível carregar {path}")

    monkeypatch.setattr(potential_router, "load_calibration", raise_missing)
    response = client.get("/api/potential")
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"


def test_api_empty_bank_keeps_empty_states_without_pmc(client) -> None:
    """Done-when T10 (CLR-03 × estado vazio): banco vazio -> 200 com os 4
    blocos e os estados vazios honestos que o empty check da UI lê
    (timeline só com o teste, vo2max null, decay []) — estado vazio, não
    erro; o `pmc` null agora mora no health (T2)."""
    response = client.get("/api/potential")
    assert response.status_code == 200
    body = response.json()
    assert list(body.keys()) == ["vdot", "predictions", "vo2max", "decay"]
    assert len(body["vdot"]["timeline"]) == 1
    assert body["vdot"]["timeline"][0]["source"] == "teste"
    assert body["vo2max"] is None
    assert body["decay"] == []


def test_api_vo2max_null_traverses_http_as_json_null(client) -> None:
    """POT-13 via HTTP (done-when T9): nenhuma corrida com vO2MaxValue ->
    vo2max=null no JSON (a UI omite o bloco inteiro)."""
    response = client.get("/api/potential")
    assert response.status_code == 200
    assert response.json()["vo2max"] is None
