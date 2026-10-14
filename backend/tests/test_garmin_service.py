"""Orquestrador do sync (T8) — máquina de estados, fases e stats_json.

Cenários derivados do spec (SYNC-04/05/06/09/10/13/14/15/17/18/19/20/
21/24/25/27) com o FakeGateway — nenhuma chamada real ao Garmin. Os
valores afirmados (janelas, contadores, mensagens PT-BR) são literais
do spec/design, nunca constantes compartilhadas com a implementação
(lição L-001). "Hoje" fica congelado em 2026-10-14 via seam `_today()`.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.db.engine import SessionLocal, init_db
from app.db.models import (
    Activity,
    BodyBattery,
    DailyLoad,
    DEFAULT_USER_ID,
    Hrv,
    PersonalRecord,
    Rhr,
    Sleep,
    Split,
    Stress,
    SyncJob,
    SyncState,
)
from app.garmin import service
from app.garmin.client import GarminAuthExpiredError, SyncBudgetExceededError
from app.garmin.service import JobConflictError, create_job, run_sync
from app.garmin.upserts import get_sync_state
from fake_garmin import CYCLING_ID, FakeGateway

TODAY = date(2026, 10, 14)
BACKFILL_ACTIVITIES_START = date(2026, 4, 17)  # TODAY - 180d (SYNC-15)
BACKFILL_HEALTH_START = date(2026, 8, 15)  # TODAY - 60d (SYNC-15)
REPULL_START = date(2026, 10, 11)  # TODAY - 3d (SYNC-10)


@pytest.fixture(autouse=True)
def _frozen_today(monkeypatch):
    monkeypatch.setattr(service, "_today", lambda: TODAY)


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _count(db, model) -> int:
    return db.execute(select(func.count()).select_from(model)).scalar_one()


def _table_counts(db) -> dict[str, int]:
    models = {
        "activities": Activity,
        "splits": Split,
        "sleep": Sleep,
        "hrv": Hrv,
        "rhr": Rhr,
        "stress": Stress,
        "body_battery": BodyBattery,
        "personal_records": PersonalRecord,
        "load": DailyLoad,
        "sync_state": SyncState,
    }
    return {name: _count(db, model) for name, model in models.items()}


def _create_job() -> SyncJob:
    with SessionLocal() as session:
        return create_job(session, DEFAULT_USER_ID)


def _load_job(job_id: int) -> SyncJob:
    with SessionLocal() as session:
        return session.get(SyncJob, job_id)


def test_create_job_conflict_when_active_job_exists(db):
    """SYNC-02: job ativo existente -> JobConflictError (base do 409)."""
    job = create_job(db, DEFAULT_USER_ID)

    with pytest.raises(JobConflictError):
        create_job(db, DEFAULT_USER_ID)

    assert db.get(SyncJob, job.id).status == "pending"  # o corrente segue intacto


def test_run_sync_happy_path_done_with_full_stats(db, monkeypatch):
    """SYNC-04/06/17: happy path completo termina done com todos os contadores."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.error is None
    assert finished.started_at is not None
    assert finished.finished_at is not None
    stats = finished.stats_json
    assert stats["message"] == "Sync concluído."
    assert stats["activities_new"] == 12
    assert stats["activities_updated"] == 0
    assert stats["splits"] == 20
    assert stats["sleep_days"] == 61
    assert stats["hrv_days"] == 61
    assert stats["rhr_days"] == 61
    assert stats["battery_days"] == 61
    assert stats["stress_days"] == 61
    assert stats["records"] == 2
    assert stats["calls_made"] == 258  # 1 atividades + 11 splits + 4x61 saúde + battery + recordes
    assert stats["duration_s"] >= 0
    assert stats["warnings"] == []
    assert stats["reauth_needed"] is False

    fake = FakeGateway.last
    assert fake.calls["activities"] == [(BACKFILL_ACTIVITIES_START, TODAY)]
    split_ids = [args[0] for args in fake.calls["splits"]]
    assert len(split_ids) == 11
    assert CYCLING_ID not in split_ids  # SYNC-12: cycling não pede splits

    with SessionLocal() as s:
        assert _table_counts(s) == {
            "activities": 12,
            "splits": 20,
            "sleep": 61,
            "hrv": 61,
            "rhr": 61,
            "stress": 61,
            "body_battery": 61,
            "personal_records": 2,
            "load": 12,  # 2026-10-03 (mais antiga) .. 10-14 (SYNC-23)
            "sync_state": 6,
        }
        treadmill = s.execute(
            select(Activity.id).where(Activity.garmin_id == "98765432101")
        ).scalar_one()
        assert (
            s.execute(
                select(func.count()).select_from(Split).where(Split.activity_id == treadmill)
            ).scalar_one()
            == 0  # esteira sem GPS: atividade válida sem splits
        )
        load_dates = s.execute(select(DailyLoad.date).order_by(DailyLoad.date)).scalars().all()
        assert load_dates[0] == date(2026, 10, 3)
        assert load_dates[-1] == TODAY
        for data_type in ("activities", "sleep", "hrv", "rhr", "stress", "body_battery"):
            assert get_sync_state(s, DEFAULT_USER_ID, data_type) == TODAY


def test_sync_is_idempotent_2x_same_counts(db, monkeypatch):
    """Independent Test do spec: 2× sync -> contagens idênticas em todas as tabelas."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)

    first_job = _create_job()
    run_sync(first_job.id)
    with SessionLocal() as s:
        counts_after_first = _table_counts(s)

    second_job = _create_job()
    run_sync(second_job.id)
    with SessionLocal() as s:
        assert _table_counts(s) == counts_after_first

    second = _load_job(second_job.id)
    assert second.status == "done"
    stats = second.stats_json
    assert stats["activities_new"] == 0  # segunda execução só atualiza
    assert stats["activities_updated"] == 4  # janela de 3 dias: 4 atividades
    assert stats["splits"] == 4
    assert stats["warnings"] == []


def test_incremental_windows_after_backfill(db, monkeypatch):
    """SYNC-10/15/18: backfill 180d/60d na 1ª sync; depois last_date - 3d."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)

    first_job = _create_job()
    run_sync(first_job.id)
    fake = FakeGateway.last
    assert fake.calls["activities"] == [(BACKFILL_ACTIVITIES_START, TODAY)]
    assert fake.calls["sleep"][0] == (BACKFILL_HEALTH_START,)
    assert len(fake.calls["sleep"]) == 61
    assert fake.calls["body_battery"] == [(BACKFILL_HEALTH_START, TODAY)]

    second_job = _create_job()
    run_sync(second_job.id)
    fake = FakeGateway.last
    assert fake.calls["activities"] == [(REPULL_START, TODAY)]  # SYNC-10
    assert fake.calls["hrv"] == [
        (REPULL_START + timedelta(days=i),) for i in range(4)
    ]
    assert len(fake.calls["stress"]) == 4
    assert fake.calls["body_battery"] == [(REPULL_START, TODAY)]


def test_second_sync_calls_made_much_smaller(db, monkeypatch):
    """SYNC-27 (Independent Test): incremental faz bem menos chamadas que o backfill."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)

    first_job = _create_job()
    run_sync(first_job.id)
    second_job = _create_job()
    run_sync(second_job.id)

    assert _load_job(first_job.id).stats_json["calls_made"] == 258
    assert _load_job(second_job.id).stats_json["calls_made"] == 22


def test_state_machine_pending_running_done_with_partial_stats(db, monkeypatch):
    """SYNC-04/05: transições gravam started_at/finished_at; stats parciais visíveis."""
    captured = []

    class SnapshotGateway(FakeGateway):
        def get_splits(self, activity_id):
            with SessionLocal() as s:
                running_job = s.execute(
                    select(SyncJob).where(SyncJob.status == "running")
                ).scalar_one()
                captured.append(
                    {
                        "status": running_job.status,
                        "started_at": running_job.started_at,
                        "finished_at": running_job.finished_at,
                        "stats": dict(running_job.stats_json),
                    }
                )
            return super().get_splits(activity_id)

    monkeypatch.setattr(service, "GarminGateway", SnapshotGateway)
    job = _create_job()
    run_sync(job.id)

    assert captured
    snapshot = captured[0]
    assert snapshot["status"] == "running"
    assert snapshot["started_at"] is not None
    assert snapshot["finished_at"] is None
    assert snapshot["stats"]["step"] == "activities"
    assert snapshot["stats"]["message"] == "Puxando 12 atividades…"
    assert snapshot["stats"]["activities_new"] == 0  # contadores parciais no banco

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.started_at is not None
    assert finished.finished_at is not None
    assert finished.finished_at >= finished.started_at


def test_invalid_transition_raises(db, monkeypatch):
    """SYNC-04: transição fora da sequência levanta e não corrompe o job."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)  # pending -> running -> done

    with pytest.raises(RuntimeError, match="Transição inválida"):
        run_sync(job.id)  # done -> running é proibido

    reloaded = _load_job(job.id)
    assert reloaded.status == "done"
    assert reloaded.finished_at is not None


def test_activities_failure_after_retries_job_error(db, monkeypatch):
    """SYNC-14: falha de atividades (tipo crítico) -> job error sem nada parcial."""

    class FailingActivities(FakeGateway):
        def get_activities(self, start, end):
            self._record("activities", start, end)
            raise RuntimeError("atividades indisponíveis (retries esgotados)")

    monkeypatch.setattr(service, "GarminGateway", FailingActivities)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "error"
    assert finished.error == "atividades indisponíveis (retries esgotados)"
    assert finished.started_at is not None
    assert finished.finished_at is not None
    stats = finished.stats_json
    assert stats["message"] == "atividades indisponíveis (retries esgotados)"
    assert stats["activities_new"] == 0
    assert stats["splits"] == 0
    assert stats["reauth_needed"] is False
    with SessionLocal() as s:
        assert _table_counts(s)["activities"] == 0  # nada parcial gravado
        assert _table_counts(s)["splits"] == 0
        assert _table_counts(s)["sleep"] == 0  # fases seguintes nem rodaram
        assert get_sync_state(s, DEFAULT_USER_ID, "activities") is None


def test_health_type_failure_warns_and_continues(db, monkeypatch):
    """SYNC-20: falha de um tipo de saúde -> warning, demais continuam, job done."""

    class FailingSleep(FakeGateway):
        def get_sleep(self, day):
            self._record("sleep", day)
            raise RuntimeError("sleep fora do ar")

    monkeypatch.setattr(service, "GarminGateway", FailingSleep)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.error is None
    stats = finished.stats_json
    assert stats["warnings"] == [{"tipo": "sleep", "erro": "sleep fora do ar"}]
    assert stats["sleep_days"] == 0
    assert stats["hrv_days"] == 61
    assert stats["rhr_days"] == 61
    assert stats["stress_days"] == 61
    assert stats["battery_days"] == 61
    assert stats["records"] == 2
    assert stats["activities_new"] == 12
    with SessionLocal() as s:
        assert _count(s, Sleep) == 0
        assert _count(s, Hrv) == 61
        assert get_sync_state(s, DEFAULT_USER_ID, "sleep") is None  # tipo falhou
        assert get_sync_state(s, DEFAULT_USER_ID, "hrv") == TODAY  # os demais avançam
        assert _count(s, DailyLoad) == 12  # PMC rodou mesmo com warning


def test_records_failure_warns_and_done(db, monkeypatch):
    """SYNC-20 (política de recordes): falha -> warning + done; demais intactos."""

    class FailingRecords(FakeGateway):
        def get_personal_records(self):
            self._record("personal_records")
            raise RuntimeError("recordes quebraram")

    monkeypatch.setattr(service, "GarminGateway", FailingRecords)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    stats = finished.stats_json
    assert stats["warnings"] == [{"tipo": "records", "erro": "recordes quebraram"}]
    assert stats["records"] == 0
    with SessionLocal() as s:
        assert _count(s, PersonalRecord) == 0
        assert _count(s, Activity) == 12
        assert _count(s, Sleep) == 61


def test_auth_expired_error_reauth_needed(db, monkeypatch):
    """SYNC-25: login com token morto -> error + reauth_needed; banco intacto."""

    class ReauthGateway(FakeGateway):
        @classmethod
        def from_settings(cls, settings=None):
            raise GarminAuthExpiredError("Sessão Garmin expirada (401)")

    monkeypatch.setattr(service, "GarminGateway", ReauthGateway)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "error"
    assert finished.error == "Sessão Garmin expirada (401)"
    stats = finished.stats_json
    assert stats["reauth_needed"] is True
    assert stats["calls_made"] == 0
    assert stats["warnings"] == []
    with SessionLocal() as s:
        assert _table_counts(s)["activities"] == 0
        assert _table_counts(s)["sleep"] == 0
        assert _table_counts(s)["sync_state"] == 0


def test_budget_exceeded_error_with_calls_stats(db, monkeypatch):
    """SYNC-09: teto atingido -> error com as estatísticas das chamadas feitas."""

    class BudgetBlown(FakeGateway):
        def get_stress(self, day):
            self._record("stress", day)
            raise SyncBudgetExceededError("Teto de chamadas atingido (1500); feitas 1500.")

    monkeypatch.setattr(service, "GarminGateway", BudgetBlown)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "error"
    assert finished.error == "Teto de chamadas atingido (1500); feitas 1500."
    stats = finished.stats_json
    assert stats["calls_made"] == 196  # stats das chamadas feitas até o teto
    assert stats["reauth_needed"] is False
    with SessionLocal() as s:
        assert _count(s, Sleep) == 61  # tipos concluídos antes do teto ficam
        assert _count(s, Stress) == 0
        assert get_sync_state(s, DEFAULT_USER_ID, "stress") is None
        assert get_sync_state(s, DEFAULT_USER_ID, "sleep") == TODAY


def test_health_day_without_data_skipped_silently(db, monkeypatch):
    """SYNC-19: dia sem HRV pula sem erro, sem linha e sem warning."""

    class HrvWithGap(FakeGateway):
        hrv_no_data = frozenset({date(2026, 10, 13)})

    monkeypatch.setattr(service, "GarminGateway", HrvWithGap)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    stats = finished.stats_json
    assert stats["hrv_days"] == 60  # 61 - o dia sem dado
    assert stats["warnings"] == []
    with SessionLocal() as s:
        assert _count(s, Hrv) == 60
        assert (
            s.execute(select(Hrv).where(Hrv.date == date(2026, 10, 13))).scalar_one_or_none()
            is None
        )
        assert get_sync_state(s, DEFAULT_USER_ID, "hrv") == TODAY  # tipo concluído


def test_per_item_progress_during_health_phase(db, monkeypatch):
    """SYNC-05: stats atualizados a cada item — contador parcial visível no banco."""
    captured = []

    class ProgressGateway(FakeGateway):
        def get_hrv(self, day):
            result = super().get_hrv(day)
            if len(self.calls["hrv"]) == 5:  # no 5º dia pedido, 4 já contabilizados
                with SessionLocal() as s:
                    running_job = s.execute(
                        select(SyncJob).where(SyncJob.status == "running")
                    ).scalar_one()
                    captured.append(dict(running_job.stats_json))
            return result

    monkeypatch.setattr(service, "GarminGateway", ProgressGateway)
    job = _create_job()
    run_sync(job.id)

    assert captured
    assert captured[0]["step"] == "hrv"
    assert captured[0]["hrv_days"] == 4
    assert captured[0]["message"] == "Puxando HRV: 4 dias…"
