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
    SPLITS_PROBE_PAYLOAD,
    STRESS_NO_DATA_PAYLOAD,
    STRESS_PAYLOAD,
    TRAIL_ACTIVITY_PAYLOAD,
    YOGA_ACTIVITY_PAYLOAD,
    YOGA_NO_DISTANCE_PAYLOAD,
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


def test_map_activity_without_distance_maps_to_zero() -> None:
    """T15 spot-check real: yoga/força vêm com distance=None e a coluna
    distance_m é NOT NULL — o mapper materializa 0.0 (a atividade não
    cobre distância); os demais campos seguem o payload.
    """
    row = map_activity(YOGA_NO_DISTANCE_PAYLOAD)
    assert row["distance_m"] == 0.0
    assert row["activity_type"] == "yoga"
    assert row["duration_s"] == 2681.52
    assert row["avg_hr"] == 61
    assert row["training_load"] == 0.4336700439453125
    assert row["raw_json"] == YOGA_NO_DISTANCE_PAYLOAD


def test_is_running_accepts_running_and_trail() -> None:
    """SYNC-12: splits só para corrida — running e trail_running."""
    assert is_running(GARMIN_ACTIVITY_PAYLOAD) is True
    assert is_running(TRAIL_ACTIVITY_PAYLOAD) is True


def test_is_running_rejects_other_types() -> None:
    assert is_running(CYCLING_ACTIVITY_PAYLOAD) is False
    assert is_running(YOGA_ACTIVITY_PAYLOAD) is False


def test_map_splits_normalizes_wrapper_and_direct_list() -> None:
    """Design: dict com lista interna (lapDTOs) e lista direta → mesmas linhas.

    Payload sem cadência/temperatura por volta → None (T1: campos novos
    de split, NULL quando ausentes).
    """
    expected = [
        {
            "idx": 1,
            "dist_m": 1000.0,
            "duration_s": 360.0,
            "pace_s": 360.0,
            "avg_hr": 142,
            "avg_cadence": None,
            "avg_temperature": None,
            "elevation_m": 25.5,
            "intensity_type": "ACTIVE",
        },
        {
            "idx": 2,
            "dist_m": 1000.0,
            "duration_s": 350.0,
            "pace_s": 350.0,
            "avg_hr": 145,
            "avg_cadence": None,
            "avg_temperature": None,
            "elevation_m": 15.0,
            "intensity_type": "INTERVAL",
        },
    ]
    assert map_splits(SPLITS_LAPDTOS_PAYLOAD) == expected
    assert map_splits(SPLITS_LIST_PAYLOAD) == expected


def test_map_splits_extracts_cadence_and_temperature() -> None:
    """T1: lapDTO real (sonda 14/10/2026) -> averageRunCadence/averageTemperature
    viram avg_cadence/avg_temperature; pace_s derivado da volta de 100m."""
    rows = map_splits(SPLITS_PROBE_PAYLOAD)
    assert rows[0]["avg_cadence"] == 155.2
    assert rows[0]["avg_temperature"] == 22.0
    assert rows[1]["avg_cadence"] == 156.0
    assert rows[1]["avg_temperature"] == 22.1
    assert rows[0]["pace_s"] == 205.0  # 20.5s por 100m


def test_map_splits_cadence_temperature_none_when_absent() -> None:
    """T1: lapDTO sem os campos (voltas antigas) -> avg_cadence/avg_temperature None."""
    row = map_splits(SPLITS_LAPDTOS_PAYLOAD)[0]
    assert row["avg_cadence"] is None
    assert row["avg_temperature"] is None


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
    """Shape real da sonda T15: valor aninhado em allMetrics.metricsMap."""
    row = map_rhr(RHR_PAYLOAD)
    assert row == {"date": date(2026, 10, 13), "value": 42.0}


def test_map_rhr_none_when_no_data() -> None:
    """SYNC-19: wrapper sem a métrica -> skip do dia."""
    assert map_rhr(None) is None
    assert map_rhr(RHR_NO_DATA_PAYLOAD) is None
    assert map_rhr({"allMetrics": {"metricsMap": {}}}) is None


def test_map_stress_produces_daily_average() -> None:
    row = map_stress(STRESS_PAYLOAD)
    assert row == {"date": date(2024, 1, 15), "avg": 25}


def test_map_stress_none_when_no_data() -> None:
    assert map_stress(None) is None
    assert map_stress(STRESS_NO_DATA_PAYLOAD) is None


def test_map_battery_one_row_per_date() -> None:
    """Design: 1 linha por `date` com o nível mais recente do dia
    (último par de bodyBatteryValuesArray — shape real da sonda T15)."""
    assert map_battery(BATTERY_ROWS) == [
        {"date": date(2026, 10, 13), "value": 62},
        {"date": date(2026, 10, 12), "value": 40},
    ]
    assert map_battery(None) == []


def test_map_battery_skips_row_with_empty_series() -> None:
    """T15: dia com série vazia não tem valor de bateria — não vira
    linha (equivalente de SYNC-19 no range de battery)."""
    rows = map_battery([{"date": "2026-10-11", "bodyBatteryValuesArray": []}])
    assert rows == []


def test_map_personal_records_filters_running_records() -> None:
    """SYNC-16: só corrida; extrai event/value/pr_date + raw_json preservado."""
    rows = map_personal_records(PERSONAL_RECORDS_PAYLOAD)
    assert [r["event"] for r in rows] == ["FASTEST_5K", "LONGEST_RUN"]
    five_k = rows[0]
    assert five_k["value"] == 1163.8299560546875
    assert five_k["pr_date"] == date(2026, 4, 26)  # data local do payload real
    assert five_k["raw_json"] == PERSONAL_RECORDS_PAYLOAD[0]
    assert rows[1]["value"] == 32000.0
    assert rows[1]["pr_date"] == date(2024, 1, 14)  # fallback prStartTimeGmt


def test_map_personal_records_normalizes_wrapper_shape() -> None:
    rows = map_personal_records(PERSONAL_RECORDS_WRAPPER)
    assert [r["event"] for r in rows] == ["FASTEST_5K"]
    assert rows[0]["value"] == 1163.8299560546875


def test_map_personal_records_pr_date_is_local_wall_clock() -> None:
    """POT-05 (done-when T3): pr_date = data LOCAL do esforço, não a GMT.

    Payload derivado da sonda real com relógio deslocado: esforço às
    22:30 do dia 26 no fuso local (= 01:30 UTC do dia 27) — a data
    gravada é 26/04 (wall clock, mesma convenção de `start_time`), e
    não 27/04 (data GMT). Falha sob a leitura GMT do bug original.
    """
    payload = [
        {
            "typeId": 3,
            "value": 1163.83,
            "activityStartDateTimeLocal": 1777242600000,  # 2026-04-26 22:30 local
            "activityStartDateTimeLocalFormatted": "2026-04-26T22:30:00.0",
            "prStartTimeGmt": 1777253400000,  # 2026-04-27 01:30 UTC
        }
    ]
    rows = map_personal_records(payload)
    assert rows[0]["pr_date"] == date(2026, 4, 26)


def test_map_personal_records_falls_back_to_pr_start_time_gmt() -> None:
    """POT-05 (done-when T3): sem activityStartDateTimeLocal → data do prStartTimeGmt."""
    payload = [{"typeId": 4, "value": 2425.0, "prStartTimeGmt": 1705190400000}]
    rows = map_personal_records(payload)
    assert rows[0]["pr_date"] == date(2024, 1, 14)


def test_map_personal_records_pr_date_null_without_timestamps() -> None:
    """POT-05 (done-when T3): nenhum timestamp → pr_date NULL (nada inventado)."""
    payload = [{"typeId": 4, "value": 2425.0}]
    rows = map_personal_records(payload)
    assert rows[0]["pr_date"] is None


def test_map_personal_records_empty_shapes() -> None:
    assert map_personal_records(None) == []
    assert map_personal_records([]) == []
    assert map_personal_records({"personalRecords": []}) == []
