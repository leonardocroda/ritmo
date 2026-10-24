# Backend — Configuração (env vars)

**Nada hardcoded** (regra travada): toda a config chega por env var, lida
uma vez por `Settings` pydantic em `app/core/config.py` com cache
(`get_settings()`), `extra="ignore"` e `.env` utf-8. O
`backend/.env.example` é o catálogo comentado.

## Banco e identidade

| Env | Default | Efeito |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://ritmo:ritmo@localhost:5432/ritmo` | Postgres via psycopg3; testes forçam o banco `ritmo_test` no conftest |
| `APP_NAME` / `APP_ENV` | `Ritmo` / `dev` | identidade/liveness |
| `TZ` (compose) / `APP_TIMEZONE` | `America/Sao_Paulo` | fuso de exibição (deitar/acordar, janelas); inválida → fallback + warning (`core/tz.py`) |
| `CORS_ORIGINS` | `http://localhost:3000` | CSV explícito — com cookies, `*` é rejeitado; só p/ acesso browser DIRETO à API (o fluxo normal é same-origin) |

## Segredos (fail-fast)

| Env | Default | Efeito |
|---|---|---|
| `TOKEN_ENCRYPTION_KEY` | *(vazio)* | chave Fernet dos tokens Garmin — **ausente/inválida = o backend não sobe** (GTDB-14). Gerar: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `NVIDIA_API_KEY` | *(vazio)* | chave NIM — vazio = `POST evaluate` responde `503` |
| `INVITE_CODE` | *(vazio)* | **vazio = registro desabilitado** (`403`); preencher abre `/registrar` |

## Avaliação IA

| Env | Default | Efeito |
|---|---|---|
| `NVIDIA_MODEL` | `z-ai/glm-5.3` | flash: `z-ai/glm-5.3-flash` (rápido p/ dia a dia) |
| `NVIDIA_TIMEOUT_S` | `420` | glm-5.3 raciocina além de 120s |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | endpoint NIM |
| `LTHR_BPM` | `177` | fallback do payload quando o perfil não tem `fclthr` (a métrica do usuário vence, AD-021) |

## Sync (guard rails)

| Env | Default | Efeito |
|---|---|---|
| `SYNC_REPULL_DAYS` | `3` | re-pull incremental (Garmin reprocessa 72h) |
| `SYNC_BACKFILL_ACTIVITIES_DAYS` | `180` | janela do primeiro sync de atividades |
| `SYNC_BACKFILL_HEALTH_DAYS` | `120` | janela de saúde (60 exibição + 59 lookback HRV) |
| `SYNC_CALL_INTERVAL_S` | `1.0` | pausa mínima entre chamadas sequenciais |
| `SYNC_MAX_CALLS` | `1500` | teto de chamadas por job |
| `SYNC_RETRY_MAX` | `3` | retries com backoff 2/4/8s |

## Sessão

| Env | Default | Efeito |
|---|---|---|
| `SESSION_TTL_DAYS` | `30` | validade da sessão |
| `SESSION_RENEW_THRESHOLD_DAYS` | `15` | gatilho do sliding renewal |
| `SESSION_COOKIE_NAME` | `ritmo_session` | nome do cookie |
| `SESSION_COOKIE_SECURE` | `false` | `true` em produção (HTTPS) — `false` na LAN |

## Dados

| Env | Default | Efeito |
|---|---|---|
| `VDOT_ZONES_PATH` | `data/vdot_zones.json` | fonte de verdade das zonas VDOT/pace e do VDOT calibrado |

## Onde cada valor vive por ambiente

| | Local (compose) | Produção (Render) |
|---|---|---|
| Origem | `backend/.env` (opcional) + `environment:` do compose | painel do Blueprint (`sync: false` = segredo pedido no dashboard) |
| `DATABASE_URL` | `postgresql+psycopg://ritmo:ritmo@postgres:5432/ritmo` | string **pooled** do Neon (`-pooler`, TLS) |
| `SESSION_COOKIE_SECURE` | `false` | `true` |
| `CORS_ORIGINS` | `http://localhost:3000` | `https://ritmo.vercel.app` |

O compose deixa o `.env` opcional: sem ele o stack sobe igual (as vars
do `environment:` vencem conflitos).
