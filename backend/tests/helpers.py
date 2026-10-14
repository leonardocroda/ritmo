"""Helpers do ambiente de teste — a suite roda no Postgres do compose (AD-007)."""

import sqlalchemy

POSTGRES_UP_HINT = "docker compose up -d postgres"

# Porta não escutada no loopback pode pendurar o SYN por minutos no Windows
# (proxy do Docker/WSL). O probe impõe teto próprio: falha "imediatamente" (INFRA-06).
PROBE_CONNECT_TIMEOUT_S = 3


def ensure_postgres_available(database_url: str) -> None:
    """Falha rápido e claro se o Postgres de testes não estiver acessível (INFRA-06).

    Levanta RuntimeError com a instrução de subida em vez de deixar a suite
    quebrar em erros de conexão espalhados.
    """
    engine = sqlalchemy.create_engine(
        database_url,
        connect_args={"connect_timeout": PROBE_CONNECT_TIMEOUT_S},
    )
    try:
        with engine.connect():
            pass
    except Exception as exc:
        raise RuntimeError(
            f"Postgres de testes inacessível ({database_url}): {exc}. "
            f"Suba o banco antes de rodar a suite: {POSTGRES_UP_HINT}"
        ) from exc
    finally:
        engine.dispose()


# ============================================================
# Fixtures de payload do Garmin (T5) — por endpoint
#
# Modeladas nos fixtures/curadoria do garmin_mcp do usuário (mesma
# lib garminconnect 0.3.2, shapes derivados de dados reais). Campos
# com incerteza de nome estão registrados como spec-precision gap
# no resumo do lote; raw_json preservado permite correção no
# spot-check da primeira sync real (T15) sem re-pull.
# ============================================================

GARMIN_ACTIVITY_PAYLOAD = {
    "activityId": 12345678901,
    "activityName": "Morning Run",
    "activityType": {"typeKey": "running", "typeId": 1},
    "eventType": {"typeKey": "race", "typeId": 1},
    "startTimeLocal": "2024-01-15 07:00:00",
    "distance": 5000.0,
    "duration": 1800.0,
    "averageHR": 145,
    "maxHR": 165,
    "averageRunningCadenceInStepsPerMinute": 170.0,
    "averagePower": 210.0,
    "elevationGain": 55.0,
    "aerobicTrainingEffect": 2.8,
    "anaerobicTrainingEffect": 0.4,
    "activityTrainingLoad": 120.0,
    "calories": 350,
}

# Atividade sem os campos opcionais — raw_json ainda tem tudo (spec)
SPARSE_ACTIVITY_PAYLOAD = {
    "activityId": 98765432101,
    "activityName": "Treadmill Run",
    "activityType": {"typeKey": "running", "typeId": 1},
    "startTimeLocal": "2024-01-14 06:30:00",
    "distance": 8000.0,
    "duration": 3000.0,
    "averageHR": 140,
}

TRAIL_ACTIVITY_PAYLOAD = {"activityType": {"typeKey": "trail_running", "typeId": 39}}
CYCLING_ACTIVITY_PAYLOAD = {"activityType": {"typeKey": "cycling", "typeId": 2}}
YOGA_ACTIVITY_PAYLOAD = {"activityType": {"typeKey": "yoga", "typeId": 62}}

# Splits: shape real é dict com lista interna (lapDTOs) — a lista
# direta é a forma alternativa normalizada pelo design
SPLITS_LAPDTOS_PAYLOAD = {
    "activityId": 12345678901,
    "lapDTOs": [
        {
            "lapIndex": 1,
            "distance": 1000.0,
            "duration": 360.0,
            "averageHR": 142,
            "averageSpeed": 2.78,
            "elevationGain": 25.5,
            "elevationLoss": 10.2,
            "intensityType": "ACTIVE",
        },
        {
            "lapIndex": 2,
            "distance": 1000.0,
            "duration": 350.0,
            "averageHR": 145,
            "averageSpeed": 2.86,
            "elevationGain": 15.0,
            "elevationLoss": 30.8,
            "intensityType": "INTERVAL",
        },
    ],
}

SPLITS_LIST_PAYLOAD = list(SPLITS_LAPDTOS_PAYLOAD["lapDTOs"])

# 1705276800000 ms = 2024-01-15 00:00:00 UTC (GMT, como entregue)
SLEEP_PAYLOAD = {
    "dailySleepDTO": {
        "id": 123456,
        "calendarDate": "2024-01-15",
        "sleepTimeSeconds": 28800,
        "napTimeSeconds": 0,
        "sleepStartTimestampGMT": 1705276800000,
        "sleepEndTimestampGMT": 1705305600000,
        "deepSleepSeconds": 7200,
        "lightSleepSeconds": 14400,
        "remSleepSeconds": 7200,
        "awakeCount": 2,
        "sleepScores": {"overall": {"value": 85, "qualifierKey": "GOOD"}},
    },
    "wellnessSpO2SleepSummaryDTO": {"calendarDate": "2024-01-15", "averageSpo2": 96},
    "avgOvernightHrv": 45,
}

HRV_PAYLOAD = {
    "userProfilePk": 12345678,
    "hrvSummary": {
        "calendarDate": "2024-01-15",
        "weeklyAvg": 45,
        "lastNightAvg": 48,
        "lastNight5MinHigh": 52,
        "status": "BALANCED",
        "feedbackPhrase": "HRV_BALANCED_2",
    },
    "hrvReadings": [
        {"hrvValue": 45, "readingTimeGMT": "2024-01-15T00:15:00.0"},
    ],
}

# Dia sem dado: o Garmin devolve o wrapper com lastNightAvg None
HRV_NO_DATA_PAYLOAD = {
    "userProfilePk": 12345678,
    "hrvSummary": {
        "calendarDate": "2024-01-15",
        "weeklyAvg": 60,
        "lastNightAvg": None,
        "lastNight5MinHigh": None,
        "status": "NONE",
    },
    "hrvReadings": [],
}

RHR_PAYLOAD = {
    "calendarDate": "2024-01-15",
    "restingHeartRate": 55,
    "lastSevenDaysAvgRestingHeartRate": 57,
    "lastNightAvgRestingHeartRate": 53,
}

RHR_NO_DATA_PAYLOAD = {
    "calendarDate": "2024-01-15",
    "restingHeartRate": None,
    "lastSevenDaysAvgRestingHeartRate": None,
}

STRESS_PAYLOAD = {
    "calendarDate": "2024-01-15",
    "avgStressLevel": 25,
    "maxStressLevel": 60,
    "stressValuesArray": [
        [1705276800000, 20],
        [1705280400000, 30],
        [1705284000000, 25],
    ],
}

STRESS_NO_DATA_PAYLOAD = {
    "calendarDate": "2024-01-15",
    "avgStressLevel": None,
    "stressValuesArray": [],
}

# Body battery: 1 chamada de range devolve uma lista de dias; a 3ª
# linha não tem calendarDate (dia sem dado) e não pode virar linha
BATTERY_ROWS = [
    {"calendarDate": "2024-01-15", "charged": 55, "drained": 45, "bodyBatteryMostRecentValue": 55},
    {"calendarDate": "2024-01-14", "charged": 100, "drained": 60, "bodyBatteryMostRecentValue": 40},
    {"charged": 90, "drained": 10, "bodyBatteryMostRecentValue": 80},
]

# Recordes: typeId é o identificador real do Garmin; corrida = 1..7
# (mapa estimado no garmin_mcp "based on real data"). typeId 8 é
# Longest Ride — filtrado pelo spec (só corrida).
PERSONAL_RECORDS_PAYLOAD = [
    {"typeId": 3, "value": 1200.0, "prStartTimeGMT": 1705276800000, "activityId": 12345678901},
    {"typeId": 8, "value": 45000.0, "prStartTimeGMT": 1705276800000, "activityId": 12345678902},
    {"typeId": 7, "value": 32000.0, "prStartTimeGMT": 1705190400000, "activityId": 12345678903},
]

PERSONAL_RECORDS_WRAPPER = {"personalRecords": [PERSONAL_RECORDS_PAYLOAD[0]]}
