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
from logging import getLogger
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities.service import RUNNING_TYPES
from app.core.config import get_settings
from app.db.models import Activity, DailyLoad, Race
from app.garmin.pmc import aggregate_daily_loads
from app.health.service import get_health
from app.home import calc
from app.potential.service import get_predictions
from app.vdot.calibration import load_calibration
from app.vdot.zones import ZoneConfigError

logger = getLogger(__name__)

# Janela do volume semanal: 10 semanas ISO (série) + a corrente
VOLUME_WINDOW_DAYS = 70

# P2 (T13): eventos do digest de previsões — 10K (referência corrente)
# e meia (objetivo ativo, spec §Assumptions); 5K/maratona moram no
# painel Performance — a Home roteia, nunca duplica painel.
PREDICTION_EVENTS = ("10K", "HALF_MARATHON")


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
    # 10 semanas (weeks) alimenta o bloco P2 `volume_weeks` (T13).
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
    volume_weeks = None
    if run_rows:
        wv = calc.weekly_volume([(t.date(), m) for t, m in run_rows], today)
        volume = {
            "week_km": wv["week_km"],
            "avg4_km": wv["avg4_km"],
            "delta_pct": wv["delta_pct"],
        }
        volume_weeks = wv["weeks"]

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

    # P2 (T13): digest de previsões — a MESMA montagem do painel
    # Performance (get_predictions extraído) com a MESMA calibração
    # (uma fonte de verdade); evento sem predição é omitido (HOME-39).
    # Arquivo de calibração ausente/inválido degrada o bloco para None:
    # a Home NUNCA 500 por causa de um bloco P2 (design §Erros).
    predictions = None
    try:
        calibration = load_calibration(get_settings().vdot_zones_path)
    except ZoneConfigError as exc:
        logger.warning("digest de previsões omitido na Home: %s", exc)
    else:
        rows = get_predictions(db, user_id, calibration)
        predictions = [
            {"event": event, "time_s": rows[event]["average_s"]}
            for event in PREDICTION_EVENTS
            if rows[event]["average_s"] is not None
        ]

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
        # P2 (T13): digests abaixo da dobra — série de 10 semanas e
        # previsões de 10K/meia (None quando não há o que dizer)
        "volume_weeks": volume_weeks,
        "predictions": predictions,
    }
