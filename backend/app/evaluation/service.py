"""Orquestração da avaliação como job (emenda 18/10 — padrão SyncJob).

`create_evaluation` é o request path: valida o que é rápido (404/422),
monta o payload determinístico e grava a linha ``status=pending`` —
**nenhuma chamada à NIM aqui**. O POST responde 201 e o worker
(``run_evaluation``, via BackgroundTasks) consome a NIM e conclui a
linha: ``done`` com o veredito sanitizado + tokens + ``evaluated=true``,
ou ``error`` com o motivo na própria linha — a tentativa nunca se
perde (decisão do usuário no UAT: perder a espera é o problema).

Escala de erro síncrona (o router mapeia): ``ActivityNotRunning`` → 422;
None → 404. Falhas da NIM/veredito não são HTTP — viram linha ``error``.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.activities import service as activities_service
from app.core.config import Settings, get_settings
from app.db.models import Activity, Evaluation
from app.evaluation import nim
from app.evaluation.payload import build_evaluation_payload
from app.evaluation.prompt import PROMPT_VERSION, SYSTEM_PROMPT_V1
from app.evaluation.verdict import sanitize_echo, validate_verdict
from app.vdot.zones import ZoneConfig

# Vocabulário de corrida do domínio (mesmo conjunto do activities/service)
RUNNING_TYPES = ("running", "trail_running")

# Estados da linha (emenda job): pending (criada) → done | error (worker)
STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_ERROR = "error"

INTERRUPTED_MESSAGE = "interrompida por restart do backend"


class ActivityNotRunning(Exception):
    """Avaliação é de corrida: não-corrida → 422 no router (EVAL-10)."""


def _evaluation_dict(evaluation: Evaluation) -> dict:
    """Linha -> dict no shape de EvaluationOut (contrato único)."""
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
        "status": evaluation.status,
        "error": evaluation.error,
        "created_at": evaluation.created_at,
    }


def create_evaluation(
    db: Session,
    activity_id: int,
    user_id: int,
    intent_type: str,
    intent_text: str | None,
    zone_config: ZoneConfig,
    settings: Settings | None = None,
) -> dict | None:
    """Cria a avaliação ``pending`` com o payload montado (EVAL-21).

    Request path: valida 404/422, monta o payload determinístico, grava
    a linha — NENHUMA chamada à NIM aqui (o worker é quem consome).
    None = atividade inexistente OU de outro usuário (404 no router —
    user-scope, USR-16: a avaliação vincula só a atividades do próprio
    usuário e grava ``user_id`` do dono da sessão).
    """
    settings = settings or get_settings()

    activity = db.execute(
        select(Activity).where(
            Activity.id == activity_id, Activity.user_id == user_id
        )
    ).scalar_one_or_none()
    if activity is None:
        return None
    if activity.activity_type not in RUNNING_TYPES:
        raise ActivityNotRunning(
            f"atividade {activity_id} não é corrida ({activity.activity_type})"
        )

    detail = activities_service.get_activity_detail(
        db, activity.id, activity.user_id, zone_config
    )
    payload = build_evaluation_payload(
        db, activity, user_id, detail, intent_type, intent_text, settings
    )

    evaluation = Evaluation(
        user_id=user_id,
        activity_id=activity.id,
        intent_type=intent_type,
        intent_text=intent_text,
        payload_json=payload,
        model=settings.nvidia_model,
        prompt_version=PROMPT_VERSION,
        verdict="",
        verdict_json=None,
        status=STATUS_PENDING,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _evaluation_dict(evaluation)


def _mark_error(db: Session, evaluation_id: int, message: str) -> None:
    """Linha pending → error com o motivo (EVAL-23) — em sessão limpa."""
    db.rollback()
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        return
    evaluation.status = STATUS_ERROR
    evaluation.error = message
    db.commit()


def run_evaluation(evaluation_id: int) -> None:
    """Worker (BackgroundTasks): pending → NIM → §9.2 → done | error.

    Sessão fresca (o request já morreu). Linha que não é pending é
    no-op (já processada ou recuperada no startup). Nenhuma exceção
    vira crash: falha da NIM/veredito vira linha ``error`` com o
    motivo (EVAL-22/23).
    """
    from app.db.engine import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        evaluation = db.get(Evaluation, evaluation_id)
        if evaluation is None or evaluation.status != STATUS_PENDING:
            return

        try:
            payload = evaluation.payload_json or {}
            verdict_data, usage = nim.chat_completion(
                SYSTEM_PROMPT_V1,
                json.dumps(payload, ensure_ascii=False),
                settings,
            )
            verdict = validate_verdict(verdict_data)

            # Eco sanitizado: pct_zona_alvo sempre do Python (AD-003)
            zona_alvo = payload.get("zona_alvo")
            python_pct = zona_alvo["pct_zona_alvo"] if zona_alvo else None
            verdict_json = sanitize_echo(verdict, python_pct)

            evaluation.verdict = verdict.veredito
            evaluation.verdict_json = verdict_json
            evaluation.tokens_in = usage["prompt_tokens"]
            evaluation.tokens_out = usage["completion_tokens"]
            evaluation.status = STATUS_DONE
            activity = db.get(Activity, evaluation.activity_id)
            if activity is not None:
                activity.evaluated = True
        except (nim.NimError, ValueError) as exc:
            _mark_error(db, evaluation_id, str(exc))
        except Exception as exc:  # worker isolado: nada derruba o container
            _mark_error(db, evaluation_id, f"erro inesperado: {exc}")
        else:
            db.commit()


def recover_stale_evaluations() -> None:
    """Startup: pending órfãs (restart no meio da chamada) viram error
    "interrompida" (EVAL-24 — padrão recover_stale_jobs do sync)."""
    from app.db.engine import SessionLocal

    with SessionLocal() as db:
        stale = (
            db.execute(
                select(Evaluation).where(Evaluation.status == STATUS_PENDING)
            )
            .scalars()
            .all()
        )
        for evaluation in stale:
            evaluation.status = STATUS_ERROR
            evaluation.error = INTERRUPTED_MESSAGE
        db.commit()


def get_evaluation(
    db: Session, activity_id: int, evaluation_id: int, user_id: int
) -> dict | None:
    """Uma avaliação do treino por id (GET de status, EVAL-25); None → 404
    (inexistente OU de outro usuário — user-scope, USR-12)."""
    evaluation = db.execute(
        select(Evaluation).where(
            Evaluation.id == evaluation_id,
            Evaluation.activity_id == activity_id,
            Evaluation.user_id == user_id,
        )
    ).scalar_one_or_none()
    return None if evaluation is None else _evaluation_dict(evaluation)


def list_evaluations(db: Session, activity_id: int, user_id: int) -> list[dict]:
    """Avaliações do treino, mais recente primeiro (EVAL-17/18/19) — só as
    do usuário da sessão (user-scope, USR-08)."""
    rows = (
        db.execute(
            select(Evaluation)
            .where(
                Evaluation.activity_id == activity_id,
                Evaluation.user_id == user_id,
            )
            .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
        )
        .scalars()
        .all()
    )
    return [_evaluation_dict(row) for row in rows]
