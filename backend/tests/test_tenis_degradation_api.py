"""API de alerta de degradação — integração (T4/T5).

Integração no Postgres do compose: GET /api/tenis/degradation/{id} devolve
sinais de degradação. 401 sem sessão, 404 inexistente, isolamento A x B.
"""

from datetime import date

from fastapi.testclient import TestClient

from app.db.engine import SessionLocal
from app.db.models import Activity, Shoe, User
from app.main import app


def _seed_user_shoe_runs(db, user_id, shoe_id, n_runs=6, base_date=date(2024, 1, 15)):
    existing = db.get(Shoe, shoe_id)
    if existing is None:
        db.add(
            Shoe(id=shoe_id, user_id=user_id, name=f"Tênis {shoe_id}", status="ativo")
        )
        db.flush()
    total_km = 0
    for i in range(n_runs):
        distance_m = 15000.0  # 15 km por corrida
        total_km += distance_m / 1000.0
        activity = Activity(
            user_id=user_id,
            garmin_id=f"act_deg_{user_id}_{shoe_id}_{i}",
            start_time=date(2024, 1, 15),
            activity_type="running",
            name=f"Run {i}",
            distance_m=distance_m,
            duration_s=360.0 * distance_m / 1000,
            avg_hr=160,
            shoe_id=shoe_id,
        )
        db.add(activity)
    db.commit()
    return total_km


def _make_user(db, email, display_name):
    user = User(display_name=display_name, email=email, password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_degradation_happy_path(session_client) -> None:
    """Done-when T4: GET /api/tenis/degradation/{id} devolve sinais."""
    client, user_id = session_client
    with SessionLocal() as db:
        total_km = _seed_user_shoe_runs(db, user_id=user_id, shoe_id=60, n_runs=12)
    res = client.get(f"/api/tenis/degradation/{60}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["shoe_id"] == 60
    assert data["total_km"] >= 150
    assert data["verdict"] is None


def test_degradation_insufficient_km(session_client) -> None:
    """Done-when T4: menos de 150 km -> insufficient True, sem erro."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_user_shoe_runs(db, user_id=user_id, shoe_id=61, n_runs=2)  # ~20 km
    res = client.get(f"/api/tenis/degradation/{61}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["insufficient"] is True
    assert data["signals"] == []


def test_degradation_401_without_session() -> None:
    """Done-when T4: sem sessão -> 401."""
    client = TestClient(app)
    res = client.get("/api/tenis/degradation/1")
    assert res.status_code == 401


def test_degradation_404_not_found(session_client) -> None:
    """Done-when T4: tênis sem corridas -> 404."""
    client, _ = session_client
    res = client.get("/api/tenis/degradation/99999")
    assert res.status_code == 404


def test_degradation_isolation_other_user(session_client) -> None:
    """Done-when T4: tênis de outro usuário -> 404."""
    client, user_id = session_client
    with SessionLocal() as db:
        other = _make_user(db, "outro@example.com", "Outro")
        _seed_user_shoe_runs(db, other.id, shoe_id=70, n_runs=6)
    res = client.get(f"/api/tenis/degradation/{70}")
    assert res.status_code == 404
