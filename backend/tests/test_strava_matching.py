"""Testes unit do matching Strava↔Garmin (T5) — funções puras.

Cobre: garmin_id_from_external_id regex, find_match fallback ±2%/±2%/5h,
ambiguous/none, distância 0 não casa.
"""

from datetime import datetime

import pytest

from app.strava.matching import find_match, garmin_id_from_external_id


class TestGarminIdFromExternalId:
    """Testes para garmin_id_from_external_id."""

    def test_matches_garmin_push_format(self) -> None:
        """Done-when T5: casa garmin_push_<id> e devolve o id como string."""
        assert garmin_id_from_external_id("garmin_push_1234567890") == "1234567890"
        assert garmin_id_from_external_id("garmin_push_1") == "1"
        assert garmin_id_from_external_id("garmin_push_9999999999999") == "9999999999999"

    def test_returns_none_for_other_formats(self) -> None:
        """Done-when T5: None para outros formatos/ausente."""
        assert garmin_id_from_external_id("strava_activity_123") is None
        assert garmin_id_from_external_id("manual_123") is None
        assert garmin_id_from_external_id("") is None
        assert garmin_id_from_external_id(None) is None
        assert garmin_id_from_external_id("garmin_push_") is None
        assert garmin_id_from_external_id("garmin_push_abc") is None


class TestFindMatch:
    """Testes para find_match."""

    def _make_candidate(
        self, id: int, distance_m: float, duration_s: float, start_time: datetime
    ) -> dict:
        return {"id": id, "distance_m": distance_m, "duration_s": duration_s, "start_time": start_time}

    def _make_strava(self, distance: float, moving_time: int, start_date: str) -> dict:
        return {"distance": distance, "moving_time": moving_time, "start_date": start_date}

    def test_exact_match_within_tolerance(self) -> None:
        """Done-when T5: casa dentro das tolerâncias (±2%, ±2%, 5h)."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [
            self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),  # exato
            self._make_candidate(2, 10000.0, 3600, datetime(2024, 1, 14, 8, 0)),  # fora
        ]
        result = find_match(strava, candidates)
        assert result == 1

    def test_match_within_2pct_distance(self) -> None:
        """Done-when T5: distância dentro de ±2% casa."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        # 2% de 5000 = 100m → 4900 a 5100
        candidates = [self._make_candidate(1, 4950.0, 1800, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result == 1

    def test_match_outside_2pct_distance_fails(self) -> None:
        """Done-when T5: distância fora de ±2% não casa."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        # 2.1% = 5105m → fora
        candidates = [self._make_candidate(1, 5105.0, 1800, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_match_within_2pct_time(self) -> None:
        """Done-when T5: tempo dentro de ±2% casa."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        # 2% de 1800 = 36s → 1764 a 1836
        candidates = [self._make_candidate(1, 5000.0, 1830, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result == 1

    def test_match_outside_2pct_time_fails(self) -> None:
        """Done-when T5: tempo fora de ±2% não casa."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        # 2.1% = 1838s → fora
        candidates = [self._make_candidate(1, 5000.0, 1838, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_match_within_5h_window(self) -> None:
        """Done-when T5: diferença de start ≤ 5h casa (cobre fuso)."""
        # Strava: 07:00 GMT = 04:00 local (fuso -3)
        # Garmin: 04:00 wall clock local → diff = 3h
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 4, 0))]
        result = find_match(strava, candidates)
        assert result == 1

    def test_match_outside_5h_window_fails(self) -> None:
        """Done-when T5: diferença de start > 5h não casa."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        # 6h de diferença
        candidates = [self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 13, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_zero_distance_no_match(self) -> None:
        """Done-when T5: distância 0 (esteira sem GPS) não casa por distância."""
        strava = self._make_strava(0.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_zero_time_no_match(self) -> None:
        """Done-when T5: tempo 0 não casa."""
        strava = self._make_strava(5000.0, 0, "2024-01-15T07:00:00Z")
        candidates = [self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_no_candidates_returns_none(self) -> None:
        """Done-when T5: 0 candidatos → None."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        result = find_match(strava, [])
        assert result is None

    def test_single_candidate_outside_tolerance_returns_none(self) -> None:
        """Done-when T5: 1 candidato fora da tolerância → None."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [self._make_candidate(1, 10000.0, 3600, datetime(2024, 1, 14, 8, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_two_candidates_ambiguous(self) -> None:
        """Done-when T5: 2+ candidatos dentro → 'ambiguous' (nunca casa)."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [
            self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),
            self._make_candidate(2, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),
        ]
        result = find_match(strava, candidates)
        assert result == "ambiguous"

    def test_three_candidates_ambiguous(self) -> None:
        """Done-when T5: 3 candidatos dentro → 'ambiguous'."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [
            self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),
            self._make_candidate(2, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),
            self._make_candidate(3, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),
        ]
        result = find_match(strava, candidates)
        assert result == "ambiguous"

    def test_candidate_missing_fields_skipped(self) -> None:
        """Done-when T5: candidatos com campos ausentes são ignorados."""
        strava = self._make_strava(5000.0, 1800, "2024-01-15T07:00:00Z")
        candidates = [
            {"id": 1, "distance_m": 5000.0},  # sem duration_s, start_time
            self._make_candidate(2, 5000.0, 1800, datetime(2024, 1, 15, 7, 0)),
        ]
        result = find_match(strava, candidates)
        assert result == 2

    def test_invalid_start_date_format_skipped(self) -> None:
        """Done-when T5: start_date inválido no Strava → None."""
        strava = {"distance": 5000.0, "moving_time": 1800, "start_date": "invalid-date"}
        candidates = [self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 15, 7, 0))]
        result = find_match(strava, candidates)
        assert result is None

    def test_timezone_cross_midnight(self) -> None:
        """Done-when T5: corrida noturna cruzando meia-noite (fuso cobre)."""
        # Strava: 2024-01-15T02:00:00Z (GMT)
        # Garmin local: 2024-01-14 23:00 (fuso -3, dia anterior)
        strava = self._make_strava(5000.0, 1800, "2024-01-15T02:00:00Z")
        candidates = [self._make_candidate(1, 5000.0, 1800, datetime(2024, 1, 14, 23, 0))]
        result = find_match(strava, candidates)
        assert result == 1