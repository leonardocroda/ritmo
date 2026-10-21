"""Modelos das séries de FC (T1, feature hr-zones) — integração no Postgres.

Append-only effective-dated (design §Data Models): SEM unique de
valid_from — duas mudanças no mesmo dia são duas linhas legítimas e a
resolução da vigente usa o tie-break (valid_from DESC, id DESC). O
usuário de teste nasce com id via sequência e todos os counts filtram
pelo seu user_id: o seed do usuário 1 (config lthr, T3) não interfere.
"""

from datetime import date

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError

from app.auth.security import hash_password
from app.db.base import Base
from app.db.engine import SessionLocal, init_db
from app.db.models import HrZoneConfig, User, UserHrMetric

TODAY = date(2026, 10, 21)

# Defaults lthr do spec (HRZ-08) — literal da fixture, nunca importado da
# implementação (lições L-001/L-002)
LTHR_BOUNDS = {
    "zones": [
        {"low": 65, "high": 80},
        {"low": 80, "high": 89},
        {"low": 89, "high": 95},
        {"low": 95, "high": 100},
        {"low": 100, "high": None},
    ]
}


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _new_user(db) -> User:
    """Usuário de teste próprio (id via sequência — não interfere no seed)."""
    user = User(
        display_name="Corredora",
        email="corredora@example.com",
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(user)
    db.flush()
    return user


def test_same_day_double_insert_allowed_without_unique_valid_from(db) -> None:
    """Done-when T1: duas linhas no mesmo dia (mesma kind) coexistem nas
    duas séries — append-only sem unique de valid_from, resolução futura
    confia no tie-break por id. Índices compostos presentes, PK em id,
    bounds JSON atravessa íntegro."""
    user = _new_user(db)
    for value in (177, 185):  # segunda mudança no mesmo dia = segunda linha
        db.add(
            UserHrMetric(
                user_id=user.id, kind="fclthr", value_bpm=value,
                source="manual", valid_from=TODAY,
            )
        )
    db.add(HrZoneConfig(user_id=user.id, method="lthr", bounds=LTHR_BOUNDS, valid_from=TODAY))
    db.add(
        HrZoneConfig(
            user_id=user.id, method="fcr",
            bounds={"zones": [{"low": 50, "high": 60}]}, valid_from=TODAY,
        )
    )
    db.commit()

    metrics = db.query(UserHrMetric).filter(UserHrMetric.user_id == user.id).all()
    assert [m.value_bpm for m in metrics] == [177, 185]
    assert metrics[1].id > metrics[0].id  # tie-break id DESC resolve a vigente

    configs = db.query(HrZoneConfig).filter(HrZoneConfig.user_id == user.id).all()
    assert [c.method for c in configs] == ["lthr", "fcr"]
    assert configs[0].bounds == LTHR_BOUNDS  # round-trip do JSON

    # Índice composto (user_id, kind, valid_from) e nenhum unique na série
    metrics_table = Base.metadata.tables["user_hr_metrics"]
    assert [c.name for c in metrics_table.primary_key.columns] == ["id"]
    assert not [c for c in metrics_table.constraints if isinstance(c, UniqueConstraint)]
    assert not any(idx.unique for idx in metrics_table.indexes)
    assert any(
        [c.name for c in idx.columns] == ["user_id", "kind", "valid_from"]
        for idx in metrics_table.indexes
    )

    # Configs: índice (user_id, valid_from), mesma regra append-only
    configs_table = Base.metadata.tables["hr_zone_configs"]
    assert [c.name for c in configs_table.primary_key.columns] == ["id"]
    assert not [c for c in configs_table.constraints if isinstance(c, UniqueConstraint)]
    assert not any(idx.unique for idx in configs_table.indexes)
    assert any(
        [c.name for c in idx.columns] == ["user_id", "valid_from"]
        for idx in configs_table.indexes
    )


def test_user_id_fk_blocks_nonexistent_user(db) -> None:
    """Done-when T1: FK em user_id impede usuário inexistente nas duas
    tabelas — nenhuma linha órfã nas séries do perfil."""
    db.add(
        UserHrMetric(
            user_id=999, kind="fcmax", value_bpm=190,
            source="garmin", valid_from=TODAY,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    db.add(
        HrZoneConfig(
            user_id=999, method="lthr",
            bounds={"zones": []}, valid_from=TODAY,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assert db.query(UserHrMetric).filter(UserHrMetric.user_id == 999).count() == 0
    assert db.query(HrZoneConfig).filter(HrZoneConfig.user_id == 999).count() == 0
