"""Cliente NVIDIA NIM — o único ponto de I/O externo da avaliação (EVAL-03/13).

Uma avaliação por aqui: Bearer + corpo OpenAI-compatível enviado a
`{NVIDIA_BASE_URL}/chat/completions` (httpx direto, sem SDK), com até
RETRY_ATTEMPTS retransmissões em HTTP 5xx (transiente da NIM, UAT 25/10).
O veredito vem em `choices[0].message.content` — cercas de código markdown
são aceitas (strip antes do parse), prosa fora do JSON não (o prompt exige
JSON exato; resposta ilegível é erro honesto, nunca veredito inventado).

`transport` é seam de teste: a suite injeta `httpx.MockTransport` e
nenhum teste toca a NIM real (Success Criteria do spec).
"""

import json
import re
import time

import httpx

from app.core.config import Settings

# Veredito estruturado: estabilidade acima de criatividade. O teto de
# saída precisa cobrir o RACIOCÍNIO dos modelos thinking (tokens de
# "pensamento" contam no max_tokens e podem consumir milhares antes do
# JSON §9.2 — UAT 18/10: com 2000 a resposta vinha content:null,
# finish_reason length); 16000 dá folga sem abrir custo ilimitado. Com
# NVIDIA_THINKING=none a geração real é ~500 tokens (UAT 25/10).
TEMPERATURE = 0.2
MAX_TOKENS = 16000

# NIM free tier sob carga derruba requests com 5xx instantâneo (UAT
# 25/10: 500 em 0,7s no mesmo payload que o retry seguinte atendeu em
# 22s) — retransmitir é barato e destrava a avaliação. Timeout NÃO é
# retransmitido: cada tentativa já espera NVIDIA_TIMEOUT_S inteiros.
RETRY_ATTEMPTS = 3
RETRY_SLEEP_S = 0.5


class NimError(Exception):
    """A NIM devolveu HTTP != 200 (EVAL-13 → 502 no router)."""


class NimTimeout(NimError):
    """A NIM não respondeu até NVIDIA_TIMEOUT_S (EVAL-13 → 504 no router)."""


class NimInvalidJSON(NimError):
    """Resposta ilegível/fora do contrato (EVAL-14 → 502 no router)."""


_FENCE_OPEN = re.compile(r"^```[a-zA-Z0-9_-]*\s*")
_FENCE_CLOSE = re.compile(r"\s*```$")


def _extract_json(content: str) -> str:
    """Remove cercas de código markdown (```json … ```), se houver."""
    text = content.strip()
    if text.startswith("```"):
        text = _FENCE_OPEN.sub("", text)
        text = _FENCE_CLOSE.sub("", text)
    return text.strip()


def chat_completion(
    system: str,
    user: str,
    settings: Settings,
    transport: httpx.BaseTransport | None = None,
) -> tuple[dict, dict]:
    """Uma chamada à NIM → (veredito parseado, usage).

    HTTP 5xx é transiente na NIM (UAT 25/10): até RETRY_ATTEMPTS
    tentativas com pausa curta — a falha volta em <1s, retransmitir é
    barato. Timeout não retenta (uma tentativa já espera o teto inteiro).
    Levanta NimTimeout / NimError / NimInvalidJSON — nada de resposta
    parcial: ou volta o veredito inteiro, ou o router devolve o erro.
    """
    body = {
        "model": settings.nvidia_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    # Raciocínio desligável por env (UAT 25/10): os números do veredito
    # vêm todos calculados do Python — sem thinking a geração cai de
    # ~5k para ~500 tokens e a latência de 95s para ~22s. Vazio (default)
    # não envia o campo: modelo sem suporte não deve 400ar.
    if settings.nvidia_thinking:
        body["chat_template_kwargs"] = {"thinking": settings.nvidia_thinking}

    response: httpx.Response | None = None
    with httpx.Client(timeout=settings.nvidia_timeout_s, transport=transport) as client:
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    json=body,
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                )
            except httpx.TimeoutException as exc:
                raise NimTimeout(f"NIM não respondeu em {settings.nvidia_timeout_s}s: {exc}") from exc
            # 4xx é erro de contrato (chave, modelo, parâmetro) — não
            # insiste. 5xx é nó sobrecarregado: tenta de novo, menos na
            # última tentativa (a mensagem de erro chega ao usuário).
            if response.status_code < 500 or attempt == RETRY_ATTEMPTS:
                break
            time.sleep(RETRY_SLEEP_S)

    assert response is not None  # o loop executa ao menos uma vez
    if response.status_code != 200:
        raise NimError(f"NIM HTTP {response.status_code}: {response.text[:200]}")

    try:
        envelope = response.json()
        message = envelope["choices"][0]["message"]
        content = message["content"]
        # Modelo raciocinador pode esgotar max_tokens no pensamento e
        # devolver content null (UAT 18/10) — erro de contrato com o
        # finish_reason visível, nunca crash 500.
        if not isinstance(content, str) or not content.strip():
            finish_reason = envelope["choices"][0].get("finish_reason")
            raise NimInvalidJSON(
                f"resposta da NIM sem conteúdo (finish_reason={finish_reason})"
            )
        verdict = json.loads(_extract_json(content))
    except NimInvalidJSON:
        raise
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise NimInvalidJSON(f"resposta da NIM fora do contrato: {exc}") from exc
    if not isinstance(verdict, dict):
        raise NimInvalidJSON("veredito não é um objeto JSON")

    usage = envelope.get("usage") or {}
    return verdict, {
        "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
        "completion_tokens": usage.get("completion_tokens", 0) or 0,
    }
