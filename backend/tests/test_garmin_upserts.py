"""Upserts idempotentes — integração no Postgres real (T6).

Cenários derivados do spec (SYNC-11/13/16/18/21) e dos done-when de
T6. O teste-chave é o Independent Test do spec: reexecutar 2× deixa
as contagens estáveis. Valores afirmados são literais das fixtures de
payload, nunca constantes compartilhadas com a implementação (L-001).
"""

from datetime import date

import pytest
from sqlalchemy import func, select

from app.db.engine import SessionLocal, init_db
from app.db.models import (
    Activity,
    BodyBattery,
    Hrv,
    PersonalRecord,
    RacePrediction,
    Rhr,
    Sleep,
    Split,
    Stress,
    SyncState,
)
from app.garmin.mappers import (
    map_activity,
    map_battery,
    map_hrv,
    map_personal_records,
    map_race_predictions,
    map_rhr,
    map_sleep,
    map_splits,
    map_stress,
)
from app.garmin.upserts import (
    get_sync_state,
    set_sync_state,
    upsert_activity,
    upsert_health_rows,
    upsert_race_predictions,
    upsert_records,
    upsert_splits,
)
from helpers import (
    BATTERY_ROWS,
    GARMIN_ACTIVITY_PAYLOAD,
    HRV_PAYLOAD,
    PERSONAL_RECORDS_PAYLOAD,
    RACE_PREDICTIONS_PAYLOAD,
    RHR_PAYLOAD,
    SLEEP_PAYLOAD,
    SPLITS_LAPDTOS_PAYLOAD,
    SPLITS_PROBE_PAYLOAD,
    STRESS_PAYLOAD,
)

# Linha extra de split (literal do teste) para o cenário de prune 3 -> 2
THIRD_SPLIT_ROW = {
    "idx": 3,
    "dist_m": 1000.0,
    "duration_s": 340.0,
    "pace_s": 340.0,
    "avg_hr": 148,
    "elevation_m": 10.0,
    "intensity_type": "ACTIVE",
}


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _count(db, model) -> int:
    return db.execute(select(func.count()).select_from(model)).scalar_one()


def _activity_db_id(db, garmin_id: str) -> int:
    return db.execute(
        select(Activity.id).where(Activity.garmin_id == garmin_id)
    ).scalar_one()


def test_upsert_activity_new_persists_all_fields(db):
    """SYNC-11: primeira execução -> "new" com os campos do payload; user_id em toda escrita (AD-001)."""
    assert upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD)) == "new"
    db.commit()

    activity = db.execute(
        select(Activity).where(Activity.garmin_id == "12345678901")
    ).scalar_one()
    assert activity.user_id == 1
    assert activity.activity_type == "running"
    assert activity.name == "Morning Run"
    assert activity.distance_m == 5000.0
    assert activity.duration_s == 1800.0
    assert activity.training_load == 120.0
    assert activity.raw_json == GARMIN_ACTIVITY_PAYLOAD
    assert _count(db, Activity) == 1


def test_upsert_activity_rerun_is_idempotent(db):
    """SYNC-11 (Independent Test): 2× upsert -> 1 linha; a segunda retorna "updated"."""
    assert upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD)) == "new"
    db.commit()
    assert upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD)) == "updated"
    db.commit()

    assert _count(db, Activity) == 1


def test_upsert_activity_update_changes_fields(db):
    """Edge do spec: atividade editada no re-pull -> upsert por garmin_id atualiza os campos."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()

    edited = map_activity(GARMIN_ACTIVITY_PAYLOAD)
    edited["distance_m"] = 5500.0
    edited["name"] = "Morning Run (edited)"
    assert upsert_activity(db, 1, edited) == "updated"
    db.commit()

    activity = db.execute(
        select(Activity).where(Activity.garmin_id == "12345678901")
    ).scalar_one()
    assert activity.distance_m == 5500.0
    assert activity.name == "Morning Run (edited)"
    assert _count(db, Activity) == 1


def test_upsert_splits_idempotent_2x_stable(db):
    """SYNC-11: 2× upsert dos mesmos splits -> 2 linhas, nunca 4."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    assert upsert_splits(db, activity_id, map_splits(SPLITS_LAPDTOS_PAYLOAD)) == 2
    db.commit()
    assert upsert_splits(db, activity_id, map_splits(SPLITS_LAPDTOS_PAYLOAD)) == 2
    db.commit()

    assert _count(db, Split) == 2
    idxs = db.execute(
        select(Split.idx).where(Split.activity_id == activity_id).order_by(Split.idx)
    ).scalars().all()
    assert idxs == [1, 2]
    first = db.execute(
        select(Split).where(Split.activity_id == activity_id, Split.idx == 1)
    ).scalar_one()
    assert first.user_id == 1
    assert first.dist_m == 1000.0
    assert first.duration_s == 360.0
    assert first.pace_s == 360.0
    assert first.intensity_type == "ACTIVE"


def test_upsert_splits_prunes_rows_beyond_new_length(db):
    """Done-when: prune de idx >= len(rows) — edição que reduz os laps da corrida."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    three_rows = map_splits(SPLITS_LAPDTOS_PAYLOAD) + [THIRD_SPLIT_ROW]
    assert upsert_splits(db, activity_id, three_rows) == 3
    db.commit()
    assert _count(db, Split) == 3

    assert upsert_splits(db, activity_id, map_splits(SPLITS_LAPDTOS_PAYLOAD)) == 2
    db.commit()

    assert _count(db, Split) == 2
    idxs = db.execute(
        select(Split.idx).where(Split.activity_id == activity_id).order_by(Split.idx)
    ).scalars().all()
    assert idxs == [1, 2]


def test_upsert_splits_empty_rows_prune_all(db):
    """Edge do spec: splits vazios (esteira sem GPS) -> atividade permanece sem splits."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    assert upsert_splits(db, activity_id, map_splits(SPLITS_LAPDTOS_PAYLOAD)) == 2
    db.commit()
    assert upsert_splits(db, activity_id, []) == 0
    db.commit()

    assert _count(db, Split) == 0


def test_upsert_splits_updates_existing_values(db):
    """SYNC-11: mesma chave (activity_id, idx) com novos valores -> atualiza sem duplicar."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    rows = map_splits(SPLITS_LAPDTOS_PAYLOAD)
    upsert_splits(db, activity_id, rows)
    db.commit()

    edited = [dict(rows[0], duration_s=400.0, pace_s=400.0), rows[1]]
    assert upsert_splits(db, activity_id, edited) == 2
    db.commit()

    first = db.execute(
        select(Split).where(Split.activity_id == activity_id, Split.idx == 1)
    ).scalar_one()
    assert first.duration_s == 400.0
    assert first.pace_s == 400.0
    assert _count(db, Split) == 2


def test_upsert_splits_stores_cadence_and_temperature(db):
    """T1/TRN-29/30: lapDTO com averageRunCadence/averageTemperature ->
    colunas avg_cadence/avg_temperature gravadas no Postgres."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    rows = map_splits(SPLITS_PROBE_PAYLOAD)
    assert upsert_splits(db, activity_id, rows) == 2
    db.commit()

    first = db.execute(
        select(Split).where(Split.activity_id == activity_id, Split.idx == 1)
    ).scalar_one()
    assert first.avg_cadence == 155.2
    assert first.avg_temperature == 22.0
    second = db.execute(
        select(Split).where(Split.activity_id == activity_id, Split.idx == 2)
    ).scalar_one()
    assert second.avg_cadence == 156.0
    assert second.avg_temperature == 22.1


def test_upsert_splits_null_when_cadence_temperature_absent(db):
    """T1/TRN-29/30: payload sem os campos -> NULL (nenhum número inventado)."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    assert upsert_splits(db, activity_id, map_splits(SPLITS_LAPDTOS_PAYLOAD)) == 2
    db.commit()

    first = db.execute(
        select(Split).where(Split.activity_id == activity_id, Split.idx == 1)
    ).scalar_one()
    assert first.avg_cadence is None
    assert first.avg_temperature is None


def test_upsert_splits_cadence_idempotent_2x(db):
    """T1/TRN-31: re-upsert com os campos novos mantém contagens estáveis
    e preserva os valores (idempotência herdada de (activity_id, idx))."""
    upsert_activity(db, 1, map_activity(GARMIN_ACTIVITY_PAYLOAD))
    db.commit()
    activity_id = _activity_db_id(db, "12345678901")

    rows = map_splits(SPLITS_PROBE_PAYLOAD)
    assert upsert_splits(db, activity_id, rows) == 2
    db.commit()
    assert upsert_splits(db, activity_id, rows) == 2
    db.commit()

    assert _count(db, Split) == 2
    first = db.execute(
        select(Split).where(Split.activity_id == activity_id, Split.idx == 1)
    ).scalar_one()
    assert first.avg_cadence == 155.2
    assert first.avg_temperature == 22.0


def test_upsert_health_rows_sleep_by_user_date(db):
    """SYNC-18: upsert genérico por (user_id, date); 2 datas, 2 execuções -> 2 linhas."""
    night = map_sleep(SLEEP_PAYLOAD)
    other_night = dict(map_sleep(SLEEP_PAYLOAD))
    other_night["date"] = date(2024, 1, 16)
    rows = [night, other_night]

    assert upsert_health_rows(db, Sleep, 1, rows) == 2
    db.commit()
    assert upsert_health_rows(db, Sleep, 1, rows) == 2
    db.commit()

    assert _count(db, Sleep) == 2
    stored = db.execute(select(Sleep).where(Sleep.date == date(2024, 1, 15))).scalar_one()
    assert stored.user_id == 1
    assert stored.duration_s == 28800
    assert stored.score == 85


def test_upsert_health_rows_updates_same_date(db):
    """SYNC-18: mesma (user_id, date) com novo valor -> atualiza, 1 linha."""
    upsert_health_rows(db, Hrv, 1, [map_hrv(HRV_PAYLOAD)])
    db.commit()

    changed = dict(map_hrv(HRV_PAYLOAD))
    changed["value"] = 52.0
    assert upsert_health_rows(db, Hrv, 1, [changed]) == 1
    db.commit()

    assert _count(db, Hrv) == 1
    stored = db.execute(select(Hrv).where(Hrv.date == date(2024, 1, 15))).scalar_one()
    assert stored.value == 52.0


def test_upsert_health_rows_covers_each_health_model(db):
    """SYNC-18: o genérico serve hrv, rhr, body battery e stress (sono coberto acima)."""
    upsert_health_rows(db, Hrv, 1, [map_hrv(HRV_PAYLOAD)])
    upsert_health_rows(db, Rhr, 1, [map_rhr(RHR_PAYLOAD)])
    upsert_health_rows(db, BodyBattery, 1, map_battery(BATTERY_ROWS))
    upsert_health_rows(db, Stress, 1, [map_stress(STRESS_PAYLOAD)])
    db.commit()

    assert _count(db, Hrv) == 1
    assert _count(db, Rhr) == 1
    assert _count(db, BodyBattery) == 2
    assert _count(db, Stress) == 1

    hrv = db.execute(select(Hrv).where(Hrv.date == date(2024, 1, 15))).scalar_one()
    assert hrv.value == 48
    rhr = db.execute(select(Rhr).where(Rhr.date == date(2026, 10, 13))).scalar_one()
    assert rhr.value == 42  # 42.0 no payload real; coluna Integer
    battery_dates = (
        db.execute(select(BodyBattery.date).order_by(BodyBattery.date)).scalars().all()
    )
    assert battery_dates == [date(2026, 10, 12), date(2026, 10, 13)]
    stress = db.execute(select(Stress).where(Stress.date == date(2024, 1, 15))).scalar_one()
    assert stress.avg == 25


def test_upsert_records_by_user_event(db):
    """SYNC-16: recordes por (user_id, event); 2× execução estável; PR batido atualiza."""
    rows = map_personal_records(PERSONAL_RECORDS_PAYLOAD)
    assert upsert_records(db, 1, rows) == 2
    db.commit()
    assert upsert_records(db, 1, map_personal_records(PERSONAL_RECORDS_PAYLOAD)) == 2
    db.commit()

    assert _count(db, PersonalRecord) == 2
    five_k = db.execute(
        select(PersonalRecord).where(PersonalRecord.event == "FASTEST_5K")
    ).scalar_one()
    assert five_k.user_id == 1
    assert five_k.value == 1163.8299560546875
    assert five_k.pr_date == date(2026, 4, 26)  # data local do payload real
    assert five_k.raw_json == PERSONAL_RECORDS_PAYLOAD[0]

    beaten = [dict(rows[0], value=1150.0, pr_date=date(2024, 2, 20))]
    assert upsert_records(db, 1, beaten) == 1
    db.commit()

    assert _count(db, PersonalRecord) == 2
    five_k = db.execute(
        select(PersonalRecord).where(PersonalRecord.event == "FASTEST_5K")
    ).scalar_one()
    assert five_k.value == 1150.0
    assert five_k.pr_date == date(2024, 2, 20)


def test_upsert_records_self_heals_pr_date_of_existing_row(db):
    """POT-06 (done-when T3): re-upsert preenche a pr_date de linhas gravadas
    pelo mapper antigo (todas NULL) — o próximo sync após o fix cura o banco
    sem duplicar linhas."""
    legacy = [
        {"event": "FASTEST_5K", "value": 1163.8299560546875, "pr_date": None,
         "raw_json": PERSONAL_RECORDS_PAYLOAD[0]},
    ]
    assert upsert_records(db, 1, legacy) == 1
    db.commit()
    stored = db.execute(
        select(PersonalRecord).where(PersonalRecord.event == "FASTEST_5K")
    ).scalar_one()
    assert stored.pr_date is None

    assert upsert_records(db, 1, map_personal_records(PERSONAL_RECORDS_PAYLOAD)) == 2
    db.commit()

    assert _count(db, PersonalRecord) == 2  # a linha existente foi atualizada, não duplicada
    healed = db.execute(
        select(PersonalRecord).where(PersonalRecord.event == "FASTEST_5K")
    ).scalar_one()
    assert healed.id == stored.id
    assert healed.pr_date == date(2026, 4, 26)


def test_upsert_race_predictions_by_user_event_idempotent_2x(db):
    """POT-02 (done-when T4): payload real da sonda -> 4 linhas; 2× upsert
    mantém as contagens estáveis e os campos gravados."""
    rows = map_race_predictions(RACE_PREDICTIONS_PAYLOAD)
    assert upsert_race_predictions(db, 1, rows) == 4
    db.commit()
    assert upsert_race_predictions(db, 1, map_race_predictions(RACE_PREDICTIONS_PAYLOAD)) == 4
    db.commit()

    assert _count(db, RacePrediction) == 4
    marathon = db.execute(
        select(RacePrediction).where(RacePrediction.event == "MARATHON")
    ).scalar_one()
    assert marathon.user_id == 1
    assert marathon.time_s == 11989.0
    assert marathon.date == date(2026, 10, 15)
    assert marathon.raw_json == RACE_PREDICTIONS_PAYLOAD


def test_upsert_race_predictions_updates_existing_rows(db):
    """POT-02: snapshot novo com tempos/date diferentes -> atualiza in place."""
    upsert_race_predictions(db, 1, map_race_predictions(RACE_PREDICTIONS_PAYLOAD))
    db.commit()

    updated_payload = dict(RACE_PREDICTIONS_PAYLOAD, calendarDate="2026-10-16", time5K=1160)
    assert upsert_race_predictions(db, 1, map_race_predictions(updated_payload)) == 4
    db.commit()

    assert _count(db, RacePrediction) == 4
    five_k = db.execute(select(RacePrediction).where(RacePrediction.event == "5K")).scalar_one()
    assert five_k.time_s == 1160.0
    assert five_k.date == date(2026, 10, 16)
    assert five_k.raw_json == updated_payload


def test_upsert_race_predictions_absent_event_leaves_row_untouched(db):
    """POT-02 (Independent Test): evento ausente no payload -> linha existente
    intocada (sem delete — mesma semântica do upsert_records)."""
    upsert_race_predictions(db, 1, map_race_predictions(RACE_PREDICTIONS_PAYLOAD))
    db.commit()
    marathon_before = db.execute(
        select(RacePrediction).where(RacePrediction.event == "MARATHON")
    ).scalar_one()

    partial = {k: v for k, v in RACE_PREDICTIONS_PAYLOAD.items() if k != "timeMarathon"}
    partial["time5K"] = 1170
    assert upsert_race_predictions(db, 1, map_race_predictions(partial)) == 3
    db.commit()

    assert _count(db, RacePrediction) == 4  # a linha da maratona permanece
    marathon_after = db.execute(
        select(RacePrediction).where(RacePrediction.event == "MARATHON")
    ).scalar_one()
    assert marathon_after.id == marathon_before.id
    assert marathon_after.time_s == marathon_before.time_s == 11989.0
    assert marathon_after.raw_json == RACE_PREDICTIONS_PAYLOAD
    five_k = db.execute(select(RacePrediction).where(RacePrediction.event == "5K")).scalar_one()
    assert five_k.time_s == 1170.0  # os demais atualizaram


def test_set_and_get_sync_state_by_data_type(db):
    """SYNC-13/21: last_date por (user_id, data_type); None antes de existir."""
    assert get_sync_state(db, 1, "activities") is None

    set_sync_state(db, 1, "activities", date(2026, 10, 14))
    set_sync_state(db, 1, "sleep", date(2026, 10, 11))
    db.commit()

    assert get_sync_state(db, 1, "activities") == date(2026, 10, 14)
    assert get_sync_state(db, 1, "sleep") == date(2026, 10, 11)
    assert _count(db, SyncState) == 2


def test_set_sync_state_updates_existing_last_date(db):
    """SYNC-13/21: novo sync avança o last_date sem duplicar a linha.

    Cada set corresponde ao fim de um sync (transação própria), por
    isso o commit entre as duas chamadas.
    """
    set_sync_state(db, 1, "activities", date(2026, 10, 13))
    db.commit()
    set_sync_state(db, 1, "activities", date(2026, 10, 14))
    db.commit()

    assert _count(db, SyncState) == 1
    assert get_sync_state(db, 1, "activities") == date(2026, 10, 14)
