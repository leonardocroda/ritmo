"""API de leitura activities (T6/T7) — TestClient + Postgres real.

Os dados são semeados direto no banco (o domínio lê exclusivamente o
banco próprio — AD-002): nenhuma chamada ao Garmin nos testes. Valores
afirmados são literais derivados das fixtures com aritmética exata
(lições L-001/L-002).
"""

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.activities import service
from app.db.engine import SessionLocal
from app.db.models import Activity, Split
from app.main import app

# Paces de fixture (s/km) escolhidos para cair em zonas conhecidas:
# 300 -> easy (cut easy/marathon = 4:41), 220 -> repetition (cut = 3:45)
EASY_PACE_S = 300.0
REPETITION_PACE_S = 220.0


@pytest.fixture()
def client():
    """TestClient: o lifespan recria o schema do teste (conftest derruba antes)."""
    with TestClient(app) as test_client:
        yield test_client


def _seed_activity(db, *, garmin_id: str, start: datetime, activity_type: str = "running",
                   name: str = "Morning Run", distance_m: float = 4000.0,
                   duration_s: float = 1200.0, avg_hr: int | None = 145,
                   evaluated: bool = False, raw_json: dict | None = None) -> Activity:
    activity = Activity(
        garmin_id=garmin_id,
        start_time=start,
        activity_type=activity_type,
        name=name,
        distance_m=distance_m,
        duration_s=duration_s,
        avg_hr=avg_hr,
        evaluated=evaluated,
        raw_json=raw_json,
    )
    db.add(activity)
    db.flush()
    return activity


def _seed_split(db, activity_id: int, idx: int, *, dist_m: float, duration_s: float,
                avg_hr: int | None = None, intensity_type: str | None = "ACTIVE") -> None:
    db.add(
        Split(
            activity_id=activity_id,
            idx=idx,
            dist_m=dist_m,
            duration_s=duration_s,
            pace_s=duration_s * 1000 / dist_m if dist_m and duration_s else None,
            avg_hr=avg_hr,
            intensity_type=intensity_type,
        )
    )


def _seed_easy_run(db, *, garmin_id: str, start: datetime, laps: int = 4,
                   evaluated: bool = False) -> Activity:
    """Corrida fácil: voltas de 1km a 5:00/km (zona easy) -> tipo 'facil'."""
    activity = _seed_activity(
        db, garmin_id=garmin_id, start=start, name="Easy Run",
        distance_m=1000.0 * laps, duration_s=EASY_PACE_S * laps, evaluated=evaluated,
    )
    for idx in range(1, laps + 1):
        _seed_split(db, activity.id, idx, dist_m=1000.0, duration_s=EASY_PACE_S, avg_hr=140)
    return activity


def _seed_strides_run(db, *, garmin_id: str, start: datetime) -> Activity:
    """Strides (shape da sonda): 2 grupos de 500m repetition separados por easy."""
    activity = _seed_activity(
        db, garmin_id=garmin_id, start=start, name="Londrina - Strides",
        distance_m=1500.0, duration_s=375.0,
    )
    _seed_split(db, activity.id, 1, dist_m=500.0, duration_s=110.0, avg_hr=160)
    _seed_split(db, activity.id, 2, dist_m=500.0, duration_s=165.0, avg_hr=130)
    _seed_split(db, activity.id, 3, dist_m=500.0, duration_s=110.0, avg_hr=165)
    return activity


# ---------------------------------------------------------------
# T6 — GET /api/activities
# ---------------------------------------------------------------


def test_list_empty_database_returns_empty_page(client) -> None:
    """Edge do spec: banco vazio -> 200 com página vazia (sem erro)."""
    response = client.get("/api/activities")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 30, "offset": 0}


def test_list_defaults_to_running_newest_first(client) -> None:
    """TRN-04: padrão = corridas por start_time DESC; não-corrida fica fora;
    payload do item completo (pace derivado 1200×1000/4000 = 300,0)."""
    with SessionLocal() as db:
        _seed_easy_run(db, garmin_id="100", start=datetime(2026, 10, 13, 7, 0))
        _seed_strides_run(db, garmin_id="101", start=datetime(2026, 10, 14, 7, 15))
        _seed_activity(
            db, garmin_id="102", start=datetime(2026, 10, 14, 19, 0),
            activity_type="cycling", name="Bike", distance_m=20000.0, duration_s=3600.0,
        )
        db.commit()

    body = client.get("/api/activities").json()
    assert body["total"] == 2
    assert body["limit"] == 30
    assert body["offset"] == 0
    assert [item["name"] for item in body["items"]] == ["Londrina - Strides", "Easy Run"]
    first = body["items"][0]
    assert first["id"] >= 1
    assert first["start_time"] == "2026-10-14T07:15:00"
    assert first["activity_type"] == "running"
    assert first["pace_s"] == 250.0  # 375×1000/1500
    assert first["avg_hr"] == 145
    assert first["evaluated"] is False


def test_list_activity_type_all_includes_non_running(client) -> None:
    """TRN-05: all inclui as demais; não-corrida -> inferred_type=null."""
    with SessionLocal() as db:
        _seed_easy_run(db, garmin_id="100", start=datetime(2026, 10, 13, 7, 0))
        _seed_activity(
            db, garmin_id="102", start=datetime(2026, 10, 14, 19, 0),
            activity_type="cycling", name="Bike", distance_m=20000.0, duration_s=3600.0,
        )
        _seed_activity(
            db, garmin_id="103", start=datetime(2026, 10, 15, 6, 0),
            activity_type="yoga", name="Ioga", distance_m=0.0, duration_s=2681.52,
        )
        db.commit()

    body = client.get("/api/activities", params={"activity_type": "all"}).json()
    assert body["total"] == 3
    by_type = {item["activity_type"]: item for item in body["items"]}
    assert by_type["yoga"]["inferred_type"] is None
    assert by_type["yoga"]["pace_s"] is None  # distance_m 0 -> null (spec)
    assert by_type["cycling"]["inferred_type"] is None
    assert by_type["cycling"]["pace_s"] == 180.0  # 3600×1000/20000 (fórmula do spec)


def test_list_pagination_beyond_end_returns_empty_items(client) -> None:
    """Edge do spec: offset além do fim não é erro -> items=[] com total."""
    with SessionLocal() as db:
        for i in range(3):
            _seed_easy_run(db, garmin_id=f"200{i}", start=datetime(2026, 10, 10 + i, 7, 0))
        db.commit()

    body = client.get("/api/activities", params={"offset": 999}).json()
    assert body == {"items": [], "total": 3, "limit": 30, "offset": 999}


def test_list_pagination_pages_concatenate_without_duplicates(client) -> None:
    """Independent Test do spec: 'Carregar mais' anexa a próxima página sem duplicatas."""
    with SessionLocal() as db:
        for i in range(3):
            _seed_easy_run(db, garmin_id=f"300{i}", start=datetime(2026, 10, 10 + i, 7, 0))
        db.commit()

    page1 = client.get("/api/activities", params={"limit": 2, "offset": 0}).json()
    page2 = client.get("/api/activities", params={"limit": 2, "offset": 2}).json()
    assert [item["total"] for item in (page1, page2)] == [3, 3]
    ids_page1 = [item["id"] for item in page1["items"]]
    ids_page2 = [item["id"] for item in page2["items"]]
    assert len(ids_page1) == 2
    assert len(ids_page2) == 1
    assert not set(ids_page1) & set(ids_page2)
    assert ids_page1[0] > ids_page1[1]  # mais recente primeiro


def test_list_same_start_time_ties_break_by_id_desc(client) -> None:
    """Edge do spec: start_time igual -> desempate id DESC (ordem estável)."""
    with SessionLocal() as db:
        first = _seed_easy_run(db, garmin_id="400", start=datetime(2026, 10, 14, 7, 0))
        second = _seed_easy_run(db, garmin_id="401", start=datetime(2026, 10, 14, 7, 0))
        db.commit()
        assert second.id > first.id

    body = client.get("/api/activities").json()
    assert [item["id"] for item in body["items"]] == [second.id, first.id]


def test_list_invalid_limit_offset_responds_422(client) -> None:
    """TRN-06: limit fora de [1,100] ou offset<0 -> 422 (validação antes da query)."""
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = client.get("/api/activities", params=params)
        assert response.status_code == 422, params


def test_list_infer_type_from_splits_and_zones(client) -> None:
    """TRN-07: tipo inferido em tempo de leitura — fácil e intervalado (strides)."""
    with SessionLocal() as db:
        _seed_easy_run(db, garmin_id="500", start=datetime(2026, 10, 13, 7, 0))
        _seed_strides_run(db, garmin_id="501", start=datetime(2026, 10, 14, 7, 15))
        db.commit()

    body = client.get("/api/activities").json()
    by_name = {item["name"]: item for item in body["items"]}
    assert by_name["Easy Run"]["inferred_type"] == "facil"
    assert by_name["Londrina - Strides"]["inferred_type"] == "intervalado"


def test_list_evaluated_flag_echoed(client) -> None:
    """TRN-08 (payload): evaluated=true vem no item para o badge 'Avaliado'."""
    with SessionLocal() as db:
        _seed_easy_run(db, garmin_id="600", start=datetime(2026, 10, 13, 7, 0), evaluated=True)
        db.commit()

    body = client.get("/api/activities").json()
    assert body["items"][0]["evaluated"] is True


def test_activities_domain_never_imports_garmin_gateway() -> None:
    """AD-002/TRN-28 (Success Criteria, verificável por código): nenhum import
    do gateway Garmin em nenhum módulo do domínio activities/."""
    domain = Path(service.__file__).parent
    modules = sorted(domain.glob("*.py"))
    assert modules  # o domínio existe
    for module in modules:
        source = module.read_text(encoding="utf-8")
        assert "from app.garmin" not in source, module.name
        assert "import app.garmin" not in source, module.name
