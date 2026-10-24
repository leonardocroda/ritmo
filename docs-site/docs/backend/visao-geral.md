# Backend — Visão Geral

FastAPI + SQLAlchemy 2 + Postgres (psycopg3), Python ≥ 3.12, dependências
gerenciadas por `uv`. O backend é o único ponto de escrita do sistema:
sync do Garmin, avaliações de IA e as telas de perfil gravam por aqui;
os painéis só leem.

| Peça | Tecnologia |
|---|---|
| API | FastAPI (routers por domínio, pydantic v2) |
| ORM | SQLAlchemy 2.x declarativo (`app/db/models.py`) |
| Driver | psycopg 3 (`postgresql+psycopg://`) |
| Garmin | `garminconnect==0.3.2` (isolada em `GarminGateway`) |
| IA | `httpx` → NVIDIA NIM (OpenAI-compatível) |
| Senhas | `argon2-cffi` (argon2id) |
| Tokens Garmin | `cryptography` (Fernet) |
| Testes | pytest + TestClient contra Postgres real (`ritmo_test`) |

## Estrutura de pastas

```
backend/
├── app/
│   ├── main.py            # entrypoint: lifespan, CORS, includes, /api/health
│   ├── core/
│   │   ├── config.py      # Settings pydantic — 100% env vars
│   │   └── tz.py          # resolvedor de fuso (APP_TIMEZONE, fallback + warning)
│   ├── db/
│   │   ├── base.py        # Base declarativa
│   │   ├── engine.py      # engine, get_db, init_db (create_all + emendas + seeds)
│   │   └── models.py      # as 23 tabelas ORM
│   ├── auth/              # registro por convite, login, sessão stateful
│   ├── garmin/            # sync (router/service/client/upserts/pmc), cofre, CLIs
│   ├── activities/        # lista + detalhe, inferência de tipo, consistência
│   ├── evaluation/        # avaliação IA (payload, prompt, nim, veredito)
│   ├── health/            # painel Saúde (router/service/calc)
│   ├── home/              # painel Home (veredito V1–V6, recomendações)
│   ├── potential/         # painel Performance (Riegel, timeline, decay, PMC)
│   ├── profile/           # zonas de FC (effective-dated) + conexão Garmin
│   └── vdot/              # equações de Daniels, zonas, calibração (CLI)
├── data/
│   └── vdot_zones.json    # calibração vigente (VDOT 50.2, 10K 41:15)
└── tests/                 # 50 arquivos, 612 testes, Postgres real do compose
```

Cada domínio é um **slice vertical**: `router.py` (HTTP) → `service.py`
(regras + queries) → `calc.py` ou módulos puros (determinísticos, sem I/O).
A lib do Garmin e a NIM só são importadas dentro de `garmin/client.py` e
`evaluation/nim.py`, respectivamente — nenhum outro módulo fala com fora.

## Convenções

- **`user_id` em toda tabela** (AD-001) com default `DEFAULT_USER_ID = 1`
  — toda query de leitura/gravação filtra pelo usuário da sessão.
- **`DateTime` naive-UTC** (`_utcnow`); datas de saúde são `Date` no
  `calendarDate` do Garmin; exibição converte para `APP_TIMEZONE`.
- **422 em PT-BR apontando o campo** — validação pydantic com mensagens
  loc em todos os schemas de entrada.
- **Exceções de domínio** nos services (ex.: `InviteRequiredError`) →
  handlers HTTP nos routers; o service nunca conhece status code.
- **`get_settings()` com cache** — config lida uma vez por processo.

## Lifespan (boot)

`app/main.py` — a ordem importa:

1. **fail-fast**: `TOKEN_ENCRYPTION_KEY` ausente/inválida = boot morre
   (nenhuma requisição é atendida sem o cofre funcionando — GTDB-14).
2. `init_db()` — `create_all` + emendas idempotentes (AD-19) + seeds +
   `setval` da sequence.
3. `recover_stale_jobs()` — syncs órfãos de restart viram `error`
   "interrompido por restart".
4. `recover_stale_evaluations()` — idem para avaliações pendentes.

## Mapa de autenticação

O `main.py` monta o mapa: o `auth_router` entra público; os outros 7
routers entram com `dependencies=[Depends(require_session)]` — **401 sem
cookie válido**. Exatamente 3 coisas ficam públicas:

- `GET /api/health` (liveness — não toca o banco de propósito)
- `POST /api/auth/register` e `POST /api/auth/login`

CORS com `allow_credentials=True` e origens explícitas de `CORS_ORIGINS`
(cookies não aceitam `*`) — no fluxo normal (same-origin, AD-020) o CORS
é só sobra de segurança para acesso browser direto à API.

Próximo: a [referência completa da API](api.md).
