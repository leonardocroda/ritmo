"""Cliente NVIDIA NIM — o único ponto de I/O externo da avaliação (EVAL-03/13).

Uma chamada por avaliação, httpx direto (sem SDK): Bearer + corpo
OpenAI-compatível em `{NVIDIA_BASE_URL}/chat/completions`. O veredito
vem em `choices[0].message.content` — cercas de código markdown são
aceitas (strip antes do parse), prosa fora do JSON não (o prompt exige
JSON exato; resposta ilegível é erro honesto, nunca veredito inventado).

`transport` é seam de teste: a suite injeta `httpx.MockTransport` e
nenhum teste toca a NIM real (Success Criteria do spec).
"""

import json
import re

import httpx

from app.core.config import Settings

# Veredito estruturado: estabilidade acima de criatividade; teto de
# custo de saída (design — o JSON §9.2 é pequeno)
TEMPERATURE = 0.2
MAX_TOKENS = 2000


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
    with httpx.Client(timeout=settings.nvidia_timeout_s, transport=transport) as client:
        try:
            response = client.post(
                f"{settings.nvidia_base_url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
            )
        except httpx.TimeoutException as exc:
            raise NimTimeout(f"NIM não respondeu em {settings.nvidia_timeout_s}s: {exc}") from exc

    if response.status_code != 200:
        raise NimError(f"NIM HTTP {response.status_code}: {response.text[:200]}")

    try:
        envelope = response.json()
        content = envelope["choices"][0]["message"]["content"]
        verdict = json.loads(_extract_json(content))
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise NimInvalidJSON(f"resposta da NIM fora do contrato: {exc}") from exc
    if not isinstance(verdict, dict):
        raise NimInvalidJSON("veredito não é um objeto JSON")

    usage = envelope.get("usage") or {}
    return verdict, {
        "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
        "completion_tokens": usage.get("completion_tokens", 0) or 0,
    }
