"""Schemas do domínio evaluation — contratos validados isolados (EVAL-04/11).

Literais e enums afirmados vêm do spec (§9.2 do plano + spec
ai-evaluation), nunca de constantes compartilhadas com a implementação
(lição L-001).
"""

import pytest
from pydantic import ValidationError

from app.evaluation.schemas import EvaluateIn, EvaluationOut, VerdictJson

# JSON §9.2 completo e válido — base dos testes de aceitação/rejeição
VERDICT_OK = {
    "veredito": "on_target",
    "headline": "Execução quase perfeita no bloco de limiar",
    "execucao_vs_intencao": {
        "pct_zona_alvo": 92.0,
        "principais_desvios": ["km 6 em repetition"],
    },
    "o_que_funcionou": ["pacing estável", "aquecimento na zona certa"],
    "corrigir_prox_vez": ["gel aos 40min"],
    "contexto_relevante": ["umidade 100% explica metade do drift"],
    "confianca": "alta",
}


def test_verdict_json_valido_completo() -> None:
    """EVAL-04: o JSON §9.2 completo valida e preserva os valores."""
    verdict = VerdictJson.model_validate(VERDICT_OK)
    assert verdict.veredito == "on_target"
    assert verdict.headline == "Execução quase perfeita no bloco de limiar"
    assert verdict.execucao_vs_intencao.pct_zona_alvo == 92.0
    assert verdict.execucao_vs_intencao.principais_desvios == ["km 6 em repetition"]
    assert verdict.o_que_funcionou == ["pacing estável", "aquecimento na zona certa"]
    assert verdict.corrigir_prox_vez == ["gel aos 40min"]
    assert verdict.contexto_relevante == ["umidade 100% explica metade do drift"]
    assert verdict.confianca == "alta"


@pytest.mark.parametrize("veredito", list(VerdictJson.model_fields["veredito"].annotation.__args__))  # type: ignore[attr-defined]
def test_verdict_json_aceita_os_cinco_vereditos(veredito: str) -> None:
    """EVAL-04: enum `veredito` tem exatamente os 5 valores do §9.2."""
    data = {**VERDICT_OK, "veredito": veredito}
    assert VerdictJson.model_validate(data).veredito == veredito


def test_verdict_json_rejeita_veredito_fora_do_enum() -> None:
    """EVAL-04: veredito fora dos 5 valores rejeita (nada de veredito inventado)."""
    with pytest.raises(ValidationError):
        VerdictJson.model_validate({**VERDICT_OK, "veredito": "excellent"})


def test_verdict_json_rejeita_confianca_fora_do_enum() -> None:
    """EVAL-04: confianca aceita alta|média|baixa (literal do §9.2) e nada mais."""
    with pytest.raises(ValidationError):
        VerdictJson.model_validate({**VERDICT_OK, "confianca": "media"})
    with pytest.raises(ValidationError):
        VerdictJson.model_validate({**VERDICT_OK, "confianca": "certa"})


def test_verdict_json_rejeita_obrigatorio_ausente() -> None:
    """EVAL-04: obrigatório ausente rejeita — Decisão E (extras ok, faltos não)."""
    for missing in (
        "veredito",
        "headline",
        "execucao_vs_intencao",
        "o_que_funcionou",
        "corrigir_prox_vez",
        "contexto_relevante",
        "confianca",
    ):
        data = {k: v for k, v in VERDICT_OK.items() if k != missing}
        with pytest.raises(ValidationError):
            VerdictJson.model_validate(data)


def test_verdict_json_ignora_campos_extras() -> None:
    """EVAL-04/Decisão E: campos além do schema são ignorados, não rejeitados."""
    verdict = VerdictJson.model_validate(
        {**VERDICT_OK, "raciocinio": "achei o treino bom", "nota": 10}
    )
    assert verdict.veredito == "on_target"
    assert not hasattr(verdict, "raciocinio")


def test_verdict_json_pct_zona_alvo_nulo() -> None:
    """EVAL-02: pct_zona_alvo null é válido (progressivo/prova sem zona alvo)."""
    verdict = VerdictJson.model_validate(
        {
            **VERDICT_OK,
            "execucao_vs_intencao": {"pct_zona_alvo": None, "principais_desvios": []},
        }
    )
    assert verdict.execucao_vs_intencao.pct_zona_alvo is None


def test_evaluate_in_aceita_sete_tipos() -> None:
    """EVAL-01/11: os 7 tipos de intenção (chaves 1:1 com inferred_type)."""
    for intent_type in (
        "prova",
        "intervalado",
        "limiar",
        "tempo",
        "progressivo",
        "longao",
        "facil",
    ):
        request = EvaluateIn(intent_type=intent_type)
        assert request.intent_type == intent_type
        assert request.intent_text is None


def test_evaluate_in_aceita_texto_livre_ate_500() -> None:
    """EVAL-01: texto livre opcional de até 500 caracteres."""
    request = EvaluateIn(intent_type="facil", intent_text="era pra ser 30min a 4:15")
    assert request.intent_text == "era pra ser 30min a 4:15"
    request_limite = EvaluateIn(intent_type="facil", intent_text="a" * 500)
    assert len(request_limite.intent_text) == 500


def test_evaluate_in_rejeita_tipo_fora_dos_sete() -> None:
    """EVAL-11: intent_type fora dos 7 tipos → 422 (pydantic rejeita na validação)."""
    with pytest.raises(ValidationError):
        EvaluateIn(intent_type="fácil")  # acento não faz parte do enum ASCII
    with pytest.raises(ValidationError):
        EvaluateIn(intent_type="recovery")


def test_evaluate_in_rejeita_texto_acima_de_500() -> None:
    """EVAL-11: intent_text com 501 caracteres rejeita (limite do spec)."""
    with pytest.raises(ValidationError):
        EvaluateIn(intent_type="facil", intent_text="a" * 501)


def test_evaluation_out_espelha_campos_persistidos() -> None:
    """EVAL-04/06: saída espelha exatamente o que a avaliação grava (AD-003)
    + status/error da emenda job (EVAL-21/25)."""
    out = EvaluationOut(
        id=1,
        activity_id=10,
        intent_type="facil",
        intent_text=None,
        verdict="on_target",
        verdict_json=VERDICT_OK,
        model="z-ai/glm-5.3",
        prompt_version="v1",
        tokens_in=1234,
        tokens_out=56,
        status="done",
        error=None,
        created_at="2026-10-18T08:00:00Z",
    )
    assert out.model == "z-ai/glm-5.3"
    assert out.prompt_version == "v1"
    assert out.tokens_in == 1234
    assert out.tokens_out == 56
    assert out.verdict_json["veredito"] == "on_target"
    assert out.verdict == "on_target"
    assert out.status == "done"
    assert out.error is None


def test_evaluation_out_pending_sem_veredito() -> None:
    """EVAL-21: o registro nasce pending — sem veredito ainda (JSON null),
    com o erro nullable; é o que o POST devolve no 201."""
    out = EvaluationOut(
        id=2,
        activity_id=10,
        intent_type="facil",
        intent_text="era pra ser 30min a 4:15",
        verdict="",
        verdict_json=None,
        model="z-ai/glm-5.3",
        prompt_version="v1",
        tokens_in=0,
        tokens_out=0,
        status="pending",
        error=None,
        created_at="2026-10-18T08:01:00Z",
    )
    assert out.status == "pending"
    assert out.verdict_json is None
    assert out.intent_text == "era pra ser 30min a 4:15"
