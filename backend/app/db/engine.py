"""Engine e sessão SQLAlchemy.

Postgres desde a v1 (AD-007), driver psycopg3 — caminho único, sem código
específico de dialeto. Config 100% via DATABASE_URL (requisito travado).
"""

from collections.abc import Iterator
from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.profile.calc import DEFAULT_BOUNDS

settings = get_settings()

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_schema() -> None:
    """Colunas de auth em bases criadas ANTES da feature (emenda UAT, 20/10).

    O ``create_all`` só cria tabela AUSENTE — nunca altera tabela
    existente. Bancos de dev/produção anteriores à feature auth têm a
    ``users`` sem ``email``/``password_hash`` e crasham no startup
    (UndefinedColumn). Migração idempotente no estilo do projeto (mesmo
    espírito do setval abaixo): zero dependência nova; Alembic fica para
    a Fase 2.5 se o schema crescer (AD-019). Condicional à coluna: base
    nova (create_all já criou tudo, inclusive a unique) não ganha índice
    redundante.
    """
    with engine.begin() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'users'"
                )
            )
        }
        if "email" in columns:
            return
        conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
        # Múltiplos NULL são permitidos em unique index (Postgres) — o seed
        # id 1 nasce sem email até o CLI vinculá-lo (AUTH-25)
        conn.execute(text("CREATE UNIQUE INDEX uq_users_email ON users (email)"))


def init_db() -> None:
    """Cria as tabelas, migra esquemas antigos e semeia o usuário default."""
    from app.db import models  # noqa: F401 — registra os modelos no Base
    from app.db.models import DEFAULT_USER_ID, HrZoneConfig, Race, User

    Base.metadata.create_all(bind=engine)
    _migrate_schema()

    with SessionLocal() as db:
        if db.get(User, DEFAULT_USER_ID) is None:
            db.add(User(id=DEFAULT_USER_ID, display_name="Leonardo"))
            db.commit()

        # HOME-22/23: a meia do countdown é fato real, não métrica
        # (decisão do spec) — semeada só quando o usuário 1 não tem
        # prova nenhuma. Guard por usuário, padrão AD-019 do seed
        # acima: re-executar não duplica, prova de outro usuário não
        # bloqueia. Sem setval — id auto como nos demais seeds de dado.
        if (
            db.query(Race)
            .filter(Race.user_id == DEFAULT_USER_ID)
            .first()
            is None
        ):
            db.add(
                Race(
                    user_id=DEFAULT_USER_ID,
                    name="The Best Açaí",
                    date=date(2026, 11, 8),
                    distance_m=21097.5,
                    goal_time_s=None,
                )
            )
            db.commit()

        # HRZ-07: o usuário 1 nasce com a config de zonas (lthr +
        # defaults, valid_from hoje) — NENHUMA métrica é seedada: vêm do
        # sync (HRZ-05) ou da edição manual; métrica manual seedada
        # bloquearia o auto-update para sempre (manual-wins). Guarda de
        # existência (padrão AD-019): re-executar não duplica.
        if (
            db.query(HrZoneConfig)
            .filter(HrZoneConfig.user_id == DEFAULT_USER_ID)
            .first()
            is None
        ):
            db.add(
                HrZoneConfig(
                    user_id=DEFAULT_USER_ID,
                    method="lthr",
                    bounds={"zones": DEFAULT_BOUNDS["lthr"]},
                    valid_from=date.today(),
                )
            )
            db.commit()

        # AUTH-27: o seed com id explícito não avança a sequência — sem o
        # setval, o primeiro INSERT sem id (register/CLI) colide com a
        # pkey 1. Pendência do handoff, corrigida aqui para acompanhar o
        # seed. Idempotente: reajusta para MAX(id) (COALESCE cobre tabela
        # vazia). Postgres-only — único dialeto (AD-007).
        db.execute(
            text("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users))")
        )
