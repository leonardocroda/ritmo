"""Testes de integração dos adaptadores SQLAlchemy (requer PostgreSQL)."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import User, Activity as ActivityModel, Split as SplitModel
from app.domain.activity.adapters.sqlalchemy_repo import SQLAlchemyActivityRepository, SQLAlchemySplitRepository
from app.domain.activity.adapters.db_zone_config import DBZoneConfigProvider
from app.domain.activity.domain.value_objects import ActivityFilter
from app.domain.activity.domain.entities import Activity, Split
from app.domain.activity.domain.value_objects import HeartRate, Cadence, Pace, ZoneKey


# Configuração de banco de teste
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine):
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    # Limpa tabelas entre testes
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


def _unique_email() -> str:
    return f"test_{uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_user(session):
    user = User(display_name="Test User", email=_unique_email())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_activity(session, test_user):
    activity = ActivityModel(
        user_id=test_user.id,
        garmin_id=f"test_{uuid4().hex[:8]}",
        start_time=datetime.now(timezone.utc),
        activity_type="running",
        name="Morning Run",
        distance_m=10000.0,
        duration_s=3000.0,
        avg_hr=150,
        max_hr=165,
        avg_cadence=180.0,
        elevation_gain_m=50.0,
        aerobic_te=100.0,
        anaerobic_te=10.0,
        training_load=50.0,
        evaluated=False,
    )
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return activity


@pytest.fixture
def test_splits(session, test_activity):
    splits = []
    for i in range(5):
        split = SplitModel(
            user_id=test_activity.user_id,
            activity_id=test_activity.id,
            idx=i + 1,
            dist_m=2000.0,
            duration_s=600.0,
            pace_s=300.0,
            avg_hr=150 + i,
            avg_cadence=180.0,
            avg_temperature=20.0,
            elevation_m=0.0,
            intensity_type="ACTIVE",
        )
        splits.append(split)
    session.add_all(splits)
    session.commit()
    return splits


class TestSQLAlchemyActivityRepository:
    def test_get_by_id(self, session, test_user, test_activity):
        repo = SQLAlchemyActivityRepository(session)
        activity = repo.get_by_id(test_activity.id, test_user.id)

        assert activity is not None
        assert activity.id == test_activity.id
        assert activity.user_id == test_user.id
        assert activity.name == "Morning Run"
        assert activity.distance_m == 10000.0

    def test_get_by_id_wrong_user(self, session, test_user, test_activity):
        repo = SQLAlchemyActivityRepository(session)
        # Cria outro usuário
        other_user = User(display_name="Other", email="other@example.com")
        session.add(other_user)
        session.commit()

        activity = repo.get_by_id(test_activity.id, other_user.id)
        assert activity is None

    def test_list_running_only(self, session, test_user, test_activity):
        repo = SQLAlchemyActivityRepository(session)

        # Adiciona atividade não-corrida
        swim = ActivityModel(
            user_id=test_user.id,
            garmin_id="swim_123",
            start_time=datetime.now(timezone.utc),
            activity_type="swimming",
            name="Swim",
            distance_m=2000.0,
            duration_s=3600.0,
        )
        session.add(swim)
        session.commit()

        filter = ActivityFilter(activity_type="running", limit=10, offset=0)
        activities = repo.list(test_user.id, filter)

        assert len(activities) == 1
        assert activities[0].activity_type == "running"

    def test_list_all_types(self, session, test_user, test_activity):
        repo = SQLAlchemyActivityRepository(session)

        # Adiciona atividade não-corrida
        swim = ActivityModel(
            user_id=test_user.id,
            garmin_id="swim_123",
            start_time=datetime.now(timezone.utc),
            activity_type="swimming",
            name="Swim",
            distance_m=2000.0,
            duration_s=3600.0,
        )
        session.add(swim)
        session.commit()

        filter = ActivityFilter(activity_type="all", limit=10, offset=0)
        activities = repo.list(test_user.id, filter)

        assert len(activities) == 2

    def test_count(self, session, test_user, test_activity):
        repo = SQLAlchemyActivityRepository(session)

        filter = ActivityFilter(activity_type="running", limit=10, offset=0)
        count = repo.count(test_user.id, filter)

        assert count == 1


class TestSQLAlchemySplitRepository:
    def test_get_by_activity(self, session, test_user, test_activity, test_splits):
        repo = SQLAlchemySplitRepository(session)
        splits = repo.get_by_activity(test_activity.id)

        assert len(splits) == 5
        assert splits[0].idx == 1
        assert splits[0].distance_m == 2000.0
        assert splits[0].pace is not None
        assert splits[0].avg_hr is not None
        assert splits[0].avg_cadence is not None

    def test_get_by_activity_empty(self, session, test_user):
        repo = SQLAlchemySplitRepository(session)

        activity = ActivityModel(
            user_id=test_user.id,
            garmin_id="empty_123",
            start_time=datetime.now(timezone.utc),
            activity_type="running",
            name="Empty",
            distance_m=5000.0,
            duration_s=1500.0,
        )
        session.add(activity)
        session.commit()

        splits = repo.get_by_activity(activity.id)
        assert len(splits) == 0


class TestDBZoneConfigProvider:
    def test_get_for_user(self, session, test_user):
        # Cria config de zona VDOT com formato correto (ms, ms_min, ms_max)
        from app.db.models import VdotZoneConfig
        vdot_config = VdotZoneConfig(
            user_id=test_user.id,
            vdot=50.0,
            source="test",
            test_date=datetime.now(timezone.utc).date(),
            distance_m=10000.0,
            time_s=3000.0,
            zones={
                "easy": {"ms": 2.5, "ms_min": 2.0, "ms_max": 3.0, "pace_range": "5:30-6:30", "description": "Easy"},
                "marathon": {"ms": 3.5, "ms_min": 3.0, "ms_max": 4.0, "pace_range": "4:30-5:30", "description": "Marathon"},
                "threshold": {"ms": 4.5, "ms_min": 4.0, "ms_max": 5.0, "pace_range": "3:45-4:30", "description": "Threshold"},
                "interval": {"ms": 5.5, "ms_min": 5.0, "ms_max": 6.0, "pace_range": "3:00-3:45", "description": "Interval"},
                "repetition": {"ms": 6.5, "ms_min": 6.0, "ms_max": 7.0, "pace_range": "2:30-3:00", "description": "Repetition"},
            },
            equivalencias={},
            valid_from=datetime.now(timezone.utc).date(),
        )
        session.add(vdot_config)
        session.commit()

        provider = DBZoneConfigProvider(session)
        config = provider.get_for_user(test_user.id)

        assert config is not None
        assert config.vdot == 50.0
        assert ZoneKey("easy") in config.pace_zones
        assert ZoneKey("threshold") in config.pace_zones

    def test_invalidate_cache(self, session, test_user):
        from app.db.models import VdotZoneConfig
        vdot_config = VdotZoneConfig(
            user_id=test_user.id,
            vdot=50.0,
            source="test",
            test_date=datetime.now(timezone.utc).date(),
            distance_m=10000.0,
            time_s=3000.0,
            zones={
                "easy": {"ms": 2.5, "ms_min": 2.0, "ms_max": 3.0, "pace_range": "5:30-6:30"},
                "marathon": {"ms": 3.5, "ms_min": 3.0, "ms_max": 4.0, "pace_range": "4:30-5:30"},
                "threshold": {"ms": 4.5, "ms_min": 4.0, "ms_max": 5.0, "pace_range": "3:45-4:30"},
                "interval": {"ms": 5.5, "ms_min": 5.0, "ms_max": 6.0, "pace_range": "3:00-3:45"},
                "repetition": {"ms": 6.5, "ms_min": 6.0, "ms_max": 7.0, "pace_range": "2:30-3:00"},
            },
            equivalencias={},
            valid_from=datetime.now(timezone.utc).date(),
        )
        session.add(vdot_config)
        session.commit()

        provider = DBZoneConfigProvider(session)
        config1 = provider.get_for_user(test_user.id)
        provider.invalidate_cache(test_user.id)
        config2 = provider.get_for_user(test_user.id)

        # Deve ser o mesmo objeto (cache invalidado mas recarregado)
        assert config2 is not None
        assert config2.vdot == 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])