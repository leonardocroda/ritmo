"""Testes dos schemas Pydantic do domínio Activity."""

import pytest
from datetime import datetime

from app.domain.activity.schemas import (
    SplitOut,
    ZoneMetaOut,
    ConsistencyOut,
    ContextOut,
    ShoeSummaryOut,
    ActivityOut,
    ActivityListItemOut,
    ActivityListOut,
    ActivityDetailOut,
    ShoeAssignmentIn,
)


class TestSplitOut:
    def test_valid_split(self):
        split = SplitOut(
            idx=1,
            dist_m=1000.0,
            duration_s=300.0,
            pace_s=300.0,
            avg_hr=150,
            avg_cadence=180.0,
            avg_temperature=20.0,
            elevation_m=10.0,
            intensity_type="ACTIVE",
            zone="threshold",
            km_label="1,0",
        )
        assert split.idx == 1
        assert split.km_label == "1,0"
        assert split.zone == "threshold"

    def test_optional_fields_none(self):
        split = SplitOut(
            idx=1,
            dist_m=None,
            duration_s=None,
            pace_s=None,
            avg_hr=None,
            avg_cadence=None,
            avg_temperature=None,
            elevation_m=None,
            intensity_type=None,
            zone=None,
            km_label="1,0",
        )
        assert split.dist_m is None
        assert split.avg_hr is None


class TestZoneMetaOut:
    def test_valid_zone(self):
        zone = ZoneMetaOut(
            key="threshold",
            label="Limiar",
            pace_range="4:30-5:00/km",
            color="#f97316",
        )
        assert zone.key == "threshold"
        assert zone.color == "#f97316"


class TestConsistencyOut:
    def test_full_consistency(self):
        c = ConsistencyOut(
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
        assert c.balance_delta_s == 10.0
        assert c.cadence_fade_spm == -2.0

    def test_partial_consistency(self):
        c = ConsistencyOut(
            first_half_pace_s=300.0,
            second_half_pace_s=None,
            balance_delta_s=None,
            balance_delta_pct=None,
            first_half_hr=None,
            second_half_hr=None,
            hr_drift_bpm=None,
            decoupling_pct=None,
        )
        assert c.first_half_pace_s == 300.0
        assert c.second_half_pace_s is None


class TestContextOut:
    def test_with_sleep_hrv(self):
        ctx = ContextOut(
            sleep={"duration_s": 28800, "score": 85},
            hrv={"value": 45.0, "status": "balanced"},
            rhr={"value": 52},
            temperature_c=18.5,
        )
        assert ctx.sleep is not None
        assert ctx.sleep["score"] == 85
        assert ctx.temperature_c == 18.5

    def test_empty_context(self):
        ctx = ContextOut()
        assert ctx.sleep is None
        assert ctx.hrv is None
        assert ctx.rhr is None


class TestShoeSummaryOut:
    def test_with_brand_model(self):
        shoe = ShoeSummaryOut(
            id=1,
            name="Nike ZoomX",
            brand="Nike",
            model="ZoomX Vaporfly",
            status="ativo",
        )
        assert shoe.brand == "Nike"
        assert shoe.model == "ZoomX Vaporfly"

    def test_minimal(self):
        shoe = ShoeSummaryOut(
            id=1,
            name="Generic",
            status="aposentado",
        )
        assert shoe.brand is None
        assert shoe.model is None


class TestActivityOut:
    def test_full_activity(self):
        act = ActivityOut(
            id=1,
            start_time=datetime.now(),
            activity_type="running",
            name="Morning Run",
            distance_m=10000.0,
            duration_s=3000.0,
            pace_s=300.0,
            avg_hr=150,
            max_hr=165,
            avg_cadence=180.0,
            elevation_gain_m=50.0,
            aerobic_te=100.0,
            anaerobic_te=10.0,
            training_load=50.0,
            evaluated=True,
            inferred_type="facil",
            structure="Corrida 10,0km",
        )
        assert act.inferred_type == "facil"
        assert act.evaluated is True


class TestActivityListItemOut:
    def test_list_item(self):
        item = ActivityListItemOut(
            id=1,
            start_time=datetime.now(),
            activity_type="running",
            name="Run",
            distance_m=5000.0,
            duration_s=1500.0,
            pace_s=300.0,
            avg_hr=150,
            inferred_type="facil",
            evaluated=False,
        )
        assert item.distance_m == 5000.0
        assert item.evaluated is False


class TestActivityListOut:
    def test_paginated_list(self):
        items = [
            ActivityListItemOut(
                id=i,
                start_time=datetime.now(),
                activity_type="running",
                name=f"Run {i}",
                distance_m=5000.0,
                duration_s=1500.0,
                pace_s=300.0,
                avg_hr=150,
                inferred_type="facil",
                evaluated=False,
            )
            for i in range(3)
        ]
        lst = ActivityListOut(items=items, total=100, limit=3, offset=0)
        assert len(lst.items) == 3
        assert lst.total == 100
        assert lst.limit == 3
        assert lst.offset == 0


class TestActivityDetailOut:
    def test_detail_with_splits(self):
        detail = ActivityDetailOut(
            activity=ActivityOut(
                id=1,
                start_time=datetime.now(),
                activity_type="running",
                name="Test",
                distance_m=10000.0,
                duration_s=3000.0,
                pace_s=300.0,
                avg_hr=150,
                max_hr=165,
                avg_cadence=180.0,
                evaluated=True,
            ),
            splits=[
                SplitOut(
                    idx=1,
                    dist_m=2000.0,
                    duration_s=600.0,
                    pace_s=300.0,
                    avg_hr=150,
                    avg_cadence=180.0,
                    avg_temperature=20.0,
                    elevation_m=10.0,
                    intensity_type="ACTIVE",
                    km_label="1,0",
                    zone="threshold",
                )
            ],
            zones=[
                ZoneMetaOut(key="easy", label="Easy", pace_range="5:30+/km", color="#22c55e"),
                ZoneMetaOut(key="threshold", label="Limiar", pace_range="4:30-5:00/km", color="#f97316"),
            ],
            hr_color="#f8fafc",
            consistency=ConsistencyOut(
                first_half_pace_s=300.0,
                second_half_pace_s=310.0,
                balance_delta_s=10.0,
                balance_delta_pct=3.3,
                first_half_hr=150.0,
                second_half_hr=155.0,
                hr_drift_bpm=5.0,
                decoupling_pct=2.5,
            ),
            context=ContextOut(),
            evaluations=[],
            shoe=ShoeSummaryOut(id=1, name="Shoe", status="ativo"),
        )
        assert len(detail.splits) == 1
        assert len(detail.zones) == 2
        assert detail.shoe is not None


class TestShoeAssignmentIn:
    def test_assign_shoe(self):
        payload = ShoeAssignmentIn(shoe_id=1)
        assert payload.shoe_id == 1

    def test_unassign_shoe(self):
        payload = ShoeAssignmentIn(shoe_id=None)
        assert payload.shoe_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])