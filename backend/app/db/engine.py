"""Engine e sessão SQLAlchemy.

SQLite em modo WAL na v1 (zero ops, requisito do plano).
Postgres na Fase 2.5 = trocar DATABASE_URL, nada mais.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args)

if engine.url.drivername.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependência FastAPI: uma sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria as tabelas e semeia o usuário default (usuário único na v1)."""
    from app.db import models  # noqa: F401 — registra os modelos no Base
    from app.db.models import DEFAULT_USER_ID, User

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.get(User, DEFAULT_USER_ID) is None:
            db.add(User(id=DEFAULT_USER_ID, display_name="Leonardo"))
            db.commit()
