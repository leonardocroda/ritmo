"""Painel Saúde — service direto (T3) + HTTP (T4), no Postgres real.

T3: chamadas diretas a `get_health` com seeds ORM (o domínio lê
exclusivamente o banco próprio — AD-002; nenhuma chamada Garmin). T4:
TestClient cobrindo a superfície HTTP (422/blocos null/fallback de tz).
Valores afirmados são literais derivados das fixtures — nunca
constantes compartilhadas com a implementação (lições L-001/L-002).

Convenção do sync (mappers.py): bed_time/wake_time são wall clock GMT
naive que caem no próprio calendarDate (01:16 GMT = 22:16 local da
véspera) — os seeds reproduzem o shape real para pinar a conversão.
"""

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.db.engine import SessionLocal, init_db
from app.db.models import Activity, Hrv, Rhr, Sleep, Stress
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


def _seed_sleep(db, day, duration_s, score=70, rem_pct=14.0, deep_pct=25.0,
                light_pct=61.0, awakenings=2, bed=None, wake=None):
    db.add(
        Sleep(
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


def _seed_hrv(db, day, value, status="BALANCED"):
    db.add(Hrv(date=day, value=value, status=status))


def _seed_rhr(db, day, value):
    db.add(Rhr(date=day, value=value))


def _seed_stress(db, day, avg):
    db.add(Stress(date=day, avg=avg))


def _seed_activity(db, garmin_id, start, activity_type, name="Treino"):
    db.add(
        Activity(
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


def _seed_full_health(db) -> None:
    for day, duration_s, score, hrv, bed, wake in NIGHTS:
        _seed_sleep(db, day, duration_s, score=score, bed=bed, wake=wake)
        _seed_hrv(db, day, hrv)
    _seed_rhr(db, date(2026, 10, 13), 45)
    _seed_rhr(db, date(2026, 10, 14), 44)
    _seed_rhr(db, date(2026, 10, 15), 43)
    _seed_stress(db, date(2026, 10, 13), 25)
    _seed_stress(db, date(2026, 10, 14), None)  # dia sem avg -> fora da série
    _seed_stress(db, date(2026, 10, 15), 23)
    # Força: 4 semanas completas (streak 4) + 1 sessão na corrente;
    # janela de 60d (17/08..16/10) contém as 4 semanas batidas
    strength_days = [date(2026, 9, 15), date(2026, 9, 17), date(2026, 9, 22),
                     date(2026, 9, 24), date(2026, 9, 29), date(2026, 10, 1),
                     date(2026, 10, 6), date(2026, 10, 8), date(2026, 10, 13)]
    for i, day in enumerate(strength_days):
        _seed_activity(db, f"s{i}", datetime(day.year, day.month, day.day, 7, 0),
                       "strength_training", "Força")
    # Yoga: 3 na janela + 1 antes dela (01/08 < 17/08)
    for i, day in enumerate((date(2026, 8, 1), date(2026, 9, 23),
                             date(2026, 10, 7), date(2026, 10, 14))):
        _seed_activity(db, f"y{i}", datetime(day.year, day.month, day.day, 6, 0),
                       "yoga", "Yoga")


# ---------------------------------------------------------------
# T3 — service.get_health (chamadas diretas com seeds)
# ---------------------------------------------------------------


def test_get_health_full_payload_from_seeds(db, fixed_today) -> None:
    """Done-when T3: os 6 blocos montados a partir do banco — pontos de
    sono com fases + horários locais (GMT naive nunca exposto), dose
    pina o contraste, lifestyle com streak/janela/corrente."""
    _seed_full_health(db)
    db.commit()

    payload = service.get_health(db, 60, SAO_PAULO)

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

    assert payload["hrv"] == {
        "points": [
            {"date": date(2026, 10, 13), "value": 82.0, "status": "BALANCED"},
            {"date": date(2026, 10, 14), "value": 68.0, "status": "BALANCED"},
            {"date": date(2026, 10, 15), "value": 75.0, "status": "BALANCED"},
        ],
        "current": {"date": date(2026, 10, 15), "value": 75.0, "status": "BALANCED"},
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
    ASC (mais antiga primeiro — padrão do painel Potencial)."""
    for day, duration_s, *_ in NIGHTS:
        _seed_sleep(db, day, duration_s)
    db.commit()

    payload = service.get_health(db, 2, SAO_PAULO)
    assert payload["sleep"]["days"] == 2
    assert [p["date"] for p in payload["sleep"]["points"]] == [
        date(2026, 10, 14), date(2026, 10, 15),
    ]


def test_empty_series_yield_null_blocks_with_honest_zeros(db, fixed_today) -> None:
    """Done-when T3 (HLT-11): banco vazio -> sono/HRV/RHR/estresse null;
    dose_response e lifestyle presentes com zeros (estado vazio, não erro)."""
    payload = service.get_health(db, 60, SAO_PAULO)

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
    _seed_sleep(db, date(2026, 10, 14), 21000)  # sem horários
    _seed_sleep(db, date(2026, 10, 15), 23400,
                bed=datetime(2026, 10, 15, 1, 16), wake=datetime(2026, 10, 15, 8, 2))
    db.commit()

    payload = service.get_health(db, 60, SAO_PAULO)
    assert payload["sleep"]["regularity"] == {"avg_bed_min": 1336.0, "avg_wake_min": 302.0}
    assert payload["sleep"]["points"][0]["bed_local"] is None
    assert payload["sleep"]["points"][0]["wake_local"] is None

    # nenhuma noite com horário -> regularity null, bloco segue de pé
    db.query(Sleep).delete()
    _seed_sleep(db, date(2026, 10, 14), 21000)
    db.commit()
    payload = service.get_health(db, 60, SAO_PAULO)
    assert payload["sleep"]["regularity"] is None
    assert payload["sleep"]["points"][0]["bed_local"] is None


def test_stress_null_avg_rows_excluded(db) -> None:
    """Design §Riscos: dia sem avg fica fora da série; janela só com dias
    sem avg -> bloco null (não lista vazia)."""
    _seed_stress(db, date(2026, 10, 14), None)
    _seed_stress(db, date(2026, 10, 15), None)
    db.commit()
    assert service.get_health(db, 60, SAO_PAULO)["stress"] is None

    db.query(Stress).delete()
    _seed_stress(db, date(2026, 10, 14), 24)
    _seed_stress(db, date(2026, 10, 15), None)
    db.commit()
    payload = service.get_health(db, 60, SAO_PAULO)
    assert payload["stress"]["points"] == [{"date": date(2026, 10, 14), "avg": 24}]
    assert payload["stress"]["avg_window"] == 24.0


def test_dose_response_crosses_hrv_of_same_date_only(db) -> None:
    """Premissa do spec (HRV da mesma noite): noite curta sem HRV na
    mesma data sai da comparação — HRV de datas vizinhas não vira par."""
    _seed_sleep(db, date(2026, 10, 14), 21500, score=60)  # 5,97h — curta
    _seed_hrv(db, date(2026, 10, 13), 90.0)  # véspera
    _seed_hrv(db, date(2026, 10, 15), 70.0)  # dia seguinte
    db.commit()

    dose = service.get_health(db, 60, SAO_PAULO)["dose_response"]
    assert dose == {
        "short": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "adequate": {"nights": 0, "avg_hrv": None, "avg_score": None},
        "neutral_nights": 0,
    }


def test_lifestyle_streak_exceeds_window(db, fixed_today) -> None:
    """Done-when T3 (AC 12): streak de semanas completas pode exceder a
    janela — janela de 19d (28/09..16/10: semanas 28/09, 05/10 e
    corrente) com 5 semanas batidas seguidas; weeks_hit mostra só as 2
    inteiramente dentro dela."""
    for week_start in (date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21),
                       date(2026, 9, 28), date(2026, 10, 5)):
        for offset in (1, 3):
            day = date.fromordinal(week_start.toordinal() + offset)
            _seed_activity(db, f"s{day.isoformat()}",
                           datetime(day.year, day.month, day.day, 7, 0),
                           "strength_training")
    db.commit()

    lifestyle = service.get_health(db, 19, SAO_PAULO)["lifestyle"]
    assert lifestyle["strength"] == {"streak_weeks": 5, "weeks_hit": 2,
                                     "weeks_total": 3, "current_week_sessions": 0}


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
