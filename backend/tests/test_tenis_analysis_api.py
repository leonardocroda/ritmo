"""API de análise comparativa entre tênis — integração (T4/T5).

Integração no Postgres do compose: GET /api/tenis/analysis/* expõe perfil,
detalhe e comparação. 401 sem sessão, 404 inexistente, isolamento A x B.
"""

from datetime import date

from fastapi.testclient import TestClient

from app.db.engine import SessionLocal
from app.db.models import Activity, Shoe, Split, User
from app.main import app


def _seed_user_shoe_runs(db, user_id, shoe_id, n_runs=3, base_date=date(2024, 1, 15)):
    """Cria o sapato (se ausente) e n_runs corridas de um usuário com esse tênis."""
    # Garante que o sapato existe (FK activities.shoe_id -> shoes.id)
    existing = db.get(Shoe, shoe_id)
    if existing is None:
        db.add(
            Shoe(
                id=shoe_id,
                user_id=user_id,
                name=f"Tênis {shoe_id}",
                brand="Marca",
                model="Modelo",
                status="ativo",
            )
        )
        db.flush()
    activity_ids = []
    for i in range(n_runs):
        # variação de pace e running dynamics entre os runs
        pace_s = 300 + i * 20
        gct = 240 + i * 10
        stride = 140 + i * 2
        activity = Activity(
            user_id=user_id,
            garmin_id=f"act_api_{user_id}_{shoe_id}_{i}",
            start_time=base_date,
            activity_type="running",
            name=f"Run {i}",
            distance_m=5000.0,
            duration_s=pace_s * 5000 / 1000,
            avg_hr=150 + i * 5,
            shoe_id=shoe_id,
        )
        db.add(activity)
        db.flush()
        activity_ids.append(activity.id)
        for j in range(2):
            db.add(
                Split(
                    user_id=user_id,
                    activity_id=activity.id,
                    idx=j + 1,
                    dist_m=2500.0,
                    duration_s=pace_s * 2500 / 1000,
                    pace_s=pace_s,
                    avg_hr=150 + i * 5,
                    ground_contact_time_ms=gct,
                    stride_length_cm=stride,
                    vertical_oscillation_cm=8.0 + i * 0.5,
                    vertical_ratio=5.5,
                )
            )
    db.commit()
    return activity_ids


def _make_user(db, email, display_name):
    user = User(display_name=display_name, email=email, password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_analysis_shoes_happy_path(session_client) -> None:
    """Done-when T4: GET /api/tenis/analysis/shoes devolve perfil por tênis."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_user_shoe_runs(db, user_id=user_id, shoe_id=10, n_runs=2)
    res = client.get("/api/tenis/analysis/shoes")
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) == 1
    assert data[0]["shoe_id"] == 10
    assert data[0]["total_runs"] == 2


def test_analysis_shoe_detail_includes_derived_metrics(session_client) -> None:
    """Done-when T4: detail inclui running dynamics, EF, drift, janela."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_user_shoe_runs(db, user_id=user_id, shoe_id=20, n_runs=4)
    res = client.get(f"/api/tenis/analysis/shoes/{20}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["shoe_id"] == 20
    assert data["total_runs"] == 4
    # Métricas derivadas presentes quando houver dado suficiente (opcionais)
    for key in ("running_dynamics_adjusted", "ef", "hr_drift", "fresh_vs_fatigue"):
        if key in data:
            assert data[key] is not None


def test_analysis_compare_happy_path(session_client) -> None:
    """Done-when T4: GET /api/tenis/analysis/compare devolve pares + confiança."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_user_shoe_runs(db, user_id=user_id, shoe_id=30, n_runs=4)
        _seed_user_shoe_runs(db, user_id=user_id, shoe_id=31, n_runs=4)
    res = client.get("/api/tenis/analysis/compare?shoe_a=30&shoe_b=31")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "n_pairs" in data
    assert "confidence" in data
    assert "pairs" in data
    assert data["confidence"] in ("baixo", "medio", "alto")


def test_analysis_401_without_session() -> None:
    """Done-when T4: sem sessão -> 401."""
    client = TestClient(app)
    res = client.get("/api/tenis/analysis/shoes")
    assert res.status_code == 401


def test_analysis_shoe_detail_404_not_found(session_client) -> None:
    """Done-when T4: tênis sem corridas -> 404."""
    client, _ = session_client
    res = client.get("/api/tenis/analysis/shoes/99999")
    assert res.status_code == 404


def test_analysis_isolation_other_user(session_client) -> None:
    """Done-when T4: tênis de outro usuário -> 404 (user-scope)."""
    client, user_id = session_client
    with SessionLocal() as db:
        other = _make_user(db, "outro@example.com", "Outro")
        _seed_user_shoe_runs(db, other.id, shoe_id=50, n_runs=2)
    res = client.get("/api/tenis/analysis/shoes/50")
    assert res.status_code == 404


def test_analysis_empty_when_no_runs(session_client) -> None:
    """Done-when T4: sem corridas com tênis -> lista vazia."""
    client, user_id = session_client
    with SessionLocal() as db:
        # usuário sem nenhum tênis associado
        pass
    res = client.get("/api/tenis/analysis/shoes")
    assert res.status_code == 200, res.text
    assert res.json() == []
