"""Payload determinístico da avaliação — 100% do banco próprio (EVAL-02/07/16).

O LLM nunca calcula: este módulo monta todos os números a partir do
`get_activity_detail` (voltas já classificadas por zona, consistência,
contexto do dia) + blocos próprios da avaliação (zona alvo por intenção,
PMC do dia, VDOT do arquivo calibrado, PRs datados, padrões ativos).

Cada bloco presente só com o que existir no banco (spec) — bloco vazio
é omitido, nunca preenchido com número inventado.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Activity, DailyLoad, Pattern, PersonalRecord

# Zonas alvo por intenção (assumption do spec): facil→easy;
# tempo/limiar→threshold; intervalado→interval; longao→easy∪marathon;
# progressivo e prova julgam por distribuição/PRs — sem zona alvo única.
TARGET_ZONES: dict[str, list[str] | None] = {
    "facil": ["easy"],
    "tempo": ["threshold"],
    "limiar": ["threshold"],
    "intervalado": ["interval"],
    "longao": ["easy", "marathon"],
    "progressivo": None,
    "prova": None,
}

# PRs canônicos de corrida → rótulo PT-BR (mesma chave de evento do
# potential: FASTEST_*; sem data não vira referência — nada inventado)
_PR_EVENTS = {
    "FASTEST_5K": "5K",
    "FASTEST_10K": "10K",
    "FASTEST_HALF_MARATHON": "Meia",
    "FASTEST_MARATHON": "Maratona",
}


def _fmt_pace(pace_s: float | None) -> str | None:
    """s/km -> "MM:SS/km" (a régua de leitura do corredor); None permanece."""
    if pace_s is None or pace_s <= 0:
        return None
    minutes, seconds = divmod(int(round(pace_s)), 60)
    return f"{minutes}:{seconds:02d}/km"


def _fmt_duration(duration_s: float | None) -> str | None:
    """Segundos -> "h:mm:ss" (com hora) ou "mm:ss"."""
    if duration_s is None or duration_s < 0:
        return None
    total = int(round(duration_s))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _keep(values: dict) -> dict:
    """Filtra None — campo honesto, só o que existir (spec)."""
    return {key: value for key, value in values.items() if value is not None}


def _resumo(activity: Activity, detail: dict) -> dict:
    source = detail["activity"]
    return _keep(
        {
            "nome": source["name"],
            "data": activity.start_time.date().isoformat(),
            "distancia_km": round(source["distance_m"] / 1000, 1) if source["distance_m"] else None,
            "duracao": _fmt_duration(source["duration_s"]),
            "pace_medio": _fmt_pace(source["pace_s"]),
            "fc_media": source["avg_hr"],
            "fc_max": source["max_hr"],
            "cadencia_media": source["avg_cadence"],
            "elevacao_gain_m": source["elevation_gain_m"],
            "te_aerobico": source["aerobic_te"],
            "te_anaerobico": source["anaerobic_te"],
            "carga_treino": source["training_load"],
            "feel": activity.feel,
            "rpe": activity.rpe,
        }
    )


def _voltas(detail: dict) -> list[dict] | None:
    """Voltas classificadas por zona; None sem voltas (EVAL-16)."""
    if not detail["splits"]:
        return None
    return [
        _keep(
            {
                "km": split["km_label"],
                "duracao_s": split["duration_s"],
                "pace": _fmt_pace(split["pace_s"]),
                "zona": split["zone"],
                "fc": split["avg_hr"],
                "cadencia": split["avg_cadence"],
                "temperatura_c": split["avg_temperature"],
                "elevacao_m": split["elevation_m"],
            }
        )
        for split in detail["splits"]
    ]


def _classified_duration(detail: dict) -> tuple[dict[str, float], float]:
    """(duração por zona, duração total) das voltas com zona válida."""
    durations: dict[str, float] = {}
    total = 0.0
    for split in detail["splits"]:
        zone = split["zone"]
        duration = split["duration_s"] or 0
        if zone is None or duration <= 0:
            continue
        durations[zone] = durations.get(zone, 0.0) + duration
        total += duration
    return durations, total


def _tempo_por_zona(detail: dict) -> dict[str, float] | None:
    """% de duração por zona (1 decimal), denominador único; None sem
    nenhuma volta classificada (EVAL-02)."""
    durations, total = _classified_duration(detail)
    if total <= 0:
        return None
    keys = [zone["key"] for zone in detail["zones"]]
    return {
        key: round(durations.get(key, 0.0) / total * 100, 1) for key in keys
    }


def _zona_alvo(detail: dict, intent_type: str) -> dict | None:
    """Zonas alvo da intenção + % de duração nelas (EVAL-02); None quando
    a intenção não tem zona alvo (progressivo/prova) ou não há voltas
    classificadas."""
    targets = TARGET_ZONES.get(intent_type)
    if not targets:
        return None
    durations, total = _classified_duration(detail)
    if total <= 0:
        return None
    in_target = sum(durations.get(zone, 0.0) for zone in targets)
    return {
        "zonas": targets,
        "pct_zona_alvo": round(in_target / total * 100, 1),
    }


def _contexto(detail: dict) -> dict | None:
    """Sono/HRV/FC de repouso/temperatura do dia — só o que existir."""
    context = detail["context"]
    out: dict = {}
    if context.get("sleep") is not None:
        out["sono"] = {
            "duracao_s": context["sleep"]["duration_s"],
            "score": context["sleep"]["score"],
        }
    if context.get("hrv") is not None:
        out["hrv"] = {
            "valor": context["hrv"]["value"],
            "status": context["hrv"]["status"],
        }
    if context.get("rhr") is not None:
        out["fc_repouso"] = {"bpm": context["rhr"]["value"]}
    if context.get("temperature_c") is not None:
        out["temperatura_c"] = context["temperature_c"]
    return out or None


def _carga_do_dia(db: Session, activity: Activity, user_id: int) -> dict | None:
    """Linha de PMC da data local do treino; None sem linha (spec)."""
    row = db.execute(
        select(DailyLoad).where(
            DailyLoad.user_id == user_id,
            DailyLoad.date == activity.start_time.date(),
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return _keep({"ctl": row.ctl, "atl": row.atl, "tsb": row.tsb, "acwr": row.acwr})


def _zonas_meta(detail: dict) -> list[dict]:
    """Zonas vigentes p/ o LLM interpretar — rótulo e faixa, sem cor (UI)."""
    return [
        {"zona": zone["key"], "rotulo": zone["label"], "faixa": zone["pace_range"]}
        for zone in detail["zones"]
    ]


def _vdot_block(settings: Settings) -> dict:
    """VDOT corrente do arquivo calibrado — mesma fonte de verdade do
    painel Performance (ex-Potencial) (o arquivo já foi validado pela dependency de zonas)."""
    with open(settings.vdot_zones_path, encoding="utf-8") as file:
        data = json.load(file)
    return _keep(
        {
            "valor": data.get("vdot"),
            "fonte": data.get("source"),
            "data_teste": data.get("test_date"),
        }
    )


def _prs(db: Session, user_id: int) -> list[dict] | None:
    """PRs canônicos DATADOS como referência de prova; None sem nenhum."""
    rows = db.execute(
        select(PersonalRecord).where(PersonalRecord.user_id == user_id)
    ).scalars().all()
    prs = [
        {
            "evento": _PR_EVENTS[row.event],
            "tempo_s": row.value,
            "data": row.pr_date.isoformat(),
        }
        for row in rows
        if row.event in _PR_EVENTS and row.pr_date is not None and row.value is not None
    ]
    return prs or None


def _padroes(db: Session, user_id: int) -> list[dict] | None:
    """Padrões pessoais de falha ativos; None quando não há."""
    rows = db.execute(
        select(Pattern).where(Pattern.user_id == user_id, Pattern.active.is_(True))
    ).scalars().all()
    if not rows:
        return None
    return [
        {"nome": row.name, "gatilho": row.trigger, "descricao": row.description}
        for row in rows
    ]


def build_evaluation_payload(
    db: Session,
    activity: Activity,
    user_id: int,
    detail: dict,
    intent_type: str,
    intent_text: str | None,
    settings: Settings,
) -> dict:
    """Payload completo da avaliação (EVAL-02): intenção + números
    determinísticos. Chaves ausentes = bloco sem dado no banco. Toda
    leitura (PMC, PRs, padrões) filtra pelo ``user_id`` do usuário da
    sessão (user-scope, USR-15).
    """
    blocks: dict = {
        "intencao": {"tipo": intent_type, "texto": intent_text},
        "resumo": _resumo(activity, detail),
        "voltas": _voltas(detail),
        "tempo_por_zona_pct": _tempo_por_zona(detail),
        "zona_alvo": _zona_alvo(detail, intent_type),
        "consistencia": detail["consistency"],
        "contexto": _contexto(detail),
        "carga_do_dia": _carga_do_dia(db, activity, user_id),
        "zonas": _zonas_meta(detail),
        "vdot": _vdot_block(settings),
        "lthr_bpm": settings.lthr_bpm,
        "prs": _prs(db, user_id),
        "padroes": _padroes(db, user_id),
    }
    return {key: value for key, value in blocks.items() if value is not None}
