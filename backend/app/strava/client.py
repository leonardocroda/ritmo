"""Cliente Strava (httpx) para backfill one-shot — sem token persistido.

Backoff exponencial (2, 4, 8 s) em 429/5xx com 3 tentativas.
Seam `http` injetável para testes (httpx MockTransport).
"""

import time
from typing import Any

import httpx

from app.core.config import get_settings


class StravaClientError(Exception):
    """Erro de domínio do cliente Strava."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"


def _get_client_id_secret() -> tuple[str, str]:
    settings = get_settings()
    client_id = settings.strava_client_id
    client_secret = settings.strava_client_secret
    if not client_id or not client_secret:
        raise StravaClientError("STRAVA_CLIENT_ID e STRAVA_CLIENT_SECRET não configurados")
    return client_id, client_secret


def _make_client(http: httpx.Client | None = None) -> httpx.Client:
    """Cria ou reusa client httpx com timeout razoável."""
    if http is not None:
        return http
    return httpx.Client(timeout=30.0)


def _request_with_backoff(
    http: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    data: dict | None = None,
    max_retries: int = 3,
) -> httpx.Response:
    """Executa request com backoff exponencial (2, 4, 8) em 429/5xx."""
    backoff_s = [2, 4, 8]
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = http.request(method, url, headers=headers, params=params, data=data)
            if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                if attempt < max_retries:
                    time.sleep(backoff_s[attempt])
                    continue
                raise StravaClientError(
                    f"Strava API error {resp.status_code} após {max_retries + 1} tentativas: {resp.text}",
                    status_code=resp.status_code,
                )
            return resp
        except httpx.RequestError as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(backoff_s[attempt])
                continue
            raise StravaClientError(f"Erro de rede ao chamar Strava: {exc}") from exc

    # Nunca chega aqui, mas por segurança
    raise StravaClientError(f"Falha após {max_retries + 1} tentativas: {last_exc}") from last_exc


def exchange_code(code: str, http: httpx.Client | None = None) -> str:
    """Troca authorization code por access token (OAuth).

    POST https://www.strava.com/oauth/token
    """
    settings = get_settings()
    client_id = settings.strava_client_id
    client_secret = settings.strava_client_secret
    redirect_uri = settings.strava_redirect_uri
    print(f"[DEBUG] exchange_code: client_id={client_id}, redirect_uri={redirect_uri}")
    http = _make_client(http)

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    resp = _request_with_backoff(http, "POST", STRAVA_TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise StravaClientError(f"Falha ao trocar code por token: {resp.text}", status_code=resp.status_code)
    token_data = resp.json()
    return token_data["access_token"]


def fetch_athlete_shoes(token: str, http: httpx.Client | None = None) -> list[dict]:
    """Busca gear (tênis) do atleta autenticado.

    GET https://www.strava.com/api/v3/athlete
    Retorna lista de gear com id, name, brand_name, model_name, distance (em metros).
    """
    http = _make_client(http)
    headers = {"Authorization": f"Bearer {token}"}
    resp = _request_with_backoff(http, "GET", STRAVA_ATHLETE_URL, headers=headers)
    if resp.status_code != 200:
        raise StravaClientError(f"Falha ao buscar atleta: {resp.text}", status_code=resp.status_code)
    athlete = resp.json()
    # O campo 'shoes' vem no atleta; pode estar ausente ou vazio
    return athlete.get("shoes", [])


def fetch_run_activities(
    token: str,
    http: httpx.Client | None = None,
    *,
    per_page: int = 200,
    after: int | None = None,
    before: int | None = None,
) -> list[dict]:
    """Busca atividades de corrida do atleta (paginado, filtra type == "Run").

    GET https://www.strava.com/api/v3/athlete/activities
    Parâmetros: per_page (max 200), page, after (epoch), before (epoch).
    Para em página vazia. Retorna lista com: id, external_id, gear_id,
    distance, moving_time, start_date, type.
    """
    http = _make_client(http)
    headers = {"Authorization": f"Bearer {token}"}
    all_runs: list[dict] = []
    page = 1

    while True:
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before

        resp = _request_with_backoff(http, "GET", STRAVA_ACTIVITIES_URL, headers=headers, params=params)
        if resp.status_code != 200:
            raise StravaClientError(f"Falha ao buscar atividades: {resp.text}", status_code=resp.status_code)

        activities = resp.json()
        if not activities:
            break

        # Filtra apenas corridas
        runs = [a for a in activities if a.get("type") == "Run"]
        all_runs.extend(runs)

        # Se a página veio com menos que per_page, acabou
        if len(activities) < per_page:
            break

        page += 1

    # Normaliza campos relevantes
    normalized = []
    for run in all_runs:
        normalized.append(
            {
                "id": run["id"],
                "external_id": run.get("external_id"),
                "gear_id": run.get("gear_id"),
                "distance": run.get("distance", 0.0),  # metros
                "moving_time": run.get("moving_time", 0),  # segundos
                "start_date": run.get("start_date"),  # ISO string GMT
            }
        )
    return normalized