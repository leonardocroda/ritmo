"""Validação e sanitização do veredito (EVAL-04/14).

`validate_verdict` transforma o erro de schema do pydantic em `ValueError`
— um único tipo de erro de contrato para o router mapear 502. A
sanitização do eco numérico fecha a brecha do AD-003: o `pct_zona_alvo`
exibido no card é SEMPRE o calculado em Python, nunca o eco do LLM.
"""

from app.evaluation.schemas import VerdictJson


def validate_verdict(data: dict) -> VerdictJson:
    """Valida o JSON da NIM contra o schema §9.2.

    Levanta ValueError quando o veredito está fora do contrato (enum,
    obrigatório ausente, tipos) — extras são ignorados (Decisão E).
    """
    try:
        return VerdictJson.model_validate(data)
    except Exception as exc:
        raise ValueError(f"veredito fora do schema §9.2: {exc}") from exc


def sanitize_echo(verdict: VerdictJson, python_pct: float | None) -> dict:
    """dict persistível do veredito com o `pct_zona_alvo` do Python.

    O LLM é instruído a ecoar o número do payload, mas o eco não é
    confiável: sobrescrevemos com o valor determinístico (ou None quando
    a intenção não tem zona alvo). AD-003 até no eco.
    """
    dump = verdict.model_dump()
    dump["execucao_vs_intencao"]["pct_zona_alvo"] = python_pct
    return dump
