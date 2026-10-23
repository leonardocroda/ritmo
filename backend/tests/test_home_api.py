"""Painel Home — HTTP (T6): contrato HomeOut 1:1 no Postgres real.

Cenários derivados dos ACs HOME-01/11/12 e do Independent Test do spec:
happy path com o contrato completo campo a campo, 401 sem sessão,
estado vazio (verdict null + blocos nulos), date no payload = hoje no
fuso, os dois fixtures independentes do spec (UNBALANCED + sono 6h ->
'Recuperação em dívida'; BALANCED + TSB +5,2 -> 'Pronto pra
qualidade'), edge de APP_TIMEZONE inválida (fallback + warning) e a
recomendação R5 com shape {text, support, why, tone}. Valores
afirmados são literais.
"""

import logging
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.core import tz as core_tz
from app.db.engine import SessionLocal
from app.db.models import Activity, DailyLoad, Hrv, Race, Sleep
from app.main import app

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _today() -> date:
    """Hoje no fuso do app — o mesmo relógio do service."""
    return datetime.now(SAO_PAULO).date()


def _seed_hrv(db, user_id, day, value):
    db.add(Hrv(user_id=user_id, date=day, value=value))


def _seed_sleep(db, user_id, day, duration_s):
    db.add(Sleep(user_id=user_id, date=day, duration_s=duration_s, score=80))


def _seed_load(db, user_id, day, tsb, acwr=None):
    db.add(DailyLoad(user_id=user_id, date=day, ctl=50.0, atl=55.0, tsb=tsb, acwr=acwr))


def _seed_activity(db, user_id, garmin_id, day, activity_type="running",
                   distance_m=10000.0, training_load=None, evaluated=False):
    db.add(
        Activity(
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
    )


def _seed_race(db, user_id, day, name="Prova"):
    db.add(Race(user_id=user_id, name=name, date=day, distance_m=21097.5))


def _seed_hrv_unbalanced(db, user_id) -> None:
    """21 dias de 60ms + semana de 40ms -> média 7d 40 abaixo da banda
    (cerca de [48,4, 61,6]) -> UNBALANCED (status AD-010)."""
    for offset in range(21):
        _seed_hrv(db, user_id, date(2026, 9, 25) + timedelta(days=offset), 60.0)
    for offset in range(7):
        _seed_hrv(db, user_id, date(2026, 10, 16) + timedelta(days=offset), 40.0)


def _seed_hrv_balanced(db, user_id) -> None:
    """28 dias estáveis de 60ms -> banda [60, 60], média 7d 60 dentro
    (limites inclusivos) -> BALANCED."""
    for offset in range(28):
        _seed_hrv(db, user_id, date(2026, 9, 25) + timedelta(days=offset), 60.0)


def _seed_nights(db, user_id, last_duration_s) -> None:
    """7 noites de 8h + a última com `last_duration_s`."""
    for offset in range(7):
        _seed_sleep(db, user_id, date(2026, 10, 15) + timedelta(days=offset), 28800.0)
    _seed_sleep(db, user_id, date(2026, 10, 22), last_duration_s)


# ---------------------------------------------------------------
# Contrato 1:1 (HOME-01)
# ---------------------------------------------------------------


def test_today_happy_path_full_contract(session_client) -> None:
    """HOME-01: 200 com o payload completo — cada bloco do painel
    presente, nenhum campo extra; recomendações 1..3 com os 4 campos."""
    client, user_id = session_client
    today = _today()
    with SessionLocal() as db:
        _seed_hrv_unbalanced(db, user_id)
        _seed_nights(db, user_id, 21600.0)  # 6h — abaixo do piso
        _seed_load(db, user_id, date(2026, 10, 22), -5.0, acwr=1.2)
        _seed_activity(db, user_id, "r1", today - timedelta(days=10),
                       distance_m=30000.0, training_load=40.0)
        _seed_activity(db, user_id, "r2", today, distance_m=5000.0,
                       training_load=20.0, evaluated=True)
        _seed_race(db, user_id, today + timedelta(days=10), name="Alvo")
        db.commit()

    response = client.get("/api/home/today")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "date", "verdict", "signals", "strip", "last_activity", "volume",
        "countdown", "recommendations", "volume_weeks", "predictions",
    }
    assert body["verdict"] == {
        "phrase": "Recuperação em dívida",
        "tone": "alert",
        "rule": "V1",
    }
    assert body["signals"]["hrv"] == {
        "value": 40.0, "status": "UNBALANCED", "as_of": "2026-10-22",
    }
    assert body["signals"]["sleep"]["duration_s"] == 21600.0
    assert body["signals"]["sleep"]["delta_s"] == -7200.0
    assert body["signals"]["fitness"] == {
        "tsb": -5.0, "acwr": 1.2, "as_of": "2026-10-22",
    }
    strip = body["strip"]
    assert len(strip) == 7
    assert [p["date"] for p in strip] == [
        (today - timedelta(days=o)).isoformat() for o in range(6, -1, -1)
    ]
    assert strip[-1]["load"] == 20.0
    assert all(p["load"] == 0.0 for p in strip[:6])  # lacuna = 0.0
    assert body["last_activity"]["distance_m"] == 5000.0
    assert body["last_activity"]["evaluated"] is True
    assert body["volume"] == {"week_km": 5.0, "avg4_km": 7.5, "delta_pct": -33.3}
    assert body["countdown"] == {
        "name": "Alvo", "date": (today + timedelta(days=10)).isoformat(), "days_left": 10,
    }
    recs = body["recommendations"]
    assert 1 <= len(recs) <= 3
    assert all(set(r) == {"text", "support", "why", "tone"} for r in recs)
    assert body["volume_weeks"] is None
    assert body["predictions"] is None


def test_today_requires_session() -> None:
    """HOME-11: sem sessão -> 401 antes de qualquer query (a dependency
    resolve primeiro — padrão dos demais routers)."""
    with TestClient(app) as client:
        response = client.get("/api/home/today")
    assert response.status_code == 401
    assert response.json() == {"detail": "não autenticado"}


def test_empty_state_verdict_null_and_null_blocks(session_client) -> None:
    """HOME-01/34 (payload): banco sem dado de saúde/carga/atividade ->
    verdict null + blocos nulos, sem frase; strip estrutural segue com
    7 dias zerados."""
    client, _ = session_client

    response = client.get("/api/home/today")

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] is None
    assert body["signals"] == {"hrv": None, "sleep": None, "fitness": None}
    assert body["last_activity"] is None
    assert body["volume"] is None
    assert body["countdown"] is None
    assert body["recommendations"] == []
    assert len(body["strip"]) == 7
    assert all(p["load"] == 0.0 for p in body["strip"])


def test_date_is_today_in_app_timezone(session_client) -> None:
    """AC HOME-12 (contrato): `date` no payload = hoje no fuso do app."""
    client, _ = session_client
    today = _today()

    response = client.get("/api/home/today")

    assert response.status_code == 200
    assert response.json()["date"] == today.isoformat()


# ---------------------------------------------------------------
# Independent Test do spec: dois fixtures, dois vereditos
# ---------------------------------------------------------------


def test_independent_fixture_unbalanced_short_sleep(session_client) -> None:
    """Independent test (spec P1-1): HRV UNBALANCED + sono 6h ->
    'Recuperação em dívida' com os chips de HRV e sono."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_hrv_unbalanced(db, user_id)
        _seed_nights(db, user_id, 21600.0)
        db.commit()

    body = client.get("/api/home/today").json()

    assert body["verdict"]["phrase"] == "Recuperação em dívida"
    assert body["verdict"]["tone"] == "alert"
    assert body["signals"]["hrv"]["status"] == "UNBALANCED"
    assert body["signals"]["sleep"]["duration_s"] == 21600.0


def test_independent_fixture_balanced_positive_tsb(session_client) -> None:
    """Independent test (spec P1-1): trocando o fixture para HRV
    BALANCED + TSB +5,2 -> 'Pronto pra qualidade' com R1."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_hrv_balanced(db, user_id)
        _seed_nights(db, user_id, 28800.0)
        _seed_load(db, user_id, date(2026, 10, 22), 5.2, acwr=1.2)
        db.commit()

    body = client.get("/api/home/today").json()

    assert body["verdict"] == {"phrase": "Pronto pra qualidade", "tone": "good", "rule": "V5"}
    assert body["signals"]["hrv"]["status"] == "BALANCED"
    assert body["signals"]["fitness"]["tsb"] == 5.2
    assert body["recommendations"][0] == {
        "text": "Boa janela pra sessão de qualidade",
        "support": None,
        "why": "HRV · sono · forma",
        "tone": "good",
    }


def test_dia_comum_carries_r5_with_support(session_client) -> None:
    """HOME-08/30 via HTTP: dado de forma sem gatilho -> 'Dia comum' +
    R5 'Siga o leve de hoje' com a copy de apoio."""
    client, user_id = session_client
    with SessionLocal() as db:
        _seed_load(db, user_id, date(2026, 10, 20), -5.0, acwr=1.2)
        db.commit()

    body = client.get("/api/home/today").json()

    assert body["verdict"]["phrase"] == "Dia comum, sem urgências"
    assert body["recommendations"] == [
        {
            "text": "Siga o leve de hoje",
            "support": "Tudo dentro da faixa",
            "why": None,
            "tone": "neutral",
        }
    ]


# ---------------------------------------------------------------
# Edge de APP_TIMEZONE inválida (HOME-12 no endpoint)
# ---------------------------------------------------------------


def test_invalid_app_timezone_falls_back_with_warning(
    session_client, monkeypatch, caplog
) -> None:
    """HOME-12: APP_TIMEZONE inválida -> fuso default + warning, o
    endpoint segue funcional (mesma edge do Saúde)."""
    client, _ = session_client
    monkeypatch.setattr(
        core_tz, "get_settings", lambda: SimpleNamespace(app_timezone="Mars/Phobos")
    )
    today = _today()

    with caplog.at_level(logging.WARNING, logger="app.core.tz"):
        response = client.get("/api/home/today")

    assert response.status_code == 200
    assert response.json()["date"] == today.isoformat()
    assert "Mars/Phobos" in caplog.text
