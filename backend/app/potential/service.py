"""Service do painel Performance (ex-Potencial) — leitura pura do banco (AD-002).

Nenhuma importação do gateway Garmin: todo número vem do banco próprio
(PRs, predições, atividades) e da calibração vigente — o painel
inteiro é montável offline (Success Criteria do spec). O filtro de
corridas/provas é em Python (AD-001: escala pessoal, ~233 linhas;
sintaxe JSON de SQL acoplaria o driver — design §Riscos).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DEFAULT_USER_ID,
    Activity,
    PersonalRecord,
    RacePrediction,
)
from app.potential.calc import decay, predictions, timeline_points
from app.vdot.calibration import Calibration

# Vocabulário de corrida do domínio (mesmo conjunto do activities)
RUNNING_TYPES = ("running", "trail_running")


def _garmin_by_event(db: Session) -> dict[str, float]:
    """Snapshot latest das predições por evento; linha sem tempo = ausente."""
    rows = (
        db.execute(
            select(RacePrediction).where(RacePrediction.user_id == DEFAULT_USER_ID)
        )
        .scalars()
        .all()
    )
    return {row.event: row.time_s for row in rows if row.time_s is not None}


def _vo2max_block(activities: list[Activity]) -> dict | None:
    """Tendência do VO2max do relógio: corridas com `vO2MaxValue` no raw_json.

    Ordem start_time ASC com desempate id ASC (determinismo do spec).
    Corrida sem o campo (ou não numérico) fica de fora; nenhuma com o
    campo -> None (estado vazio, não erro).
    """
    runs = sorted(
        (a for a in activities if a.activity_type in RUNNING_TYPES),
        key=lambda a: (a.start_time, a.id),
    )
    points = []
    for run in runs:
        value = (run.raw_json or {}).get("vO2MaxValue")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        points.append({"date": run.start_time.date(), "value": float(value)})
    return {"points": points} if points else None


def _races(activities: list[Activity]) -> list[Activity]:
    """Atividades marcadas como prova (eventType=race no raw_json)."""
    return [
        activity
        for activity in activities
        if ((activity.raw_json or {}).get("eventType") or {}).get("typeKey") == "race"
    ]


def _demonstrated_block(points: list[dict], prs: list[PersonalRecord]) -> dict | None:
    """O maior VDOT dos pontos com a origem para exibição (design §Contrato).

    PR -> o evento (`FASTEST_5K`); prova -> nome da atividade; teste ->
    source do arquivo (verbatim). Vazio -> None (nenhum número inventado).
    """
    if not points:
        return None
    best = max(points, key=lambda p: p["vdot"])
    if best["source"] == "pr":
        source = next(
            (
                pr.event
                for pr in prs
                if pr.pr_date == best["date"] and pr.value == best["time_s"]
            ),
            best["label"],
        )
    else:
        source = best["label"]
    return {"vdot": best["vdot"], "source": source, "date": best["date"]}


def get_potential(db: Session, calibration: Calibration) -> dict:
    """Payload do painel — os 4 blocos do design §Contrato.

    Sem `pmc` e sem janela `days` (CLR-03): a curva de carga mora no
    health (panel-clarity T1/T2). A matemática vive em calc.py (pura,
    AD-003) — aqui é só leitura e montagem.
    """
    prs = (
        db.execute(
            select(PersonalRecord).where(PersonalRecord.user_id == DEFAULT_USER_ID)
        )
        .scalars()
        .all()
    )
    activities = (
        db.execute(select(Activity).where(Activity.user_id == DEFAULT_USER_ID))
        .scalars()
        .all()
    )

    points = timeline_points(prs, _races(activities), calibration)
    block_demonstrated = _demonstrated_block(points, prs)
    gap_pct = (
        round(calibration.vdot / block_demonstrated["vdot"] * 100, 1)
        if block_demonstrated is not None
        else None
    )
    pr_5k_s = next((pr.value for pr in prs if pr.event == "FASTEST_5K"), None)

    return {
        "vdot": {
            "current": {
                "vdot": calibration.vdot,
                "source": calibration.source,
                "test_date": calibration.test_date,
            },
            "demonstrated": block_demonstrated,
            "gap_pct": gap_pct,
            "timeline": points,
        },
        "predictions": predictions(_garmin_by_event(db), pr_5k_s, calibration.vdot, prs),
        "vo2max": _vo2max_block(activities),
        "decay": decay(prs, calibration.vdot),
    }
