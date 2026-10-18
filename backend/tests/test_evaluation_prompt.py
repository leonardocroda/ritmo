"""System prompt v1 — marcadores contratuais (EVAL-03).

A qualidade do texto é julgada no UAT (spot-check do success criteria);
estes testes prendem o CONTRATO: os 5 vereditos, as chaves §9.2, a proibição
de recalcular, a hierarquia pace>FC, a regra do calor e o versionamento
(AD-003 — toda avaliação rastreia o prompt que a produziu).
"""

from app.evaluation.prompt import PROMPT_VERSION, SYSTEM_PROMPT_V1

VERDICTS = (
    "on_target",
    "too_hard",
    "too_easy",
    "context_explained",
    "fatigue_signal",
)

JSON_KEYS = (
    "veredito",
    "headline",
    "execucao_vs_intencao",
    "pct_zona_alvo",
    "principais_desvios",
    "o_que_funcionou",
    "corrigir_prox_vez",
    "contexto_relevante",
    "confianca",
)


def test_prompt_version_e_v1() -> None:
    """EVAL-03/06: versão casada com o prompt — auditoria por avaliação (AD-003)."""
    assert PROMPT_VERSION == "v1"
    assert SYSTEM_PROMPT_V1  # constante não-vazia


def test_prompt_contem_os_cinco_vereditos() -> None:
    """EVAL-04: o prompt ensina exatamente os 5 vereditos do §9.2."""
    for verdict in VERDICTS:
        assert verdict in SYSTEM_PROMPT_V1


def test_prompt_contem_as_chaves_do_json_92() -> None:
    """EVAL-03: o formato de saída mostra todas as chaves do JSON §9.2."""
    for key in JSON_KEYS:
        assert key in SYSTEM_PROMPT_V1


def test_prompt_proibe_recalcular_e_exige_numeros_do_payload() -> None:
    """EVAL-03/AD-003: o LLM usa exclusivamente os números do payload."""
    assert "exclusivamente os números do payload" in SYSTEM_PROMPT_V1
    assert "nunca recalcular" in SYSTEM_PROMPT_V1
    assert "nunca inventar" in SYSTEM_PROMPT_V1


def test_prompt_define_hierarquia_pace_decide_fc_corrobora() -> None:
    """EVAL-03/AD-005: pace/zona decidem; FC corrobora e nunca decide sozinha."""
    assert "Pace e zona decidem" in SYSTEM_PROMPT_V1
    assert "nunca decide sozinha" in SYSTEM_PROMPT_V1


def test_prompt_traz_regra_do_calor_e_lthr() -> None:
    """EVAL-03: calor muda a régua do fácil; LTHR é a referência de FC."""
    assert "25°C" in SYSTEM_PROMPT_V1
    assert "LTHR" in SYSTEM_PROMPT_V1


def test_prompt_e_pt_br() -> None:
    """EVAL-03: resposta em PT-BR — o prompt instrui no idioma do card."""
    assert "português do Brasil" in SYSTEM_PROMPT_V1
    assert "PT-BR" in SYSTEM_PROMPT_V1


def test_prompt_cobre_payload_sem_voltas() -> None:
    """EVAL-16: sem voltas o julgamento é pelos agregados, com confiança baixa."""
    assert "não tem voltas" in SYSTEM_PROMPT_V1
    assert '"baixa"' in SYSTEM_PROMPT_V1
