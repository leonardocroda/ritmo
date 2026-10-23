"""Service do painel Home — montagem do payload de hoje (design §Components).

Lê as fontes uma vez e monta o payload 1:1; zero regra de negócio aqui
— veredito, recomendações, delta e volume vivem no calc (puro, AD-003).
Os sinais de saúde vêm INTEGRais de `get_health(8)` (abordagem A do
design): mesmo modelo AD-010 do painel Saúde, consistência por
construção — o custo dos blocos que a Home descarta é desprezível. A
strip de carga usa a mesma fonte da PMC e o último treino/volume o
mesmo vocabulário de corrida de activities: uma fonte de verdade por
pergunta.
"""

from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.service import RUNNING_TYPES
from app.db.models import Activity, DailyLoad, Race
from app.garmin.pmc import aggregate_daily_loads
from app.health.service import get_health
from app.home import calc

# Janela do volume semanal: 10 semanas ISO (série) + a corrente
VOLUME_WINDOW_DAYS = 70


def _today(tz: ZoneInfo) -> date:
    """Hoje no fuso do app — 3 linhas locais: duplicá-las custa menos
    que acoplar a private de outro módulo (decisão do design §Reuses)."""
    return datetime.now(tz).date()


def get_home(db: Session, user_id: int, tz: ZoneInfo) -> dict:
    """Payload completo de hoje — o router só tipa o contrato (HomeOut)."""
    today = _today(tz)
    health = get_health(db, user_id, 8, tz)

    # Sinais: HRV current do Saúde (AD-010) + última noite + forma (PMC)
    hrv = None
    if health["hrv"] is not None:
        current = health["hrv"]["current"]
        hrv = calc.HrvSignal(
            value=current["value"], status=current["status"], as_of=current["date"]
        )
    sleep = None
    delta_s = None
    if health["sleep"] is not None:
        points = health["sleep"]["points"]
        last_night = points[-1]
        sleep = calc.SleepSignal(
            duration_s=last_night["duration_s"], as_of=last_night["date"]
        )
        delta_s = calc.sleep_delta([p["duration_s"] for p in points])
    load_row = db.execute(
        select(DailyLoad)
        .where(DailyLoad.user_id == user_id)
        .order_by(DailyLoad.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    fitness = None
    if load_row is not None:
        fitness = calc.FitnessSignal(
            tsb=load_row.tsb, acwr=load_row.acwr, as_of=load_row.date
        )

    v = calc.verdict(calc.Signals(hrv=hrv, sleep=sleep, fitness=fitness))

    # Strip: últimos 7 dias corridos terminando hoje; lacuna = 0.0
    loads = dict(aggregate_daily_loads(db, user_id))
    strip = [
        {"date": day, "load": loads.get(day, 0.0)}
        for day in (today - timedelta(days=offset) for offset in range(6, -1, -1))
    ]

    # Último treino: só corrida (RUNNING_TYPES) — força/yoga não são
    # "treino" no contexto da Home (design §Decisões)
    last = db.execute(
        select(Activity)
        .where(Activity.user_id == user_id, Activity.activity_type.in_(RUNNING_TYPES))
        .order_by(Activity.start_time.desc(), Activity.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    last_activity = (
        {
            "id": last.id,
            "date": last.start_time.date(),
            "distance_m": last.distance_m,
            "evaluated": last.evaluated,
        }
        if last is not None
        else None
    )

    # Volume semanal: corridas da janela das 10 semanas ISO; sem
    # corrida na janela não há volume a dizer (bloco nulo). A série de
    # 10 semanas (weeks) é o bloco P2 `volume_weeks` — T13 assume.
    run_rows = db.execute(
        select(Activity.start_time, Activity.distance_m)
        .where(
            Activity.user_id == user_id,
            Activity.activity_type.in_(RUNNING_TYPES),
            Activity.start_time
            >= datetime.combine(today - timedelta(days=VOLUME_WINDOW_DAYS), time.min),
        )
    ).all()
    volume = None
    if run_rows:
        wv = calc.weekly_volume([(t.date(), m) for t, m in run_rows], today)
        volume = {
            "week_km": wv["week_km"],
            "avg4_km": wv["avg4_km"],
            "delta_pct": wv["delta_pct"],
        }

    # Countdown: próxima prova com date >= hoje ("é hoje" quando 0; a
    # passada é ignorada — o chip some quando a prova passa)
    race = db.execute(
        select(Race)
        .where(Race.user_id == user_id, Race.date >= today)
        .order_by(Race.date.asc())
        .limit(1)
    ).scalar_one_or_none()
    countdown = (
        {
            "name": race.name,
            "date": race.date,
            "days_left": (race.date - today).days,
        }
        if race is not None
        else None
    )

    recommendations = calc.recommendations(
        v.rule if v is not None else None,
        countdown["days_left"] if countdown is not None else None,
    )

    return {
        "date": today,
        "verdict": (
            {"phrase": v.phrase, "tone": v.tone, "rule": v.rule}
            if v is not None
            else None
        ),
        "signals": {
            "hrv": (
                {"value": hrv.value, "status": hrv.status, "as_of": hrv.as_of}
                if hrv is not None
                else None
            ),
            "sleep": (
                {"duration_s": sleep.duration_s, "delta_s": delta_s, "as_of": sleep.as_of}
                if sleep is not None
                else None
            ),
            "fitness": (
                {"tsb": fitness.tsb, "acwr": fitness.acwr, "as_of": fitness.as_of}
                if fitness is not None
                else None
            ),
        },
        "strip": strip,
        "last_activity": last_activity,
        "volume": volume,
        "countdown": countdown,
        "recommendations": [asdict(r) for r in recommendations],
        # P2 (T13): digests abaixo da dobra — ficam None até lá
        "volume_weeks": None,
        "predictions": None,
    }
