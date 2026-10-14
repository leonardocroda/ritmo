"""Engine e sessão SQLAlchemy.

Postgres desde a v1 (AD-007), driver psycopg3 — caminho único, sem código
específico de dialeto. Config 100% via DATABASE_URL (requisito travado).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

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


def init_db() -> None:
    """Cria as tabelas e semeia o usuário default (usuário único na v1)."""
    from app.db import models  # noqa: F401 — registra os modelos no Base
    from app.db.models import DEFAULT_USER_ID, User

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.get(User, DEFAULT_USER_ID) is None:
            db.add(User(id=DEFAULT_USER_ID, display_name="Leonardo"))
            db.commit()
