"""Matemática do painel Potencial — funções puras (design).

Sem DB, sem I/O — a mesma entrada devolve sempre os mesmos valores
(AD-003), pinável em teste e trocável no v2 (média ponderada dos PRs
está no Out of Scope do spec). As entradas são as linhas do banco
(duck typing: atributos), as saídas são dicts prontos para o payload.

Distâncias canônicas (spec): só 5K/10K/meia/maratona entram na
timeline, no demonstrado e nas previsões — 1K/milha são marcadores de
velocidade, LONGEST_RUN é distância, não tempo (Out of Scope).

Riegel (premissa do spec): âncora fixa no PR de 5K, expoente 1.06 —
a direção confiável (10K → meia → maratona, projeções para cima).
"""

from datetime import date

from app.vdot.daniels import calculate_vdot, equivalent_time

# Distâncias canônicas em metros — mesmas do RACE_DISTANCES_KM do script
CANONICAL: dict[str, float] = {
    "5K": 5000.0,
    "10K": 10000.0,
    "HALF_MARATHON": 21097.5,
    "MARATHON": 42195.0,
}

# PR -> distância canônica (eventos FASTEST_* do SYNC-16)
_PR_EVENT_TO_CANONICAL = {
    "FASTEST_5K": "5K",
    "FASTEST_10K": "10K",
    "FASTEST_HALF_MARATHON": "HALF_MARATHON",
    "FASTEST_MARATHON": "MARATHON",
}

# Rótulos exibíveis por distância canônica (design §Contrato)
_LABELS = {
    "5K": "5K",
    "10K": "10K",
    "HALF_MARATHON": "Meia",
    "MARATHON": "Maratona",
}


def riegel_time(anchor_s: float, anchor_m: float, target_m: float, exponent: float = 1.06) -> float:
    """Riegel: T2 = T1 × (D2/D1)^expoente — projeção entre distâncias."""
    return anchor_s * (target_m / anchor_m) ** exponent


def _format_duration(total_s: float) -> str:
    """Tempo exibível: h:mm:ss acima de 1h, m:ss abaixo (design §Contrato)."""
    seconds = int(total_s)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _valid_effort(distance_m: float | None, time_s: float | None) -> bool:
    """Esforço com VDOT definível: distância e tempo > 0 (edge do spec)."""
    return bool(distance_m and distance_m > 0 and time_s and time_s > 0)


def timeline_points(prs, races, calibration) -> list[dict]:
    """Pontos da timeline VDOT — ordenados por data (design §Contrato).

    - PR canônico datado e válido -> source="pr", label "5K 19:23";
      PR sem data/inválido (distância ou tempo ≤ 0) fica fora (spec:
      VDOT indefinido, nada inventado).
    - Prova (atividade eventType=race, já filtrada pelo service) ->
      source="prova", label = nome da atividade; dedup: prova na mesma
      data de um PR canônico não vira ponto (o PR certificado prevalece).
    - Teste de calibração -> source="teste", label = source do arquivo;
      mesmo com data igual a um PR, ambos viram pontos (edge do spec).
    """
    points: list[dict] = []
    for pr in prs:
        canonical = _PR_EVENT_TO_CANONICAL.get(pr.event)
        if canonical is None or pr.pr_date is None or not _valid_effort(CANONICAL[canonical], pr.value):
            continue
        points.append(
            {
                "date": pr.pr_date,
                "vdot": calculate_vdot(CANONICAL[canonical], pr.value),
                "source": "pr",
                "label": f"{_LABELS[canonical]} {_format_duration(pr.value)}",
                "distance_m": CANONICAL[canonical],
                "time_s": pr.value,
            }
        )

    pr_dates = {p["date"] for p in points}
    for race in races:
        if race.start_time is None or not _valid_effort(race.distance_m, race.duration_s):
            continue
        race_date: date = race.start_time.date()
        if race_date in pr_dates:
            continue  # dedup: o PR certificado prevalece na mesma data
        points.append(
            {
                "date": race_date,
                "vdot": calculate_vdot(race.distance_m, race.duration_s),
                "source": "prova",
                "label": race.name,
                "distance_m": race.distance_m,
                "time_s": race.duration_s,
            }
        )

    points.append(
        {
            "date": calibration.test_date,
            "vdot": calculate_vdot(calibration.distance_m, calibration.time_s),
            "source": "teste",
            "label": calibration.source,
            "distance_m": calibration.distance_m,
            "time_s": calibration.time_s,
        }
    )
    return sorted(points, key=lambda p: p["date"])


def demonstrated(points: list[dict]) -> float | None:
    """Maior VDOT entre os pontos — o potencial demonstrado (§9.5); vazio -> None."""
    if not points:
        return None
    return max(p["vdot"] for p in points)


def _canonical_prs(prs) -> dict[str, object]:
    """PRs canônicos válidos por distância — esforço 0/negativo fica fora (spec)."""
    by_event: dict[str, object] = {}
    for pr in prs:
        canonical = _PR_EVENT_TO_CANONICAL.get(pr.event)
        if canonical is not None and pr.value and pr.value > 0:
            by_event[canonical] = pr
    return by_event


def predictions(garmin, pr_5k_s, current_vdot, prs) -> dict[str, dict]:
    """As 4 estimativas por distância canônica (design §Contrato).

    - `riegel_s`: ancorado no PR de 5K (T2 = T1 × (D2/5000)^1.06); NULL
      sem âncora — nunca substituída por outra distância (spec).
    - `vdot_s`: equivalência do VDOT corrente (`equivalent_time`).
    - `average_s`: média aritmética só das estimativas presentes — o
      "—" do spec não entra na conta; todas ausentes -> None.
    - `pr_s`/`pr_date`: do PR canônico; NULL quando ausente.

    Valores calculados com 1 decimal — o payload é auto-consistente
    (a média e o delta conferem com os números exibidos).
    """
    pr_by_event = _canonical_prs(prs)
    rows: dict[str, dict] = {}
    for event, distance_m in CANONICAL.items():
        garmin_s = garmin.get(event)
        riegel_s = (
            round(riegel_time(pr_5k_s, CANONICAL["5K"], distance_m), 1)
            if pr_5k_s and pr_5k_s > 0
            else None
        )
        vdot_s = round(equivalent_time(current_vdot, distance_m / 1000), 1)
        present = [v for v in (garmin_s, riegel_s, vdot_s) if v is not None]
        pr = pr_by_event.get(event)
        rows[event] = {
            "garmin_s": round(garmin_s, 1) if garmin_s is not None else None,
            "riegel_s": riegel_s,
            "vdot_s": vdot_s,
            "average_s": round(sum(present) / len(present), 1) if present else None,
            "pr_s": round(pr.value, 1) if pr is not None else None,
            "pr_date": pr.pr_date if pr is not None else None,
        }
    return rows


def decay(prs, current_vdot) -> list[dict]:
    """Decaimento de ritmo por distância canônica COM PR (POT-14).

    `real_pace_s` (PR) vs `ideal_pace_s` (equivalência do VDOT corrente)
    e `delta_pct = (ideal−real)/ideal × 100` — negativo = gap (o real
    está mais lento que o ideal). Distância sem PR fica de fora da
    lista (nenhum número inventado — spec); delta calculado dos paces
    do payload (1 decimal), para os números exibidos se conferirem.
    """
    pr_by_event = _canonical_prs(prs)
    rows: list[dict] = []
    for event, distance_m in CANONICAL.items():
        pr = pr_by_event.get(event)
        if pr is None:
            continue
        distance_km = distance_m / 1000
        real_pace_s = round(pr.value / distance_km, 1)
        ideal_pace_s = round(equivalent_time(current_vdot, distance_km) / distance_km, 1)
        rows.append(
            {
                "event": event,
                "real_pace_s": real_pace_s,
                "ideal_pace_s": ideal_pace_s,
                "delta_pct": round((ideal_pace_s - real_pace_s) / ideal_pace_s * 100, 1),
            }
        )
    return rows
