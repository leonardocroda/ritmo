"""API de atividades — running dynamics no detail (T5).

Integração no Postgres do compose: GET /api/activities/{id} expõe
gct_ms, stride_cm, vert_osc_cm, vert_ratio por split (null quando nao
houve dado). 401 sem sessao, 404 inexistente, isolamento A x B.
"""

from datetime import date

from fastapi.testclient import TestClient

from app.db.engine import SessionLocal
from app.db.models import Activity, Split, User
from app.main import app


def _seed_activity_with_splits(db, *, user_id, garmin_id, with_dynamics=True):
    activity = Activity(
        user_id=user_id,
        garmin_id=garmin_id,
        start_time=date(2024, 1, 15),
        activity_type="running",
        name="Morning Run",
        distance_m=5000.0,
        duration_s=1800.0,
    )
    db.add(activity)
    db.flush()
    for idx in (1, 2):
        db.add(
            Split(
                user_id=user_id,
                activity_id=activity.id,
                idx=idx,
                dist_m=1000.0,
                duration_s=360.0,
                pace_s=360.0,
                ground_contact_time_ms=250 if with_dynamics else None,
                stride_length_cm=145.5 if with_dynamics else None,
                vertical_oscillation_cm=8.2 if with_dynamics else None,
                vertical_ratio=5.8 if with_dynamics else None,
            )
        )
    db.commit()
    return activity.id


def test_activity_detail_exposes_running_dynamics(session_client) -> None:
    """Done-when T5: GET /api/activities/{id} devolve os 4 campos de
    running dynamics por split."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity_id = _seed_activity_with_splits(db, user_id=user_id, garmin_id="act_api_1")

    res = client.get(f"/api/activities/{activity_id}")
    assert res.status_code == 200, res.text
    splits = res.json()["splits"]
    assert len(splits) == 2
    for split in splits:
        assert split["gct_ms"] == 250
        assert split["stride_cm"] == 145.5
        assert split["vert_osc_cm"] == 8.2
        assert split["vert_ratio"] == 5.8


def test_activity_detail_null_when_no_running_dynamics(session_client) -> None:
    """Done-when T5: sem running dynamics -> campos null, split nao omitido."""
    client, user_id = session_client
    with SessionLocal() as db:
        activity_id = _seed_activity_with_splits(
            db, user_id=user_id, garmin_id="act_api_2", with_dynamics=False
        )

    res = client.get(f"/api/activities/{activity_id}")
    assert res.status_code == 200, res.text
    splits = res.json()["splits"]
    assert len(splits) == 2
    for split in splits:
        assert split["gct_ms"] is None
        assert split["stride_cm"] is None
        assert split["vert_osc_cm"] is None
        assert split["vert_ratio"] is None


def test_activity_detail_401_without_session() -> None:
    """Done-when T5: sem sessao -> 401."""
    client = TestClient(app)
    res = client.get("/api/activities/1")
    assert res.status_code == 401


def test_activity_detail_404_not_found(session_client) -> None:
    """Done-when T5: atividade inexistente -> 404."""
    client, _ = session_client
    res = client.get("/api/activities/99999")
    assert res.status_code == 404


def test_activity_detail_isolation_other_user(session_client) -> None:
    """Done-when T5: atividade de outro usuario -> 404 (user-scope)."""
    client, user_id = session_client
    with SessionLocal() as db:
        # outra usuario cria atividade
        other = User(display_name="Outro", email="outro@example.com")
        db.add(other)
        db.flush()
        activity_id = _seed_activity_with_splits(
            db, user_id=other.id, garmin_id="act_api_other"
        )

    res = client.get(f"/api/activities/{activity_id}")
    assert res.status_code == 404
