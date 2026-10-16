"""Matemática do painel Saúde — funções puras (design).

Sem DB, sem I/O — a mesma entrada devolve sempre os mesmos valores
(AD-003), pinável em teste. As entradas são dicts montados pelo service
(noites de sono com a HRV/score da mesma data já cruzados e os horários
de deitar/acordar já convertidos para minutos locais); as saídas são
dicts prontos para o payload.

Buckets do dose-resposta (§4.5): <6h vs ≥6h45 com faixa neutra
6h–6h45 — contraste máximo, sem diluir o recado no meio. Piso de sono
7h e banda REM 21–31% são réguas do backend: a UI não inventa régua.
"""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Réguas do painel (design §Components): piso 7h, banda REM ideal 21–31%,
# buckets do dose-resposta (<6h = short / ≥6h45 = adequate).
SLEEP_FLOOR_S = 25200
REM_BAND = (21.0, 31.0)
SHORT_MAX_S = 21600
ADEQUATE_MIN_S = 24300

_MINUTES_DAY = 1440
_HALF_DAY = 720


def local_minute(naive_utc: datetime, tz: ZoneInfo) -> int:
    """Wall clock GMT naive -> minuto do dia local (contraparte da
    conversão do sync — design §Reuse).

    A conversão usa o datetime completo e cruza a meia-noite: 01:16 GMT
    -> 1336 (22:16 do dia anterior em America/Sao_Paulo)."""
    local = naive_utc.replace(tzinfo=timezone.utc).astimezone(tz)
    return local.hour * 60 + local.minute


def _circular_mean(minutes: list[int]) -> float:
    """Média de minutos do dia com o truque do deslocamento de ±12h
    (design §Riscos): medidos a partir do meio-dia, 23:50 e 00:10 têm
    média 00:00 — não 12:00."""
    shifted = [(m - _HALF_DAY) % _MINUTES_DAY for m in minutes]
    return (sum(shifted) / len(shifted) + _HALF_DAY) % _MINUTES_DAY


def _avg(values: list[float]) -> float | None:
    """Média com 1 casa — bucket/média vazia -> None (nada inventado)."""
    return round(sum(values) / len(values), 1) if values else None


def dose_response(nights: list[dict]) -> dict:
    """O "juros" do sono curto (§4.5): noites <6h vs ≥6h45 com HRV e
    score médios da mesma noite (spec AC 9).

    Cada noite já traz `hrv`/`score` da mesma data (o cruzamento é
    garantido pelo service); noite sem HRV na mesma data fica fora da
    comparação — contada como neutra apenas na faixa 6h–6h45 (edge do
    spec). Bucket sem noites -> médias None (estado vazio, não erro).
    """
    short_hrv: list[float] = []
    short_score: list[float] = []
    adequate_hrv: list[float] = []
    adequate_score: list[float] = []
    neutral = 0
    for night in nights:
        duration = night["duration_s"]
        if SHORT_MAX_S <= duration < ADEQUATE_MIN_S:
            neutral += 1
        hrv = night.get("hrv")
        if hrv is None:
            continue
        if duration < SHORT_MAX_S:
            short_hrv.append(hrv)
            if night.get("score") is not None:
                short_score.append(night["score"])
        elif duration >= ADEQUATE_MIN_S:
            adequate_hrv.append(hrv)
            if night.get("score") is not None:
                adequate_score.append(night["score"])
    return {
        "short": {
            "nights": len(short_hrv),
            "avg_hrv": _avg(short_hrv),
            "avg_score": _avg(short_score),
        },
        "adequate": {
            "nights": len(adequate_hrv),
            "avg_hrv": _avg(adequate_hrv),
            "avg_score": _avg(adequate_score),
        },
        "neutral_nights": neutral,
    }


def weekday_pattern(nights: list[dict]) -> list[dict]:
    """Média de duração por dia da semana — 7 entradas seg..dom (AC 4),
    pelo weekday da data de acordar (premissa do spec: a noite que
    virou sexta é da sexta). Dia sem noites -> None/0."""
    by_weekday: dict[int, list[float]] = {weekday: [] for weekday in range(7)}
    for night in nights:
        by_weekday[night["date"].weekday()].append(night["duration_s"])
    return [
        {
            "weekday": weekday,
            "avg_duration_s": _avg(durations),
            "nights": len(durations),
        }
        for weekday, durations in by_weekday.items()
    ]


def below_floor(nights: list[dict]) -> dict:
    """Noites abaixo do piso de 7h: contagem + % da janela (AC 4),
    pct com 1 casa."""
    below = [n for n in nights if n["duration_s"] < SLEEP_FLOOR_S]
    pct = round(len(below) / len(nights) * 100, 1) if nights else 0.0
    return {"nights": len(below), "pct": pct}


def regularity(nights: list[dict]) -> dict | None:
    """Horários médios de deitar/acordar em minutos locais (AC 4).

    Noite sem `bed_time`/`wake_time` fica fora (nenhum horário
    inventado — edge do spec); sem noites elegíveis -> None. A média
    usa o truque ±12h: deitar 23:50 e 00:10 média 00:00, não 12:00."""
    eligible = [
        n
        for n in nights
        if n.get("bed_min") is not None and n.get("wake_min") is not None
    ]
    if not eligible:
        return None
    return {
        "avg_bed_min": round(_circular_mean([n["bed_min"] for n in eligible]), 1),
        "avg_wake_min": round(_circular_mean([n["wake_min"] for n in eligible]), 1),
    }


def strength_weeks(
    sessions: list[datetime | date], today: date, window_start: date
) -> dict:
    """Checklist de força 2×/semana por semana ISO (spec AC 12).

    - Semana ISO = segunda a domingo (chave da segunda-feira — mesma
      agrupação de `isocalendar()`, aritmética segura na virada de ano).
    - `streak_weeks`: semanas completas (≥2 sessões) consecutivas
      terminando na última semana completa — a corrente, em andamento,
      nunca é julgada (edge do spec) e a contagem pode exceder a janela.
    - `weeks_hit`/`weeks_total`: limitados à janela (sessões contadas
      dentro dela; weeks_total = semanas ISO que a janela toca).
    - `current_week_sessions`: sessões da semana corrente, à parte.
    """
    days = [s.date() if isinstance(s, datetime) else s for s in sessions]

    def week_of(day: date) -> date:
        return day - timedelta(days=day.weekday())

    by_week: dict[date, int] = {}
    for day in days:
        key = week_of(day)
        by_week[key] = by_week.get(key, 0) + 1

    streak = 0
    week = week_of(today) - timedelta(days=7)
    while by_week.get(week, 0) >= 2:
        streak += 1
        week -= timedelta(days=7)

    current_week = week_of(today)
    window_by_week: dict[date, int] = {}
    for day in days:
        if window_start <= day <= today:
            key = week_of(day)
            window_by_week[key] = window_by_week.get(key, 0) + 1

    weeks_total = 0
    weeks_hit = 0
    week = week_of(window_start)
    while week <= current_week:
        weeks_total += 1
        if window_by_week.get(week, 0) >= 2:
            weeks_hit += 1
        week += timedelta(days=7)

    return {
        "streak_weeks": streak,
        "weeks_hit": weeks_hit,
        "weeks_total": weeks_total,
        "current_week_sessions": by_week.get(current_week, 0),
    }
