"""Cliente NIM — todos os caminhos via httpx.MockTransport (EVAL-03/13).

NENHUM teste aqui toca a NIM real (Success Criteria do spec): o
transporte é sempre um MockTransport local. Valores e corpo pinados
vêm do design (temperature 0.2, max_tokens 2000, Bearer, URL).
"""

import json

import httpx
import pytest

from app.core.config import Settings
from app.evaluation.nim import (
    MAX_TOKENS,
    TEMPERATURE,
    NimError,
    NimInvalidJSON,
    NimTimeout,
    chat_completion,
)

VERDICT = {
    "veredito": "on_target",
    "headline": "Bloco de limiar bem executado",
    "execucao_vs_intencao": {"pct_zona_alvo": 92.0, "principais_desvios": []},
    "o_que_funcionou": ["pacing estável"],
    "corrigir_prox_vez": [],
    "contexto_relevante": [],
    "confianca": "alta",
}


def _envelope(content: str, *, usage: dict | None = None) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": usage,
    }


@pytest.fixture(autouse=True)
def _clean_nim_env(monkeypatch):
    for var in ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL", "NVIDIA_TIMEOUT_S"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")


@pytest.fixture()
def settings() -> Settings:
    return Settings(_env_file=None)


def test_200_json_limpo_devolve_veredito_e_usage(settings) -> None:
    """EVAL-03: 200 com JSON limpo → (veredito, usage do payload)."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json=_envelope(json.dumps(VERDICT), usage={"prompt_tokens": 1234, "completion_tokens": 56}),
        )
    )
    verdict, usage = chat_completion("system", "user", settings, transport=transport)
    assert verdict == VERDICT
    assert usage == {"prompt_tokens": 1234, "completion_tokens": 56}


def test_json_cercado_parseia_igual(settings) -> None:
    """EVAL-03: conteúdo em cerca ```json é aceito (strip antes do parse)."""
    fenced = f"```json\n{json.dumps(VERDICT)}\n```"
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_envelope(fenced))
    )
    verdict, _usage = chat_completion("system", "user", settings, transport=transport)
    assert verdict == VERDICT


def test_usage_ausente_devolve_zeros(settings) -> None:
    """Edge do spec: sem `usage`, tokens 0 (custo desconhecido, avaliação persiste)."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_envelope(json.dumps(VERDICT)))
    )
    _verdict, usage = chat_completion("system", "user", settings, transport=transport)
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0}


def test_content_nulo_levanta_nim_invalid_json(settings) -> None:
    """UAT 18/10: raciocínio esgota max_tokens e a NIM devolve content
    null (finish_reason length) → NimInvalidJSON com o finish_reason na
    mensagem — 502 honesto no lugar de crash 500."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": None}, "finish_reason": "length"}]},
        )
    )
    with pytest.raises(NimInvalidJSON) as exc_info:
        chat_completion("system", "user", settings, transport=transport)
    assert "finish_reason=length" in str(exc_info.value)


def test_content_vazio_levanta_nim_invalid_json(settings) -> None:
    """String vazia de conteúdo também é contrato quebrado (sem crash)."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_envelope("   "))
    )
    with pytest.raises(NimInvalidJSON):
        chat_completion("system", "user", settings, transport=transport)


def test_http_500_levanta_nim_error(settings) -> None:
    """EVAL-13: HTTP != 200 → NimError (o router mapeia 502)."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, text="upstream exploded")
    )
    with pytest.raises(NimError) as exc_info:
        chat_completion("system", "user", settings, transport=transport)
    assert "500" in str(exc_info.value)
    assert not isinstance(exc_info.value, NimTimeout)


def test_timeout_levanta_nim_timeout(settings) -> None:
    """EVAL-13: timeout do httpx → NimTimeout (o router mapeia 504)."""

    def _timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    transport = httpx.MockTransport(_timeout)
    with pytest.raises(NimTimeout):
        chat_completion("system", "user", settings, transport=transport)


def test_corpo_nao_json_levanta_nim_invalid_json(settings) -> None:
    """EVAL-14: conteúdo sem JSON válido → NimInvalidJSON, nunca veredito inventado."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_envelope("acho que foi um bom treino"))
    )
    with pytest.raises(NimInvalidJSON):
        chat_completion("system", "user", settings, transport=transport)


def test_envelope_malformado_levanta_nim_invalid_json(settings) -> None:
    """EVAL-14: envelope sem choices/message também é ilegível."""
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"error": "shape"}))
    with pytest.raises(NimInvalidJSON):
        chat_completion("system", "user", settings, transport=transport)


def test_veredito_nao_objeto_rejeitado(settings) -> None:
    """EVAL-14: JSON válido mas não-objeto (lista/número) não é veredito."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=_envelope("[1, 2, 3]"))
    )
    with pytest.raises(NimInvalidJSON):
        chat_completion("system", "user", settings, transport=transport)


def test_requisicao_tem_corpo_do_design(settings) -> None:
    """EVAL-03: Bearer, URL NIM, model do settings, temperature 0.2 e
    max_tokens 2000 — o contrato da chamada pinado."""
    seen: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json=_envelope(json.dumps(VERDICT)))

    transport = httpx.MockTransport(_capture)
    chat_completion("system prompt", "payload do usuário", settings, transport=transport)

    request = seen["request"]
    assert str(request.url) == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"

    body = json.loads(request.content.decode("utf-8"))
    assert body["model"] == "z-ai/glm-5.3"
    assert body["temperature"] == TEMPERATURE == 0.2
    assert body["max_tokens"] == MAX_TOKENS == 16000
    assert body["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "payload do usuário"},
    ]
