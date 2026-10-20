"""API de leitura activities (T6/T7) — TestClient + Postgres real.

User-scope (T2, USR-01/02/03/06/07/08): toda query filtra pelo
``user_id`` do usuário da sessão — os testes usam ``session_client``
(sessão real por usuário, sem o override do conftest) e semeiam com o
``user_id`` devolvido; 401 sem sessão e 404 para recurso de outro
usuário são afirmados aqui.

Os dados são semeados direto no banco (o domínio lê exclusivamente o
banco próprio — AD-002): nenhuma chamada ao Garmin nos testes. Valores
afirmados são literais derivados das fixtures com aritmética exata
(lições L-001/L-002). Avaliações são semeadas SEM ``user_id`` explícito
(default 1) — o ``list_evaluations`` segue no interim DEFAULT_USER_ID
até a T6 migrar o domínio evaluation.
"""

from datetime import date, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.activities import router as activities_router
from app.activities import service
from app.auth.deps import require_session
from app.auth.security import hash_password
from app.db.engine import SessionLocal
from app.db.models import Activity, Evaluation, Hrv, Rhr, Sleep, Split, User
from app.main import app
from app.vdot.zones import ZoneConfigError

# Paces de fixture (s/km) escolhidos para cair em zonas conhecidas:
# 300 -> easy (cut easy/marathon = 4:41), 220 -> repetition (cut = 3:45)
EASY_PACE_S = 300.0
REPETITION_PACE_S = 220.0


def _seed_activity(db, *, user_id: int, garmin_id: str, start: datetime,
                   activity_type: str = "running",
                   name: str = "Morning Run", distance_m: float = 4000.0,
                   duration_s: float = 1200.0, avg_hr: int | None = 145,
                   evaluated: bool = False, raw_json: dict | None = None) -> Activity:
    activity = Activity(
        user_id=user_id,
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
                avg_hr: int | None = None, intensity_type: str | None = "ACTIVE",
                avg_cadence: float | None = None, avg_temperature: float | None = None,
                elevation_m: float | None = None) -> None:
    db.add(
        Split(
            activity_id=activity_id,
            idx=idx,
            dist_m=dist_m,
            duration_s=duration_s,
            pace_s=duration_s * 1000 / dist_m if dist_m and duration_s else None,
            avg_hr=avg_hr,
            avg_cadence=avg_cadence,
            avg_temperature=avg_temperature,
            elevation_m=elevation_m,
            intensity_type=intensity_type,
        )
    )


def _seed_easy_run(db, *, user_id: int, garmin_id: str, start: datetime, laps: int = 4,
                   evaluated: bool = False) -> Activity:
    """Corrida fácil: voltas de 1km a 5:00/km (zona easy) -> tipo 'facil'."""
    activity = _seed_activity(
        db, user_id=user_id, garmin_id=garmin_id, start=start, name="Easy Run",
        distance_m=1000.0 * laps, duration_s=EASY_PACE_S * laps, evaluated=evaluated,
    )
    for idx in range(1, laps + 1):
        _seed_split(db, activity.id, idx, dist_m=1000.0, duration_s=EASY_PACE_S, avg_hr=140)
    return activity


def _seed_strides_run(db, *, user_id: int, garmin_id: str, start: datetime) -> Activity:
    """Strides (shape da sonda): 2 grupos de 500m repetition separados por easy."""
    activity = _seed_activity(
        db, user_id=user_id, garmin_id=garmin_id, start=start, name="Londrina - Strides",
        distance_m=1500.0, duration_s=375.0,
    )
    _seed_split(db, activity.id, 1, dist_m=500.0, duration_s=110.0, avg_hr=160)
    _seed_split(db, activity.id, 2, dist_m=500.0, duration_s=165.0, avg_hr=130)
    _seed_split(db, activity.id, 3, dist_m=500.0, duration_s=110.0, avg_hr=165)
    return activity


def _seed_long_run_with_laps(db, *, user_id: int, garmin_id: str, start: datetime) -> Activity:
    """Longão 8×1000m com FC e cadência: 1ª metade 5:00/km FC 140 cad 172,
    2ª metade 4:50/km FC 145 cad 170 (valores conferidos à mão no T4)."""
    activity = _seed_activity(
        db, user_id=user_id, garmin_id=garmin_id, start=start, name="Long Run",
        distance_m=8000.0, duration_s=2360.0, avg_hr=142,
    )
    for idx in range(1, 5):
        _seed_split(db, activity.id, idx, dist_m=1000.0, duration_s=300.0,
                    avg_hr=140, avg_cadence=172.0)
    for idx in range(5, 9):
        _seed_split(db, activity.id, idx, dist_m=1000.0, duration_s=290.0,
                    avg_hr=145, avg_cadence=170.0)
    return activity


def _make_other_user(db) -> User:
    """Usuário Y (≠ X, ≠ seed 1) para os testes de isolamento."""
    other = User(
        display_name="Outra",
        email="outro@example.com",
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(other)
    db.flush()
    return other


# ---------------------------------------------------------------
# T2 (user-scope) — 401, isolamento A×B, 404 recurso alheio
# ---------------------------------------------------------------


def test_list_401_without_session() -> None:
    """USR-07: sem sessão válida → 401 JSON sem nenhum dado."""
    app.dependency_overrides.pop(require_session, None)
    with TestClient(app) as raw_client:
        response = raw_client.get("/api/activities")
        assert response.status_code == 401
        assert response.json() == {"detail": "não autenticado"}


def test_list_returns_only_own_user_activities(session_client) -> None:
    """USR-01/08: a sessão de X lista só as atividades de X — a corrida de Y
    (outro usuário, mesmo banco) não aparece nem no total nem nos items."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_easy_run(db, user_id=user_id, garmin_id="u1a",
                       start=datetime(2026, 10, 13, 7, 0))
        other = _make_other_user(db)
        _seed_easy_run(db, user_id=other.id, garmin_id="u1b",
                       start=datetime(2026, 10, 14, 7, 0))
        db.commit()
        other_id = other.id

    body = client.get("/api/activities").json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    with SessionLocal() as db:
        own = db.execute(
            select(Activity).where(Activity.user_id == user_id)
        ).scalars().all()
        assert len(own) == 1
        assert body["items"][0]["id"] == own[0].id
        assert own[0].user_id == user_id
        assert other_id != user_id


def test_detail_404_for_other_users_activity(session_client) -> None:
    """USR-02: atividade com user_id ≠ X → 404 na sessão de X (não 403,
    não vaza a existência nem o dado)."""
    client, _user_id = session_client
    with SessionLocal() as db:
        other = _make_other_user(db)
        activity = _seed_activity(db, user_id=other.id, garmin_id="u1c",
                                  start=datetime(2026, 10, 13, 7, 0))
        db.commit()
        activity_id = activity.id

    response = client.get(f"/api/activities/{activity_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"


def test_detail_context_isolated_per_user(session_client) -> None:
    """USR-03 (contexto do detalhe): sono/HRV/RHR de Y na mesma data não
    vazam para o detalhe de X — cada bloco null."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_easy_run(db, user_id=user_id, garmin_id="u1d",
                                  start=datetime(2026, 10, 14, 7, 0))
        other = _make_other_user(db)
        db.add(Sleep(user_id=other.id, date=date(2026, 10, 14),
                     duration_s=28800.0, score=99))
        db.add(Hrv(user_id=other.id, date=date(2026, 10, 14), value=88.0))
        db.add(Rhr(user_id=other.id, date=date(2026, 10, 14), value=33))
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    assert detail["context"]["sleep"] is None
    assert detail["context"]["hrv"] is None
    assert detail["context"]["rhr"] is None


# ---------------------------------------------------------------
# T6 — GET /api/activities
# ---------------------------------------------------------------


def test_list_empty_database_returns_empty_page(session_client) -> None:
    """Edge do spec: banco vazio -> 200 com página vazia (sem erro)."""
    client, _user_id = session_client
    response = client.get("/api/activities")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 30, "offset": 0}


def test_list_defaults_to_running_newest_first(session_client) -> None:
    """TRN-04: padrão = corridas por start_time DESC; não-corrida fica fora;
    payload do item completo (pace derivado 1200×1000/4000 = 300,0)."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_easy_run(db, user_id=user_id, garmin_id="100",
                       start=datetime(2026, 10, 13, 7, 0))
        _seed_strides_run(db, user_id=user_id, garmin_id="101",
                          start=datetime(2026, 10, 14, 7, 15))
        _seed_activity(
            db, user_id=user_id, garmin_id="102",
            start=datetime(2026, 10, 14, 19, 0),
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


def test_list_activity_type_all_includes_non_running(session_client) -> None:
    """TRN-05: all inclui as demais; não-corrida -> inferred_type=null."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_easy_run(db, user_id=user_id, garmin_id="100",
                       start=datetime(2026, 10, 13, 7, 0))
        _seed_activity(
            db, user_id=user_id, garmin_id="102",
            start=datetime(2026, 10, 14, 19, 0),
            activity_type="cycling", name="Bike", distance_m=20000.0, duration_s=3600.0,
        )
        _seed_activity(
            db, user_id=user_id, garmin_id="103",
            start=datetime(2026, 10, 15, 6, 0),
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


def test_list_pagination_beyond_end_returns_empty_items(session_client) -> None:
    """Edge do spec: offset além do fim não é erro -> items=[] com total."""
    client, user_id = session_client
    with SessionLocal() as db:
        for i in range(3):
            _seed_easy_run(db, user_id=user_id, garmin_id=f"200{i}",
                           start=datetime(2026, 10, 10 + i, 7, 0))
        db.commit()

    body = client.get("/api/activities", params={"offset": 999}).json()
    assert body == {"items": [], "total": 3, "limit": 30, "offset": 999}


def test_list_pagination_pages_concatenate_without_duplicates(session_client) -> None:
    """Independent Test do spec: 'Carregar mais' anexa a próxima página sem duplicatas."""
    client, user_id = session_client
    with SessionLocal() as db:
        for i in range(3):
            _seed_easy_run(db, user_id=user_id, garmin_id=f"300{i}",
                           start=datetime(2026, 10, 10 + i, 7, 0))
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


def test_list_same_start_time_ties_break_by_id_desc(session_client) -> None:
    """Edge do spec: start_time igual -> desempate id DESC (ordem estável)."""
    client, user_id = session_client
    with SessionLocal() as db:
        first = _seed_easy_run(db, user_id=user_id, garmin_id="400",
                               start=datetime(2026, 10, 14, 7, 0))
        second = _seed_easy_run(db, user_id=user_id, garmin_id="401",
                                start=datetime(2026, 10, 14, 7, 0))
        db.commit()
        assert second.id > first.id

    body = client.get("/api/activities").json()
    assert [item["id"] for item in body["items"]] == [second.id, first.id]


def test_list_invalid_limit_offset_responds_422(session_client) -> None:
    """TRN-06: limit fora de [1,100] ou offset<0 -> 422 (validação antes da query)."""
    client, _user_id = session_client
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        response = client.get("/api/activities", params=params)
        assert response.status_code == 422, params


def test_list_infer_type_from_splits_and_zones(session_client) -> None:
    """TRN-07: tipo inferido em tempo de leitura — fácil e intervalado (strides)."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_easy_run(db, user_id=user_id, garmin_id="500",
                       start=datetime(2026, 10, 13, 7, 0))
        _seed_strides_run(db, user_id=user_id, garmin_id="501",
                          start=datetime(2026, 10, 14, 7, 15))
        db.commit()

    body = client.get("/api/activities").json()
    by_name = {item["name"]: item for item in body["items"]}
    assert by_name["Easy Run"]["inferred_type"] == "facil"
    assert by_name["Londrina - Strides"]["inferred_type"] == "intervalado"


def test_list_evaluated_flag_echoed(session_client) -> None:
    """TRN-08 (payload): evaluated=true vem no item para o badge 'Avaliado'."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_easy_run(db, user_id=user_id, garmin_id="600",
                       start=datetime(2026, 10, 13, 7, 0), evaluated=True)
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


# ---------------------------------------------------------------
# T7 — GET /api/activities/{id}
# ---------------------------------------------------------------


def _get_detail(client, activity_id: int) -> dict:
    response = client.get(f"/api/activities/{activity_id}")
    assert response.status_code == 200
    return response.json()


def test_detail_404_unknown_id(session_client) -> None:
    """TRN-13: id inexistente -> 404."""
    client, _user_id = session_client
    response = client.get("/api/activities/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "atividade não encontrada"


def test_detail_missing_zones_file_responds_500(session_client, monkeypatch) -> None:
    """Edge do spec: vdot_zones.json ausente/inválido -> 500 com a mensagem exata."""
    def raise_missing(path):
        raise ZoneConfigError(f"não foi possível carregar {path}")

    monkeypatch.setattr(activities_router, "load_zone_config", raise_missing)
    client, _user_id = session_client
    response = client.get("/api/activities/1")
    assert response.status_code == 500
    assert response.json()["detail"] == "zonas VDOT não configuradas"


def test_detail_easy_run_full_payload(session_client) -> None:
    """TRN-19/21/22: longão fácil com consistência completa, zonas e splits.

    8×1000m: 5:00/km FC 140 cad 172 -> 4:50/km FC 145 cad 170 (valores do
    T4 conferidos à mão). decoupling = (145/290)/(140/300) - 1 = +7,1%.
    """
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_long_run_with_laps(db, user_id=user_id, garmin_id="700",
                                           start=datetime(2026, 10, 13, 7, 0))
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)

    activity_payload = detail["activity"]
    assert activity_payload["id"] == activity_id
    assert activity_payload["name"] == "Long Run"
    assert activity_payload["inferred_type"] == "facil"
    assert activity_payload["pace_s"] == 295.0  # 2360×1000/8000
    assert activity_payload["avg_hr"] == 142
    assert activity_payload["evaluated"] is False
    assert activity_payload["structure"] == "Corrida"  # todas as voltas ACTIVE

    consistency = detail["consistency"]
    assert consistency == {
        "first_half_pace_s": 300.0,
        "second_half_pace_s": 290.0,
        "balance_delta_s": -10.0,
        "balance_delta_pct": -3.3,
        "first_half_hr": 140.0,
        "second_half_hr": 145.0,
        "hr_drift_bpm": 5.0,
        "decoupling_pct": 7.1,
        "cadence_fade_spm": -2.0,
    }

    assert len(detail["zones"]) == 5
    assert detail["zones"][0] == {
        "key": "easy", "label": "Easy", "pace_range": "5:51–4:53/km", "color": "#22c55e",
    }

    # TRN-17 no payload: cor da linha de FC distinta da cor de interval
    interval_color = next(z["color"] for z in detail["zones"] if z["key"] == "interval")
    assert detail["hr_color"] == "#f8fafc"
    assert detail["hr_color"] != interval_color

    assert len(detail["splits"]) == 8
    first_split = detail["splits"][0]
    assert first_split == {
        "idx": 1,
        "dist_m": 1000.0,
        "duration_s": 300.0,
        "pace_s": 300.0,
        "avg_hr": 140,
        "avg_cadence": 172.0,
        "avg_temperature": None,
        "elevation_m": None,
        "intensity_type": "ACTIVE",
        "zone": "easy",
        "km_label": "1,0",
    }
    assert detail["splits"][4]["zone"] == "easy"  # pace 290 ainda é easy (cut 4:41)
    assert detail["splits"][7]["km_label"] == "8,0"

    # Contexto sem dados na data: cada campo null; temperatura omitida
    assert detail["context"]["sleep"] is None
    assert detail["context"]["hrv"] is None
    assert detail["context"]["rhr"] is None
    assert "temperature_c" not in detail["context"]


def test_detail_strides_short_laps_zones_and_km_labels(session_client) -> None:
    """TRN-19: voltas curtas (strides da sonda) classificadas em repetition com
    recuperação easy; km acumulado com 1 decimal; consistência null (<8000m)."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_activity(
            db, user_id=user_id, garmin_id="701",
            start=datetime(2026, 10, 14, 7, 15),
            name="Londrina - Strides", distance_m=3600.0, duration_s=1330.0,
        )
        _seed_split(db, activity.id, 1, dist_m=2000.0, duration_s=600.0,
                    intensity_type="WARMUP")
        _seed_split(db, activity.id, 2, dist_m=100.0, duration_s=22.0,
                    intensity_type="ACTIVE")
        _seed_split(db, activity.id, 3, dist_m=200.0, duration_s=66.0,
                    intensity_type="REST")
        _seed_split(db, activity.id, 4, dist_m=100.0, duration_s=22.0,
                    intensity_type="ACTIVE")
        _seed_split(db, activity.id, 5, dist_m=200.0, duration_s=66.0,
                    intensity_type="REST")
        _seed_split(db, activity.id, 6, dist_m=1000.0, duration_s=300.0,
                    intensity_type="COOLDOWN")
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)

    assert detail["activity"]["inferred_type"] == "intervalado"
    assert detail["activity"]["structure"] == (
        "Aquecimento 2,0km + Corrida 0,1km + Descanso 0,2km + Corrida 0,1km "
        "+ Descanso 0,2km + Desaquecimento 1,0km"
    )

    zones = [(split["idx"], split["zone"], split["km_label"]) for split in detail["splits"]]
    assert zones == [
        (1, "easy", "2,0"),
        (2, "repetition", "2,1"),  # 100m a 220 s/km (3:40) -> repetition
        (3, "easy", "2,3"),
        (4, "repetition", "2,4"),
        (5, "easy", "2,6"),
        (6, "easy", "3,6"),
    ]
    assert detail["consistency"] is None  # 3600m < 8000m (gate do T4)


def test_detail_zone_null_when_pace_invalid(session_client) -> None:
    """Edge do spec: volta com distance=0 -> pace null e zone null; km_label acumula."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_easy_run(db, user_id=user_id, garmin_id="702",
                                  start=datetime(2026, 10, 13, 7, 0), laps=4)
        _seed_split(db, activity.id, 5, dist_m=0.0, duration_s=30.0, intensity_type="REST")
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    rest = detail["splits"][4]
    assert rest["dist_m"] == 0.0
    assert rest["pace_s"] is None
    assert rest["zone"] is None
    assert rest["km_label"] == "4,0"  # volta sem distância não avança o acumulado
    assert detail["splits"][3]["km_label"] == "4,0"


def test_detail_activity_without_splits(session_client) -> None:
    """Edge do spec (esteira): resumo sem splits, sem consistência, sem estrutura."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_activity(
            db, user_id=user_id, garmin_id="703",
            start=datetime(2026, 10, 13, 6, 30),
            name="Treadmill Run", distance_m=8000.0, duration_s=3000.0,
        )
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    assert detail["splits"] == []
    assert detail["consistency"] is None
    assert detail["activity"]["structure"] is None
    assert detail["activity"]["inferred_type"] == "facil"
    assert detail["activity"]["pace_s"] == 375.0  # 3000×1000/8000


def test_detail_non_running_activity(session_client) -> None:
    """Edge do spec (modo all): não-corrida -> resumo, sem tipo, sem consistência."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_activity(
            db, user_id=user_id, garmin_id="704",
            start=datetime(2026, 10, 9, 19, 6),
            activity_type="yoga", name="Ioga", distance_m=0.0, duration_s=2681.52,
            avg_hr=61,
        )
        db.commit()
        activity_id = activity.id

    response = client.get(f"/api/activities/{activity_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["activity"]["inferred_type"] is None
    assert detail["activity"]["pace_s"] is None  # distance_m 0 -> null (spec)
    assert detail["activity"]["avg_hr"] == 61
    assert detail["splits"] == []
    assert detail["consistency"] is None


def test_detail_consistency_null_with_8000m_but_3_laps(session_client) -> None:
    """Gate do T4: >=8000m mas <4 voltas -> consistency=null."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_activity(
            db, user_id=user_id, garmin_id="705",
            start=datetime(2026, 10, 13, 7, 0),
            distance_m=9000.0, duration_s=2700.0,
        )
        for idx in range(1, 4):
            _seed_split(db, activity.id, idx, dist_m=3000.0, duration_s=900.0)
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    assert detail["consistency"] is None


def test_detail_context_from_local_start_date(session_client) -> None:
    """TRN-26/27: sono/HRV/RHR da data local de início; temperatura média
    ponderada pela duração das voltas com temperatura ((22×300+24×300)/600 = 23,0)."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_long_run_with_laps(db, user_id=user_id, garmin_id="706",
                                           start=datetime(2026, 10, 14, 7, 0))
        db.add(Sleep(user_id=user_id, date=date(2026, 10, 14),
                     duration_s=28800.0, score=85))
        db.add(Hrv(user_id=user_id, date=date(2026, 10, 14), value=48.0,
                   status="BALANCED"))
        db.add(Rhr(user_id=user_id, date=date(2026, 10, 14), value=42))
        db.commit()
        splits = (
            db.execute(
                select(Split).where(
                    Split.activity_id == activity.id, Split.idx.in_((1, 2))
                )
            )
            .scalars()
            .all()
        )
        splits[0].avg_temperature = 22.0
        splits[1].avg_temperature = 24.0
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    assert detail["context"]["sleep"] == {"duration_s": 28800.0, "score": 85}
    assert detail["context"]["hrv"] == {"value": 48.0, "status": "BALANCED"}
    assert detail["context"]["rhr"] == {"value": 42}
    assert detail["context"]["temperature_c"] == 23.0
    assert detail["consistency"] is not None


def test_detail_context_null_when_no_health_data_for_date(session_client) -> None:
    """TRN-26: dia sem sono/HRV/RHR -> cada campo null (UI esconde); sem
    temperatura nas voltas -> campo omitido (spec)."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_easy_run(db, user_id=user_id, garmin_id="707",
                                 start=datetime(2026, 10, 13, 7, 0))
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    assert detail["context"] == {"sleep": None, "hrv": None, "rhr": None}


# ---------------------------------------------------------------
# T8 (ai-evaluation) — Detalhe expõe avaliações + activity_type
# ---------------------------------------------------------------


def _seed_evaluation(db, activity_id: int, *, verdict: str, created_at: datetime) -> None:
    # Interim user-scope: SEM user_id explícito (default 1) — o
    # list_evaluations segue filtrando DEFAULT_USER_ID até a T6 migrar
    # o domínio evaluation.
    db.add(
        Evaluation(
            activity_id=activity_id,
            intent_type="facil",
            intent_text=None,
            payload_json={"intencao": {"tipo": "facil", "texto": None}},
            model="z-ai/glm-5.3",
            prompt_version="v1",
            verdict=verdict,
            verdict_json={"veredito": verdict},
            tokens_in=1234,
            tokens_out=56,
            created_at=created_at,
        )
    )


def test_detail_exposes_evaluations_newest_first(session_client) -> None:
    """EVAL-17: avaliações do treino no detalhe, mais recente primeiro."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_easy_run(db, user_id=user_id, garmin_id="801",
                                 start=datetime(2026, 10, 13, 7, 0))
        db.flush()
        _seed_evaluation(
            db, activity.id, verdict="too_hard", created_at=datetime(2026, 10, 15, 8, 0, 0)
        )
        _seed_evaluation(
            db, activity.id, verdict="on_target", created_at=datetime(2026, 10, 16, 9, 0, 0)
        )
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    evaluations = detail["evaluations"]
    assert [e["verdict"] for e in evaluations] == ["on_target", "too_hard"]
    newest = evaluations[0]
    assert newest["activity_id"] == activity_id
    assert newest["intent_type"] == "facil"
    assert newest["model"] == "z-ai/glm-5.3"
    assert newest["prompt_version"] == "v1"
    assert newest["tokens_in"] == 1234
    assert newest["tokens_out"] == 56
    assert newest["verdict_json"] == {"veredito": "on_target"}


def test_detail_without_evaluations_returns_empty_list(session_client) -> None:
    """EVAL-17: sem avaliações -> lista vazia (estado vazio, não erro)."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_easy_run(db, user_id=user_id, garmin_id="802",
                                 start=datetime(2026, 10, 13, 7, 0))
        db.commit()
        activity_id = activity.id

    detail = _get_detail(client, activity_id)
    assert detail["evaluations"] == []


def test_detail_exposes_activity_type(session_client) -> None:
    """Contrato aditivo do ai-evaluation: a UI distingue corrida para
    renderizar o formulário de avaliação (EVAL-10)."""
    client, user_id = session_client
    with SessionLocal() as db:
        run = _seed_easy_run(db, user_id=user_id, garmin_id="803",
                             start=datetime(2026, 10, 13, 7, 0))
        yoga = _seed_activity(
            db, user_id=user_id, garmin_id="804",
            start=datetime(2026, 10, 13, 19, 0),
            activity_type="yoga", name="Ioga", distance_m=0.0, duration_s=2681.0,
            avg_hr=61,
        )
        db.commit()
        run_id, yoga_id = run.id, yoga.id

    assert _get_detail(client, run_id)["activity"]["activity_type"] == "running"
    assert _get_detail(client, yoga_id)["activity"]["activity_type"] == "yoga"
