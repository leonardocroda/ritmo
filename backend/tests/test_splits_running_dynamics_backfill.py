"""Backfill de running dynamics por atividade — integração (T4).

Integração no Postgres do compose: enriquece splits existentes com running
dynamics, idempotente, atividade inexistente → erro, não-running → skip.
`fetch_typed_splits` injetado (Sem chamada real ao Garmin).
"""

from datetime import date

import pytest
from sqlalchemy import text

from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Split, User
from app.strava.backfill_activity import backfill_activity, BackfillActivityError


@pytest.fixture()
def db():
    init_db()
    with SessionLocal() as session:
        yield session


def _seed_activity(db, user_id=1, activity_type="running", garmin_id="act_bf_1"):
    activity = Activity(
        user_id=user_id,
        garmin_id=garmin_id,
        start_time=date(2024, 1, 15),
        activity_type=activity_type,
        name="Morning Run",
        distance_m=5000.0,
        duration_s=1800.0,
    )
    db.add(activity)
    db.flush()
    for idx in (1, 2, 3):
        db.add(
            Split(
                user_id=user_id,
                activity_id=activity.id,
                idx=idx,
                dist_m=1000.0,
                duration_s=360.0,
                pace_s=360.0,
            )
        )
    db.commit()
    return activity


def _typed_splits(with_dynamics: bool = True):
    laps = []
    for idx in (1, 2, 3):
        lap = {
            "lapIndex": idx,
            "distance": 1000.0,
            "duration": 360.0,
        }
        if with_dynamics:
            lap.update(
                {
                    "groundContactTime": 250 + idx * 10,
                    "strideLength": 145.0 + idx,
                    "verticalOscillation": 8.0 + idx * 0.1,
                    "verticalRatio": 5.5 + idx * 0.1,
                }
            )
        laps.append(lap)
    return {"lapDTOs": laps}


def test_backfill_enriches_splits_with_running_dynamics(db) -> None:
    """Done-when T4: enriquece splits existentes com as 4 colunas de
    running dynamics (upsert por activity_id + idx)."""
    activity = _seed_activity(db)
    result = backfill_activity(
        db, user_id=1, activity_id=activity.id,
        fetch_typed_splits=lambda aid: _typed_splits(True),
    )
    assert result["splits_updated"] == 3
    assert result["laps_returned"] == 3

    splits = (
        db.query(Split).filter(Split.activity_id == activity.id).order_by(Split.idx).all()
    )
    assert len(splits) == 3
    assert splits[0].ground_contact_time_ms == 260
    assert splits[0].stride_length_cm == 146.0
    assert splits[0].vertical_oscillation_cm == 8.1
    assert splits[0].vertical_ratio == 5.6
    assert splits[2].ground_contact_time_ms == 280
    assert splits[2].stride_length_cm == 148.0


def test_backfill_idempotent_rerun(db) -> None:
    """Done-when T4: re-run não duplica splits nem altera valores."""
    activity = _seed_activity(db)
    backfill_activity(
        db, user_id=1, activity_id=activity.id,
        fetch_typed_splits=lambda aid: _typed_splits(True),
    )
    backfill_activity(
        db, user_id=1, activity_id=activity.id,
        fetch_typed_splits=lambda aid: _typed_splits(True),
    )

    splits = (
        db.query(Split).filter(Split.activity_id == activity.id).order_by(Split.idx).all()
    )
    assert len(splits) == 3  # não duplicou
    assert all(s.ground_contact_time_ms is not None for s in splits)


def test_backfill_partial_dynamics_null_for_missing(db) -> None:
    """Done-when T4: lapDTO sem alguma métrica → essa coluna fica NULL
    (não zero inventado)."""
    activity = _seed_activity(db)

    def partial(aid: int):
        return {
            "lapDTOs": [
                {"lapIndex": 1, "distance": 1000.0, "duration": 360.0},
                {"lapIndex": 2, "distance": 1000.0, "duration": 360.0,
                 "groundContactTime": 270, "strideLength": 148.0},
                {"lapIndex": 3, "distance": 1000.0, "duration": 360.0,
                 "verticalOscillation": 7.5},
            ]
        }

    backfill_activity(
        db, user_id=1, activity_id=activity.id,
        fetch_typed_splits=partial,
    )
    splits = (
        db.query(Split).filter(Split.activity_id == activity.id).order_by(Split.idx).all()
    )
    # lap 1: sem nenhuma dinâmica -> todos NULL
    assert splits[0].ground_contact_time_ms is None
    assert splits[0].stride_length_cm is None
    assert splits[0].vertical_oscillation_cm is None
    assert splits[0].vertical_ratio is None
    # lap 2: só GCT e stride
    assert splits[1].ground_contact_time_ms == 270
    assert splits[1].stride_length_cm == 148.0
    assert splits[1].vertical_oscillation_cm is None
    assert splits[1].vertical_ratio is None
    # lap 3: só oscilação
    assert splits[2].vertical_oscillation_cm == 7.5
    assert splits[2].ground_contact_time_ms is None


def test_backfill_activity_not_found_raises(db) -> None:
    """Done-when T4: atividade inexistente → erro claro, sem gravação."""
    with pytest.raises(BackfillActivityError) as exc:
        backfill_activity(
            db, user_id=1, activity_id=99999,
            fetch_typed_splits=lambda aid: _typed_splits(True),
        )
    assert "não encontrada" in str(exc.value)
    # nada gravado
    assert db.query(Split).count() == 0


def test_backfill_non_running_skipped(db) -> None:
    """Done-when T4: atividade não-running → skipped, sem enriquecer."""
    activity = _seed_activity(db, activity_type="yoga", garmin_id="act_bf_yoga")
    result = backfill_activity(
        db, user_id=1, activity_id=activity.id,
        fetch_typed_splits=lambda aid: _typed_splits(True),
    )
    assert result["skipped"] == "not_running"
    splits = db.query(Split).filter(Split.activity_id == activity.id).all()
    assert all(s.ground_contact_time_ms is None for s in splits)
