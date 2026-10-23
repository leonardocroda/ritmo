"""Painel Home — digests P2 (T13): série de 10 semanas e digest de
previsões, no Postgres real.

Cenários derivados dos ACs HOME-37/38/39 e do done-when de T13: digest
com dados por evento (pins da sonda real de 15/10 + calibração vigente
— os mesmos do test_potential_calc), evento sem predição OMITIDO (nunca
"—"), ZoneConfigError -> predictions None (a Home nunca 500 por bloco
P2), volume_weeks com exatamente as 10 últimas semanas ISO e a delegação
get_potential -> get_predictions (não-regressão do painel Performance).
`_today` pinado como no test_home_service (dias relativos não são
pináveis). Valores afirmados são literais.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.auth.security import hash_password
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, PersonalRecord, RacePrediction, User
from app.home import service as home_service
from app.potential import service as potential_service
from app.vdot.calibration import Calibration
from app.vdot.zones import ZoneConfigError

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
TODAY = date(2026, 10, 23)  # sexta — pino do _today do service
MONDAY = date(2026, 10, 19)

# Calibração vigente (campos reais do vdot_zones.json — mesmo pino do
# test_potential_api)
CALIBRATION = Calibration(
    vdot=50.2,
    source="10K em 41:15",
    test_date=date(2026, 10, 3),
    distance_m=10012,
    time_s=2475,
)

# PRs canônicos + predições da sonda real (mesmos pins do test_potential_calc)
REAL_PRS = [
    ("FASTEST_10K", 2425.0, date(2024, 10, 5)),
    ("FASTEST_5K", 1163.8299560546875, date(2026, 4, 26)),
    ("FASTEST_HALF_MARATHON", 5409.188, date(2026, 5, 3)),
    ("FASTEST_MARATHON", 13925.76, date(2026, 7, 5)),
]
REAL_GARMIN = [
    ("5K", 1165.0),
    ("10K", 2447.0),
    ("HALF_MARATHON", 5437.0),
    ("MARATHON", 11989.0),
]


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def fixed_today(monkeypatch):
    """Hoje determinístico no service (dias relativos não são pináveis)."""
    monkeypatch.setattr(home_service, "_today", lambda tz: TODAY)
    return TODAY


def _new_user(db) -> User:
    user = User(
        display_name="Corredora",
        email="corredora@example.com",
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(user)
    db.flush()
    return user


def _seed_run(db, user_id, garmin_id, day, distance_m=10000.0):
    db.add(
        Activity(
            user_id=user_id,
            garmin_id=garmin_id,
            start_time=datetime(day.year, day.month, day.day, 7, 0),
            activity_type="running",
            name="Treino",
            distance_m=distance_m,
            duration_s=3600.0,
        )
    )


def _seed_prs_and_predictions(db, user_id) -> None:
    """PRs canônicos + predições da sonda — as 3 estimativas por evento."""
    for event, value, pr_date in REAL_PRS:
        db.add(PersonalRecord(user_id=user_id, event=event, value=value,
                              pr_date=pr_date, raw_json={}))
    for event, time_s in REAL_GARMIN:
        db.add(RacePrediction(user_id=user_id, event=event, time_s=time_s,
                              date=date(2026, 10, 15), raw_json={}))


# ---------------------------------------------------------------
# Digest de previsões (HOME-38/39)
# ---------------------------------------------------------------


def test_predictions_digest_with_data_for_both_events(db, fixed_today) -> None:
    """HOME-38: 10K e meia no digest com os tempos médios (average_s) —
    pins da sonda + calibração vigente: 10K (2447 + 2426,5 + 2471,1)/3,
    meia (5437 + 5353,8 + 5472,3)/3. A calibração é a do arquivo real
    (mesma fonte do painel Performance — uma fonte de verdade)."""
    user = _new_user(db)
    _seed_prs_and_predictions(db, user.id)
    db.commit()

    predictions = home_service.get_home(db, user.id, SAO_PAULO)["predictions"]

    assert predictions == [
        {"event": "10K", "time_s": 2448.2},
        {"event": "HALF_MARATHON", "time_s": 5421.0},
    ]


def test_event_without_prediction_is_omitted(db, fixed_today, monkeypatch) -> None:
    """HOME-39: evento sem predição (average_s None) fica FORA do digest —
    nunca '—', nunca número inventado. Com calibração real toda estimativa
    existiria (a equivalência VDOT sempre calcula), então o cenário é
    montado na fronteira do potential — o que conta é o digest omitir."""
    monkeypatch.setattr(
        home_service,
        "get_predictions",
        lambda db, user_id, calibration: {
            "10K": {"average_s": None},
            "HALF_MARATHON": {"average_s": 5421.0},
        },
    )
    user = _new_user(db)
    db.commit()

    predictions = home_service.get_home(db, user.id, SAO_PAULO)["predictions"]

    assert predictions == [{"event": "HALF_MARATHON", "time_s": 5421.0}]


def test_zone_config_error_predictions_null_not_500(db, fixed_today, monkeypatch) -> None:
    """Edge do design (§Erros): calibração ausente/inválida -> predictions
    None no payload — a Home NUNCA 500 por causa de um bloco P2; o resto
    do painel segue íntegro (o bloco degrada sozinho)."""

    def raise_error(path):
        raise ZoneConfigError(f"não foi possível carregar {path}")

    monkeypatch.setattr(home_service, "load_calibration", raise_error)
    user = _new_user(db)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["predictions"] is None
    assert payload["date"] == TODAY
    assert payload["verdict"] is None  # banco sem sinais — sem frase falsa
    assert len(payload["strip"]) == 7


# ---------------------------------------------------------------
# Série de 10 semanas (HOME-37 via payload)
# ---------------------------------------------------------------


def test_volume_weeks_exactly_ten_iso_weeks_ascending(db, fixed_today) -> None:
    """HOME-37 (payload): volume_weeks com exatamente as 10 últimas
    semanas ISO, ASC, terminando na corrente (segunda 19/10); semana sem
    corrida segue com 0.0 (descanso é informação)."""
    user = _new_user(db)
    _seed_run(db, user.id, "v1", date(2026, 9, 21), distance_m=20000.0)
    _seed_run(db, user.id, "v2", MONDAY, distance_m=10000.0)
    db.commit()

    weeks = home_service.get_home(db, user.id, SAO_PAULO)["volume_weeks"]

    assert len(weeks) == 10
    assert [w["week_start"] for w in weeks] == [
        date(2026, 8, 17) + timedelta(days=7 * i) for i in range(10)
    ]
    assert weeks[-1] == {"week_start": MONDAY, "km": 10.0}
    assert weeks[5] == {"week_start": date(2026, 9, 21), "km": 20.0}
    assert [w["km"] for i, w in enumerate(weeks) if i not in (5, 9)] == [0.0] * 8


def test_volume_weeks_none_without_runs_in_window(db, fixed_today) -> None:
    """Sem corrida na janela de 10 semanas não há série a dizer — bloco
    nulo (design §Components), igual ao `volume`."""
    user = _new_user(db)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["volume_weeks"] is None
    assert payload["volume"] is None


# ---------------------------------------------------------------
# Extração get_predictions — não-regressão do painel Performance
# ---------------------------------------------------------------


def test_get_potential_uses_get_predictions(db) -> None:
    """Done-when T13: o painel Performance monta o bloco `predictions`
    pela MESMA leitura extraída — get_potential delega em get_predictions
    (zero duplicação da montagem), com os pins da sonda reais."""
    user = _new_user(db)
    _seed_prs_and_predictions(db, user.id)
    db.commit()

    payload = potential_service.get_potential(db, user.id, CALIBRATION)

    assert payload["predictions"] == potential_service.get_predictions(
        db, user.id, CALIBRATION
    )
    assert payload["predictions"]["10K"]["average_s"] == 2448.2
    assert payload["predictions"]["HALF_MARATHON"]["average_s"] == 5421.0
