"""Carga determinística (PMC) — CTL/ATL/TSB/ACWR em Python puro (SYNC-22..24).

EWMA diária: CTL α=1/42, ATL α=1/7, TSB = CTL − ATL. A semente do
`recompute` vem da última linha de `load` anterior à janela (SYNC-23);
sem linha, é o load do primeiro dia da série. `recompute` reescreve só
a janela afetada — o histórico anterior fica intocado (spec).
ACWR = soma(7d)/(soma(28d)/4), `None` até existirem 28 dias completos
de carga (parcial enganaria o painel — design).
"""

from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Activity, DailyLoad

CTL_ALPHA = 1 / 42  # ~42 dias de meia-vida de fitness
ATL_ALPHA = 1 / 7  # ~7 dias de meia-vida de fadiga
ACWR_LONG_DAYS = 28
ACWR_SHORT_DAYS = 7


def aggregate_daily_loads(db: Session, user_id: int) -> list[tuple[date, float]]:
    """Soma de `training_load` por data local; gaps ficam com carga 0.

    Série contígua da primeira à última atividade do usuário. Atividade
    sem `training_load` conta 0 no seu dia (SYNC-24).
    """
    rows = db.execute(
        select(Activity.start_time, Activity.training_load)
        .where(Activity.user_id == user_id)
        .order_by(Activity.start_time)
    ).all()
    if not rows:
        return []
    loads: dict[date, float] = {}
    for start_time, training_load in rows:
        day = start_time.date()
        loads[day] = loads.get(day, 0.0) + (training_load or 0.0)
    first, last = min(loads), max(loads)
    return [
        (first + timedelta(days=offset), loads.get(first + timedelta(days=offset), 0.0))
        for offset in range((last - first).days + 1)
    ]


def recompute(db: Session, user_id: int, from_date: date, today: date) -> int:
    """Recalcula a PMC só de `from_date` até `today` (SYNC-23).

    Apaga e reinsere apenas as linhas da janela. A semente CTL/ATL vem
    da última linha de `load` anterior à janela — sem linha, do load do
    primeiro dia da série. Retorna o número de linhas escritas.
    """
    series = aggregate_daily_loads(db, user_id)
    if not series:
        return 0
    loads = dict(series)
    first_day = series[0][0]
    start = max(from_date, first_day)
    seed = db.execute(
        select(DailyLoad)
        .where(DailyLoad.user_id == user_id, DailyLoad.date < from_date)
        .order_by(DailyLoad.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if seed is not None:
        ctl, atl = float(seed.ctl), float(seed.atl)
    else:
        ctl = atl = loads.get(first_day, 0.0)

    total_days = (today - first_day).days + 1
    full = [loads.get(first_day + timedelta(days=i), 0.0) for i in range(total_days)]
    db.execute(
        delete(DailyLoad).where(
            DailyLoad.user_id == user_id,
            DailyLoad.date >= start,
            DailyLoad.date <= today,
        )
    )
    written = 0
    for offset in range((start - first_day).days, total_days):
        load = full[offset]
        ctl += CTL_ALPHA * (load - ctl)
        atl += ATL_ALPHA * (load - atl)
        acwr = None
        if offset >= ACWR_LONG_DAYS - 1:  # janela de 28d completa a partir do dia 28
            long_sum = sum(full[offset - (ACWR_LONG_DAYS - 1) : offset + 1])
            short_sum = sum(full[offset - (ACWR_SHORT_DAYS - 1) : offset + 1])
            acwr = short_sum / (long_sum / 4)
        db.add(
            DailyLoad(
                user_id=user_id,
                date=first_day + timedelta(days=offset),
                ctl=ctl,
                atl=atl,
                tsb=ctl - atl,
                acwr=acwr,
            )
        )
        written += 1
    return written
