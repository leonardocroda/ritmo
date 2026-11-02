"""Testes dos providers de DI (FastAPI Depends) do domínio Activities."""

import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from app.domain.activity.dependencies import (
    get_activity_repo,
    get_split_repo,
    get_zone_provider,
    get_consistency,
    get_activity_service,
)
from app.domain.activity.ports.repositories import ActivityRepository, SplitRepository
from app.domain.activity.ports.zone_config import ZoneConfigProvider
from app.domain.activity.domain.services import ConsistencyCalculator
from app.domain.activity.service import ActivityService


class TestDIProviders:
    def test_get_activity_repo(self):
        mock_db = Mock(spec=Session)
        repo = get_activity_repo(mock_db)

        assert isinstance(repo, ActivityRepository)

    def test_get_split_repo(self):
        mock_db = Mock(spec=Session)
        repo = get_split_repo(mock_db)

        assert isinstance(repo, SplitRepository)

    def test_get_zone_provider(self):
        mock_db = Mock(spec=Session)
        provider = get_zone_provider(mock_db)

        assert isinstance(provider, ZoneConfigProvider)

    def test_get_consistency(self):
        calc = get_consistency()

        assert isinstance(calc, ConsistencyCalculator)

    def test_get_activity_service(self):
        mock_repo = Mock(spec=ActivityRepository)
        mock_split_repo = Mock(spec=SplitRepository)
        mock_zone_provider = Mock(spec=ZoneConfigProvider)
        mock_consistency = Mock(spec=ConsistencyCalculator)

        service = get_activity_service(
            repo=mock_repo,
            split_repo=mock_split_repo,
            zone_provider=mock_zone_provider,
            consistency=mock_consistency,
        )

        assert isinstance(service, ActivityService)
        assert service.repo is mock_repo
        assert service.split_repo is mock_split_repo
        assert service.zone_provider is mock_zone_provider
        assert service.consistency is mock_consistency


if __name__ == "__main__":
    pytest.main([__file__, "-v"])