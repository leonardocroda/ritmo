"""Painel Saúde — service direto (T3) + HTTP (T4), no Postgres real.

User-scope (T3, USR-03/06): toda leitura filtra pelo ``user_id`` do
usuário da sessão — os testes diretos criam um usuário próprio e o
passam ao service; os HTTP usam ``session_client`` (sessão real por
usuário, sem o override do conftest) e semeiam com o ``user_id``
devolvido.

T3: chamadas diretas a `get_health` com seeds ORM (o domínio lê
exclusivamente o banco próprio — AD-002; nenhuma chamada Garmin). T4:
TestClient cobrindo a superfície HTTP (422/blocos null/fallback de tz).
Valores afirmados são literais derivados das fixtures — nunca
constantes compartilhadas com a implementação (lições L-001/L-002).

Convenção do sync (mappers.py): bed_time/wake_time são wall clock GMT
naive que caem no próprio calendarDate (01:16 GMT = 22:16 local da
véspera) — os seeds reproduzem o shape real para pinar a conversão.
"""

from datetime import date, datetime, timedelta
import logging
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.auth.security import hash_password
from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, DailyLoad, Hrv, Rhr, Sleep, Stress, User
from app.health import router as health_router
from app.health import service

SAO_PAULO = ZoneInfo("America/Sao_Paulo")

# "Hoje" fixo dos pins de lifestyle (janela 60d: 17/08..16/10/2026 ->
# 9 semanas ISO; 17/08/2026 é segunda)
TODAY = date(2026, 10, 16)


@pytest.fixture()
def db():
    """Schema criado pelo init_db (o conftest derruba antes de cada teste)."""
    init_db()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def fixed_today(monkeypatch):
    """Lifestyle determinístico: `_today` injetado (dias relativos a hoje
    não são pináveis com datas fixas)."""
    monkeypatch.setattr(service, "_today", lambda tz: TODAY)
    return TODAY


def _new_user(db, email: str = "corredora@example.com") -> User:
    """Usuário de teste para os testes diretos do service (id via sequência)."""
    user = User(
        display_name="Corredora",
        email=email,
        password_hash=hash_password("senha-segura-123"),
    )
    db.add(user)
    db.flush()
    return user


def _seed_sleep(db, user_id: int, day, duration_s, score=70, rem_pct=14.0,
                deep_pct=25.0, light_pct=61.0, awakenings=2, bed=None, wake=None):
    db.add(
        Sleep(
            user_id=user_id,
            date=day,
            duration_s=duration_s,
            score=score,
            rem_pct=rem_pct,
            deep_pct=deep_pct,
            light_pct=light_pct,
            awakenings=awakenings,
            bed_time=bed,
            wake_time=wake,
        )
    )


def _seed_hrv(db, user_id: int, day, value, status="BALANCED"):
    db.add(Hrv(user_id=user_id, date=day, value=value, status=status))


def _seed_rhr(db, user_id: int, day, value):
    db.add(Rhr(user_id=user_id, date=day, value=value))


def _seed_stress(db, user_id: int, day, avg):
    db.add(Stress(user_id=user_id, date=day, avg=avg))


def _seed_load(db, user_id: int, day, ctl, atl, tsb, acwr=None):
    """Linha de `load` (PMC do sync) — acwr null = janela 28d incompleta."""
    db.add(DailyLoad(user_id=user_id, date=day, ctl=ctl, atl=atl, tsb=tsb, acwr=acwr))


def _seed_activity(db, user_id: int, garmin_id, start, activity_type, name="Treino"):
    db.add(
        Activity(
            user_id=user_id,
            garmin_id=garmin_id,
            start_time=start,
            activity_type=activity_type,
            name=name,
            distance_m=0.0,
            duration_s=3600.0,
        )
    )


# Noites do painel completo (shapes do design §Contrato):
# 13/10 adequada (7,5h), 14/10 curta (5,83h), 15/10 neutra (6,5h)
NIGHTS = [
    # (date, duration_s, score, hrv, bed GMT, wake GMT)
    (date(2026, 10, 13), 27000, 80, 82.0, datetime(2026, 10, 13, 1, 16), datetime(2026, 10, 13, 8, 2)),
    (date(2026, 10, 14), 21000, 60, 68.0, datetime(2026, 10, 14, 1, 27), datetime(2026, 10, 14, 7, 32)),
    (date(2026, 10, 15), 23400, 70, 75.0, datetime(2026, 10, 15, 1, 16), datetime(2026, 10, 15, 8, 2)),
]


def _seed_full_health(db, user_id: int) -> None:
    for day, duration_s, score, hrv, bed, wake in NIGHTS:
        _seed_sleep(db, user_id, day, duration_s, score=score, bed=bed, wake=wake)
        _seed_hrv(db, user_id, day, hrv)
    _seed_rhr(db, user_id, date(2026, 10, 13), 45)
    _seed_rhr(db, user_id, date(2026, 10, 14), 44)
    _seed_rhr(db, user_id, date(2026, 10, 15), 43)
    _seed_stress(db, user_id, date(2026, 10, 13), 25)
    _seed_stress(db, user_id, date(2026, 10, 14), None)  # dia sem avg -> fora da série
    _seed_stress(db, user_id, date(2026, 10, 15), 23)
    # Força: 4 semanas completas (streak 4) + 1 sessão na corrente;
    # janela de 60d (17/08..16/10) contém as 4 semanas batidas
    strength_days = [date(2026, 9, 15), date(2026, 9, 17), date(2026, 9, 22),
                     date(2026, 9, 24), date(2026, 9, 29), date(2026, 10, 1),
                     date(2026, 10, 6), date(2026, 10, 8), date(2026, 10, 13)]
    for i, day in enumerate(strength_days):
        _seed_activity(db, user_id, f"s{i}",
                       datetime(day.year, day.month, day.day, 7, 0),
                       "strength_training", "Força")
    # Yoga: 3 na janela + 1 antes dela (01/08 < 17/08)
    for i, day in enumerate((date(2026, 8, 1), date(2026, 9, 23),
                             date(2026, 10, 7), date(2026, 10, 14))):
        _seed_activity(db, user_id, f"y{i}",
                       datetime(day.year, day.month, day.day, 6, 0),
                       "yoga", "Yoga")


# ---------------------------------------------------------------
# T3 — service.get_health (chamadas diretas com seeds)
# ---------------------------------------------------------------


def test_get_health_full_payload_from_seeds(db, fixed_today) -> None:
    """Done-when T3: os 6 blocos montados a partir do banco — pontos de
    sono com fases + horários locais (GMT naive nunca exposto), dose
    pina o contraste, lifestyle com streak/janela/corrente."""
    user = _new_user(db)
    _seed_full_health(db, user.id)
    db.commit()

    payload = service.get_health(db, user.id, 60, SAO_PAULO)

    sleep = payload["sleep"]
    assert sleep["days"] == 60
    assert sleep["floor_s"] == 25200
    assert sleep["rem_band"] == [21.0, 31.0]
    assert sleep["below_floor"] == {"nights": 2, "pct": 66.7}
    # deitar: (1336+1347+1336)/3 = 1339,7; acordar: (302+272+302)/3 = 292
    assert sleep["regularity"] == {"avg_bed_min": 1339.7, "avg_wake_min": 292.0}
    assert [(e["weekday"], e["avg_duration_s"], e["nights"]) for e in sleep["weekday_pattern"]] == [
        (0, None, 0), (1, 27000.0, 1), (2, 21000.0, 1), (3, 23400.0, 1),
        (4, None, 0), (5, None, 0), (6, None, 0),
    ]
    assert sleep["points"] == [
        {
            "date": date(2026, 10, 13), "duration_s": 27000, "score": 80,
            "rem_pct": 14.0, "deep_pct": 25.0, "light_pct": 61.0, "awakenings": 2,
            "bed_local": "22:16", "wake_local": "05:02",
        },
        {
            "date": date(2026, 10, 14), "duration_s": 21000, "score": 60,
            "rem_pct": 14.0, "deep_pct": 25.0, "light_pct": 61.0, "awakenings": 2,
            "bed_local": "22:27", "wake_local": "04:32",
        },
        {
            "date": date(2026, 10, 15), "duration_s": 23400, "score": 70,
            "rem_pct": 14.0, "deep_pct": 25.0, "light_pct": 61.0, "awakenings": 2,
            "bed_local": "22:16", "wake_local": "05:02",
        },
    ]

    assert payload["dose_response"] == {
        "short": {"nights": 1, "avg_hrv": 68.0, "avg_score": 60.0},
        "adequate": {"nights": 1, "avg_hrv": 82.0, "avg_score": 80.0},
        "neutral_nights": 1,
    }

    # HRV (HRV-01..09): janela de 60 dias corridos terminando em 15/10;
    # 3 noites semeadas -> média 7d sobre o disponível, banda/status null
    # (<14 valores — "coletando linha de base")
    hrv = payload["hrv"]
    assert len(hrv["points"]) == 60
    assert hrv["points"][0]["date"] == date(2026, 8, 17)
    assert hrv["points"][0] == {
        "date": date(2026, 8, 17), "value": None, "avg7": None,
        "band_low": None, "band_high": None,
    }
    by_day = {p["date"]: p for p in hrv["points"]}
    assert by_day[date(2026, 10, 13)]["avg7"] == 82.0  # janela truncada: só ela
    assert by_day[date(2026, 10, 14)]["avg7"] == 75.0  # (82+68)/2
    assert by_day[date(2026, 10, 15)]["value"] == 75.0
    assert by_day[date(2026, 10, 15)]["avg7"] == 75.0  # (82+68+75)/3
    assert all(p["band_low"] is None for p in hrv["points"])
    assert hrv["current"] == {
        "date": date(2026, 10, 15), "value": 75.0, "avg7": 75.0,
        "band_low": None, "band_high": None, "status": None,
    }
    assert payload["rhr"] == {
        "points": [
            {"date": date(2026, 10, 13), "value": 45},
            {"date": date(2026, 10, 14), "value": 44},
            {"date": date(2026, 10, 15), "value": 43},
        ],
        "baseline": 44.0,
    }
    # dia com avg NULL (14/10) fora da série — a janela não está vazia
    assert payload["stress"] == {
        "points": [{"date": date(2026, 10, 13), "avg": 25}, {"date": date(2026, 10, 15), "avg": 23}],
        "avg_window": 24.0,
    }

    assert payload["lifestyle"] == {
        "strength": {"streak_weeks": 4, "weeks_hit": 4, "weeks_total": 9,
                     "current_week_sessions": 1},
        "yoga": {"sessions": 3, "per_week_avg": 0.3},
    }


def test_sleep_window_limits_series_and_keeps_asc(db) -> None:
    """Done-when T3: janela pedida corta as noites mais antigas e devolve
    ASC (mais antiga primeiro — padrão do painel Performance)."""
    user = _new_user(db)
    for day, duration_s, *_ in NIGHTS:
        _seed_sleep(db, user.id, day, duration_s)
    db.commit()

    payload = service.get_health(db, user.id, 2, SAO_PAULO)
    assert payload["sleep"]["days"] == 2
    assert [p["date"] for p in payload["sleep"]["points"]] == [
        date(2026, 10, 14), date(2026, 10, 15),
    ]


def test_empty_series_yield_null_blocks_with_honest_zeros(db, fixed_today) -> None:
    """Done-when T3 (HLT-11): banco vazio -> sono/HRV/RHR/estresse null;
    dose_response e lifestyle presentes com zeros (estado vazio, não erro)."""
    user = _new_user(db)
    db.commit()

    payload = service.get_health(db, user.id, 60, SAO_PAULO)

    assert payload["sleep"] is None
    assert payload["hrv"] is None
    assert payload["rhr"] is None
    assert payload["stress"] is None
    assert payload["dose_response"] == {
        "short": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "adequate": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "neutral_nights": 0,
    }
    assert payload["lifestyle"] == {
        "strength": {"streak_weeks": 0, "weeks_hit": 0, "weeks_total": 9,
                     "current_week_sessions": 0},
        "yoga": {"sessions": 0, "per_week_avg": 0.0},
    }


def test_regularity_null_without_bed_wake_times(db) -> None:
    """Edge do spec: noite sem bed_time/wake_time entra nos gráficos, mas
    fica fora da regularity (nenhum horário inventado) e expõe null nos
    pontos."""
    user = _new_user(db)
    _seed_sleep(db, user.id, date(2026, 10, 14), 21000)  # sem horários
    _seed_sleep(db, user.id, date(2026, 10, 15), 23400,
                bed=datetime(2026, 10, 15, 1, 16), wake=datetime(2026, 10, 15, 8, 2))
    db.commit()

    payload = service.get_health(db, user.id, 60, SAO_PAULO)
    assert payload["sleep"]["regularity"] == {"avg_bed_min": 1336.0, "avg_wake_min": 302.0}
    assert payload["sleep"]["points"][0]["bed_local"] is None
    assert payload["sleep"]["points"][0]["wake_local"] is None

    # nenhuma noite com horário -> regularity null, bloco segue de pé
    db.query(Sleep).delete()
    _seed_sleep(db, user.id, date(2026, 10, 14), 21000)
    db.commit()
    payload = service.get_health(db, user.id, 60, SAO_PAULO)
    assert payload["sleep"]["regularity"] is None
    assert payload["sleep"]["points"][0]["bed_local"] is None


def test_stress_null_avg_rows_excluded(db) -> None:
    """Design §Riscos: dia sem avg fica fora da série; janela só com dias
    sem avg -> bloco null (não lista vazia)."""
    user = _new_user(db)
    _seed_stress(db, user.id, date(2026, 10, 14), None)
    _seed_stress(db, user.id, date(2026, 10, 15), None)
    db.commit()
    assert service.get_health(db, user.id, 60, SAO_PAULO)["stress"] is None

    db.query(Stress).delete()
    _seed_stress(db, user.id, date(2026, 10, 14), 24)
    _seed_stress(db, user.id, date(2026, 10, 15), None)
    db.commit()
    payload = service.get_health(db, user.id, 60, SAO_PAULO)
    assert payload["stress"]["points"] == [{"date": date(2026, 10, 14), "avg": 24}]
    assert payload["stress"]["avg_window"] == 24.0


def test_dose_response_crosses_hrv_of_same_date_only(db) -> None:
    """Premissa do spec (HRV da mesma noite): noite curta sem HRV na
    mesma data sai da comparação — HRV de datas vizinhas não vira par."""
    user = _new_user(db)
    _seed_sleep(db, user.id, date(2026, 10, 14), 21500, score=60)  # 5,97h — curta
    _seed_hrv(db, user.id, date(2026, 10, 13), 90.0)  # véspera
    _seed_hrv(db, user.id, date(2026, 10, 15), 70.0)  # dia seguinte
    db.commit()

    dose = service.get_health(db, user.id, 60, SAO_PAULO)["dose_response"]
    assert dose == {
        "short": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "adequate": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "neutral_nights": 0,
    }


def test_other_users_rows_never_leak_into_panel(db, fixed_today) -> None:
    """Fix 1 do Verifier (sensor M3) + convenção AD-001 + user-scope
    (USR-08): linhas de outro usuário nunca vazam para nenhum bloco — o
    usuário X tem as 3 noites canônicas (e nenhum RHR/estresse/
    atividade), o usuário Y tem uma noite de 4h com HRV, RHR/estresse
    alheios e 3 forças + yoga. Sem o filtro ``user_id``, TODOS os blocos
    mudariam."""
    user = _new_user(db)  # X — dono da sessão
    other = _new_user(db, email="outro@example.com")  # Y — dados alheios
    db.flush()
    stranger_day = date(2026, 10, 12)

    for day, duration_s, score, hrv, bed, wake in NIGHTS:
        _seed_sleep(db, user.id, day, duration_s, score=score, bed=bed, wake=wake)
        _seed_hrv(db, user.id, day, hrv)
    # Dados alheios que mudariam cada bloco se vazassem: sono de 4h
    # (cairia no bucket short com HRV 40), RHR 99, estresse 90 e
    # forças que virariam streak (2 na semana completa 05-11/10 + 1 na
    # corrente) + yoga na janela.
    db.add(Sleep(user_id=other.id, date=stranger_day, duration_s=14400,
                 score=30, rem_pct=5.0, deep_pct=10.0, light_pct=85.0,
                 awakenings=9))
    db.add(Hrv(user_id=other.id, date=stranger_day, value=40.0, status="LOW"))
    db.add(Rhr(user_id=other.id, date=stranger_day, value=99))
    db.add(Stress(user_id=other.id, date=stranger_day, avg=90))
    for garmin_id, day in (("o-s1", date(2026, 10, 6)), ("o-s2", date(2026, 10, 8)),
                           ("o-s3", date(2026, 10, 15)), ("o-y1", date(2026, 10, 15))):
        db.add(Activity(user_id=other.id, garmin_id=garmin_id,
                        start_time=datetime(day.year, day.month, day.day, 7, 0),
                        activity_type="strength_training" if garmin_id.startswith("o-s")
                        else "yoga",
                        name="Alheio", distance_m=0.0, duration_s=3600.0))
    db.commit()

    payload = service.get_health(db, user.id, 60, SAO_PAULO)

    # Sono: só as 3 noites de X; a noite alheia de 4h não entra
    # nos pontos, no below_floor (2 noites, não 3) nem no dose (a noite
    # alheia faria short = 2 noites, avg_hrv 54,0, avg_score 45,0).
    assert [p["date"] for p in payload["sleep"]["points"]] == [
        date(2026, 10, 13), date(2026, 10, 14), date(2026, 10, 15),
    ]
    assert payload["sleep"]["below_floor"] == {"nights": 2, "pct": 66.7}
    assert payload["dose_response"] == {
        "short": {"nights": 1, "avg_hrv": 68.0, "avg_score": 60.0},
        "adequate": {"nights": 1, "avg_hrv": 82.0, "avg_score": 80.0},
        "neutral_nights": 1,
    }
    # HRV alheia ausente do modelo (lição L-005): a noite alheia de 12/10
    # (valor 40) não vira value nem alimenta a média 7d daquele dia; o
    # current continua sendo a última noite de X
    hrv = payload["hrv"]
    assert len(hrv["points"]) == 60  # dias corridos da janela de X
    by_day = {p["date"]: p for p in hrv["points"]}
    assert by_day[date(2026, 10, 12)] == {
        "date": date(2026, 10, 12), "value": None, "avg7": None,
        "band_low": None, "band_high": None,
    }  # sem o filtro user_id, value seria 40 e avg7 40
    assert hrv["current"] == {
        "date": date(2026, 10, 15), "value": 75.0, "avg7": 75.0,
        "band_low": None, "band_high": None, "status": None,
    }
    # X não tem RHR/estresse: bloco null — a linha alheia
    # (RHR 99 / estresse 90) tornaria os blocos não-null.
    assert payload["rhr"] is None
    assert payload["stress"] is None
    # Atividades alheias não viram streak/yoga de X
    assert payload["lifestyle"]["strength"] == {
        "streak_weeks": 0, "weeks_hit": 0, "weeks_total": 9,
        "current_week_sessions": 0,
    }
    assert payload["lifestyle"]["yoga"] == {"sessions": 0, "per_week_avg": 0.0}


# ---------------------------------------------------------------
# hrv-baseline — modelo científico na API (HRV-01..HRV-15)
# ---------------------------------------------------------------


def test_hrv_band_slides_day_by_day_with_full_history(db, fixed_today) -> None:
    """HRV-04 (banda por dia): 119 dias semeados (70,0 até 16/08; 80,0 de
    17/08 a 15/10) — os 60 dias exibidos têm banda com janela completa e
    ela DESLIZA: no primeiro dia exibido (17/08: 59×70 + 1×80 -> média
    70,1667, DP √(5/3) -> banda 69,2/71,1) difere do último (80,0
    chapada). A média 7d do primeiro dia usa noites de FORA da janela de
    exibição (6×70 + 1×80 = 71,4 — sem lookback seria 80,0)."""
    user = _new_user(db)
    day = date(2026, 6, 19)
    while day <= date(2026, 10, 15):
        _seed_hrv(db, user.id, day, 70.0 if day < date(2026, 8, 17) else 80.0)
        day += timedelta(days=1)
    db.commit()

    hrv = service.get_health(db, user.id, 60, SAO_PAULO)["hrv"]

    assert len(hrv["points"]) == 60
    assert hrv["points"][0]["date"] == date(2026, 8, 17)
    assert all(p["band_low"] is not None for p in hrv["points"])
    assert hrv["points"][0]["avg7"] == 71.4  # 6×70 (11..16/08) + 1×80 (lookback)
    assert hrv["points"][0]["band_low"] == 69.2
    assert hrv["points"][0]["band_high"] == 71.1
    assert hrv["current"] == {
        "date": date(2026, 10, 15), "value": 80.0, "avg7": 80.0,
        "band_low": 80.0, "band_high": 80.0, "status": "BALANCED",
    }


def test_hrv_status_unbalanced_after_recent_suppression(db, fixed_today) -> None:
    """HRV-06/05: queda recente (14 dias a 80 e 7 a 20) — média 7d 20
    abaixo da banda (60 ± 0,75√840 -> 38,3/81,7) -> UNBALANCED no card;
    dias com janela vazia ficam sem banda (threshold por dia)."""
    user = _new_user(db)
    day = date(2026, 9, 25)
    while day <= date(2026, 10, 8):
        _seed_hrv(db, user.id, day, 80.0)
        day += timedelta(days=1)
    day = date(2026, 10, 9)
    while day <= date(2026, 10, 15):
        _seed_hrv(db, user.id, day, 20.0)
        day += timedelta(days=1)
    db.commit()

    hrv = service.get_health(db, user.id, 60, SAO_PAULO)["hrv"]

    assert hrv["points"][0]["date"] == date(2026, 8, 17)
    assert hrv["points"][0]["band_low"] is None  # janela sem valor nenhum
    assert hrv["current"] == {
        "date": date(2026, 10, 15), "value": 20.0, "avg7": 20.0,
        "band_low": 38.3, "band_high": 81.7, "status": "UNBALANCED",
    }


def test_hrv_short_window_keeps_sixty_day_band_lookback(db, fixed_today) -> None:
    """HRV-15 (efeito de leitura) + design §Riscos: days=7 exibe 7 pontos
    mas a banda continua com a janela de 60 dias — o lookback de 65 dias
    (12/08..15/10, tudo 80) sustenta banda mesmo no primeiro dia exibido."""
    user = _new_user(db)
    day = date(2026, 8, 12)
    while day <= date(2026, 10, 15):
        _seed_hrv(db, user.id, day, 80.0)
        day += timedelta(days=1)
    db.commit()

    hrv = service.get_health(db, user.id, 7, SAO_PAULO)["hrv"]

    assert len(hrv["points"]) == 7
    assert hrv["points"][0]["date"] == date(2026, 10, 9)
    assert hrv["points"][0]["band_low"] == 80.0  # 59 valores na janela 60d
    assert hrv["current"] == {
        "date": date(2026, 10, 15), "value": 80.0, "avg7": 80.0,
        "band_low": 80.0, "band_high": 80.0, "status": "BALANCED",
    }


def test_lifestyle_streak_exceeds_window(db, fixed_today) -> None:
    """Done-when T3 (AC 12): streak de semanas completas pode exceder a
    janela — janela de 19d (28/09..16/10: semanas 28/09, 05/10 e
    corrente) com 5 semanas batidas seguidas; weeks_hit mostra só as 2
    inteiramente dentro dela."""
    user = _new_user(db)
    for week_start in (date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21),
                       date(2026, 9, 28), date(2026, 10, 5)):
        for offset in (1, 3):
            day = date.fromordinal(week_start.toordinal() + offset)
            _seed_activity(db, user.id, f"s{day.isoformat()}",
                           datetime(day.year, day.month, day.day, 7, 0),
                           "strength_training")
    db.commit()

    lifestyle = service.get_health(db, user.id, 19, SAO_PAULO)["lifestyle"]
    assert lifestyle["strength"] == {"streak_weeks": 5, "weeks_hit": 2,
                                     "weeks_total": 3, "current_week_sessions": 0}


# ---------------------------------------------------------------
# AD-017 — o bloco pmc saiu da Saúde (voltou ao painel Performance):
# a exclusão é do contrato, não do dado vazio.
# ---------------------------------------------------------------


def test_health_payload_omits_pmc_even_with_load_rows(db) -> None:
    """AD-017 (revérte o lado Saúde da CLR-01): com linhas de `load` no
    banco a chave continua ausente — a curva mora no payload de
    /api/potential (test_potential_api). Ordem das chaves pinada — o
    espelho do router e do cliente seguem a mesma posição."""
    user = _new_user(db)
    _seed_load(db, user.id, date(2026, 10, 15), 22.0, 28.0, -6.0, 1.42)
    db.commit()

    payload = service.get_health(db, user.id, 60, SAO_PAULO)
    assert list(payload.keys()) == [
        "sleep", "hrv", "rhr", "stress", "dose_response", "lifestyle",
    ]


def test_health_domain_never_imports_garmin_gateway() -> None:
    """AD-002 (Success Criteria, verificável por código): nenhum import do
    gateway Garmin em nenhum módulo do domínio health/ — leitura 100%
    do banco próprio (mesmo pin do domínio potential)."""
    domain = Path(service.__file__).parent
    modules = sorted(domain.glob("*.py"))
    assert modules  # o domínio existe
    for module in modules:
        source = module.read_text(encoding="utf-8")
        assert "from app.garmin" not in source, module.name
        assert "import app.garmin" not in source, module.name


# ---------------------------------------------------------------
# T4 — GET /api/health/summary (TestClient + superfície HTTP)
# ---------------------------------------------------------------


def test_api_happy_path_200_full_payload(session_client, fixed_today) -> None:
    """HLT-01/02: 200 com o payload completo em JSON — datas ISO,
    horários locais como "HH:MM", default days=60 e os pins do design
    atravessando o HTTP (sessão real do usuário da session_client)."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_full_health(db, user_id)
        db.commit()

    response = client.get("/api/health/summary")
    assert response.status_code == 200
    body = response.json()

    assert body["sleep"]["days"] == 60  # default do endpoint
    assert body["sleep"]["floor_s"] == 25200
    assert body["sleep"]["rem_band"] == [21.0, 31.0]
    assert body["sleep"]["below_floor"] == {"nights": 2, "pct": 66.7}
    assert body["sleep"]["regularity"] == {"avg_bed_min": 1339.7, "avg_wake_min": 292.0}
    assert [(e["weekday"], e["nights"]) for e in body["sleep"]["weekday_pattern"]] == [
        (0, 0), (1, 1), (2, 1), (3, 1), (4, 0), (5, 0), (6, 0),
    ]
    assert body["sleep"]["points"][1] == {
        "date": "2026-10-14", "duration_s": 21000.0, "score": 60,
        "rem_pct": 14.0, "deep_pct": 25.0, "light_pct": 61.0, "awakenings": 2,
        "bed_local": "22:27", "wake_local": "04:32",
    }

    assert body["dose_response"] == {
        "short": {"nights": 1, "avg_hrv": 68.0, "avg_score": 60.0},
        "adequate": {"nights": 1, "avg_hrv": 82.0, "avg_score": 80.0},
        "neutral_nights": 1,
    }
    assert body["hrv"]["points"][59] == {
        "date": "2026-10-15", "value": 75.0, "avg7": 75.0,
        "band_low": None, "band_high": None,
    }
    assert body["hrv"]["current"] == {
        "date": "2026-10-15", "value": 75.0, "avg7": 75.0,
        "band_low": None, "band_high": None, "status": None,
    }
    assert body["rhr"]["baseline"] == 44.0
    assert body["stress"]["avg_window"] == 24.0
    assert body["lifestyle"] == {
        "strength": {"streak_weeks": 4, "weeks_hit": 4, "weeks_total": 9,
                     "current_week_sessions": 1},
        "yoga": {"sessions": 3, "per_week_avg": 0.3},
    }


def test_api_days_out_of_range_responds_422(session_client) -> None:
    """HLT-03: days fora de [7, 365] -> 422 antes de qualquer query."""
    client, _user_id = session_client
    for params in ({"days": 6}, {"days": 366}, {"days": 0}, {"days": -1}):
        response = client.get("/api/health/summary", params=params)
        assert response.status_code == 422, params


def test_api_days_boundaries_respond_200(session_client) -> None:
    """HLT-02/03: os extremos do intervalo são válidos (7 e 365 -> 200);
    sem dados, os blocos de série já atravessam como null."""
    client, _user_id = session_client
    for params in ({"days": 7}, {"days": 365}):
        response = client.get("/api/health/summary", params=params)
        assert response.status_code == 200, params
        assert response.json()["sleep"] is None


def test_api_null_blocks_traverse_http_with_honest_zeros(session_client, fixed_today) -> None:
    """HLT-11 via HTTP (done-when T4): banco vazio -> sono/HRV/RHR/
    estresse null no JSON; dose_response e lifestyle presentes com zeros."""
    client, _user_id = session_client
    response = client.get("/api/health/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["sleep"] is None
    assert body["hrv"] is None
    assert body["rhr"] is None
    assert body["stress"] is None
    assert body["dose_response"] == {
        "short": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "adequate": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "neutral_nights": 0,
    }
    assert body["lifestyle"]["yoga"] == {"sessions": 0, "per_week_avg": 0.0}
    assert body["lifestyle"]["strength"]["streak_weeks"] == 0


def test_api_window_cuts_oldest_points(session_client) -> None:
    """HLT-02 (edge do spec): janela pedida corta as noites mais antigas —
    8 noites semeadas, days=7 devolve as 7 mais recentes em ASC."""
    client, user_id = session_client
    with SessionLocal() as db:
        for offset in range(8):
            _seed_sleep(db, user_id, date(2026, 10, 8 + offset), 22000)
        db.commit()

    response = client.get("/api/health/summary", params={"days": 7})
    assert response.status_code == 200
    points = response.json()["sleep"]["points"]
    assert [p["date"] for p in points] == [
        "2026-10-09", "2026-10-10", "2026-10-11", "2026-10-12",
        "2026-10-13", "2026-10-14", "2026-10-15",
    ]


def test_api_invalid_app_timezone_falls_back_with_warning(session_client, monkeypatch, caplog) -> None:
    """Edge do spec (HLT-05): APP_TIMEZONE inválida -> fallback
    America/Sao_Paulo com warning log, sem crash — 22:16 local, nunca o
    GMT de 01:16."""
    client, user_id = session_client
    monkeypatch.setattr(
        health_router, "get_settings", lambda: SimpleNamespace(app_timezone="Mars/Phobos")
    )
    with SessionLocal() as db:
        _seed_sleep(db, user_id, date(2026, 10, 15), 23400,
                    bed=datetime(2026, 10, 15, 1, 16), wake=datetime(2026, 10, 15, 8, 2))
        db.commit()

    with caplog.at_level(logging.WARNING, logger="app.health.router"):
        response = client.get("/api/health/summary")

    assert response.status_code == 200
    point = response.json()["sleep"]["points"][0]
    assert point["bed_local"] == "22:16"
    assert point["wake_local"] == "05:02"
    assert "Mars/Phobos" in caplog.text


# ---------------------------------------------------------------
# AD-017 — GET /api/health/summary sem pmc (HTTP)
# ---------------------------------------------------------------


def test_api_health_payload_omits_pmc_even_with_load(session_client) -> None:
    """AD-017 via HTTP: banco com `load` -> payload sem a chave `pmc`
    (a exclusão é do contrato, não do dado vazio — a curva mora no
    /api/potential agora); ordem das chaves pinada. O resto do payload
    intacto (HLT-03 segue verde: days fora de [7, 365] continua 422
    antes da query)."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_load(db, user_id, date(2026, 10, 14), 21.0, 27.0, -6.0, 1.40)
        db.commit()

    response = client.get("/api/health/summary", params={"days": 60})
    assert response.status_code == 200
    body = response.json()

    assert list(body.keys()) == [
        "sleep", "hrv", "rhr", "stress", "dose_response", "lifestyle",
    ]
    assert body["dose_response"]["neutral_nights"] == 0
