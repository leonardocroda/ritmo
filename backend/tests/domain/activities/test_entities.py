"""Testes das entidades e value objects do domínio Activities."""

import pytest
from datetime import datetime

from app.domain.activities.domain.value_objects import (
    Pace,
    HeartRate,
    Cadence,
    ZoneKey,
    ZoneConfigVO,
    ActivityFilter,
)
from app.domain.activities.domain.entities import (
    RunningDynamics,
    Split,
    Activity,
)


class TestPace:
    def test_from_seconds_per_km(self):
        p = Pace.from_seconds_per_km(330)
        assert p.seconds_per_km == 330
        assert p.format_min_km() == "5:30"

    def test_from_seconds_per_meter(self):
        p = Pace.from_seconds_per_meter(0.33)  # 330 s/km = 0.33 s/m
        assert p.seconds_per_km == 330

    def test_format_various(self):
        assert Pace.from_seconds_per_km(180).format_min_km() == "3:00"
        assert Pace.from_seconds_per_km(420).format_min_km() == "7:00"
        assert Pace.from_seconds_per_km(3661).format_min_km() == "61:01"

    def test_comparison(self):
        assert Pace.from_seconds_per_km(300) < Pace.from_seconds_per_km(330)
        assert Pace.from_seconds_per_km(330) <= Pace.from_seconds_per_km(330)

    def test_float_conversion(self):
        p = Pace.from_seconds_per_km(330)
        assert float(p) == 330.0


class TestHeartRate:
    def test_creation(self):
        hr = HeartRate(150)
        assert hr.bpm == 150
        assert int(hr) == 150

    def test_comparison(self):
        assert HeartRate(140) < HeartRate(150)


class TestCadence:
    def test_creation(self):
        c = Cadence(180)
        assert c.spm == 180
        assert int(c) == 180


class TestZoneKey:
    def test_valid_zones(self):
        for zone in ["easy", "marathon", "threshold", "interval", "repetition"]:
            z = ZoneKey(zone)
            assert z == zone

    def test_invalid_zone_raises(self):
        with pytest.raises(ValueError):
            ZoneKey("invalid")


class TestZoneConfigVO:
    def test_classify_pace(self):
        config = ZoneConfigVO(
            vdot=50.0,
            pace_zones={
                ZoneKey("easy"): (360, None),      # >= 360 s/km (slower)
                ZoneKey("marathon"): (300, 360),   # 300-360
                ZoneKey("threshold"): (240, 300),  # 240-300
                ZoneKey("interval"): (180, 240),   # 180-240
                ZoneKey("repetition"): (None, 180), # <= 180 (faster)
            },
            hr_zones={},
        )
        assert config.classify_pace(400) == ZoneKey("easy")
        assert config.classify_pace(330) == ZoneKey("marathon")
        assert config.classify_pace(270) == ZoneKey("threshold")
        assert config.classify_pace(210) == ZoneKey("interval")
        assert config.classify_pace(150) == ZoneKey("repetition")
        assert config.classify_pace(None) is None


class TestActivityFilter:
    def test_defaults(self):
        f = ActivityFilter()
        assert f.activity_type == "running"
        assert f.limit == 30
        assert f.offset == 0

    def test_custom_values(self):
        f = ActivityFilter(activity_type="all", limit=50, offset=10)
        assert f.activity_type == "all"
        assert f.limit == 50
        assert f.offset == 10

    def test_invalid_activity_type(self):
        with pytest.raises(ValueError):
            ActivityFilter(activity_type="invalid")

    def test_invalid_limit(self):
        with pytest.raises(ValueError):
            ActivityFilter(limit=0)
        with pytest.raises(ValueError):
            ActivityFilter(limit=101)

    def test_invalid_offset(self):
        with pytest.raises(ValueError):
            ActivityFilter(offset=-1)


class TestRunningDynamics:
    def test_creation(self):
        rd = RunningDynamics(gct_ms=250, stride_cm=110.5, vert_osc_cm=8.0, vert_ratio=5.5)
        assert rd.gct_ms == 250
        assert rd.stride_cm == 110.5
        assert rd.vert_osc_cm == 8.0
        assert rd.vert_ratio == 5.5

    def test_defaults(self):
        rd = RunningDynamics()
        assert rd.gct_ms is None
        assert rd.stride_cm is None
        assert rd.vert_osc_cm is None
        assert rd.vert_ratio is None


class TestSplit:
    def test_creation(self):
        split = Split(
            idx=1,
            distance_m=1000.0,
            duration_s=330.0,
            pace=Pace.from_seconds_per_km(330),
            avg_hr=HeartRate(150),
            avg_cadence=Cadence(180),
            avg_temperature=22.5,
            elevation_m=10.0,
            intensity_type="ACTIVE",
            zone=ZoneKey("threshold"),
            km_label="1,0",
        )
        assert split.idx == 1
        assert split.distance_m == 1000.0
        assert split.pace.seconds_per_km == 330
        assert split.avg_hr.bpm == 150
        assert split.avg_cadence.spm == 180
        assert split.zone == ZoneKey("threshold")
        assert split.km_label == "1,0"

    def test_pace_s_property(self):
        split = Split(
            idx=1,
            distance_m=1000.0,
            duration_s=330.0,
            pace=Pace.from_seconds_per_km(330),
            avg_hr=None,
            avg_cadence=None,
            avg_temperature=None,
            elevation_m=None,
            intensity_type=None,
            zone=None,
            km_label="1,0",
        )
        assert split.pace_s == 330.0

    def test_pace_s_none(self):
        split = Split(
            idx=1,
            distance_m=None,
            duration_s=None,
            pace=None,
            avg_hr=None,
            avg_cadence=None,
            avg_temperature=None,
            elevation_m=None,
            intensity_type=None,
            zone=None,
            km_label="1,0",
        )
        assert split.pace_s is None


class TestActivity:
    def test_pace_property(self):
        activity = Activity(
            id=1,
            user_id=1,
            start_time=datetime.now(),
            activity_type="running",
            name="Morning Run",
            distance_m=10000.0,
            duration_s=3000.0,
            avg_hr=HeartRate(150),
            max_hr=HeartRate(165),
            avg_cadence=Cadence(180),
            elevation_gain_m=50.0,
            aerobic_te=100.0,
            anaerobic_te=10.0,
            training_load=50.0,
            inferred_type="facil",
            structure=None,
            splits=(),
            evaluated=False,
        )
        # 10000m in 3000s = 300 s/km = 5:00/km
        assert activity.pace is not None
        assert abs(activity.pace.seconds_per_km - 300.0) < 1.0

    def test_is_running(self):
        run = Activity(
            id=1,
            user_id=1,
            start_time=datetime.now(),
            activity_type="running",
            name=None,
            distance_m=5000.0,
            duration_s=1500.0,
            avg_hr=None,
            max_hr=None,
            avg_cadence=None,
            elevation_gain_m=None,
            aerobic_te=None,
            anaerobic_te=None,
            training_load=None,
            inferred_type=None,
            structure=None,
            splits=(),
            evaluated=False,
        )
        trail = Activity(
            id=2,
            user_id=1,
            start_time=datetime.now(),
            activity_type="trail_running",
            name=None,
            distance_m=5000.0,
            duration_s=1500.0,
            avg_hr=None,
            max_hr=None,
            avg_cadence=None,
            elevation_gain_m=None,
            aerobic_te=None,
            anaerobic_te=None,
            training_load=None,
            inferred_type=None,
            structure=None,
            splits=(),
            evaluated=False,
        )
        swim = Activity(
            id=3,
            user_id=1,
            start_time=datetime.now(),
            activity_type="swimming",
            name=None,
            distance_m=2000.0,
            duration_s=3600.0,
            avg_hr=None,
            max_hr=None,
            avg_cadence=None,
            elevation_gain_m=None,
            aerobic_te=None,
            anaerobic_te=None,
            training_load=None,
            inferred_type=None,
            structure=None,
            splits=(),
            evaluated=False,
        )
        assert run.is_running
        assert trail.is_running
        assert not swim.is_running

    def test_distance_km(self):
        activity = Activity(
            id=1,
            user_id=1,
            start_time=datetime.now(),
            activity_type="running",
            name=None,
            distance_m=10000.0,
            duration_s=3000.0,
            avg_hr=None,
            max_hr=None,
            avg_cadence=None,
            elevation_gain_m=None,
            aerobic_te=None,
            anaerobic_te=None,
            training_load=None,
            inferred_type=None,
            structure=None,
            splits=(),
            evaluated=False,
        )
        assert activity.distance_km == 10.0

    def test_duration_min(self):
        activity = Activity(
            id=1,
            user_id=1,
            start_time=datetime.now(),
            activity_type="running",
            name=None,
            distance_m=5000.0,
            duration_s=1800.0,
            avg_hr=None,
            max_hr=None,
            avg_cadence=None,
            elevation_gain_m=None,
            aerobic_te=None,
            anaerobic_te=None,
            training_load=None,
            inferred_type=None,
            structure=None,
            splits=(),
            evaluated=False,
        )
        assert activity.duration_min == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])