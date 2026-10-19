# Auth Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/auth/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` (§Testes — suite no Postgres do compose, nada em SQLite), `backend/tests/conftest.py` (schema dropado por teste, lifespan re-semeia), `backend/pyproject.toml` (pytest, sem thresholds), `frontend/package.json` (sem test runner — lint/build apenas). Sem thresholds de cobertura configurados → strong defaults aplicados na profundidade.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domínio puro de auth (`auth/security.py`, `auth/rate_limit.py`) | unit | All branches; 1:1 aos ACs (AUTH-08, AUTH-15); edge cases de janela/limite | `backend/tests/test_auth_security.py`, `backend/tests/test_auth_rate_limit.py` | `uv run pytest tests/test_auth_security.py tests/test_auth_rate_limit.py` (workdir `backend/`) |
| Persistência de auth (`db/models.py`, `db/engine.py`) | integration | Modelos + sequência: happy + edge (email NULL múltiplo, id sequencial pós-setval) | `backend/tests/test_auth_models.py` | `uv run pytest tests/test_auth_models.py` (workdir `backend/`, Postgres do compose no ar) |
| API de auth + proteção (`auth/service.py`, `auth/router.py`, `auth/deps.py`, `main.py`) | integration | Rotas em escopo: happy + todo edge case listado + erros (403/409/422/429/401); proteção dos routers existentes; CORS; sliding | `backend/tests/test_auth_service.py`, `backend/tests/test_auth_api.py` | `uv run pytest tests/test_auth_service.py tests/test_auth_api.py` (workdir `backend/`) |
| CLI (`auth/set_password.py`) | unit (seam) | 1:1 aos ACs AUTH-25/26; inputs injetáveis (padrão `garmin/login.py`) | `backend/tests/test_auth_cli.py` | `uv run pytest tests/test_auth_cli.py` (workdir `backend/`) |
| Frontend (`proxy.ts`, `api.ts`, telas, `UserMenu`) | none | - (build gate only; comportamento verificado por UAT 390px — padrão do projeto) | - | build gate only |
| Config/docs (`core/config.py`, `.env.example`, `README.md`) | none | - (build gate only) | - | build gate only |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (a suite falha rápido sem ele — padrão do repo).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após task com testes novos em arquivo(s) de auth | `cd backend && uv run pytest tests/test_auth_security.py tests/test_auth_rate_limit.py tests/test_auth_models.py tests/test_auth_service.py tests/test_auth_api.py tests/test_auth_cli.py` (rode só os arquivos da task) |
| Full | Após task que toca wiring/config/modelos (o suite inteiro deve continuar verde) | `cd backend && uv run pytest` |
| Build | Após task frontend ou docs | `cd frontend && npm run lint && npm run build` |
| Build+Full (final) | Última task da feature | `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação backend (modelos, config, primitivas)

Schema de sessão, fix da sequência, settings de auth e as duas peças puras (segurança, rate limit).

```
T1 → T2
```

### Phase 2: API de auth (service, endpoints, CLI)

O módulo `auth/` completo: service → endpoints + proteção; CLI de bootstrap por último para
que a janela com login impossível nunca exista entre commits. Arestas de dependência
cross-phase apontam para trás (permitido) e estão desenhadas no bloco da task de destino.

```
T1 → T6
T4 → T6
T5 → T6
T6 → T7
T1 → T8
T4 → T8
T2 → T7
T3 → T7
```

### Phase 3: Frontend (wrapper, rotas, telas, menu)

Wrapper de fetch centraliza `credentials` + redirect 401; route groups e proxy; telas por último.

```
T7 → T9
T9 → T10
T11 → T12
T9 → T13
T11 → T13
T9 → T14
T11 → T14
T9 → T15
T11 → T15
```

### Phase 4: Documentação

```
T15 → T16
```

---

## Task Breakdown

### T1: Modelos de auth (User.email/password_hash + UserSession)

**What**: `User` ganha `email` (String(255), unique, nullable, normalizado lowercase no service) e `password_hash` (String(255), nullable); nova classe `UserSession` (`__tablename__="sessions"`): `id`, `user_id` FK CASCADE, `token_hash` String(64) unique index, `expires_at` DateTime index, `created_at`.
**Where**: `backend/app/db/models.py`
**Depends on**: None
**Reuses**: padrão das models existentes (`SyncJob`, `PersonalRecord` — `Mapped[]`, `_utcnow`)
**Requirement**: AUTH-09, AUTH-14, AUTH-15, AUTH-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `UserSession` com unique em `token_hash` e FK CASCADE (deletar usuário derruba sessões)
- [x] `User.email` nullable + unique (múltiplos NULL permitidos — seed id 1 sem email)
- [x] Testes: email NULL múltiplo aceito; email duplicado viola unique; delete de usuário cascata nas sessões
- [x] Gate check passes: `uv run pytest tests/test_auth_models.py` + Full suite verde
- [x] Test count: ~3 novos + 362 existentes (no silent deletions)

**Tests**: integration
**Gate**: full

**Commit**: `feat(db): add user email/password and sessions table`

---

### T2: Fix da sequência users_pkey no init_db

**What**: `init_db()` roda `SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id),1) FROM users))` após o seed (via `text()`, Postgres-only por decisão AD-007).
**Where**: `backend/app/db/engine.py`
**Depends on**: T1
**Reuses**: seed existente do usuário 1 (permanece intocado)
**Requirement**: AUTH-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Após `init_db`, INSERT sem id explícito recebe id > 1 sem duplicate key
- [x] Re-executar `init_db` é idempotente (seed não duplica, setval reajusta)
- [x] Testes: insert sem id → id > 1; segundo insert → id crescente
- [x] Gate check passes: `uv run pytest tests/test_auth_models.py` + Full suite verde
- [x] Test count: ~2 novos + 362 existentes

**Tests**: integration
**Gate**: full

**Commit**: `fix(db): resync users_pkey sequence in init_db`

---

### T3: Settings de auth + CORS explícito

**What**: `Settings` ganha `invite_code: str = ""`, `session_ttl_days: int = 30`, `session_renew_threshold_days: int = 15`, `session_cookie_name: str = "ritmo_session"`, `session_cookie_secure: bool = False`; default de `cors_origins` muda de `"*"` para `"http://localhost:3000"`. Atualiza `backend/.env.example` com as novas vars documentadas.
**Where**: `backend/app/core/config.py`
**Depends on**: None
**Reuses**: padrão `Settings`/pydantic-settings existente
**Requirement**: AUTH-02, AUTH-28, AUTH-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 5 settings novas com defaults do design; `cors_origins_list` segue funcionando com lista explícita
- [x] `.env.example` documenta `INVITE_CODE`, `SESSION_*` e `CORS_ORIGINS` (com exemplo do IP da LAN)
- [x] Gate check passes: Full suite verde (config-only — nenhum comportamento muda até o wiring)
- [x] Test count: 362 existentes

**Tests**: none
**Gate**: full

**Commit**: `feat(core): auth settings and explicit cors origins default`

---

### T4: Primitivas de segurança (argon2id + token de sessão)

**What**: `app/auth/security.py` com `hash_password`, `verify_password` (argon2id via `argon2-cffi` — adicionada ao `pyproject.toml`), `new_session_token` (`secrets.token_urlsafe(32)`) e `hash_token` (SHA-256 hex de 64 chars — o único formato que vai ao banco).
**Where**: `backend/app/auth/security.py`
**Depends on**: None
**Reuses**: nada — funções puras
**Requirement**: AUTH-06, AUTH-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Roundtrip hash/verify funciona; senha errada → verify False
- [x] `new_session_token()` gera strings únicas de entropia adequada; `hash_token` é determinístico, 64 hex, e nunca devolve o token
- [x] `argon2-cffi` no `pyproject.toml` (`uv sync` ok)
- [x] Testes: roundtrip, verify negativo, tokens distintos, hash 64-hex determinístico
- [x] Gate check passes: `uv run pytest tests/test_auth_security.py`
- [x] Test count: ~6 novos + 362 existentes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(auth): argon2 password hashing and session token utils`

---

### T5: Rate limiter de login (em memória)

**What**: `app/auth/rate_limit.py` com classe `RateLimiter`: `check(email)` levanta `RateLimitedError` com ≥5 falhas em 15 min; `record_failure(email)`; `reset(email)` no sucesso; `_store` acessível para fixture de teste. Lock de threading para o worker único.
**Where**: `backend/app/auth/rate_limit.py`
**Depends on**: None
**Reuses**: nada — stdlib (`threading`, `time`)
**Requirement**: AUTH-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 4 falhas → check passa; 5ª falha → check levanta `RateLimitedError` (mesmo com senha correta depois)
- [x] Janela expira (timestamps manipulados no teste) → check passa de novo
- [x] Sucesso (`reset`) zera o contador; emails são isolados entre si
- [x] Testes cobrem os 4 comportamentos acima
- [x] Gate check passes: `uv run pytest tests/test_auth_rate_limit.py`
- [x] Test count: ~5 novos + 362 existentes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(auth): in-memory login rate limiter`

---

### T6: Service de sessão (register/login/sliding/revoke/prune)

**What**: `app/auth/service.py` com exceções de domínio (`InviteDisabledError`, `InviteInvalidError`, `EmailTakenError`) e funções: `register` (valida convite/normaliza email/cria user+sessão), `login` (401 genérico nos dois ramos, limiter, prune lazy), `create_session`, `resolve_session` (hash→lookup `expires_at > now`; renewal quando restam ≤15d — `expires_at = now + 30d` — e sinaliza renovação), `revoke` (DELETE, idempotente).
**Where**: `backend/app/auth/service.py`
**Depends on**: T1, T4, T5
**Reuses**: `User`, `SessionLocal`, padrão service dos domínios existentes
**Requirement**: AUTH-01..07, AUTH-09, AUTH-12, AUTH-13, AUTH-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Register: convite válido → user + sessão; email normalizado lowercase; erros de domínio nos 3 casos
- [x] Login: sucesso → token; senha/email errado → mesma exceção genérica; lockout respeita o limiter; prune das sessões expiradas roda no login (AUTH-16)
- [x] `resolve_session`: token válido → user; expirado/revogado/ausente → None; sliding renova quando `expires_at - now ≤ 15d` (borda inclusa)
- [x] `revoke` em token inexistente não levanta
- [x] Testes (DB-backed): ~10 cobrindo os fluxos acima
- [x] Gate check passes: `uv run pytest tests/test_auth_service.py`
- [x] Test count: ~10 novos + 362 existentes

**Tests**: integration
**Gate**: quick

**Commit**: `feat(auth): session service with register login sliding renewal`

---

### T7: API de auth + proteção dos routers (endpoints, deps, wiring)

**What**: O módulo auth exposto como API — entrega coesa e atomicamente testável (deps sem router é não-testável; router sem deps fica incompleto — merge-forward das regras do workflow). Conteúdo: `schemas.py` (RegisterIn/LoginIn/MeOut), `router.py` (`POST /api/auth/register` 201+cookie, `POST /api/auth/login` 200+cookie, `POST /api/auth/logout` 204 protegido, `GET /api/auth/me` 200 protegido; cookie `HttpOnly`+`SameSite=Lax`+`Max-Age=30d`+host-only+`secure=settings`), `deps.py` (`require_session`: cookie→`resolve_session`→User ou 401; renewal re-seta o cookie no response injetado) e `main.py` (include do auth router + `dependencies=[Depends(require_session)]` explícito em TODOS os routers existentes; `/api/health` fora).
**Where**: `backend/app/auth/`
**Depends on**: T2, T3, T6
**Reuses**: padrão router/schemas de `activities/`/`evaluation/`; `parseError` do lado FE depois (T9)
**Requirement**: AUTH-01..13, AUTH-27, AUTH-28

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Register: 201 + cookie + auto-login; 403 "registro desabilitado" com env vazio; 403 código inválido; 409 email duplicado (case-variant pega); 422 por campo (senha <8, email malformado, nome vazio/>120)
- [x] Login: 200 + cookie com flags corretos; 401 genérico único; 429 no lockout
- [x] Logout: 204 + sessão revogada no banco + cookie limpo; sem sessão → 401
- [x] Me: 200 `{id, email, display_name}` com sessão; 401 sem
- [x] Proteção: `GET /api/activities` (e demais routers existentes) → 401 sem cookie, 200 com; `GET /api/health` → 200 público; OPTIONS preflight → isento de sessão
- [x] Sliding: request com sessão no limiar → `expires_at` renovado no banco + header Set-Cookie presente
- [x] CORS: origem listada → `Access-Control-Allow-Origin` exata + allow-credentials; origem fora → sem headers
- [x] Sequência: 2 registros seguidos → ids > 1, sem colisão (dependência do T2)
- [x] Gate check passes: `uv run pytest tests/test_auth_api.py tests/test_auth_service.py` + Full suite verde
- [x] Test count: 15 novos + 392 existentes (407 no total)

**Tests**: integration
**Gate**: full

**Commit**: `feat(auth): auth api endpoints and route protection`

---

### T8: CLI set_password (bootstrap e suporte)

**What**: `app/auth/set_password.py` — `run_set_password(email, password)` (seam) e `main()` (email via `input`, senha via `getpass`): email inédito + seed id 1 sem email → vincula preservando display_name; email inédito + seed já vinculado → cria conta; email existente → substitui o hash sem tocar no nome.
**Where**: `backend/app/auth/set_password.py`
**Depends on**: T1, T4
**Reuses**: padrão do `app/garmin/login.py` (`__main__` guard, inputs injetáveis para teste)
**Requirement**: AUTH-25, AUTH-26

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Os 3 caminhos funcionam: vincula seed / cria nova / reseta existente (display_name preservado)
- [ ] `uv run python -m app.auth.set_password` roda interativo no compose (`docker compose exec backend ...` documentado na T16)
- [ ] Testes com monkeypatch de input/getpass cobrem os 3 caminhos
- [ ] Gate check passes: `uv run pytest tests/test_auth_cli.py` + Full suite verde
- [ ] Test count: ~5 novos + 362 existentes

**Tests**: unit
**Gate**: full

**Commit**: `feat(auth): set_password cli for bootstrap and support`

---

### T9: Wrapper de API no frontend (credentials + redirect 401)

**What**: `apiFetch(path, init)` injeta `credentials: "include"` e, em 401 com path fora de `/api/auth/*` e browser fora de `/login`, faz `window.location.replace("/login?next=" + encodeURIComponent(location.pathname + location.search))`. Helpers novos: `login`, `register`, `logout`, `me` (tipos `MeOut`, `AuthError` reutilizando `ApiError`).
**Where**: `frontend/src/lib/api.ts`
**Depends on**: T7 (contrato dos endpoints)
**Reuses**: `API_BASE`, `ApiError`, `parseError` existentes
**Requirement**: AUTH-21

**Tools**:

- MCP: NONE
- Skill: NONE (ler `frontend/node_modules/next/dist/docs/` se mexer em convenções Next)

**Done when**:

- [ ] `apiFetch` com `credentials: "include"` em todo request; redirect 401 com `next` correto e guardas anti-loop
- [ ] Helpers de auth tipados espelhando os contratos da T7
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner no frontend (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): auth api client with credentials and 401 redirect`

---

### T10: Migrar call sites existentes para o wrapper

**What**: Os ~10 `fetch` diretos em `api.ts` (`startSync`, `getLatestJob`, `getActivities`, `getActivityDetail`, `evaluateActivity`, `getEvaluation`, `getPotential`, `getHealthSummary`) passam por `apiFetch` — nenhum comportamento além de credentials + redirect 401.
**Where**: `frontend/src/lib/api.ts`
**Depends on**: T9
**Reuses**: assinaturas/retornos existentes — mudança mecânica
**Requirement**: AUTH-21

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Zero `fetch(` direto restante em `api.ts` (grep)
- [ ] Painéis continuam renderizando (build ok; UAT final confere)
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `refactor(frontend): route all fetches through apiFetch`

---

### T11: Route groups (app)/(auth) com layout mínimo de auth

**What**: Mover `layout.tsx`, `page.tsx`, `treinos/`, `performance/`, `saude/` para `src/app/(app)/`; criar `src/app/(auth)/layout.tsx` mínimo (sem Header/Nav/SyncButton). URLs não mudam; home autenticada segue redirecionando para `/treinos` (AUTH-20).
**Where**: `frontend/src/app/`
**Depends on**: None
**Reuses**: arquivos existentes apenas movidos (git mv); `AGENTS.md` do frontend: ler docs de layouts antes
**Requirement**: AUTH-22, AUTH-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Painéis em `(app)` com header; `/login`/`/registrar` futuras herdarão layout mínimo
- [ ] Rotas e comportamento atuais preservados (home → /treinos)
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): split route groups for app and auth layouts`

---

### T12: Proxy otimista de sessão (proxy.ts)

**What**: `src/proxy.ts` — rotas protegidas (`/`, `/treinos/*`, `/performance`, `/saude`) sem cookie `ritmo_session` → redirect `/login?next=<pathname+search>`; `/login`/`/registrar` com cookie → redirect `/treinos`; resto → next(). Matcher exclui `/api/:path*`, `_next/static`, `_next/image`, favicon. **Checa só presença — nunca valida token** (AD-018).
**Where**: `frontend/src/proxy.ts`
**Depends on**: T11
**Reuses**: convenção do guia oficial (Next 16 renomeou middleware → proxy — `01-getting-started/16-proxy.md` + guia de autenticação)
**Requirement**: AUTH-17, AUTH-18, AUTH-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem cookie em rota protegida → `/login?next=` (URL-encoded, preserva query); `/` sem cookie → `/login?next=/treinos`
- [ ] Com cookie em `/login`/`/registrar` → `/treinos`
- [ ] Matcher não roda em `/api/*` nem assets estáticos
- [ ] Gate check passes: `npm run lint && npm run build` (comportamento no UAT final)
- [ ] Test count: sem test runner (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): optimistic session proxy`

---

### T13: Tela /login com volta à rota original

**What**: `src/app/(auth)/login/page.tsx` — form client component (email/senha, tema escuro 390px), lê `next` do search param, chama `login()`, erro exibido inline (401 genérica / 429 com janela), sucesso → `router.replace(next ?? "/treinos")`. Link para `/registrar`.
**Where**: `frontend/src/app/(auth)/login/page.tsx`
**Depends on**: T9, T11
**Reuses**: helpers `login`/`ApiError` da T9; layout mínimo da T11; tema dos painéis
**Requirement**: AUTH-18, AUTH-06/07/08 (consumo da API)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Login válido entra e aterrissa em `next` (ou `/treinos`); erros 401/429 inline em PT-BR
- [ ] Sem header de painéis (layout da T11)
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): login screen with return-to-route`

---

### T14: Tela /registrar com código de convite

**What**: `src/app/(auth)/registrar/page.tsx` — form (display_name, email, senha, código de convite), chama `register()`, erros 403/409/422 inline por campo, sucesso (201 + auto-login) → `router.replace(next ?? "/treinos")`. Link para `/login`.
**Where**: `frontend/src/app/(auth)/registrar/page.tsx`
**Depends on**: T9, T11
**Reuses**: mesmos padrões da T13; helpers `register`
**Requirement**: AUTH-01..05 (consumo da UI)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cadastro válido entra auto-logado; 403/409/422 exibidos inline por campo
- [ ] Sem header de painéis
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): invite-code registration screen`

---

### T15: UserMenu no header (nome + Sair)

**What**: `src/components/UserMenu.tsx` (client) — monta → `me()`: sucesso → display_name + botão "Sair"; 401 → não renderiza. "Sair" → `logout()` → `location.assign("/login")`. Header (server component) passa a renderizá-lo ao lado do SyncButton.
**Where**: `frontend/src/components/UserMenu.tsx`
**Depends on**: T9, T11
**Reuses**: `Header.tsx` (server component que já compõe client components), helpers `me`/`logout`
**Requirement**: AUTH-23, AUTH-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Header autenticado exibe display_name + "Sair"; não exibe nada sem sessão
- [ ] Sair revoga no servidor e aterrissa em `/login` (voltar não reabre painel — UAT final)
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): user menu with logout in header`

---

### T16: Documentação (README §auth, .env.example, compose)

**What**: README: seção "Login e acesso" (CLI `docker compose exec backend python -m app.auth.set_password`, convite via `INVITE_CODE`, **constraint same-host** frontend/API no §LAN, flags do cookie, interim do sync até o `user-scope`); `.env.example` final revisado; nota de status no topo do README.
**Where**: `README.md`
**Depends on**: T15 (todas as fases anteriores)
**Reuses**: estrutura atual do README (§Rodando, §LAN, §Decisões)
**Requirement**: suporte a AUTH-25, AUTH-28 (operação); nenhum AC novo

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] README documenta CLI, convite, same-host e interim; status atualizado com "auth ✅"
- [ ] `.env.example` completo e coerente com `core/config.py`
- [ ] Gate check passes: Build+Full final — `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build`
- [ ] Test count: suite inteira verde (~407)

**Tests**: none
**Gate**: build+full

**Commit**: `docs(auth): document login invite cli and same-host constraint`

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in order:

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 → T2

Phase 2:  T6 → T7

Phase 3:  T9 → T10
          T11 → T12
          T9 → T13
          T11 → T13
          T9 → T14
          T11 → T14
          T9 → T15
          T11 → T15

Phase 4:  T15 → T16
```

Arestas completas (incluindo cross-phase backward) estão no Execution Plan; dentro de uma fase
a execução é sequencial — sem paralelismo intra-fase.

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**How phase-based execution works:**

At Execute, the agent counts total tasks and packs phases into **task-budgeted batches** (~7 tasks
per worker, whole phases - the benchmarked sweet spot is ~20 tasks → ~3 workers). A **phase** is the
semantic/dependency unit; a **batch** is one or more *consecutive whole phases* assigned to one
worker. The cut only ever lands on a phase boundary - a phase is never split across workers. When
packing yields more than one batch (> ~8 tasks), the agent offers to dispatch batch sub-agents.
Batches run sequentially: each worker executes ALL its tasks in order, then reports a compact summary
before the next batch starts.

When the whole feature fits a single batch (≤ ~8 tasks), execution happens inline in the main window
with no sub-agents spawned.

**The orchestrating agent's role during Execute:**
1. Count total tasks and pack phases into ~7-task batches - offer batch sub-agents if that yields more than one batch and the user accepts
2. Dispatch the next batch (to a worker, or execute inline)
3. Receive the compact batch summary
4. Update tasks.md with results
5. If the batch summary shows all tasks complete: proceed to the next batch
6. If a task failed: decide fix/escalate before dispatching the next batch

---

## Task Granularity Check

Before approving tasks, verify they are granular enough:

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Modelos de auth | 1 arquivo (models.py) | ✅ Granular |
| T2: setval no init_db | 1 função | ✅ Granular |
| T3: Settings de auth | 1 arquivo (+ .env.example documental) | ✅ Granular |
| T4: Primitivas de segurança | 1 módulo puro | ✅ Granular |
| T5: Rate limiter | 1 classe | ✅ Granular |
| T6: Service de sessão | 1 módulo (funções coesas do ciclo de sessão) | ✅ Granular |
| T7: API de auth + proteção | 1 seam coeso (`app/auth/` + wiring) — deps sem router é não-testável | ⚠️ Cohesive (justificado — merge-forward das regras do workflow) |
| T8: CLI set_password | 1 módulo CLI | ✅ Granular |
| T9: Wrapper apiFetch | 1 arquivo (api.ts) | ✅ Granular |
| T10: Migrar call sites | 1 arquivo (mudança mecânica) | ✅ Granular |
| T11: Route groups | 1 estrutura (movimentação) | ✅ Granular |
| T12: proxy.ts | 1 arquivo | ✅ Granular |
| T13/T14: Telas | 1 página cada | ✅ Granular |
| T15: UserMenu | 1 componente (+ integração no Header) | ✅ Granular |
| T16: Documentação | 1 arquivo principal (README) | ✅ Granular |

**Granularity check**:

- ✅ 1 component / 1 function / 1 endpoint = Good
- ⚠️ 2-3 related things in same file = OK if cohesive
- ❌ Multiple components or files = MUST split

---

## Diagram-Definition Cross-Check

Before approving tasks, verify the execution diagram is consistent with the task definitions. These are independent artifacts that can drift - the diagram is drawn for visual clarity while task bodies are written for precision. Both must agree.

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | raiz da Phase 1 | ✅ Match |
| T2 | T1 | T1 ──→ T2 | ✅ Match |
| T3 | None | standalone | ✅ Match |
| T4 | None | standalone | ✅ Match |
| T5 | None | standalone | ✅ Match |
| T6 | T1, T4, T5 (cross-phase, backward) | T6 ──→ T7 (arestas cross-phase ficam no body) | ✅ Match |
| T7 | T2, T3, T6 (T6 intra-fase; T2/T3 backward) | T6 ──→ T7 | ✅ Match |
| T8 | T1, T4 (cross-phase, backward) | standalone na Phase 2 | ✅ Match |
| T9 | T7 (backward) | raiz do bloco frontend | ✅ Match |
| T10 | T9 | T9 ──→ T10 | ✅ Match |
| T11 | None | standalone (raiz do par T11→…) | ✅ Match |
| T12 | T11 | T11 ──→ T12 | ✅ Match |
| T13 | T9, T11 | T9 ──→ T13, T11 ──→ T13 | ✅ Match |
| T14 | T9, T11 | T9 ──→ T14, T11 ──→ T14 | ✅ Match |
| T15 | T9, T11 | T9 ──→ T15, T11 ──→ T15 | ✅ Match |
| T16 | T15 (todas anteriores, backward) | standalone na Phase 4 | ✅ Match |

**Rules:**

- Every `Depends on` in a task body must have a corresponding arrow in the diagram.
- Every arrow in the diagram must correspond to a `Depends on` in the target task's body.
- A task must never depend on a task in a later phase - dependencies point backward or within the same phase only.

---

## Test Co-location Validation

Before approving tasks, verify EVERY task's `Tests` field is consistent with the **Test Coverage Matrix** generated above. This is a hard gate - tasks that fail this check MUST be fixed.

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Persistência (models) | integration | integration | ✅ OK |
| T2 | Persistência (engine) | integration | integration | ✅ OK |
| T3 | Config/docs | none | none | ✅ OK |
| T4 | Domínio puro (security) | unit | unit | ✅ OK |
| T5 | Domínio puro (rate_limit) | unit | unit | ✅ OK |
| T6 | API/service (DB-backed) | integration | integration | ✅ OK |
| T7 | API + proteção | integration | integration | ✅ OK |
| T8 | CLI (seam) | unit | unit | ✅ OK |
| T9 | Frontend (api.ts) | none | none | ✅ OK |
| T10 | Frontend (api.ts) | none | none | ✅ OK |
| T11 | Frontend (estrutura) | none | none | ✅ OK |
| T12 | Frontend (proxy) | none | none | ✅ OK |
| T13 | Frontend (tela) | none | none | ✅ OK |
| T14 | Frontend (tela) | none | none | ✅ OK |
| T15 | Frontend (componente) | none | none | ✅ OK |
| T16 | Docs | none | none | ✅ OK |

**Rules:**

- "Tested in another task" is NOT a valid justification for `Tests: none`. That is test deferral - the exact anti-pattern this validation prevents.
- `Tests: none` is only valid when the coverage matrix says "none" for that code layer.
- If a task creates MULTIPLE code layers (e.g., service + controller), use the HIGHEST test type required by any of them.
- Any ❌ VIOLATION → restructure the task to include its required tests before proceeding.
