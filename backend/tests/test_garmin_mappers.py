"""Mappers puros — JSON do Garmin em dicts prontos para o ORM.

Cenários derivados do spec (SYNC-11/12/16/18/19) e dos done-when de
T5; os valores afirmados são literais das fixtures de payload, nunca
constantes compartilhadas com o módulo implementado (lição L-001).
"""

import warnings
from datetime import date, datetime

from helpers import (
    BATTERY_ROWS,
    CYCLING_ACTIVITY_PAYLOAD,
    GARMIN_ACTIVITY_PAYLOAD,
    HRV_NO_DATA_PAYLOAD,
    HRV_PAYLOAD,
    PERSONAL_RECORDS_PAYLOAD,
    PERSONAL_RECORDS_WRAPPER,
    RHR_NO_DATA_PAYLOAD,
    RHR_PAYLOAD,
    SLEEP_PAYLOAD,
    SPARSE_ACTIVITY_PAYLOAD,
    SPLITS_LAPDTOS_PAYLOAD,
    SPLITS_LIST_PAYLOAD,
    STRESS_NO_DATA_PAYLOAD,
    STRESS_PAYLOAD,
    TRAIL_ACTIVITY_PAYLOAD,
    YOGA_ACTIVITY_PAYLOAD,
)
from app.garmin.mappers import (
    is_running,
    map_activity,
    map_battery,
    map_hrv,
    map_personal_records,
    map_rhr,
    map_sleep,
    map_splits,
    map_stress,
)


def test_map_activity_all_fields() -> None:
    """SYNC-11: todos os campos de Activity + raw_json preservado."""
    row = map_activity(GARMIN_ACTIVITY_PAYLOAD)
    assert row["garmin_id"] == "12345678901"
    assert row["start_time"] == datetime(2024, 1, 15, 7, 0)
    assert row["activity_type"] == "running"
    assert row["name"] == "Morning Run"
    assert row["distance_m"] == 5000.0
    assert row["duration_s"] == 1800.0
    assert row["avg_hr"] == 145
    assert row["max_hr"] == 165
    assert row["avg_cadence"] == 170.0
    assert row["power"] == 210.0
    assert row["elevation_gain_m"] == 55.0
    assert row["aerobic_te"] == 2.8
    assert row["anaerobic_te"] == 0.4
    assert row["training_load"] == 120.0
    assert row["raw_json"] == GARMIN_ACTIVITY_PAYLOAD


def test_map_activity_sparse_payload_preserves_raw_json() -> None:
    """Sem campos opcionais → None; raw_json sempre preservado (spec).

    training_load ausente → None: a decisão de carga 0 é do PMC
    (SYNC-24), o mapper só entrega o que existe.
    """
    row = map_activity(SPARSE_ACTIVITY_PAYLOAD)
    assert row["training_load"] is None
    assert row["power"] is None
    assert row["aerobic_te"] is None
    assert row["raw_json"] == SPARSE_ACTIVITY_PAYLOAD


def test_is_running_accepts_running_and_trail() -> None:
    """SYNC-12: splits só para corrida — running e trail_running."""
    assert is_running(GARMIN_ACTIVITY_PAYLOAD) is True
    assert is_running(TRAIL_ACTIVITY_PAYLOAD) is True


def test_is_running_rejects_other_types() -> None:
    assert is_running(CYCLING_ACTIVITY_PAYLOAD) is False
    assert is_running(YOGA_ACTIVITY_PAYLOAD) is False


def test_map_splits_normalizes_wrapper_and_direct_list() -> None:
    """Design: dict com lista interna (lapDTOs) e lista direta → mesmas linhas."""
    expected = [
        {
            "idx": 1,
            "dist_m": 1000.0,
            "duration_s": 360.0,
            "pace_s": 360.0,
            "avg_hr": 142,
            "elevation_m": 25.5,
            "intensity_type": "ACTIVE",
        },
        {
            "idx": 2,
            "dist_m": 1000.0,
            "duration_s": 350.0,
            "pace_s": 350.0,
            "avg_hr": 145,
            "elevation_m": 15.0,
            "intensity_type": "INTERVAL",
        },
    ]
    assert map_splits(SPLITS_LAPDTOS_PAYLOAD) == expected
    assert map_splits(SPLITS_LIST_PAYLOAD) == expected


def test_map_splits_empty_variants_return_empty_list() -> None:
    """Edge do spec: vazio/None → [] sem warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # qualquer warning vira falha
        assert map_splits(None) == []
        assert map_splits({}) == []
        assert map_splits([]) == []
        assert map_splits({"activityId": 12345678901, "lapDTOs": []}) == []


def test_map_sleep_full_night() -> None:
    """Sono → Sleep: duração, score, percentuais, despertares, horários GMT."""
    row = map_sleep(SLEEP_PAYLOAD)
    assert row == {
        "date": date(2024, 1, 15),
        "duration_s": 28800,
        "score": 85,
        "deep_pct": 25.0,
        "light_pct": 50.0,
        "rem_pct": 25.0,
        "awakenings": 2,
        "bed_time": datetime(2024, 1, 15, 0, 0),
        "wake_time": datetime(2024, 1, 15, 8, 0),
    }


def test_map_sleep_none_when_no_data() -> None:
    """SYNC-19: sem dailySleepDTO/sleepTimeSeconds → None (skip do dia)."""
    assert map_sleep(None) is None
    assert map_sleep({}) is None
    assert map_sleep({"dailySleepDTO": {"calendarDate": "2024-01-15"}}) is None


def test_map_hrv_extracts_last_night_avg() -> None:
    row = map_hrv(HRV_PAYLOAD)
    assert row == {"date": date(2024, 1, 15), "value": 48, "status": "BALANCED"}


def test_map_hrv_none_when_no_data() -> None:
    """SYNC-19: lastNightAvg None → skip do dia, mesmo com wrapper presente."""
    assert map_hrv(None) is None
    assert map_hrv(HRV_NO_DATA_PAYLOAD) is None
    assert map_hrv({"hrvSummary": {"weeklyAvg": 60}}) is None


def test_map_rhr_extracts_resting_hr() -> None:
    row = map_rhr(RHR_PAYLOAD)
    assert row == {"date": date(2024, 1, 15), "value": 55}


def test_map_rhr_none_when_no_data() -> None:
    assert map_rhr(None) is None
    assert map_rhr(RHR_NO_DATA_PAYLOAD) is None


def test_map_stress_produces_daily_average() -> None:
    row = map_stress(STRESS_PAYLOAD)
    assert row == {"date": date(2024, 1, 15), "avg": 25}


def test_map_stress_none_when_no_data() -> None:
    assert map_stress(None) is None
    assert map_stress(STRESS_NO_DATA_PAYLOAD) is None


def test_map_battery_one_row_per_calendar_date() -> None:
    """Design: 1 linha por calendarDate; dia sem data não vira linha."""
    assert map_battery(BATTERY_ROWS) == [
        {"date": date(2024, 1, 15), "value": 55},
        {"date": date(2024, 1, 14), "value": 40},
    ]
    assert map_battery(None) == []


def test_map_personal_records_filters_running_records() -> None:
    """SYNC-16: só corrida; extrai event/value/pr_date + raw_json preservado."""
    rows = map_personal_records(PERSONAL_RECORDS_PAYLOAD)
    assert [r["event"] for r in rows] == ["FASTEST_5K", "LONGEST_RUN"]
    five_k = rows[0]
    assert five_k["value"] == 1200.0
    assert five_k["pr_date"] == date(2024, 1, 15)
    assert five_k["raw_json"] == PERSONAL_RECORDS_PAYLOAD[0]
    assert rows[1]["value"] == 32000.0
    assert rows[1]["pr_date"] == date(2024, 1, 14)


def test_map_personal_records_normalizes_wrapper_shape() -> None:
    rows = map_personal_records(PERSONAL_RECORDS_WRAPPER)
    assert [r["event"] for r in rows] == ["FASTEST_5K"]
    assert rows[0]["value"] == 1200.0


def test_map_personal_records_empty_shapes() -> None:
    assert map_personal_records(None) == []
    assert map_personal_records([]) == []
    assert map_personal_records({"personalRecords": []}) == []
