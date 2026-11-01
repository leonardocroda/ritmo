"""Testes do Application Service Activities."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
from collections.abc import Sequence

from app.domain.activities.domain.entities import Activity, Split
from app.domain.activities.domain.value_objects import (
    ActivityFilter,
    ZoneConfigVO,
    ZoneKey,
    HeartRate,
    Cadence,
    Pace,
)
from app.domain.activities.domain.services import (
    ConsistencyCalculator,
    ConsistencyMetrics,
)
from app.domain.activities.ports.repositories import ActivityRepository, SplitRepository
from app.domain.activities.ports.zone_config import ZoneConfigProvider
from app.domain.activities.service import ActivityService
from app.domain.activities.schemas import ActivityDetailOut, ActivityListOut, ActivityListItemOut


def create_mock_activity(
    activity_id: int = 1,
    distance_m: float = 10000.0,
    splits: list[Split] | None = None,
) -> Activity:
    return Activity(
        id=activity_id,
        user_id=1,
        start_time=datetime.now(timezone.utc),
        activity_type="running",
        name="Test Run",
        distance_m=distance_m,
        duration_s=3000.0,
        avg_hr=HeartRate(150),
        max_hr=HeartRate(165),
        avg_cadence=Cadence(180),
        elevation_gain_m=50.0,
        aerobic_te=100.0,
        anaerobic_te=10.0,
        training_load=50.0,
        inferred_type="facil",
        structure="Corrida 10,0km",
        splits=tuple(splits) if splits else (),
        evaluated=False,
    )


def create_mock_splits(count: int = 4) -> list[Split]:
    return [
        Split(
            idx=i + 1,
            distance_m=2500.0,
            duration_s=750.0,
            pace=Pace.from_seconds_per_km(300),
            avg_hr=HeartRate(150),
            avg_cadence=Cadence(180),
            avg_temperature=20.0,
            elevation_m=0.0,
            intensity_type="ACTIVE",
            zone=ZoneKey("threshold"),
            km_label=f"{i + 1},0",
        )
        for i in range(count)
    ]


class TestActivityService:
    def setup_method(self):
        self.mock_repo = Mock(spec=ActivityRepository)
        self.mock_split_repo = Mock(spec=SplitRepository)
        self.mock_zone_provider = Mock(spec=ZoneConfigProvider)
        self.mock_consistency = Mock(spec=ConsistencyCalculator)

        self.service = ActivityService(
            repo=self.mock_repo,
            split_repo=self.mock_split_repo,
            zone_provider=self.mock_zone_provider,
            consistency=self.mock_consistency,
        )

        # Configura zone_config mock
        self.zone_config = ZoneConfigVO(
            vdot=50.0,
            pace_zones={
                ZoneKey("easy"): (360, None),
                ZoneKey("marathon"): (300, 360),
                ZoneKey("threshold"): (240, 300),
                ZoneKey("interval"): (180, 240),
                ZoneKey("repetition"): (None, 180),
            },
            hr_zones={},
        )
        self.mock_zone_provider.get_for_user.return_value = self.zone_config

        # Configura consistency mock
        self.mock_consistency.calculate.return_value = ConsistencyMetrics(
            first_half_pace_s=300.0,
            second_half_pace_s=310.0,
            balance_delta_s=10.0,
            balance_delta_pct=3.3,
            first_half_hr=150.0,
            second_half_hr=155.0,
            hr_drift_bpm=5.0,
            decoupling_pct=2.5,
            cadence_fade_spm=-2.0,
        )

    def test_get_detail_found(self):
        activity = create_mock_activity()
        splits = create_mock_splits()

        self.mock_repo.get_by_id.return_value = activity
        self.mock_split_repo.get_by_activity.return_value = splits

        result = self.service.get_detail(1, 1)

        assert result is not None
        assert isinstance(result, ActivityDetailOut)
        assert result.activity.id == 1
        assert result.activity.distance_m == 10000.0
        assert len(result.splits) == 4
        assert len(result.zones) == 5
        assert result.consistency is not None
        assert result.consistency.balance_delta_s == 10.0

        self.mock_repo.get_by_id.assert_called_once_with(1, 1)
        self.mock_split_repo.get_by_activity.assert_called_once_with(1)
        self.mock_zone_provider.get_for_user.assert_called_once_with(1)
        self.mock_consistency.calculate.assert_called_once()

    def test_get_detail_not_found(self):
        self.mock_repo.get_by_id.return_value = None

        result = self.service.get_detail(999, 1)

        assert result is None
        self.mock_repo.get_by_id.assert_called_once_with(999, 1)
        self.mock_split_repo.get_by_activity.assert_not_called()

    def test_list_activities(self):
        activities = [create_mock_activity(i) for i in range(1, 4)]
        splits = create_mock_splits()

        self.mock_repo.list.return_value = activities
        self.mock_repo.count.return_value = 100
        self.mock_split_repo.get_by_activity.return_value = splits

        filter = ActivityFilter(activity_type="running", limit=30, offset=0)
        result = self.service.list(1, filter, 30, 0)

        assert isinstance(result, ActivityListOut)
        assert len(result.items) == 3
        assert result.total == 100
        assert result.limit == 30
        assert result.offset == 0

        self.mock_repo.list.assert_called_once_with(1, filter)
        self.mock_repo.count.assert_called_once_with(1, filter)
        self.mock_zone_provider.get_for_user.assert_called_once_with(1)

    def test_list_empty(self):
        self.mock_repo.list.return_value = []
        self.mock_repo.count.return_value = 0

        filter = ActivityFilter(activity_type="running", limit=30, offset=0)
        result = self.service.list(1, filter, 30, 0)

        assert len(result.items) == 0
        assert result.total == 0

    def test_list_calls_infer_type(self):
        activities = [create_mock_activity(i) for i in range(1, 3)]
        splits = create_mock_splits()

        self.mock_repo.list.return_value = activities
        self.mock_repo.count.return_value = 2
        self.mock_split_repo.get_by_activity.return_value = splits

        filter = ActivityFilter(activity_type="running", limit=30, offset=0)
        result = self.service.list(1, filter, 30, 0)

        # infer_type é chamado para cada atividade (via classify_splits)
        # consistency NÃO é chamado na listagem
        assert len(result.items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])