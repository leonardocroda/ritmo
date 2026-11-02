"""Testes do Router da API de domínio Activities."""

import pytest
from unittest.mock import Mock
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.auth.deps import require_session
from app.db.models import User
from app.domain.activity.service import ActivityService
from app.domain.activity.schemas import (
    ActivityListOut,
    ActivityDetailOut,
    ActivityListItemOut,
    ActivityOut,
    ZoneMetaOut,
    ConsistencyOut,
    ContextOut,
)
from app.domain.activity.router import router
from app.domain.activity.dependencies import get_activity_service
from app.domain.activity.service import ActivityService
from app.domain.activity.domain.value_objects import ActivityFilter


# App de teste
test_app = FastAPI()
test_app.include_router(router)


def override_require_session():
    return User(id=1, display_name="Test User", email="test@example.com")


# Mock service singleton para persistir configuração entre chamadas
_mock_service = Mock(spec=ActivityService)


def create_mock_service():
    return _mock_service


test_app.dependency_overrides[require_session] = override_require_session
test_app.dependency_overrides[get_activity_service] = create_mock_service

client = TestClient(test_app)


class TestActivitiesRouter:
    def setup_method(self):
        # Reset mock before each test
        _mock_service.reset_mock()

    def test_list_activities(self):
        _mock_service.list.return_value = ActivityListOut(
            items=[
                ActivityListItemOut(
                    id=1,
                    start_time=datetime.now(),
                    activity_type="running",
                    name="Morning Run",
                    distance_m=10000.0,
                    duration_s=3000.0,
                    pace_s=300.0,
                    avg_hr=150,
                    inferred_type="facil",
                    evaluated=False,
                )
            ],
            total=1,
            limit=30,
            offset=0,
        )

        response = client.get("/api/v1/activities")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == 1

    def test_list_activities_params(self):
        _mock_service.list.return_value = ActivityListOut(items=[], total=0, limit=10, offset=5)

        response = client.get("/api/v1/activities?activity_type=all&limit=10&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5

    def test_list_activities_invalid_limit(self):
        response = client.get("/api/v1/activities?limit=0")
        assert response.status_code == 422

        response = client.get("/api/v1/activities?limit=101")
        assert response.status_code == 422

    def test_get_activity_found(self):
        detail = ActivityDetailOut(
            activity=ActivityOut(
                id=1,
                start_time=datetime.now(),
                activity_type="running",
                name="Test Run",
                distance_m=10000.0,
                duration_s=3000.0,
                pace_s=300.0,
                avg_hr=150,
                max_hr=165,
                avg_cadence=180.0,
                elevation_gain_m=50.0,
                evaluated=True,
                inferred_type="facil",
                structure="Corrida 10,0km",
            ),
            splits=[],
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
            shoe=None,
        )
        _mock_service.get_detail.return_value = detail

        response = client.get("/api/v1/activities/1")
        assert response.status_code == 200
        data = response.json()
        assert data["activity"]["id"] == 1
        assert data["activity"]["distance_m"] == 10000.0

    def test_get_activity_not_found(self):
        _mock_service.get_detail.return_value = None

        response = client.get("/api/v1/activities/999")
        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"]

    def test_get_activity_invalid_id(self):
        # ID 0 não existe -> 404 (service não encontra)
        response = client.get("/api/v1/activities/0")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])