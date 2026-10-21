"""Modelo de dados do Ritmo.

Tradução direta da seção 5 ("Modelo de dados essencial") do plano
(docs/PLANO_PLATAFORMA.md).

Requisito travado (Fase 1): TODA tabela carrega ``user_id`` — mesmo com
usuário único — para que o isolamento multiusuário da Fase 2.5 seja só
uma query a mais, nunca um refactor.
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DEFAULT_USER_ID = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    # Auth (feature auth): email único — normalizado lowercase no service;
    # nullable porque o seed id 1 nasce sem email até o CLI vinculá-lo
    # (múltiplos NULL são permitidos em unique no Postgres)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # argon2id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class UserSession(Base):
    """Sessão stateful (feature auth): token opaco no cookie, banco guarda
    só o hash SHA-256 (AUTH-15). Logout = DELETE (sem flag); sliding de
    30 dias move ``expires_at``. Nome da classe evita colisão com
    ``sqlalchemy.orm.Session``."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # CASCADE: deletar o usuário derruba as sessões (revogação total)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    garmin_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    activity_type: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(200))
    distance_m: Mapped[float] = mapped_column(Float)
    duration_s: Mapped[float] = mapped_column(Float)
    avg_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    avg_cadence: Mapped[float | None] = mapped_column(Float)
    power: Mapped[float | None] = mapped_column(Float)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    aerobic_te: Mapped[float | None] = mapped_column(Float)
    anaerobic_te: Mapped[float | None] = mapped_column(Float)
    training_load: Mapped[float | None] = mapped_column(Float)
    feel: Mapped[int | None] = mapped_column(Integer)
    rpe: Mapped[int | None] = mapped_column(Integer)
    raw_json: Mapped[dict | None] = mapped_column(JSON)
    evaluated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Split(Base):
    __tablename__ = "splits"
    __table_args__ = (UniqueConstraint("activity_id", "idx", name="uq_split_activity_idx"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)  # ordem do split
    dist_m: Mapped[float] = mapped_column(Float)
    duration_s: Mapped[float] = mapped_column(Float)
    pace_s: Mapped[float | None] = mapped_column(Float)  # s por km (derivável, mas guardado)
    avg_hr: Mapped[int | None] = mapped_column(Integer)
    avg_cadence: Mapped[float | None] = mapped_column(Float)
    avg_temperature: Mapped[float | None] = mapped_column(Float)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    intensity_type: Mapped[str | None] = mapped_column(String(30))


class Sleep(Base):
    """Uma noite por (user_id, date)."""

    __tablename__ = "sleep"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_sleep_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    duration_s: Mapped[float] = mapped_column(Float)
    score: Mapped[int | None] = mapped_column(Integer)
    deep_pct: Mapped[float | None] = mapped_column(Float)
    rem_pct: Mapped[float | None] = mapped_column(Float)
    light_pct: Mapped[float | None] = mapped_column(Float)
    awakenings: Mapped[int | None] = mapped_column(Integer)
    bed_time: Mapped[datetime | None] = mapped_column(DateTime)
    wake_time: Mapped[datetime | None] = mapped_column(DateTime)


class Hrv(Base):
    __tablename__ = "hrv"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_hrv_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String(20))


class Rhr(Base):
    __tablename__ = "rhr"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_rhr_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[int] = mapped_column(Integer)


class BodyBattery(Base):
    __tablename__ = "body_battery"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_bodybattery_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[int | None] = mapped_column(Integer)


class Stress(Base):
    __tablename__ = "stress"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_stress_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    avg: Mapped[int | None] = mapped_column(Integer)


class DailyLoad(Base):
    """PMC (CTL/ATL/TSB) + ACWR por dia — alimenta o painel Performance."""

    __tablename__ = "load"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_load_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    ctl: Mapped[float | None] = mapped_column(Float)
    atl: Mapped[float | None] = mapped_column(Float)
    tsb: Mapped[float | None] = mapped_column(Float)
    acwr: Mapped[float | None] = mapped_column(Float)
    load_focus: Mapped[dict | None] = mapped_column(JSON)


class VdotTest(Base):
    """Prova/teste máximo que recalibra o VDOT (ex.: 10K 41:15 -> 50.2)."""

    __tablename__ = "vdot_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    distance_m: Mapped[float] = mapped_column(Float)
    time_s: Mapped[float] = mapped_column(Float)
    vdot: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30))  # prova | teste | estimado


class ZoneConfig(Base):
    """Zonas vigentes (VDOT + FC) — uma versão por calibração."""

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    zones: Mapped[dict] = mapped_column(JSON)
    valid_from: Mapped[date] = mapped_column(Date, index=True)


class Evaluation(Base):
    """Avaliação de IA — um treino (ou série) sob a intenção declarada.

    Requisito travado: grava model, prompt_version e tokens de toda chamada.
    Emenda job (18/10, EVAL-21..23): ``status`` pending|done|error +
    ``error`` com o motivo — a tentativa sobrevive à falha da NIM; o
    worker conclui a linha, o POST só a cria.
    """

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"), index=True
    )
    intent_type: Mapped[str] = mapped_column(String(40))
    intent_text: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1")
    verdict: Mapped[str] = mapped_column(String(40))
    verdict_json: Mapped[dict | None] = mapped_column(JSON)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    # Emenda job: pending -> done (worker) | error (motivo em `error`)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Race(Base):
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    name: Mapped[str] = mapped_column(String(200))
    date: Mapped[date] = mapped_column(Date, index=True)
    distance_m: Mapped[float] = mapped_column(Float)
    goal_time_s: Mapped[float | None] = mapped_column(Float)
    result_time_s: Mapped[float | None] = mapped_column(Float)
    vdot_estimated: Mapped[float | None] = mapped_column(Float)


class Pattern(Base):
    """Padrões pessoais de falha (ex.: 'km1_rápido', 'fade_15_19')."""

    __tablename__ = "patterns"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_pattern_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    name: Mapped[str] = mapped_column(String(100))
    trigger: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SyncJob(Base):
    """Job de sync — isolado por usuário e janela (requisito travado).

    Lição travada: sempre sequencial, re-puxa últimos 3 dias
    (Garmin reprocessa por até 72h) + atividades novas.
    """

    __tablename__ = "sync_jobs"
    # Lock por usuário no nível do banco (SYNC-02): um job ativo por usuário,
    # sem janela de corrida entre check e insert.
    __table_args__ = (
        Index(
            "uq_syncjobs_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    window_days: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|error
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)
    stats_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class PersonalRecord(Base):
    """Recorde pessoal de corrida — upsert por (user_id, event)."""

    __tablename__ = "personal_records"
    __table_args__ = (UniqueConstraint("user_id", "event", name="uq_pr_user_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    event: Mapped[str] = mapped_column(String(60))  # ex.: "FASTEST_5K" / "5K"
    value: Mapped[float | None] = mapped_column(Float)
    pr_date: Mapped[date | None] = mapped_column(Date)
    raw_json: Mapped[dict | None] = mapped_column(JSON)  # sempre preservado (spec)


class RacePrediction(Base):
    """Snapshot latest da predição de prova do Garmin — upsert por (user_id, event).

    Namespace de `event` distinto dos `FASTEST_*` dos PRs (design):
    predição ≠ recorde — nunca cruzar as chaves.
    """

    __tablename__ = "race_predictions"
    __table_args__ = (UniqueConstraint("user_id", "event", name="uq_racepred_user_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    event: Mapped[str] = mapped_column(String(30))  # 5K | 10K | HALF_MARATHON | MARATHON
    time_s: Mapped[float | None] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date, index=True)  # calendarDate do snapshot
    raw_json: Mapped[dict | None] = mapped_column(JSON)  # sempre preservado (spec)


class SyncState(Base):
    """last_sync por tipo de dado — memória do incremental."""

    __tablename__ = "sync_state"
    __table_args__ = (UniqueConstraint("user_id", "data_type", name="uq_syncstate_user_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    data_type: Mapped[str] = mapped_column(String(40))  # activities|sleep|hrv|rhr|stress|body_battery|records
    last_date: Mapped[date] = mapped_column(Date)  # fim da última janela concluída com sucesso


class UserHrMetric(Base):
    """Métrica fisiológica do corredor (feature hr-zones) — série
    effective-dated append-only: uma linha por mudança, nunca update.

    A vigente em D é a de maior (valid_from, id) com valid_from ≤ D;
    SEM unique de valid_from — duas mudanças no mesmo dia são duas
    linhas legítimas, resolvidas pelo tie-break id DESC."""

    __tablename__ = "user_hr_metrics"
    __table_args__ = (
        Index("ix_userhrmetrics_user_kind_valid_from", "user_id", "kind", "valid_from"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    kind: Mapped[str] = mapped_column(String(10))  # fcmax | fcrest | fclthr
    value_bpm: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(10))  # garmin | manual
    valid_from: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class HrZoneConfig(Base):
    """Config de zonas de FC — método + percentuais por zona, série
    effective-dated independente das métricas (edge do spec: mudar
    métrica não cria config e vice-versa). Zonas em bpm são derivadas
    na leitura, nunca persistidas."""

    __tablename__ = "hr_zone_configs"
    __table_args__ = (
        Index("ix_hrzoneconfigs_user_valid_from", "user_id", "valid_from"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=DEFAULT_USER_ID, index=True)
    method: Mapped[str] = mapped_column(String(10))  # lthr | fcr | fcmax
    bounds: Mapped[dict] = mapped_column(JSON)  # {"zones": [{"low", "high"} ×5]}
    valid_from: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
