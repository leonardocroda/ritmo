"""Service de séries de FC (T4, feature hr-zones) — integração no Postgres.

Resolução vigente-na-data (HRZ-12), escritas idempotentes com
manual-wins (HRZ-03/06) e validação cross-field do conjunto merge
(HRZ-04) — 1:1 aos ACs, chamadas diretas ao service com usuário
próprio (padrão test_health_api). Datas fixas em 2026-10 pinam o
effective-dating sem depender do relógio.
"""

from datetime import date

import pytest

from app.auth.security import hash_password
from app.db.engine import SessionLocal, init_db
from app.db.models import HrZoneConfig, User, UserHrMetric
from app.profile import service
from app.profile.calc import DEFAULT_BOUNDS

# Calendário fixo dos pins de vigência (T4)
D05, D10, D15, D20, D21 = (
    date(2026, 10, 5),
    date(2026, 10, 10),
    date(2026, 10, 15),
    date(2026, 10, 20),
    date(2026, 10, 21),
)

LTHR_DEFAULTS_ZONES = [
    {"low": 65, "high": 80},
    {"low": 80, "high": 89},
    {"low": 89, "high": 95},
    {"low": 95, "high": 100},
    {"low": 100, "high": None},
]


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


def _new_user(db, email: str = "corredora@example.com") -> User:
    """Usuário de teste próprio (id via sequência — não interfere no seed)."""
    user = User(
        display_name="Corredora",
        email=email,
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------
# Resolução vigente-na-data (HRZ-12)
# ---------------------------------------------------------------


def test_metric_on_resolves_vigente_na_data(db) -> None:
    """HRZ-12: linha de 20/10 não é lida com on_date de 19/10 nem antes
    dela — a vigente em D é a última com valid_from ≤ D."""
    user = _new_user(db)
    assert service.set_metric(db, user.id, "fcmax", 170, "garmin", on_date=D10)
    assert service.set_metric(db, user.id, "fcmax", 180, "garmin", on_date=D20)
    db.commit()

    assert service.metric_on(db, user.id, "fcmax", date(2026, 10, 9)) is None
    row = service.metric_on(db, user.id, "fcmax", D15)
    assert (row.value_bpm, row.valid_from) == (170, D10)
    row = service.metric_on(db, user.id, "fcmax", D21)
    assert (row.value_bpm, row.valid_from) == (180, D20)


def test_metric_on_tie_break_same_day_prefers_higher_id(db) -> None:
    """HRZ-12 (done-when T4): duas mudanças no mesmo dia → a vigente é a
    de maior id (tie-break id DESC), não a primeira."""
    user = _new_user(db)
    assert service.set_metric(db, user.id, "fclthr", 170, "manual", on_date=D20)
    assert service.set_metric(db, user.id, "fclthr", 175, "manual", on_date=D20)
    db.commit()

    assert db.query(UserHrMetric).count() == 2  # ambas persistem
    row = service.metric_on(db, user.id, "fclthr", D21)
    assert row.value_bpm == 175


def test_metrics_on_returns_all_kinds_with_none_for_missing(db) -> None:
    """HRZ-01 (shape da leitura): metrics_on devolve as 3 kinds — só a
    semeada tem linha, as outras None (nunca configurado)."""
    user = _new_user(db)
    assert service.set_metric(db, user.id, "fcmax", 190, "garmin", on_date=D10)
    db.commit()

    metrics = service.metrics_on(db, user.id, D21)
    assert set(metrics) == {"fcmax", "fcrest", "fclthr"}
    assert (metrics["fcmax"].value_bpm, metrics["fcmax"].source) == (190, "garmin")
    assert metrics["fcrest"] is None
    assert metrics["fclthr"] is None


def test_config_on_effective_dated(db) -> None:
    """HRZ-12: config vigente em D — lthr até 19/10, fcr de 20/10 em
    diante; antes da primeira config, None."""
    user = _new_user(db)
    assert service.set_config(db, user.id, "lthr", DEFAULT_BOUNDS["lthr"], on_date=D10)
    assert service.set_config(db, user.id, "fcr", DEFAULT_BOUNDS["fcr"], on_date=D20)
    db.commit()

    assert service.config_on(db, user.id, date(2026, 10, 9)) is None
    assert service.config_on(db, user.id, D15).method == "lthr"
    assert service.config_on(db, user.id, D21).method == "fcr"
    # tie-break id DESC no mesmo dia
    assert service.set_config(db, user.id, "fcmax", DEFAULT_BOUNDS["fcmax"], on_date=D20)
    db.commit()
    assert service.config_on(db, user.id, D21).method == "fcmax"


# ---------------------------------------------------------------
# Escrita idempotente com manual-wins (HRZ-03/06)
# ---------------------------------------------------------------


def test_set_metric_same_value_is_idempotent(db) -> None:
    """HRZ-03: valor igual ao vigente → False sem linha nova — vale para
    manual sobre manual e para garmin sobre manual (o check de igualdade
    precede o manual-wins)."""
    user = _new_user(db)
    assert service.set_metric(db, user.id, "fclthr", 177, "manual")  # cria
    db.commit()

    assert service.set_metric(db, user.id, "fclthr", 177, "manual") is False
    assert service.set_metric(db, user.id, "fclthr", 177, "garmin") is False
    db.commit()

    assert db.query(UserHrMetric).count() == 1
    row = service.metric_on(db, user.id, "fclthr", date.today())
    assert (row.value_bpm, row.source) == (177, "manual")


def test_set_metric_garmin_never_overrides_manual(db) -> None:
    """HRZ-06 (done-when T4): vigente manual + garmin com valor novo →
    False sem linha — a edição manual nunca é sobrescrita pelo sync."""
    user = _new_user(db)
    assert service.set_metric(db, user.id, "fclthr", 177, "manual")
    db.commit()

    assert service.set_metric(db, user.id, "fclthr", 185, "garmin") is False
    db.commit()

    assert db.query(UserHrMetric).count() == 1
    row = service.metric_on(db, user.id, "fclthr", date.today())
    assert (row.value_bpm, row.source) == (177, "manual")


def test_set_metric_inserts_on_real_change(db) -> None:
    """HRZ-02/03: valor novo cria linha — garmin sobre ausente, garmin
    sobre garmin e manual sobre garmin (a edição manual VENCE o sync no
    sentido inverso: é escreva legítima)."""
    user = _new_user(db)
    assert service.set_metric(db, user.id, "fcmax", 190, "garmin")
    assert service.set_metric(db, user.id, "fcmax", 192, "garmin")
    assert service.set_metric(db, user.id, "fcmax", 188, "manual")
    db.commit()

    assert db.query(UserHrMetric).count() == 3
    row = service.metric_on(db, user.id, "fcmax", date.today())
    assert (row.value_bpm, row.source) == (188, "manual")


def test_set_config_idempotent_same_method_and_bounds(db) -> None:
    """HRZ-08 (done-when T4): mesma config (método E bounds) → False sem
    linha nova; bounds diferente no mesmo método → config nova."""
    user = _new_user(db)
    assert service.set_config(db, user.id, "lthr", DEFAULT_BOUNDS["lthr"])
    db.commit()

    assert service.set_config(db, user.id, "lthr", DEFAULT_BOUNDS["lthr"]) is False
    db.commit()
    assert db.query(HrZoneConfig).filter(HrZoneConfig.user_id == user.id).count() == 1

    custom = [
        {"low": 64, "high": 79},
        {"low": 79, "high": 88},
        {"low": 88, "high": 94},
        {"low": 94, "high": 99},
        {"low": 99, "high": None},
    ]
    assert service.set_config(db, user.id, "lthr", custom)
    db.commit()
    assert db.query(HrZoneConfig).filter(HrZoneConfig.user_id == user.id).count() == 2


def test_set_config_new_method_inserts(db) -> None:
    """HRZ-08: método novo → config nova (a métrica é série independente
    — nada em user_hr_metrics muda)."""
    user = _new_user(db)
    assert service.set_config(db, user.id, "lthr", DEFAULT_BOUNDS["lthr"])
    assert service.set_config(db, user.id, "fcr", DEFAULT_BOUNDS["fcr"])
    db.commit()

    rows = (
        db.query(HrZoneConfig)
        .filter(HrZoneConfig.user_id == user.id)
        .order_by(HrZoneConfig.id)
        .all()
    )
    assert [r.method for r in rows] == ["lthr", "fcr"]
    assert service.config_on(db, user.id, date.today()).method == "fcr"
    assert db.query(UserHrMetric).count() == 0  # métricas intactas


# ---------------------------------------------------------------
# Validação do conjunto (HRZ-04 + edge cases)
# ---------------------------------------------------------------


def test_validate_metrics_set_rejects_out_of_range(db) -> None:
    """HRZ-04: limites por métrica (fcmax 100–230, fcrest 30–110, fclthr
    100–220) → MetricValidationError com campo e faixa exatos."""
    cases = [
        ("fcmax", 99, "deve estar entre 100 e 230 bpm"),
        ("fcmax", 231, "deve estar entre 100 e 230 bpm"),
        ("fcrest", 29, "deve estar entre 30 e 110 bpm"),
        ("fcrest", 111, "deve estar entre 30 e 110 bpm"),
        ("fclthr", 99, "deve estar entre 100 e 220 bpm"),
        ("fclthr", 221, "deve estar entre 100 e 220 bpm"),
    ]
    for field, value, reason in cases:
        with pytest.raises(service.MetricValidationError) as excinfo:
            service.validate_metrics_set({}, {field: value})
        assert excinfo.value.field == field, (field, value)
        assert str(excinfo.value) == reason


def test_validate_metrics_set_rejects_incoherent_set(db) -> None:
    """HRZ-04 + edge: incoerências fcrest ≥ fcmax e fclthr ≥ fcmax
    apontam o campo e o motivo exatos — inclusive quando a incoerência
    só existe no MERGE (fcmax vigente + fclthr novo, e vice-versa)."""
    with pytest.raises(service.MetricValidationError) as excinfo:
        service.validate_metrics_set({}, {"fcrest": 105, "fcmax": 100})
    assert excinfo.value.field == "fcrest"
    assert str(excinfo.value) == "FC de repouso acima da FC máxima"

    # a igualdade também é incoerente (≥ no spec)
    with pytest.raises(service.MetricValidationError) as excinfo:
        service.validate_metrics_set({}, {"fclthr": 190, "fcmax": 190})
    assert excinfo.value.field == "fclthr"
    assert str(excinfo.value) == "limiar acima da FC máxima"  # spec (edge)

    # merge: fcmax vigente 190, update fclthr 195 → incoerente
    with pytest.raises(service.MetricValidationError) as excinfo:
        service.validate_metrics_set({"fcmax": 190}, {"fclthr": 195})
    assert excinfo.value.field == "fclthr"
    assert str(excinfo.value) == "limiar acima da FC máxima"

    # merge no sentido inverso: fclthr vigente 185, update fcmax 180
    with pytest.raises(service.MetricValidationError) as excinfo:
        service.validate_metrics_set({"fclthr": 185}, {"fcmax": 180})
    assert excinfo.value.field == "fclthr"


def test_validate_metrics_set_accepts_valid_and_boundaries(db) -> None:
    """HRZ-04: limites inclusivos por métrica (testados sozinhos — os
    extremos de fcmax e fclthr não coexistem com coerência, já que
    fclthr ≥ fcmax é erro) e conjunto coerente completo passa."""
    service.validate_metrics_set({}, {"fcmax": 100})
    service.validate_metrics_set({}, {"fcmax": 230})
    service.validate_metrics_set({}, {"fcrest": 30})
    service.validate_metrics_set({}, {"fcrest": 110})
    service.validate_metrics_set({}, {"fclthr": 100})
    service.validate_metrics_set({}, {"fclthr": 220})
    service.validate_metrics_set(
        {"fcmax": 190}, {"fcrest": 45, "fclthr": 177}
    )  # merge coerente
    service.validate_metrics_set({"fcmax": 190}, {"fcmax": 195})  # update da própria fcmax


# ---------------------------------------------------------------
# zonas_on — config + zonas derivadas vigentes na data (HRZ-10/11/12)
# ---------------------------------------------------------------


def test_zones_on_pairs_config_with_derived_zones(db) -> None:
    """HRZ-12/10/11: zonas_on devolve a config vigente na data + as
    zonas derivadas (fclthr 177 lthr → [115, 142, 158, 168, 177+]);
    antes da primeira config → (None, None); config sem a métrica
    exigida → (config, None) — estado vazio honesto."""
    user = _new_user(db)
    assert service.set_config(db, user.id, "lthr", DEFAULT_BOUNDS["lthr"], on_date=D10)
    assert service.set_metric(db, user.id, "fclthr", 177, "manual", on_date=D10)
    db.commit()

    config, zones = service.zones_on(db, user.id, D21)
    assert config.method == "lthr"
    assert config.bounds == {"zones": LTHR_DEFAULTS_ZONES}
    assert zones == [
        {"n": 1, "low": 115, "high": 142},
        {"n": 2, "low": 142, "high": 158},
        {"n": 3, "low": 158, "high": 168},
        {"n": 4, "low": 168, "high": 177},
        {"n": 5, "low": 177, "high": None},
    ]

    # antes da config: nada vigente
    assert service.zones_on(db, user.id, date(2026, 10, 9)) == (None, None)

    # config vigente sem a métrica exigida pelo método → zonas None
    other = _new_user(db, email="outra@example.com")
    assert service.set_config(db, other.id, "lthr", DEFAULT_BOUNDS["lthr"], on_date=D10)
    db.commit()
    config, zones = service.zones_on(db, other.id, D21)
    assert config.method == "lthr"
    assert zones is None
