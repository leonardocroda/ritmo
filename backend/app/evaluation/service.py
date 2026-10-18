"""Orquestração da avaliação: payload → prompt → NIM → veredito → banco.

Nada é gravado em falha (Decisão E): o commit único acontece no fim,
depois de toda validação — uma exceção em qualquer etapa não deixa
linha de `Evaluation` nem altera `activity.evaluated`.

Escala de erro (o router mapeia): `ActivityNotRunning` → 422;
`NimTimeout` → 504; `NimError`/`ValueError` de veredito → 502;
None → 404.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities import service as activities_service
from app.core.config import Settings, get_settings
from app.db.models import DEFAULT_USER_ID, Activity, Evaluation
from app.evaluation import nim
from app.evaluation.payload import build_evaluation_payload
from app.evaluation.prompt import PROMPT_VERSION, SYSTEM_PROMPT_V1
from app.evaluation.verdict import sanitize_echo, validate_verdict
from app.vdot.zones import ZoneConfig

# Vocabulário de corrida do domínio (mesmo conjunto do activities/service)
RUNNING_TYPES = ("running", "trail_running")


class ActivityNotRunning(Exception):
    """Avaliação é de corrida: não-corrida → 422 no router (EVAL-10)."""


def evaluate(
    db: Session,
    activity_id: int,
    intent_type: str,
    intent_text: str | None,
    zone_config: ZoneConfig,
    settings: Settings | None = None,
) -> dict | None:
    """Avalia uma corrida de ponta a ponta; None = atividade inexistente.

    Fluxo (EVAL-02/03/04): detail → payload determinístico → uma chamada
    NIM → veredito validado e sanitizado → Evaluation + evaluated=true.
    """
    settings = settings or get_settings()

    activity = db.execute(
        select(Activity).where(
            Activity.id == activity_id, Activity.user_id == DEFAULT_USER_ID
        )
    ).scalar_one_or_none()
    if activity is None:
        return None
    if activity.activity_type not in RUNNING_TYPES:
        raise ActivityNotRunning(
            f"atividade {activity_id} não é corrida ({activity.activity_type})"
        )

    detail = activities_service.get_activity_detail(db, activity.id, zone_config)
    payload = build_evaluation_payload(
        db, activity, detail, intent_type, intent_text, settings
    )

    # LLM interpreta; números já vieram prontos no payload (AD-003)
    verdict_data, usage = nim.chat_completion(
        SYSTEM_PROMPT_V1, json.dumps(payload, ensure_ascii=False), settings
    )

    verdict = validate_verdict(verdict_data)

    # Eco sanitizado: pct_zona_alvo sempre do Python (nunca do LLM)
    zona_alvo = payload.get("zona_alvo")
    python_pct = zona_alvo["pct_zona_alvo"] if zona_alvo else None
    verdict_json = sanitize_echo(verdict, python_pct)

    evaluation = Evaluation(
        activity_id=activity.id,
        intent_type=intent_type,
        intent_text=intent_text,
        payload_json=payload,
        model=settings.nvidia_model,
        prompt_version=PROMPT_VERSION,
        verdict=verdict.veredito,
        verdict_json=verdict_json,
        tokens_in=usage["prompt_tokens"],
        tokens_out=usage["completion_tokens"],
    )
    db.add(evaluation)
    activity.evaluated = True
    db.commit()
    db.refresh(evaluation)

    return {
        "id": evaluation.id,
        "activity_id": evaluation.activity_id,
        "intent_type": evaluation.intent_type,
        "intent_text": evaluation.intent_text,
        "verdict": evaluation.verdict,
        "verdict_json": evaluation.verdict_json,
        "model": evaluation.model,
        "prompt_version": evaluation.prompt_version,
        "tokens_in": evaluation.tokens_in,
        "tokens_out": evaluation.tokens_out,
        "created_at": evaluation.created_at,
    }


def list_evaluations(db: Session, activity_id: int) -> list[dict]:
    """Avaliações do treino, mais recente primeiro (EVAL-17/18/19)."""
    rows = (
        db.execute(
            select(Evaluation)
            .where(
                Evaluation.activity_id == activity_id,
                Evaluation.user_id == DEFAULT_USER_ID,
            )
            .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": row.id,
            "activity_id": row.activity_id,
            "intent_type": row.intent_type,
            "intent_text": row.intent_text,
            "verdict": row.verdict,
            "verdict_json": row.verdict_json,
            "model": row.model,
            "prompt_version": row.prompt_version,
            "tokens_in": row.tokens_in,
            "tokens_out": row.tokens_out,
            "created_at": row.created_at,
        }
        for row in rows
    ]
