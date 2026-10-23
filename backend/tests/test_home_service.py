"""Painel Home — montagem do service (T5), no Postgres real.

Cenários derivados dos done-when de T5 e dos ACs HOME-01/10/14..16/19/
20/24: sinais vindos de `get_health(8)` (consistência HRV == Saúde por
construção), strip de 7 dias com lacuna zerada, último treino só
RUNNING_TYPES, countdown da próxima prova (hoje/passada/sem prova),
volume semanal, banco vazio -> veredito None e blocos nulos. `_today`
pinado (padrão do suite do health) — datas relativas a hoje não são
pináveis com fixtures fixas. Valores afirmados são literais.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.auth.security import hash_password
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, DailyLoad, Hrv, Race, Sleep, User
from app.health.service import get_health
from app.home import service as home_service

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
TODAY = date(2026, 10, 23)  # sexta — pino do _today do service
MONDAY = date(2026, 10, 19)


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


def _seed_hrv(db, user_id, day, value):
    db.add(Hrv(user_id=user_id, date=day, value=value))


def _seed_sleep(db, user_id, day, duration_s):
    db.add(Sleep(user_id=user_id, date=day, duration_s=duration_s, score=80))


def _seed_load(db, user_id, day, tsb, acwr=None):
    db.add(DailyLoad(user_id=user_id, date=day, ctl=50.0, atl=55.0, tsb=tsb, acwr=acwr))


def _seed_race(db, user_id, day, name="Prova"):
    db.add(Race(user_id=user_id, name=name, date=day, distance_m=21097.5))


def _seed_activity(db, user_id, garmin_id, day, activity_type="running",
                   distance_m=10000.0, training_load=None, evaluated=False):
    activity = Activity(
        user_id=user_id,
        garmin_id=garmin_id,
        start_time=datetime(day.year, day.month, day.day, 7, 0),
        activity_type=activity_type,
        name="Treino",
        distance_m=distance_m,
        duration_s=3600.0,
        training_load=training_load,
        evaluated=evaluated,
    )
    db.add(activity)
    db.flush()
    return activity


def _seed_full_signals(db, user_id) -> None:
    """HRV UNBALANCED (média 7d 40 abaixo da banda ~[48,4, 61,6]) +
    última noite 6h (abaixo do piso) + forma TSB −5 -> V1."""
    for offset in range(21):  # 21 dias estáveis de 60ms (25/09..15/10)
        _seed_hrv(db, user_id, date(2026, 9, 25) + timedelta(days=offset), 60.0)
    for offset in range(7):  # semana de 40ms (16..22/10) -> UNBALANCED
        _seed_hrv(db, user_id, date(2026, 10, 16) + timedelta(days=offset), 40.0)
    for offset in range(7):  # 7 noites de 8h (15..21/10)
        _seed_sleep(db, user_id, date(2026, 10, 15) + timedelta(days=offset), 28800.0)
    _seed_sleep(db, user_id, date(2026, 10, 22), 21600.0)  # última: 6h
    _seed_load(db, user_id, date(2026, 10, 22), -5.0, acwr=1.2)


# ---------------------------------------------------------------
# Sinais + veredito (montagem das fontes existentes)
# ---------------------------------------------------------------


def test_signals_assembled_from_health_and_load(db, fixed_today) -> None:
    """AC HOME-10/19: HRV current do get_health(8), última noite com
    delta das 8 noites, forma da última linha de `load` -> V1 com
    frase/tom do motor."""
    user = _new_user(db)
    _seed_full_signals(db, user.id)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["verdict"] == {
        "phrase": "Recuperação em dívida",
        "tone": "alert",
        "rule": "V1",
    }
    assert payload["signals"]["hrv"] == {
        "value": 40.0,
        "status": "UNBALANCED",
        "as_of": date(2026, 10, 22),
    }
    assert payload["signals"]["sleep"] == {
        "duration_s": 21600.0,
        "delta_s": -7200.0,  # 6h vs média de 8h das 7 anteriores
        "as_of": date(2026, 10, 22),
    }
    assert payload["signals"]["fitness"] == {
        "tsb": -5.0,
        "acwr": 1.2,
        "as_of": date(2026, 10, 22),
    }


def test_hrv_status_matches_health_panel(db, fixed_today) -> None:
    """AC de consistência: mesmo fixture -> status na Home == status no
    painel Saúde (mesma função AD-010, não reimplementação)."""
    user = _new_user(db)
    _seed_full_signals(db, user.id)
    db.commit()

    home = home_service.get_home(db, user.id, SAO_PAULO)
    health = get_health(db, user.id, 8, SAO_PAULO)

    assert home["signals"]["hrv"]["status"] == health["hrv"]["current"]["status"]
    assert home["signals"]["hrv"]["status"] == "UNBALANCED"
    assert home["signals"]["hrv"]["value"] == health["hrv"]["current"]["value"]
    assert home["signals"]["hrv"]["as_of"] == health["hrv"]["current"]["date"]


def test_partial_data_honest_dia_comum(db, fixed_today) -> None:
    """Edge do spec: só forma existe (sem sono/HRV) -> 'Dia comum' com
    chip de forma — nunca frase de alerta sem evidência."""
    user = _new_user(db)
    _seed_load(db, user.id, date(2026, 10, 20), -5.0, acwr=1.2)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["verdict"]["rule"] == "V6"
    assert payload["verdict"]["phrase"] == "Dia comum, sem urgências"
    assert payload["signals"]["hrv"] is None
    assert payload["signals"]["sleep"] is None
    assert payload["signals"]["fitness"]["tsb"] == -5.0


# ---------------------------------------------------------------
# Strip 7 dias (carga da PMC, lacuna zerada)
# ---------------------------------------------------------------


def test_strip_seven_days_ending_today_with_gaps(db, fixed_today) -> None:
    """AC HOME-14/15: exatamente 7 dias terminando hoje; dia sem
    atividade = carga 0.0 (descanso é informação); atividade fora da
    janela não entra."""
    user = _new_user(db)
    _seed_activity(db, user.id, "a0", TODAY - timedelta(days=9), training_load=99.0)
    _seed_activity(db, user.id, "a1", TODAY - timedelta(days=6), training_load=50.0)
    _seed_activity(db, user.id, "a2", TODAY - timedelta(days=4), training_load=30.0)
    _seed_activity(db, user.id, "a3", TODAY, training_load=20.0)
    db.commit()

    strip = home_service.get_home(db, user.id, SAO_PAULO)["strip"]

    assert strip == [
        {"date": TODAY - timedelta(days=6), "load": 50.0},
        {"date": TODAY - timedelta(days=5), "load": 0.0},
        {"date": TODAY - timedelta(days=4), "load": 30.0},
        {"date": TODAY - timedelta(days=3), "load": 0.0},
        {"date": TODAY - timedelta(days=2), "load": 0.0},
        {"date": TODAY - timedelta(days=1), "load": 0.0},
        {"date": TODAY, "load": 20.0},
    ]


# ---------------------------------------------------------------
# Último treino (só RUNNING_TYPES) + volume
# ---------------------------------------------------------------


def test_last_activity_is_running_not_strength(db, fixed_today) -> None:
    """AC HOME-19/24: última corrida vence mesmo com força mais recente;
    carrega id/date/distância/avaliado."""
    user = _new_user(db)
    _seed_activity(db, user.id, "s1", TODAY, "strength_training", distance_m=0.0)
    run = _seed_activity(db, user.id, "r1", TODAY - timedelta(days=1), "running",
                         distance_m=8000.0, evaluated=True)
    db.commit()

    last = home_service.get_home(db, user.id, SAO_PAULO)["last_activity"]

    assert last == {
        "id": run.id,
        "date": TODAY - timedelta(days=1),
        "distance_m": 8000.0,
        "evaluated": True,
    }


def test_last_activity_none_without_runs(db, fixed_today) -> None:
    """AC HOME-24: sem corridas (só força) o chip é omitido, não
    renderiza estado vazio."""
    user = _new_user(db)
    _seed_activity(db, user.id, "s1", TODAY, "strength_training", distance_m=0.0)
    db.commit()

    assert home_service.get_home(db, user.id, SAO_PAULO)["last_activity"] is None


def test_volume_weekly_from_running_types(db, fixed_today) -> None:
    """AC HOME-20: semana corrente vs média das 4 completas (só corrida
    conta — força não entra); P2 (volume_weeks/predictions) fica None
    até T13."""
    user = _new_user(db)
    _seed_activity(db, user.id, "v1", date(2026, 9, 21), distance_m=20000.0)
    _seed_activity(db, user.id, "v2", date(2026, 9, 28), distance_m=30000.0)
    _seed_activity(db, user.id, "v3", date(2026, 10, 5), distance_m=40000.0)
    _seed_activity(db, user.id, "v4", date(2026, 10, 12), distance_m=45000.0)
    _seed_activity(db, user.id, "v5", date(2026, 10, 18), distance_m=5000.0)  # domingo
    _seed_activity(db, user.id, "v6", MONDAY, distance_m=10000.0)
    _seed_activity(db, user.id, "s9", TODAY, "strength_training", distance_m=5000.0)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["volume"] == {
        "week_km": 10.0,
        "avg4_km": 35.0,
        "delta_pct": -71.4,
    }
    assert payload["volume_weeks"] is None
    assert payload["predictions"] is None


def test_volume_none_without_recent_runs(db, fixed_today) -> None:
    """Edge (design §Components volume | None): sem corrida na janela
    de 10 semanas não há volume a dizer — bloco nulo; o último treino
    (sem janela) continua presente."""
    user = _new_user(db)
    _seed_activity(db, user.id, "old", TODAY - timedelta(days=100), distance_m=10000.0)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["volume"] is None
    assert payload["last_activity"]["distance_m"] == 10000.0


# ---------------------------------------------------------------
# Countdown da próxima prova
# ---------------------------------------------------------------


def test_countdown_picks_nearest_upcoming_race(db, fixed_today) -> None:
    """AC HOME-22: provas passadas ignoradas; a próxima mais próxima
    vence com days_left = prova − hoje."""
    user = _new_user(db)
    _seed_race(db, user.id, TODAY - timedelta(days=5), name="Passou")
    _seed_race(db, user.id, TODAY + timedelta(days=10), name="Alvo")
    _seed_race(db, user.id, TODAY + timedelta(days=20), name="Depois")
    db.commit()

    assert home_service.get_home(db, user.id, SAO_PAULO)["countdown"] == {
        "name": "Alvo",
        "date": TODAY + timedelta(days=10),
        "days_left": 10,
    }


def test_countdown_race_today_days_left_zero(db, fixed_today) -> None:
    """AC HOME-22: prova HOJE -> payload carrega 0 (o 'é hoje' é
    render do frontend)."""
    user = _new_user(db)
    _seed_race(db, user.id, TODAY, name="Dia D")
    db.commit()

    countdown = home_service.get_home(db, user.id, SAO_PAULO)["countdown"]
    assert countdown["days_left"] == 0
    assert countdown["date"] == TODAY


def test_countdown_past_race_only_is_none(db, fixed_today) -> None:
    """AC HOME-22: só prova passada -> countdown None (chip some quando
    a prova passa)."""
    user = _new_user(db)
    _seed_race(db, user.id, TODAY - timedelta(days=1), name="Ontem foi")
    db.commit()

    assert home_service.get_home(db, user.id, SAO_PAULO)["countdown"] is None


def test_countdown_no_races_is_none(db, fixed_today) -> None:
    """Sem prova -> countdown None."""
    user = _new_user(db)
    db.commit()

    assert home_service.get_home(db, user.id, SAO_PAULO)["countdown"] is None


# ---------------------------------------------------------------
# Banco vazio: veredito None + blocos nulos (estado orientando sync)
# ---------------------------------------------------------------


def test_empty_bank_verdict_none_and_null_blocks(db, fixed_today) -> None:
    """AC HOME-01/34 (payload): nenhum dado de saúde/carga/atividade ->
    veredito None (sem frase), sinais nulos, sem recomendação; strip
    estrutural segue com 7 dias zerados."""
    user = _new_user(db)
    db.commit()

    payload = home_service.get_home(db, user.id, SAO_PAULO)

    assert payload["date"] == TODAY
    assert payload["verdict"] is None
    assert payload["signals"] == {"hrv": None, "sleep": None, "fitness": None}
    assert payload["last_activity"] is None
    assert payload["volume"] is None
    assert payload["countdown"] is None
    assert payload["recommendations"] == []
    assert payload["strip"] == [
        {"date": TODAY - timedelta(days=offset), "load": 0.0} for offset in range(6, -1, -1)
    ]
