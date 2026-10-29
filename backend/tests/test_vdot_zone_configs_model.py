"""Modelos das zonas VDOT (T3, feature pace-zones) — integração no Postgres.

Uma linha vigente por usuário (upsert na recalibração). Índice composto em
(user_id, valid_from). JSONB para zones e equivalencias. FK para users.
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.security import hash_password
from app.db.engine import SessionLocal, init_db
from app.db.models import VdotZoneConfig, User


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _new_user(db) -> User:
    """Usuário de teste próprio (id via sequência — não interfere no seed)."""
    user = User(
        display_name="Corredora",
        email="corredora@example.com",
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(user)
    db.flush()
    return user


def test_vdot_zone_config_instantiation_and_persist(db) -> None:
    """Model instantiation with all fields persists correctly."""
    user = _new_user(db)
    zones = {
        "easy": {"pace_range": "5:51/km-4:53/km", "ms_min": 2.851, "ms_max": 3.418, "description": "Recuperação"},
        "marathon": {"pace": "4:30/km", "ms": 3.701, "description": "Ritmo de maratona"},
        "threshold": {"pace_range": "4:14/km-4:27/km", "ms_min": 3.749, "ms_max": 3.931, "description": "Limiar"},
        "interval": {"pace_range": "3:59/km-3:49/km", "ms_min": 4.183, "ms_max": 4.36, "description": "Intervalado"},
        "repetition": {"pace": "3:40/km", "ms": 4.536, "description": "Repetição"},
    }
    equivalencias = {
        "5K": "3:58/km",
        "10K": "4:07/km",
        "Meia Maratona": "4:19/km",
        "Maratona": "4:30/km",
    }

    config = VdotZoneConfig(
        user_id=user.id,
        vdot=50.2,
        source="10K em 41:15",
        test_date=date(2026, 10, 3),
        distance_m=10012.0,
        time_s=2475.0,
        zones=zones,
        equivalencias=equivalencias,
        valid_from=date(2026, 10, 3),
    )
    db.add(config)
    db.commit()

    # Reload and verify
    reloaded = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user.id).first()
    assert reloaded is not None
    assert reloaded.vdot == 50.2
    assert reloaded.source == "10K em 41:15"
    assert reloaded.test_date == date(2026, 10, 3)
    assert reloaded.distance_m == 10012.0
    assert reloaded.time_s == 2475.0
    assert reloaded.zones == zones
    assert reloaded.equivalencias == equivalencias
    assert reloaded.valid_from == date(2026, 10, 3)
    assert reloaded.created_at is not None


def test_vdot_zone_config_fk_to_user(db) -> None:
    """FK to users table works correctly."""
    user = _new_user(db)
    config = VdotZoneConfig(
        user_id=user.id,
        vdot=50.2,
        source="test",
        test_date=date(2026, 10, 3),
        distance_m=10000.0,
        time_s=2400.0,
        zones={"easy": {"description": "test"}},
        equivalencias={"5K": "4:00/km"},
        valid_from=date(2026, 10, 3),
    )
    db.add(config)
    db.commit()

    # Verify FK relationship
    reloaded = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user.id).first()
    assert reloaded.user_id == user.id


def test_vdot_zone_config_jsonb_fields(db) -> None:
    """JSONB fields accept dict and persist correctly."""
    user = _new_user(db)
    zones = {"easy": {"pace_range": "5:00/km-4:30/km", "description": "Easy"}}
    equivalencias = {"5K": "4:00/km", "10K": "4:10/km"}

    config = VdotZoneConfig(
        user_id=user.id,
        vdot=45.0,
        source="test",
        test_date=date(2026, 10, 3),
        distance_m=10000.0,
        time_s=2400.0,
        zones=zones,
        equivalencias=equivalencias,
        valid_from=date(2026, 10, 3),
    )
    db.add(config)
    db.commit()

    reloaded = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user.id).first()
    assert isinstance(reloaded.zones, dict)
    assert isinstance(reloaded.equivalencias, dict)
    assert reloaded.zones == zones
    assert reloaded.equivalencias == equivalencias


def test_vdot_zone_config_index_exists(db) -> None:
    """Index on (user_id, valid_from) exists."""
    # This test verifies the index exists by checking the table metadata
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    indexes = inspector.get_indexes("vdot_zone_configs")
    index_names = [idx["name"] for idx in indexes]
    assert "ix_vdotzoneconfigs_user_valid_from" in index_names


def test_vdot_zone_config_valid_from_date(db) -> None:
    """valid_from field stores date correctly."""
    user = _new_user(db)
    test_date = date(2026, 10, 3)

    config = VdotZoneConfig(
        user_id=user.id,
        vdot=50.2,
        source="test",
        test_date=test_date,
        distance_m=10012.0,
        time_s=2475.0,
        zones={"easy": {"description": "test"}},
        equivalencias={"5K": "4:00/km"},
        valid_from=test_date,
    )
    db.add(config)
    db.commit()

    reloaded = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user.id).first()
    assert reloaded.valid_from == test_date
    assert isinstance(reloaded.valid_from, date)


def test_vdot_zone_config_upsert_pattern(db) -> None:
    """Two configs for same user on different dates - both allowed (append-only)."""
    user = _new_user(db)

    # First calibration
    config1 = VdotZoneConfig(
        user_id=user.id,
        vdot=50.0,
        source="10K 40:00",
        test_date=date(2026, 10, 1),
        distance_m=10000.0,
        time_s=2400.0,
        zones={"easy": {"description": "v1"}},
        equivalencias={"5K": "4:00/km"},
        valid_from=date(2026, 10, 1),
    )
    db.add(config1)
    db.commit()

    # Second calibration (new valid_from)
    config2 = VdotZoneConfig(
        user_id=user.id,
        vdot=51.0,
        source="5K 18:30",
        test_date=date(2026, 10, 15),
        distance_m=5000.0,
        time_s=1110.0,
        zones={"easy": {"description": "v2"}},
        equivalencias={"5K": "3:55/km"},
        valid_from=date(2026, 10, 15),
    )
    db.add(config2)
    db.commit()

    # Both should exist
    configs = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user.id).all()
    assert len(configs) == 2
    vdots = {c.vdot for c in configs}
    assert vdots == {50.0, 51.0}


def test_vdot_zone_config_cascade_delete_user(db) -> None:
    """Deleting user cascades to vdot_zone_configs."""
    user = _new_user(db)
    config = VdotZoneConfig(
        user_id=user.id,
        vdot=50.2,
        source="test",
        test_date=date(2026, 10, 3),
        distance_m=10012.0,
        time_s=2475.0,
        zones={"easy": {"description": "test"}},
        equivalencias={"5K": "4:00/km"},
        valid_from=date(2026, 10, 3),
    )
    db.add(config)
    db.commit()

    # Delete user
    db.delete(user)
    db.commit()

    # Config should be gone
    count = db.query(VdotZoneConfig).filter(VdotZoneConfig.user_id == user.id).count()
    assert count == 0