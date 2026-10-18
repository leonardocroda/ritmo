"""Contratos Pydantic do domínio evaluation.

Módulo próprio (não inline no router) porque dois routers consomem os
modelos: o do POST /evaluate (evaluation) e o do detalhe de activities
(lista de avaliações) — sem ciclo de imports.

- EvaluateIn (EVAL-01/11): os 7 tipos de intenção — chaves 1:1 com
  `inferred_type` (ASCII; acento é camada de exibição) — e texto livre
  opcional de até 500 caracteres. Fora do contrato → 422 automático.
- VerdictJson (EVAL-04, §9.2): o JSON que a NIM devolve. Extras são
  ignorados; obrigatórios ausentes rejeitam (Decisão E — veredito
  nunca é inventado).
- EvaluationOut (EVAL-04/06): espelha exatamente a linha persistida.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Os 7 tipos de intenção — mesmas chaves do infer.py (pré-preenchimento 1:1)
IntentType = Literal[
    "prova",
    "intervalado",
    "limiar",
    "tempo",
    "progressivo",
    "longao",
    "facil",
]

# Vereditos do plano §9.2
Verdict = Literal[
    "on_target",
    "too_hard",
    "too_easy",
    "context_explained",
    "fatigue_signal",
]

MAX_INTENT_TEXT = 500


class EvaluateIn(BaseModel):
    """Corpo do POST /api/activities/{id}/evaluate (EVAL-01/11)."""

    intent_type: IntentType
    intent_text: str | None = Field(default=None, max_length=MAX_INTENT_TEXT)


class ExecucaoVsIntencao(BaseModel):
    """Bloco de execução vs intenção do veredito (§9.2).

    `pct_zona_alvo` null quando a intenção não tem zona alvo única
    (progressivo, prova) ou quando não há voltas classificadas —
    nullable, mas a CHAVE é obrigatória (Decisão E: ausente rejeita).
    """

    pct_zona_alvo: float | None
    principais_desvios: list[str]


class VerdictJson(BaseModel):
    """JSON de veredito devolvido pela NIM (§9.2) — validado antes de persistir.

    Extras ignorados (Decisão E): o modelo pode acrescentar campos sem
    quebrar a avaliação; obrigatório ausente rejeita — nunca inventamos
    o que o LLM não disse. Todas as chaves do §9.2 são obrigatórias
    (lista pode vir vazia; a chave tem que existir).
    """

    model_config = ConfigDict(extra="ignore")

    veredito: Verdict
    headline: str
    execucao_vs_intencao: ExecucaoVsIntencao
    o_que_funcionou: list[str]
    corrigir_prox_vez: list[str]
    contexto_relevante: list[str]
    confianca: Literal["alta", "média", "baixa"]


class EvaluationOut(BaseModel):
    """Avaliação persistida — resposta do POST e item da lista no detalhe."""

    id: int
    activity_id: int
    intent_type: str
    intent_text: str | None
    verdict: str
    verdict_json: dict
    model: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    created_at: datetime
