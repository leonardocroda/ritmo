"""Orquestrador do sync (T8) — máquina de estados, fases e stats_json.

Cenários derivados do spec (SYNC-04/05/06/09/10/13/14/15/17/18/19/20/
21/24/25/27) com o FakeGateway — nenhuma chamada real ao Garmin. Os
valores afirmados (janelas, contadores, mensagens PT-BR) são literais
do spec/design, nunca constantes compartilhadas com a implementação
(lição L-001). "Hoje" fica congelado em 2026-10-14 via seam `_today()`.
"""

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.engine import SessionLocal, init_db
from app.db.models import (
    Activity,
    BodyBattery,
    DailyLoad,
    Hrv,
    PersonalRecord,
    RacePrediction,
    Rhr,
    Sleep,
    Split,
    Stress,
    SyncJob,
    SyncState,
    User,
    UserHrMetric,
)
from app.garmin import service
from app.garmin.client import GarminAuthExpiredError, SyncBudgetExceededError
from app.garmin.service import (
    JobConflictError,
    _fcmax_from_zones,
    create_job,
    run_sync,
)
from app.profile import service as profile_service
from app.garmin.upserts import get_sync_state
from app.main import app
from fake_garmin import CYCLING_ID, FakeGateway
from helpers import RHR_PAYLOAD

TODAY = date(2026, 10, 14)
BACKFILL_ACTIVITIES_START = date(2026, 4, 17)  # TODAY - 180d (SYNC-15)
BACKFILL_HEALTH_START = date(2026, 6, 16)  # TODAY - 120d (SYNC-15, HRV-15: lookback de banda)
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
        "race_predictions": RacePrediction,
        "load": DailyLoad,
        "sync_state": SyncState,
    }
    return {name: _count(db, model) for name, model in models.items()}


def _create_job(user_id: int | None = None) -> SyncJob:
    """Job pending — usuário novo quando ``user_id`` ausente, o mesmo
    usuário quando o teste roda syncs sequenciais (o incremental é por
    usuário: user-scope). O commit do create_job grava os dois."""
    with SessionLocal() as session:
        if user_id is None:
            user = User(display_name="Corredora")
            session.add(user)
            session.flush()
            user_id = user.id
        return create_job(session, user_id)


def _load_job(job_id: int) -> SyncJob:
    with SessionLocal() as session:
        return session.get(SyncJob, job_id)


def test_create_job_conflict_when_active_job_exists(db):
    """SYNC-02: job ativo existente -> JobConflictError (base do 409)."""
    user = User(display_name="Corredora")
    db.add(user)
    db.flush()
    job = create_job(db, user.id)

    with pytest.raises(JobConflictError):
        create_job(db, user.id)

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
    assert stats["sleep_days"] == 121
    assert stats["hrv_days"] == 121
    assert stats["rhr_days"] == 121
    assert stats["battery_days"] == 121
    assert stats["stress_days"] == 121
    assert stats["records"] == 2
    assert stats["predictions"] == 4
    assert stats["calls_made"] == 502  # 1 atividades + 11 splits + 4x121 saúde + battery + recordes + 1 predições + 3 physio (1 settings + 2 LTHR)
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
            "sleep": 121,
            "hrv": 121,
            "rhr": 121,
            "stress": 121,
            "body_battery": 121,
            "personal_records": 2,
            "race_predictions": 4,
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
            assert get_sync_state(s, job.user_id, data_type) == TODAY


def test_sync_is_idempotent_2x_same_counts(db, monkeypatch):
    """Independent Test do spec: 2× sync -> contagens idênticas em todas as tabelas."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)

    first_job = _create_job()
    run_sync(first_job.id)
    with SessionLocal() as s:
        counts_after_first = _table_counts(s)

    second_job = _create_job(first_job.user_id)
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
    """SYNC-10/15/18: backfill 180d/120d na 1ª sync; depois last_date - 3d."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)

    first_job = _create_job()
    run_sync(first_job.id)
    fake = FakeGateway.last
    assert fake.calls["activities"] == [(BACKFILL_ACTIVITIES_START, TODAY)]
    assert fake.calls["sleep"][0] == (BACKFILL_HEALTH_START,)
    assert len(fake.calls["sleep"]) == 121
    assert fake.calls["body_battery"] == [(BACKFILL_HEALTH_START, TODAY)]

    second_job = _create_job(first_job.user_id)
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
    second_job = _create_job(first_job.user_id)
    run_sync(second_job.id)

    assert _load_job(first_job.id).stats_json["calls_made"] == 502
    assert _load_job(second_job.id).stats_json["calls_made"] == 26  # 23 + 3 da fase physio


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
        assert get_sync_state(s, job.user_id, "activities") is None


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
    assert stats["hrv_days"] == 121
    assert stats["rhr_days"] == 121
    assert stats["stress_days"] == 121
    assert stats["battery_days"] == 121
    assert stats["records"] == 2
    assert stats["activities_new"] == 12
    with SessionLocal() as s:
        assert _count(s, Sleep) == 0
        assert _count(s, Hrv) == 121
        assert get_sync_state(s, job.user_id, "sleep") is None  # tipo falhou
        assert get_sync_state(s, job.user_id, "hrv") == TODAY  # os demais avançam
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
        assert _count(s, Sleep) == 121


def test_predictions_synced_after_records_exactly_one_call(db, monkeypatch):
    """POT-01/02 (done-when T5): passo de predições após records com
    exatamente 1 chamada; 4 eventos upsertados no banco."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    stats = finished.stats_json
    assert stats["predictions"] == 4
    fake = FakeGateway.last
    assert fake.calls["race_predictions"] == [()]  # exatamente 1 chamada do orçamento
    with SessionLocal() as s:
        events = s.execute(select(RacePrediction.event)).scalars().all()
        assert len(events) == 4
        assert set(events) == {"5K", "10K", "HALF_MARATHON", "MARATHON"}


def test_predictions_step_consumes_one_extra_budget_call(db, monkeypatch):
    """POT-01: +1 chamada no orçamento total do sync (backfill 502 =
    498 das fases anteriores + predições + 3 da fase physio)."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)
    assert _load_job(job.id).stats_json["calls_made"] == 502


def test_predictions_failure_warns_and_sync_continues(db, monkeypatch):
    """POT-03: falha no passo -> warning {tipo: "predictions"}, job done,
    predictions 0; os passos seguintes (pmc) rodam."""

    class FailingPredictions(FakeGateway):
        def get_race_predictions(self):
            self._record("race_predictions")
            raise RuntimeError("predições fora do ar")

    monkeypatch.setattr(service, "GarminGateway", FailingPredictions)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.error is None
    stats = finished.stats_json
    assert stats["warnings"] == [{"tipo": "predictions", "erro": "predições fora do ar"}]
    assert stats["predictions"] == 0
    assert stats["records"] == 2  # o passo anterior concluiu
    assert stats["step"] == "pmc"  # o passo seguinte rodou
    with SessionLocal() as s:
        assert _count(s, RacePrediction) == 0
        assert _count(s, DailyLoad) == 12  # pmc rodou mesmo com o warning


def test_sync_step_order_records_then_predictions_then_pmc(db, monkeypatch):
    """POT-01 (done-when T5): ordem rígida records → predictions → pmc,
    observada pelo step gravado no banco na hora de cada chamada do gateway
    e pelo step final do job concluído."""
    observed_steps = []

    class OrderGateway(FakeGateway):
        def _running_step(self) -> str:
            with SessionLocal() as s:
                running = s.execute(
                    select(SyncJob).where(SyncJob.status == "running")
                ).scalar_one()
                return running.stats_json["step"]

        def get_personal_records(self):
            self._record("personal_records")
            observed_steps.append(self._running_step())
            return super().get_personal_records()

        def get_race_predictions(self):
            self._record("race_predictions")
            observed_steps.append(self._running_step())
            return super().get_race_predictions()

    monkeypatch.setattr(service, "GarminGateway", OrderGateway)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert observed_steps == ["records", "predictions"]
    stats = finished.stats_json
    assert stats["step"] == "pmc"  # pmc foi o último passo
    assert stats["records"] == 2
    assert stats["predictions"] == 4


def test_predictions_resync_updates_without_duplicates(db, monkeypatch):
    """Independent Test do spec (POT-02): 2× sync -> mesmas 4 linhas,
    sem duplicar; contador do segundo sync também em 4."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)

    first_job = _create_job()
    run_sync(first_job.id)
    second_job = _create_job(first_job.user_id)
    run_sync(second_job.id)

    with SessionLocal() as s:
        assert _count(s, RacePrediction) == 4
    assert _load_job(first_job.id).stats_json["predictions"] == 4
    assert _load_job(second_job.id).stats_json["predictions"] == 4


def test_auth_expired_error_reauth_needed(db, monkeypatch):
    """SYNC-25: login com token morto -> error + reauth_needed; banco intacto."""

    class ReauthGateway(FakeGateway):
        @classmethod
        def from_user(cls, db, user_id, settings=None):
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
    assert stats["calls_made"] == 376  # stats das chamadas feitas até o teto
    assert stats["reauth_needed"] is False
    with SessionLocal() as s:
        assert _count(s, Sleep) == 121  # tipos concluídos antes do teto ficam
        assert _count(s, Stress) == 0
        assert get_sync_state(s, job.user_id, "stress") is None
        assert get_sync_state(s, job.user_id, "sleep") == TODAY


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
    assert stats["hrv_days"] == 120  # 121 - o dia sem dado
    assert stats["warnings"] == []
    with SessionLocal() as s:
        assert _count(s, Hrv) == 120
        assert (
            s.execute(select(Hrv).where(Hrv.date == date(2026, 10, 13))).scalar_one_or_none()
            is None
        )
        assert get_sync_state(s, job.user_id, "hrv") == TODAY  # tipo concluído


def test_health_backfill_covers_hrv_band_lookback(db, monkeypatch):
    """HRV-15 (Independent Test): backfill de 120 dias persiste janela
    completa para a banda móvel do modelo de HRV — exibição de 60 dias
    + lookback de banda de 59 = 119 necessários; 121 dias corridos
    gravados, do TODAY-120 ao TODAY."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)

    with SessionLocal() as s:
        oldest = s.execute(select(func.min(Hrv.date))).scalar_one()
        newest = s.execute(select(func.max(Hrv.date))).scalar_one()
        assert oldest == BACKFILL_HEALTH_START  # 2026-06-16 = TODAY - 120d
        assert newest == TODAY
        assert _count(s, Hrv) == 121  # [start, hoje] fechado >= 119 do AC


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


def test_startup_recovers_orphan_running_job(db):
    """SYNC-02 (T9): job running órfão vira error no startup — nenhum 409 eterno."""
    user = User(display_name="Corredora")
    db.add(user)
    db.flush()
    job = create_job(db, user.id)
    job.status = "running"  # simula o processo morto no meio do sync
    job.started_at = datetime(2026, 10, 14, 12, 0, 0)
    db.commit()

    with TestClient(app):  # o lifespan roda a recovery
        pass

    reloaded = _load_job(job.id)
    assert reloaded.status == "error"
    assert reloaded.error == "interrompido por restart do servidor"
    assert reloaded.finished_at is not None

    with SessionLocal() as s:  # lock liberado: novo sync é aceito
        assert create_job(s, user.id).status == "pending"


def test_startup_leaves_finished_jobs_untouched(db, monkeypatch):
    """T9: jobs done|error não são tocados pelo recovery do lifespan."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    done_job = _create_job()
    run_sync(done_job.id)
    done_before = _load_job(done_job.id)
    with SessionLocal() as s:
        error_job = create_job(s, done_job.user_id)
        error_job.status = "error"
        error_job.error = "falha anterior"
        error_job.finished_at = datetime(2026, 10, 13, 8, 0, 0)
        s.commit()

    with TestClient(app):
        pass

    done_after = _load_job(done_job.id)
    assert done_after.status == "done"
    assert done_after.error is None
    assert done_after.finished_at == done_before.finished_at
    error_after = _load_job(error_job.id)
    assert error_after.status == "error"
    assert error_after.error == "falha anterior"
    assert error_after.finished_at == datetime(2026, 10, 13, 8, 0, 0)


# ---------------------------------------------------------------
# Fase physio (hr-zones T8) — métricas fisiológicas no final do sync
# ---------------------------------------------------------------


def test_sync_physio_phase_creates_three_garmin_metrics(db, monkeypatch):
    """HRZ-05: fase physio cria fcmax/fclthr/fcrest source=garmin e
    consome +3 chamadas (1 das zonas de FC + 2 internas do LTHR)."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    stats = finished.stats_json
    assert stats["calls_made"] == 502  # 499 das fases anteriores + 3 da physio
    assert stats["warnings"] == []
    fake = FakeGateway.last
    assert fake.calls["heart_rate_zones"] == [()]
    assert fake.calls["lactate_threshold"] == [()]

    with SessionLocal() as s:
        rows = (
            s.execute(
                select(UserHrMetric).where(UserHrMetric.user_id == job.user_id)
            )
            .scalars()
            .all()
        )
        by_kind = {row.kind: row for row in rows}
        assert set(by_kind) == {"fcmax", "fcrest", "fclthr"}
        assert by_kind["fcmax"].value_bpm == 190
        assert by_kind["fclthr"].value_bpm == 172
        assert by_kind["fcrest"].value_bpm == 42  # mínimo-7d da série rhr (42 todo dia)
        assert all(row.source == "garmin" for row in rows)


def test_sync_physio_lthr_none_skips_fclthr_without_warning(db, monkeypatch):
    """Edge do design: LTHR nunca detectado (heartRate None) -> fclthr
    pulada sem warning; fcmax/fcrest chegam; job done."""
    class NoLthr(FakeGateway):
        lthr_none = True

    monkeypatch.setattr(service, "GarminGateway", NoLthr)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.error is None
    assert finished.stats_json["warnings"] == []
    with SessionLocal() as s:
        kinds = (
            s.execute(
                select(UserHrMetric.kind).where(UserHrMetric.user_id == job.user_id)
            )
            .scalars()
            .all()
        )
        assert set(kinds) == {"fcmax", "fcrest"}  # fclthr não chegou — pulei


def test_sync_physio_manual_wins_and_repeat_sync_no_new_rows(db, monkeypatch):
    """HRZ-06 ponta a ponta: vigente manual (preferência `manual`, como o
    PUT registra) não é sobrescrita pelo sync; 2º sync com os mesmos
    valores não cria linha nenhuma (HRZ-03)."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    with SessionLocal() as s:
        # o estado manual da produção nasce do set_metric (PUT) — que
        # registra a preferência `manual` junto (HRZ-20)
        profile_service.set_metric(
            s, job.user_id, "fclthr", 185, "manual", on_date=date(2026, 10, 10)
        )
        s.commit()
    run_sync(job.id)

    with SessionLocal() as s:
        lthr_rows = (
            s.execute(
                select(UserHrMetric).where(
                    UserHrMetric.user_id == job.user_id,
                    UserHrMetric.kind == "fclthr",
                )
                .order_by(UserHrMetric.id)
            )
            .scalars()
            .all()
        )
        assert len(lthr_rows) == 1  # manual-wins: o sync não sobrescreveu
        assert lthr_rows[0].value_bpm == 185
        assert lthr_rows[0].source == "manual"
        assert _count(s, UserHrMetric) == 3  # fclthr manual + fcmax + fcrest

    second_job = _create_job(job.user_id)
    run_sync(second_job.id)
    with SessionLocal() as s:
        assert _count(s, UserHrMetric) == 3  # valores iguais: nada novo


def test_sync_physio_reclaim_after_release_flips_ownership(db, monkeypatch):
    """HRZ-21 ponta a ponta: depois do 'voltar a puxar do Garmin' (a
    preferência volta a `garmin`), o PRÓXIMO sync reassume a métrica —
    linha `source=garmin` com o valor do sync; os syncs seguintes ficam
    no update-if-changed normal."""
    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    with SessionLocal() as s:
        profile_service.set_metric(
            s, job.user_id, "fclthr", 185, "manual", on_date=date(2026, 10, 10)
        )
        s.commit()
    run_sync(job.id)  # manual-wins: held
    with SessionLocal() as s:
        profile_service.set_sync_mode(s, job.user_id, "fclthr", "garmin")
        s.commit()

    second_job = _create_job(job.user_id)
    run_sync(second_job.id)
    with SessionLocal() as s:
        lthr_rows = (
            s.execute(
                select(UserHrMetric).where(
                    UserHrMetric.user_id == job.user_id,
                    UserHrMetric.kind == "fclthr",
                )
                .order_by(UserHrMetric.id)
            )
            .scalars()
            .all()
        )
        # flip de posse: 185 manual + 172 garmin (valor do sync)
        assert [(row.value_bpm, row.source) for row in lthr_rows] == [
            (185, "manual"),
            (172, "garmin"),
        ]
        assert _count(s, UserHrMetric) == 4  # + fcmax + fcrest

    third_job = _create_job(job.user_id)
    run_sync(third_job.id)
    with SessionLocal() as s:
        assert _count(s, UserHrMetric) == 4  # retoma o update-if-changed


def test_sync_physio_fcrest_follows_min_7d_of_rhr_series(db, monkeypatch):
    """HRZ-05/edge: fcrest = mínimo-7d da série `rhr` do próprio usuário
    — a linha nova registra a mudança da série, e só quando ela muda."""

    class LowerRhr(FakeGateway):
        """Série nova: RHR 40 em todo dia (a evolução da fcrest)."""

        def get_rhr(self, day):
            self._record("rhr", day)
            if day in self.rhr_no_data:
                return None
            reading = dict(
                RHR_PAYLOAD["allMetrics"]["metricsMap"]["WELLNESS_RESTING_HEART_RATE"][0],
                value=40.0,
                calendarDate=day.isoformat(),
            )
            return dict(
                RHR_PAYLOAD,
                allMetrics={"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [reading]}},
            )

    monkeypatch.setattr(service, "GarminGateway", FakeGateway)
    job = _create_job()
    run_sync(job.id)

    monkeypatch.setattr(service, "GarminGateway", LowerRhr)
    second_job = _create_job(job.user_id)
    run_sync(second_job.id)
    third_job = _create_job(second_job.user_id)
    run_sync(third_job.id)

    with SessionLocal() as s:
        rows = (
            s.execute(
                select(UserHrMetric).where(
                    UserHrMetric.user_id == job.user_id,
                    UserHrMetric.kind == "fcrest",
                )
                .order_by(UserHrMetric.id)
            )
            .scalars()
            .all()
        )
        # 1ª série (42) -> linha; nova série (40) -> linha; 3º sync igual -> nada
        assert [row.value_bpm for row in rows] == [42, 40]
        assert all(row.source == "garmin" for row in rows)


def test_sync_physio_failure_warns_and_job_done(db, monkeypatch):
    """SYNC-20 na fase physio: falha -> warning {tipo: "physio"}, job
    done, fases anteriores intactas e nenhuma métrica gravada."""

    class FailingPhysio(FakeGateway):
        def get_heart_rate_zones(self):
            self._record("heart_rate_zones")
            raise RuntimeError("zonas fora do ar")

    monkeypatch.setattr(service, "GarminGateway", FailingPhysio)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.error is None
    stats = finished.stats_json
    assert stats["warnings"] == [{"tipo": "physio", "erro": "zonas fora do ar"}]
    with SessionLocal() as s:
        assert _count(s, Activity) == 12  # fases anteriores intactas
        assert _count(s, RacePrediction) == 4
        assert _count(s, DailyLoad) == 12  # pmc rodou depois do warning
        assert _count(s, UserHrMetric) == 0  # a fase não gravou nada


def test_sync_physio_max_hr_absent_skips_fcmax(db, monkeypatch):
    """Extração resiliente: zonas sem maxHeartRateUsed -> fcmax pulada
    sem warning; fclthr/fcrest chegam normalmente."""

    class NoMaxHr(FakeGateway):
        def get_heart_rate_zones(self):
            self._record("heart_rate_zones")
            return [
                {
                    "trainingMethod": "LACTATE_THRESHOLD",
                    "sport": "RUNNING",
                    "changeState": "UNCHANGED",
                }
            ]

    monkeypatch.setattr(service, "GarminGateway", NoMaxHr)
    job = _create_job()
    run_sync(job.id)

    finished = _load_job(job.id)
    assert finished.status == "done"
    assert finished.stats_json["warnings"] == []
    with SessionLocal() as s:
        kinds = (
            s.execute(
                select(UserHrMetric.kind).where(UserHrMetric.user_id == job.user_id)
            )
            .scalars()
            .all()
        )
        assert set(kinds) == {"fcrest", "fclthr"}  # fcmax não chegou — pulei


def test_fcmax_from_zones_prefers_running_sport():
    """Fix UAT (HRZ-05): fcmax vem do maxHeartRateUsed do esporte
    RUNNING — a entry CYCLING (método HR_RESERVE, max 191) é ignorada."""
    zones = [
        {"sport": "DEFAULT", "maxHeartRateUsed": 190},
        {"sport": "RUNNING", "maxHeartRateUsed": 199},
        {"sport": "CYCLING", "maxHeartRateUsed": 191},
    ]
    assert _fcmax_from_zones(zones) == 199


def test_fcmax_from_zones_falls_back_to_default():
    """Fix UAT (HRZ-05): conta sem entry RUNNING -> usa a entry DEFAULT."""
    zones = [
        {"sport": "DEFAULT", "maxHeartRateUsed": 190},
        {"sport": "CYCLING", "maxHeartRateUsed": 191},
    ]
    assert _fcmax_from_zones(zones) == 190


def test_fcmax_from_zones_absent_or_malformed_returns_none():
    """Fix UAT (HRZ-05): extração resiliente — sem maxHeartRateUsed, valor
    não-inteiro ou payload inesperado -> None (métrica pulada, sem erro)."""
    assert _fcmax_from_zones([{"sport": "RUNNING"}]) is None
    assert _fcmax_from_zones([{"sport": "RUNNING", "maxHeartRateUsed": None}]) is None
    assert _fcmax_from_zones([]) is None
    assert _fcmax_from_zones(None) is None
    assert _fcmax_from_zones({"sport": "RUNNING", "maxHeartRateUsed": 199}) is None
