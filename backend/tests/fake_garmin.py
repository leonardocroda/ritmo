"""FakeGateway — a interface do GarminGateway sobre os fixtures de payload do T5.

Nenhuma chamada de rede: os payloads vêm das fixtures com a data de
calendário do dia pedido (o payload real carrega a própria data).
Falhas e buracos de dados vêm de subclasses definidas por cenário nos
testes; o dia sem dado devolve None (SYNC-19).
"""

from datetime import date, timedelta

from helpers import (
    BATTERY_ROWS,
    GARMIN_ACTIVITY_PAYLOAD,
    HRV_PAYLOAD,
    PERSONAL_RECORDS_PAYLOAD,
    RACE_PREDICTIONS_PAYLOAD,
    RHR_PAYLOAD,
    SLEEP_PAYLOAD,
    SPARSE_ACTIVITY_PAYLOAD,
    SPLITS_LAPDTOS_PAYLOAD,
    STRESS_PAYLOAD,
)

TREADMILL_ID = 98765432101  # corrida sem splits (esteira — edge do spec)
CYCLING_ID = 55500000001  # não é corrida: nunca pede splits (SYNC-12)

# Fase physio (hr-zones): user settings (userData.maxHeartRate) e LTHR
# latest (speed_and_heart_rate.heartRate) — shapes da lib 0.3.2
USER_SETTINGS_PAYLOAD = {
    "userData": {
        "displayName": "Corredora",
        "measurementSystem": "METRIC",
        "maxHeartRate": 190,
    },
}

LACTATE_THRESHOLD_PAYLOAD = {
    "speed_and_heart_rate": {
        "userProfilePK": 122886821,
        "version": None,
        "calendarDate": "2026-10-13",
        "sequence": 1,
        "speed": 3.53,
        "heartRate": 172,
        "heartRateCycling": None,
    },
    "power": {"minAvgPower": 3.6, "maxAvgPower": 4.1},
}

# LTHR nunca detectado pelo relógio — heartRate None (edge do design)
LACTATE_THRESHOLD_NONE_PAYLOAD = dict(
    LACTATE_THRESHOLD_PAYLOAD,
    speed_and_heart_rate=dict(
        LACTATE_THRESHOLD_PAYLOAD["speed_and_heart_rate"], heartRate=None
    ),
)


def _with_date(payload: dict, day: date, clock: str = "07:00:00") -> dict:
    data = dict(payload)
    data["startTimeLocal"] = f"{day.isoformat()} {clock}"
    return data


def _sleep_payload(day: date) -> dict:
    dto = dict(SLEEP_PAYLOAD["dailySleepDTO"], calendarDate=day.isoformat())
    return dict(SLEEP_PAYLOAD, dailySleepDTO=dto)


def _hrv_payload(day: date) -> dict:
    summary = dict(HRV_PAYLOAD["hrvSummary"], calendarDate=day.isoformat())
    return dict(HRV_PAYLOAD, hrvSummary=summary)


def _rhr_payload(day: date) -> dict:
    # Shape real (T15): a data do dia vive dentro de allMetrics.metricsMap
    reading = dict(
        RHR_PAYLOAD["allMetrics"]["metricsMap"]["WELLNESS_RESTING_HEART_RATE"][0],
        calendarDate=day.isoformat(),
    )
    return dict(
        RHR_PAYLOAD,
        allMetrics={"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [reading]}},
    )


def _stress_payload(day: date) -> dict:
    return dict(STRESS_PAYLOAD, calendarDate=day.isoformat())


class FakeGateway:
    """Happy path: 12 atividades na janela pedida e saúde em todo dia.

    A instância mais recente fica em `<classe>.last` para os testes
    auditarem as janelas pedidas (o service constrói o gateway).
    """

    last: "FakeGateway | None" = None

    # Dias que devolvem None — subclasses configuram o buraco (SYNC-19)
    sleep_no_data: frozenset[date] = frozenset()
    hrv_no_data: frozenset[date] = frozenset()
    rhr_no_data: frozenset[date] = frozenset()
    stress_no_data: frozenset[date] = frozenset()
    battery_no_data: frozenset[date] = frozenset()
    # Fase physio: LTHR nunca detectado pelo relógio (heartRate None)
    lthr_none: bool = False

    def __init__(self) -> None:
        self._calls = 0
        self.calls: dict[str, list] = {}
        type(self).last = self

    @classmethod
    def from_settings(cls, settings=None) -> "FakeGateway":
        return cls()

    @property
    def calls_made(self) -> int:
        return self._calls

    def _record(self, name: str, *args) -> None:
        self._calls += 1
        self.calls.setdefault(name, []).append(args)

    # -- 11 métodos de dados (interface do GarminGateway) ----------------

    def get_activities(self, start: date, end: date) -> list[dict]:
        self._record("activities", start, end)
        activities = [
            _with_date(GARMIN_ACTIVITY_PAYLOAD, end),  # corrida com splits
            _with_date(SPARSE_ACTIVITY_PAYLOAD, end - timedelta(days=1), "06:30:00"),  # esteira
            dict(
                _with_date(GARMIN_ACTIVITY_PAYLOAD, end - timedelta(days=2)),
                activityId=CYCLING_ID,
                activityType={"typeKey": "cycling", "typeId": 2},
            ),
        ]
        for i in range(3, 12):
            activities.append(
                dict(
                    _with_date(GARMIN_ACTIVITY_PAYLOAD, end - timedelta(days=i)),
                    activityId=12345678900 + i,
                )
            )
        return [
            a
            for a in activities
            if start <= date.fromisoformat(a["startTimeLocal"].split(" ")[0]) <= end
        ]

    def get_splits(self, activity_id) -> dict:
        self._record("splits", activity_id)
        if activity_id == TREADMILL_ID:
            return {"activityId": activity_id, "lapDTOs": []}  # esteira sem GPS
        return dict(SPLITS_LAPDTOS_PAYLOAD, activityId=activity_id)

    def get_sleep(self, day: date):
        self._record("sleep", day)
        if day in self.sleep_no_data:
            return None
        return _sleep_payload(day)

    def get_hrv(self, day: date):
        self._record("hrv", day)
        if day in self.hrv_no_data:
            return None
        return _hrv_payload(day)

    def get_rhr(self, day: date):
        self._record("rhr", day)
        if day in self.rhr_no_data:
            return None
        return _rhr_payload(day)

    def get_stress(self, day: date):
        self._record("stress", day)
        if day in self.stress_no_data:
            return None
        return _stress_payload(day)

    def get_body_battery(self, start: date, end: date) -> list[dict]:
        self._record("body_battery", start, end)
        rows = []
        day = start
        while day <= end:
            if day not in self.battery_no_data:
                rows.append(dict(BATTERY_ROWS[0], date=day.isoformat()))
            day += timedelta(days=1)
        return rows

    def get_personal_records(self) -> list[dict]:
        self._record("personal_records")
        return PERSONAL_RECORDS_PAYLOAD

    def get_race_predictions(self) -> dict:
        self._record("race_predictions")
        return RACE_PREDICTIONS_PAYLOAD

    def get_user_settings(self) -> dict:
        self._record("user_settings")
        return USER_SETTINGS_PAYLOAD

    def get_lactate_threshold(self) -> dict:
        # 1 `_call` que custa 2 chamadas internas na lib (power + HR) —
        # o orçamento conta as duas (mesma contabilidade do gateway real)
        self._record("lactate_threshold")
        self._calls += 1
        if self.lthr_none:
            return LACTATE_THRESHOLD_NONE_PAYLOAD
        return LACTATE_THRESHOLD_PAYLOAD
