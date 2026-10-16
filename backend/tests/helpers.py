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

# Atividade sem distância — payload REAL capturado na primeira sync (T15):
# o Garmin entrega distance=None para yoga/força e a coluna distance_m é
# NOT NULL; o mapper materializa 0.0 (zero distância coberta).
YOGA_NO_DISTANCE_PAYLOAD = {
    "activityId": 24667764311,
    "activityName": "Ioga",
    "activityType": {"typeKey": "yoga", "typeId": 62},
    "startTimeLocal": "2026-10-09 19:06:47",
    "distance": None,
    "duration": 2681.52,
    "averageHR": 61,
    "maxHR": 89,
    "aerobicTrainingEffect": 0.0,
    "anaerobicTrainingEffect": 0.0,
    "activityTrainingLoad": 0.4336700439453125,
}

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

# Splits com cadência/temperatura por volta: shape REAL da sonda de
# 14/10/2026 (garmin_id 24719288630, "Londrina - Strides") — o lapDTO
# traz `averageRunCadence` e `averageTemperature`; o nome da listagem
# (averageRunningCadenceInStepsPerMinute) NÃO existe por volta.
SPLITS_PROBE_PAYLOAD = {
    "activityId": 24719288630,
    "lapDTOs": [
        {
            "lapIndex": 1,
            "distance": 100.0,
            "duration": 20.5,
            "averageHR": 123,
            "averageRunCadence": 155.2,
            "averageTemperature": 22.0,
            "elevationGain": 0.0,
            "intensityType": "ACTIVE",
        },
        {
            "lapIndex": 2,
            "distance": 100.0,
            "duration": 21.0,
            "averageHR": 131,
            "averageRunCadence": 156.0,
            "averageTemperature": 22.1,
            "elevationGain": 0.0,
            "intensityType": "ACTIVE",
        },
    ],
}

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
    # Payload REAL da sonda T15 (get_rhr_day, metricId=60): o valor vem
    # aninhado em allMetrics.metricsMap — shape confirmado contra a API.
    "userProfileId": 122886821,
    "statisticsStartDate": "2026-10-13",
    "statisticsEndDate": "2026-10-13",
    "allMetrics": {
        "metricsMap": {
            "WELLNESS_RESTING_HEART_RATE": [
                {"value": 42.0, "calendarDate": "2026-10-13"}
            ]
        }
    },
    "groupedMetrics": None,
}

# Dia sem dado: o wrapper vem sem a métrica (SYNC-19)
RHR_NO_DATA_PAYLOAD = {
    "userProfileId": 122886821,
    "statisticsStartDate": "2026-10-13",
    "statisticsEndDate": "2026-10-13",
    "allMetrics": {"metricsMap": {}},
    "groupedMetrics": None,
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

# Body battery: payload REAL da sonda T15 (get_body_battery range) — a
# linha do dia tem `date` (não calendarDate) e a série
# bodyBatteryValuesArray de pares [timestamp, nível]; o valor mais
# recente do dia é o último nível. A 3ª linha não tem `date` e a 4ª tem
# série vazia (dia sem dado) — nenhuma pode virar linha (SYNC-19).
BATTERY_ROWS = [
    {
        "date": "2026-10-13",
        "charged": 58,
        "drained": 82,
        "bodyBatteryValuesArray": [
            [1789614000000, 32],
            [1789632900000, 86],
            [1789642800000, 62],
        ],
    },
    {
        "date": "2026-10-12",
        "charged": 100,
        "drained": 60,
        "bodyBatteryValuesArray": [[1789527600000, 40]],
    },
    {"charged": 90, "drained": 10, "bodyBatteryValuesArray": [[1789441200000, 80]]},
    {"date": "2026-10-11", "bodyBatteryValuesArray": []},
]

# Recordes: shape REAL do banco (sonda de 15/10/2026, PR 2909304221 —
# "Londrina Corrida"): a data vem de `activityStartDateTimeLocal` (ms,
# wall clock local — bate com o campo `...LocalFormatted`) e a key GMT
# é `prStartTimeGmt` (o antigo `prStartTimeGMT` nunca existiu no payload).
# O 1º espelha a sonda exata; o 2º (typeId 8 = Longest Ride, filtrado —
# só corrida) e o 3º (LONGEST_RUN, sem timestamp local → fallback GMT)
# mantêm os timestamps das fixtures originais com as keys reais.
PERSONAL_RECORDS_PAYLOAD = [
    {
        "id": 2909304221,
        "typeId": 3,
        "status": "ACCEPTED",
        "activityId": 22664345610,
        "activityName": "Londrina Corrida",
        "activityType": "running",
        "activityStartDateTimeInGMT": 1777198253000,
        "actStartDateTimeInGMTFormatted": "2026-04-26T10:10:53.0",
        "activityStartDateTimeLocal": 1777187453000,
        "activityStartDateTimeLocalFormatted": "2026-04-26T07:10:53.0",
        "value": 1163.8299560546875,
        "prStartTimeGmt": 1777198254000,
        "prStartTimeGmtFormatted": "2026-04-26T10:10:54.0",
        "prStartTimeLocal": None,
    },
    {"typeId": 8, "value": 45000.0, "prStartTimeGmt": 1705276800000, "activityId": 12345678902},
    {"typeId": 7, "value": 32000.0, "prStartTimeGmt": 1705190400000, "activityId": 12345678903},
]

PERSONAL_RECORDS_WRAPPER = {"personalRecords": [PERSONAL_RECORDS_PAYLOAD[0]]}
