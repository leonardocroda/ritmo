"""Schemas Pydantic para API de domínio Evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ExecutionVsIntentOut(BaseModel):
    pct_zona_alvo: Optional[float]
    principais_desvios: list[str]


class VerdictJsonOut(BaseModel):
    veredito: str
    headline: str
    execucao_vs_intencao: ExecutionVsIntentOut
    o_que_funcionou: list[str]
    corrigir_prox_vez: list[str]
    contexto_relevante: list[str]
    confianca: str


class VerdictOut(BaseModel):
    veredito: str
    headline: str
    execucao_vs_intencao: ExecutionVsIntentOut
    o_que_funcionou: list[str]
    corrigir_prox_vez: list[str]
    contexto_relevante: list[str]
    confianca: str


class EvaluationOut(BaseModel):
    id: int
    activity_id: int
    intent_type: str
    intent_text: Optional[str]
    verdict: str
    verdict_json: Optional[VerdictJsonOut]
    model: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    status: str
    error: Optional[str]
    created_at: datetime


class EvaluateIn(BaseModel):
    intent_type: str
    intent_text: Optional[str] = None