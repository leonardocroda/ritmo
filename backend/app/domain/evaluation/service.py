"""Application Service do domínio Evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.evaluation.domain.entities import EvaluationJob, EvaluationRecord, Verdict
from app.domain.evaluation.ports.repositories import EvaluationRepository
from app.domain.evaluation.ports.ai_client import AIClient
from app.domain.evaluation.schemas import EvaluationOut, EvaluateIn, VerdictOut
from app.domain.activities.domain.value_objects import ZoneConfigVO
from app.domain.activities.domain.entities import Activity


@dataclass
class EvaluationService:
    repo: EvaluationRepository
    ai_client: AIClient

    async def create_evaluation(
        self,
        activity: Activity,
        user_id: int,
        intent_type: str,
        intent_text: Optional[str],
        zone_config: ZoneConfigVO,
    ) -> EvaluationRecord:
        job = EvaluationJob(
            id=0,  # Será preenchido pelo repo
            activity_id=activity.id,
            user_id=user_id,
            intent_type=intent_type,
            intent_text=intent_text,
            status="pending",
            created_at=None,
        )

        record = self.repo.create(EvaluationRecord(
            id=0,
            activity_id=activity.id,
            user_id=user_id,
            intent_type=intent_type,
            intent_text=intent_text,
            verdict=None,
            model="nim",
            prompt_version="v1",
            tokens_in=0,
            tokens_out=0,
            status="pending",
            error=None,
            created_at=None,
        ))

        return record

    async def run_evaluation(self, eval_id: int) -> EvaluationRecord:
        record = self.repo.get_by_id(eval_id, 0)  # user_id validado no repo
        if not record:
            raise ValueError("Avaliação não encontrada")

        # Buscar atividade e zone_config
        # Placeholder - implementar busca real
        activity = None  # buscar activity
        zone_config = None  # buscar zone_config

        try:
            verdict = await self.ai_client.evaluate(
                EvaluationJob(
                    id=record.id,
                    activity_id=record.activity_id,
                    user_id=record.user_id,
                    intent_type=record.intent_type,
                    intent_text=record.intent_text,
                    status="running",
                    created_at=record.created_at,
                ),
                zone_config,
            )

            record = self.repo.update_status(
                eval_id,
                "done",
                verdict=verdict,
            )
        except Exception as e:
            record = self.repo.update_status(eval_id, "error", str(e))

        return record

    def to_out(self, record: EvaluationRecord) -> EvaluationOut:
        return EvaluationOut(
            id=record.id,
            activity_id=record.activity_id,
            intent_type=record.intent_type,
            intent_text=record.intent_text,
            verdict=record.verdict.verdict if record.verdict else "pending",
            verdict_json=None,  # preencher se houver
            model=record.model,
            prompt_version=record.prompt_version,
            tokens_in=record.tokens_in,
            tokens_out=record.tokens_out,
            status=record.status,
            error=record.error,
            created_at=record.created_at,
        )