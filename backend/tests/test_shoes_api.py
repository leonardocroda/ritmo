"""API de tênis (T2) — TestClient + Postgres real.

User-scope: toda query filtra pelo user_id do usuário da sessão —
testes usam session_client (sessão real por usuário) e semeiam com
o user_id devolvido; 401 sem sessão e 404 para recurso de outro
usuário são afirmados aqui. Envelope {items, attribution_30d_pct}.
"""

from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.engine import SessionLocal
from app.db.models import Activity, Shoe, User
from app.main import app


def _recent_dt(days_ago: int = 1) -> datetime:
    """Retorna datetime dentro da janela de 30 dias para testes de attribution."""
    return datetime.utcnow() - timedelta(days=days_ago)


def _seed_shoe(db, *, user_id: int, **kwargs) -> Shoe:
    defaults = {
        "name": "Kayano 30",
        "brand": "ASICS",
        "model": "Gel-Kayano 30",
        "acquired_date": date(2024, 1, 15),
        "initial_km": 0.0,
        "max_km": 800.0,
        "status": "ativo",
        "strava_gear_id": None,
    }
    defaults.update(kwargs)
    shoe = Shoe(user_id=user_id, **defaults)
    db.add(shoe)
    db.flush()
    return shoe


def _seed_activity(db, *, user_id: int, garmin_id: str, distance_m: float = 5000.0, **kwargs) -> Activity:
    defaults = {
        "user_id": user_id,
        "garmin_id": garmin_id,
        "start_time": _recent_dt(1),
        "activity_type": "running",
        "name": "Morning Run",
        "distance_m": distance_m,
        "duration_s": 1800.0,
        "shoe_id": None,
    }
    defaults.update(kwargs)
    activity = Activity(**defaults)
    db.add(activity)
    db.flush()
    return activity


def test_list_shoes_empty(session_client) -> None:
    """Done-when T2: GET /api/shoes vazio → items=[], attribution_30d_pct=null."""
    client, user_id = session_client
    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert data == {"items": [], "attribution_30d_pct": None}


def test_create_shoe_happy(session_client) -> None:
    """Done-when T2: POST cria com status "ativo" default, user_id explícito."""
    client, user_id = session_client
    r = client.post("/api/shoes", json={"name": "Kayano 30", "brand": "ASICS"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Kayano 30"
    assert data["brand"] == "ASICS"
    assert data["status"] == "ativo"
    assert data["current_km"] == 0.0
    assert data["run_count"] == 0
    assert data["last_use"] is None
    assert data["life_pct"] is None
    assert "id" in data


def test_create_shoe_with_initial_km(session_client) -> None:
    """Done-when T2: POST com initial_km > 0 → current_km = initial_km."""
    client, user_id = session_client
    r = client.post("/api/shoes", json={"name": "Kayano 30", "initial_km": 100.5})
    assert r.status_code == 200
    data = r.json()
    assert data["initial_km"] == 100.5
    assert data["current_km"] == 100.5


def test_create_shoe_validation_empty_name(session_client) -> None:
    """Done-when T2: 422 nome vazio."""
    client, user_id = session_client
    r = client.post("/api/shoes", json={"name": ""})
    assert r.status_code == 422
    assert "nome é obrigatório" in r.json()["detail"]


def test_create_shoe_validation_negative_initial_km(session_client) -> None:
    """Done-when T2: 422 initial_km negativo."""
    client, user_id = session_client
    r = client.post("/api/shoes", json={"name": "Test", "initial_km": -1})
    assert r.status_code == 422
    assert "deve ser >=" in r.json()["detail"]


def test_create_shoe_validation_invalid_status(session_client) -> None:
    """Done-when T2: 422 status inválido."""
    client, user_id = session_client
    r = client.post("/api/shoes", json={"name": "Test", "status": "invalid"})
    assert r.status_code == 422
    # Pydantic literal validation runs first
    assert "ativo" in r.json()["detail"][0]["msg"] or "aposentado" in r.json()["detail"][0]["msg"]


def test_list_shoes_with_km_derivada(session_client) -> None:
    """Done-when T2: GET /api/shoes devolve current_km = initial_km + Σ distance_m."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id, initial_km=50.0, max_km=800.0)
        _seed_activity(db, user_id=user_id, garmin_id="act_1", distance_m=5000.0, shoe_id=shoe.id)
        _seed_activity(db, user_id=user_id, garmin_id="act_2", distance_m=3000.0, shoe_id=shoe.id)
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    # initial_km 50 + 8km = 58.0
    assert item["current_km"] == 58.0
    assert item["run_count"] == 2
    assert item["last_use"] is not None
    assert item["life_pct"] == round((58.0 / 800.0) * 100, 1)


def test_list_shoes_ordering_active_first_then_last_use_desc(session_client) -> None:
    """Done-when T2: ordenação ativos primeiro, depois last_use DESC."""
    client, user_id = session_client
    with SessionLocal() as db:
        # Tênis aposentado com uso recente
        retired = _seed_shoe(db, user_id=user_id, name="Aposentado", status="aposentado")
        _seed_activity(db, user_id=user_id, garmin_id="act_1", distance_m=5000.0, shoe_id=retired.id,
                       start_time=datetime(2024, 6, 15))
        # Tênis ativo com uso antigo
        active_old = _seed_shoe(db, user_id=user_id, name="Ativo Antigo")
        _seed_activity(db, user_id=user_id, garmin_id="act_2", distance_m=5000.0, shoe_id=active_old.id,
                       start_time=datetime(2024, 1, 15))
        # Tênis ativo com uso recente
        active_new = _seed_shoe(db, user_id=user_id, name="Ativo Novo")
        _seed_activity(db, user_id=user_id, garmin_id="act_3", distance_m=5000.0, shoe_id=active_new.id,
                       start_time=datetime(2024, 6, 10))
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    names = [item["name"] for item in data["items"]]
    # Ativos primeiro (Ativo Novo, Ativo Antigo), depois aposentado
    assert names == ["Ativo Novo", "Ativo Antigo", "Aposentado"]


def test_update_shoe_happy(session_client) -> None:
    """Done-when T2: PATCH edita campos e status."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        db.commit()
        shoe_id = shoe.id

    r = client.patch(f"/api/shoes/{shoe_id}", json={"name": "Kayano 31", "status": "aposentado"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Kayano 31"
    assert data["status"] == "aposentado"


def test_update_shoe_404_other_user(session_client) -> None:
    """Done-when T2: 404 tênis de outro usuário."""
    client, user_id = session_client
    with SessionLocal() as db:
        # Cria outro usuário
        other = User(display_name="Outro", email="outro@example.com")
        db.add(other)
        db.flush()
        shoe = _seed_shoe(db, user_id=other.id)
        db.commit()
        shoe_id = shoe.id

    r = client.patch(f"/api/shoes/{shoe_id}", json={"name": "Hack"})
    assert r.status_code == 404
    assert "não encontrado" in r.json()["detail"]


def test_update_shoe_validation_negative_initial_km(session_client) -> None:
    """Done-when T2: 422 initial_km negativo no PATCH."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        db.commit()
        shoe_id = shoe.id

    r = client.patch(f"/api/shoes/{shoe_id}", json={"initial_km": -5})
    assert r.status_code == 422
    assert "deve ser >=" in r.json()["detail"]


def test_update_shoe_validation_invalid_status(session_client) -> None:
    """Done-when T2: 422 status inválido no PATCH."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        db.commit()
        shoe_id = shoe.id

    r = client.patch(f"/api/shoes/{shoe_id}", json={"status": "lixo"})
    assert r.status_code == 422
    # Pydantic literal validation runs first
    assert "ativo" in r.json()["detail"][0]["msg"] or "aposentado" in r.json()["detail"][0]["msg"]


def test_update_shoe_validation_empty_name(session_client) -> None:
    """Done-when T2: 422 nome vazio no PATCH."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        db.commit()
        shoe_id = shoe.id

    r = client.patch(f"/api/shoes/{shoe_id}", json={"name": ""})
    assert r.status_code == 422
    assert "nome é obrigatório" in r.json()["detail"]


def test_no_delete_route(session_client) -> None:
    """Done-when T2: sem rota de DELETE (405)."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        db.commit()
        shoe_id = shoe.id

    r = client.delete(f"/api/shoes/{shoe_id}")
    assert r.status_code == 405


def test_401_without_session() -> None:
    """Done-when T2: 401 sem sessão."""
    with TestClient(app) as client:
        r = client.get("/api/shoes")
        assert r.status_code == 401


def test_isolation_cross_user_list(session_client) -> None:
    """Done-when T2: isolamento A×B — lista só vê seus tênis."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_shoe(db, user_id=user_id, name="Meu Tênis")
        other = User(display_name="Outro", email="outro@example.com")
        db.add(other)
        db.flush()
        _seed_shoe(db, user_id=other.id, name="Dele")
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Meu Tênis"


def test_shoe_with_no_max_km_life_pct_null(session_client) -> None:
    """Done-when T2: life_pct null quando max_km ausente."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id, max_km=None, initial_km=100.0)
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert data["items"][0]["life_pct"] is None


def test_envelope_structure(session_client) -> None:
    """Done-when T2: resposta em envelope {items, attribution_30d_pct}."""
    client, user_id = session_client
    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "attribution_30d_pct" in data
    assert data["attribution_30d_pct"] is None


# ---------------------------------------------------------------
# T3: Associação de tênis por atividade
# ---------------------------------------------------------------


def _seed_running_activity(db, *, user_id: int, garmin_id: str, **kwargs) -> Activity:
    defaults = {
        "user_id": user_id,
        "garmin_id": garmin_id,
        "start_time": _recent_dt(1),
        "activity_type": "running",
        "name": "Morning Run",
        "distance_m": 5000.0,
        "duration_s": 1800.0,
        "shoe_id": None,
    }
    defaults.update(kwargs)
    activity = Activity(**defaults)
    db.add(activity)
    db.flush()
    return activity


def _seed_non_running_activity(db, *, user_id: int, garmin_id: str, **kwargs) -> Activity:
    defaults = {
        "user_id": user_id,
        "garmin_id": garmin_id,
        "start_time": _recent_dt(1),
        "activity_type": "cycling",
        "name": "Bike Ride",
        "distance_m": 20000.0,
        "duration_s": 3600.0,
        "shoe_id": None,
    }
    defaults.update(kwargs)
    activity = Activity(**defaults)
    db.add(activity)
    db.flush()
    return activity


def test_assign_shoe_to_running_activity(session_client) -> None:
    """Done-when T3: PATCH associa tênis a corrida."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        activity = _seed_running_activity(db, user_id=user_id, garmin_id="act_1")
        db.commit()
        shoe_id, activity_id = shoe.id, activity.id

    r = client.patch(f"/api/activities/{activity_id}/shoe", json={"shoe_id": shoe_id})
    assert r.status_code == 200
    data = r.json()
    assert data["shoe"]["id"] == shoe_id
    assert data["shoe"]["name"] == shoe.name


def test_assign_shoe_to_non_running_activity_422(session_client) -> None:
    """Done-when T3: 422 em atividade não-corrida."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        activity = _seed_non_running_activity(db, user_id=user_id, garmin_id="act_bike")
        db.commit()
        shoe_id, activity_id = shoe.id, activity.id

    r = client.patch(f"/api/activities/{activity_id}/shoe", json={"shoe_id": shoe_id})
    assert r.status_code == 422
    assert "não é uma corrida" in r.json()["detail"]


def test_assign_shoe_404_activity_other_user(session_client) -> None:
    """Done-when T3: 404 posse - atividade de outro usuário."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        other = User(display_name="Outro", email="outro@example.com")
        db.add(other)
        db.flush()
        activity = _seed_running_activity(db, user_id=other.id, garmin_id="act_other")
        db.commit()
        shoe_id, activity_id = shoe.id, activity.id

    r = client.patch(f"/api/activities/{activity_id}/shoe", json={"shoe_id": shoe_id})
    assert r.status_code == 404
    assert "não encontrada" in r.json()["detail"]


def test_assign_shoe_404_shoe_other_user(session_client) -> None:
    """Done-when T3: 404 posse - tênis de outro usuário."""
    client, user_id = session_client
    with SessionLocal() as db:
        other = User(display_name="Outro", email="outro@example.com")
        db.add(other)
        db.flush()
        shoe = _seed_shoe(db, user_id=other.id)
        activity = _seed_running_activity(db, user_id=user_id, garmin_id="act_1")
        db.commit()
        shoe_id, activity_id = shoe.id, activity.id

    r = client.patch(f"/api/activities/{activity_id}/shoe", json={"shoe_id": shoe_id})
    assert r.status_code == 404
    assert "não encontrada" in r.json()["detail"]


def test_assign_shoe_404_activity_not_found(session_client) -> None:
    """Done-when T3: 404 atividade inexistente."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        db.commit()
        shoe_id = shoe.id

    r = client.patch("/api/activities/99999/shoe", json={"shoe_id": shoe_id})
    assert r.status_code == 404
    assert "não encontrada" in r.json()["detail"]


def test_unassign_shoe(session_client) -> None:
    """Done-when T3: desassociação com null funciona."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        activity = _seed_running_activity(db, user_id=user_id, garmin_id="act_1", shoe_id=shoe.id)
        db.commit()
        activity_id = activity.id

    r = client.patch(f"/api/activities/{activity_id}/shoe", json={"shoe_id": None})
    assert r.status_code == 200
    data = r.json()
    assert data["shoe"] is None

    # Verifica no banco
    with SessionLocal() as db:
        activity = db.get(Activity, activity_id)
        assert activity.shoe_id is None


def test_activity_detail_includes_shoe(session_client) -> None:
    """Done-when T3: GET /api/activities/{id} detail expõe shoe summary."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id, name="Kayano 30", brand="ASICS", model="Gel-Kayano 30")
        activity = _seed_running_activity(db, user_id=user_id, garmin_id="act_1", shoe_id=shoe.id)
        db.commit()
        activity_id = activity.id

    r = client.get(f"/api/activities/{activity_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["shoe"] is not None
    assert data["shoe"]["id"] == shoe.id
    assert data["shoe"]["name"] == "Kayano 30"
    assert data["shoe"]["brand"] == "ASICS"
    assert data["shoe"]["model"] == "Gel-Kayano 30"
    assert data["shoe"]["status"] == "ativo"


def test_activity_detail_shoe_null_when_unassigned(session_client) -> None:
    """Done-when T3: detail expõe shoe: null quando sem tênis."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity = _seed_running_activity(db, user_id=user_id, garmin_id="act_1")
        db.commit()
        activity_id = activity.id

    r = client.get(f"/api/activities/{activity_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["shoe"] is None


# ---------------------------------------------------------------
# T8: attribution_30d_pct (higiene dos dados)
# ---------------------------------------------------------------


def test_attribution_30d_pct_with_shoe(session_client) -> None:
    """Done-when T8: GET /api/shoes devolve attribution_30d_pct correto com tênis."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        # 3 corridas nos últimos 30 dias, todas com tênis
        _seed_running_activity(db, user_id=user_id, garmin_id="act_1", shoe_id=shoe.id)
        _seed_running_activity(db, user_id=user_id, garmin_id="act_2", shoe_id=shoe.id)
        _seed_running_activity(db, user_id=user_id, garmin_id="act_3", shoe_id=shoe.id)
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert data["attribution_30d_pct"] == 100.0


def test_attribution_30d_pct_partial(session_client) -> None:
    """Done-when T8: attribution_30d_pct parcial (2 de 3 com tênis = 66.7%)."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        # 2 com tênis, 1 sem tênis
        _seed_running_activity(db, user_id=user_id, garmin_id="act_1", shoe_id=shoe.id)
        _seed_running_activity(db, user_id=user_id, garmin_id="act_2", shoe_id=shoe.id)
        _seed_running_activity(db, user_id=user_id, garmin_id="act_3", shoe_id=None)
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert data["attribution_30d_pct"] == 66.7


def test_attribution_30d_pct_none_when_no_runs(session_client) -> None:
    """Done-when T8: attribution_30d_pct null quando não há corridas na janela."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_shoe(db, user_id=user_id)
        # Sem atividades nos últimos 30 dias
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    assert data["attribution_30d_pct"] is None


def test_attribution_30d_pct_ignores_old_runs(session_client) -> None:
    """Done-when T8: corridas >30 dias não contam para attribution_30d_pct."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        # 2 corridas antigas (não contam)
        _seed_running_activity(
            db, user_id=user_id, garmin_id="act_old1", shoe_id=shoe.id,
            start_time=datetime(2020, 1, 1)
        )
        _seed_running_activity(
            db, user_id=user_id, garmin_id="act_old2", shoe_id=None,
            start_time=datetime(2020, 1, 1)
        )
        # 1 corrida recente sem tênis
        _seed_running_activity(db, user_id=user_id, garmin_id="act_new", shoe_id=None)
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    # Só 1 corrida na janela (a recente), sem tênis = 0%
    assert data["attribution_30d_pct"] == 0.0


def test_attribution_30d_pct_ignores_non_running(session_client) -> None:
    """Done-when T8: atividades não-corrida não contam para attribution_30d_pct."""
    client, user_id = session_client
    with SessionLocal() as db:
        shoe = _seed_shoe(db, user_id=user_id)
        # 1 corrida com tênis
        _seed_running_activity(db, user_id=user_id, garmin_id="act_run", shoe_id=shoe.id)
        # 5 bikes (não contam)
        for i in range(5):
            _seed_non_running_activity(db, user_id=user_id, garmin_id=f"act_bike_{i}")
        db.commit()

    r = client.get("/api/shoes")
    assert r.status_code == 200
    data = r.json()
    # Só 1 corrida na janela, com tênis = 100%
    assert data["attribution_30d_pct"] == 100.0