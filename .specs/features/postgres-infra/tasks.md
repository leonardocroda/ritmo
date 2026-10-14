# Infra Postgres + Docker Compose — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: inline — feature média, sem `design.md` (decisões na AD-007 e no spec)
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `frontend/AGENTS.md` (regras Next.js 16), `backend/pyproject.toml` (pytest>=9, sem thresholds de cobertura) — strong defaults aplicados no limite do spec.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Config (Settings/env) | integration | INFRA-03: `DATABASE_URL` só por env (override refletido; default é `postgresql+psycopg`, sem `sqlite://`) | `backend/tests/test_infra.py` | `uv run pytest` (requer postgres do compose de pé) |
| Engine/bootstrap DB | integration | INFRA-04: create_all + seed no Postgres; INFRA-09: dialeto postgres no engine; INFRA-05: banco `ritmo_test` com estado limpo por teste (só o seed) | `backend/tests/test_infra.py` + `backend/tests/test_health.py` (suite existente como piso) | `uv run pytest` |
| Fail-fast de conexão nos testes | integration | INFRA-06: Postgres inacessível → erro imediato com instrução `docker compose up -d postgres` | `backend/tests/test_infra.py` | `uv run pytest` |
| Docker/compose/Dockerfiles | none | - (build gate: `docker compose config -q` + `up` + curls) | - | build gate |
| Docs/env example | none | - (build gate) | - | build gate |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Suite inteira é integration; "full" = quick aqui.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com testes (T1, T2, T4) | `uv run pytest` (em `backend/`) |
| Full | Última task de fase com testes (T4) | `uv run pytest` (em `backend/`) |
| Build | Config/infra/docs (T3, T5, T6, T7) e fechamento (T8) | `docker compose config -q && docker compose up -d --build && curl -fsS http://localhost:8000/api/health && curl -fsSI http://localhost:3000 && uv run pytest (em backend/) && npm run build && npm run lint (em frontend/)` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend switch para Postgres

Config e engine deixam de ser SQLite; suite continua verde (conftest ainda aponta para o banco de teste atual, trocado na Phase 2).

```
T1 → T2
```

### Phase 2: Postgres local + testes no Postgres

Compose ganha o postgres; a suite de testes migra para o banco real.

```
T3 → T4
```

### Phase 3: Containers do app + docs

Backend e frontend containerizados; documentação do setup.

```
T5 ──→ T7
T6 ──→ T7
```

### Phase 4: Verificação de ponta a ponta

Stack completo de pé, gate full executado.

```
T8
```

---

## Task Breakdown

### Phase 1: Backend switch para Postgres

#### T1: Driver psycopg3 + default `DATABASE_URL` postgres

**What**: Adicionar `psycopg[binary]` às dependências (via `uv add`, atualizando pyproject e uv.lock) e trocar o default de `database_url` em `Settings` para `postgresql+psycopg://ritmo:ritmo@localhost:5432/ritmo`.
**Where**: `backend/app/core/config.py`
**Depends on**: None
**Reuses**: `app/core/config.py` (pydantic-settings já casa env vars)
**Requirement**: INFRA-09, INFRA-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `uv.lock` e `pyproject.toml` contêm `psycopg[binary]`
- [x] Default `database_url` começa com `postgresql+psycopg://` e não contém `sqlite`
- [x] Teste novo: `Settings()` sem `DATABASE_URL` no ambiente usa default postgres (INFRA-03)
- [x] Teste novo: `DATABASE_URL` no ambiente sobrepõe o default (INFRA-03)
- [x] Gate check passes: `uv run pytest` — 5 tests pass (3 existentes + 2 novos)

**Tests**: integration (2 novos em `backend/tests/test_infra.py`)
**Gate**: quick

**Status**: ✅ Complete — gate 5/5 (2026-10-14)

**Commit**: `build(backend): switch default database to postgres with psycopg3 driver`

---

#### T2: Engine sem código SQLite

**What**: Remover do engine a branch SQLite (`check_same_thread`, pragmas WAL/foreign_keys); engine assume caminho único Postgres, com get_db/init_db inalterados.
**Where**: `backend/app/db/engine.py`
**Depends on**: T1
**Reuses**: estrutura existente de engine/session; só remove código morto
**Requirement**: INFRA-09, INFRA-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Nenhuma referência a `sqlite`, `PRAGMA` ou `check_same_thread` no engine
- [x] `init_db` continua criando schema + seed do usuário default (coberto pela suite existente)
- [x] Gate check passes: `uv run pytest` — 5 tests pass (nenhum deletado)

**Tests**: integration (suite existente; sem novos asserts — remoção de código morto)
**Gate**: quick

**Status**: ✅ Complete — gate 5/5 (2026-10-14)

**Commit**: `refactor(db): drop sqlite-specific engine code for postgres-only path`

---

### Phase 2: Postgres local + testes no Postgres

#### T3: Serviço postgres no compose + init + volume

**What**: Criar o compose com serviço `postgres:16` (healthcheck `pg_isready`, volume nomeado `postgres-data`, porta 5432) e script de init (montado em `docker/postgres/init/`) criando o banco `ritmo_test` além do `ritmo`.
**Where**: `docker-compose.yml`
**Depends on**: None
**Reuses**: convenção `docker-entrypoint-initdb.d` da imagem oficial postgres
**Requirement**: INFRA-07, INFRA-08, INFRA-01 (parte postgres)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `docker compose config -q` passa
- [x] `docker compose up -d postgres` deixa o healthcheck `healthy` e `\l` mostra `ritmo` e `ritmo_test`
- [x] Volume `postgres-data` declarado; `docker compose down` (sem `-v`) preserva os dados
- [x] Gate check passes: build (compose config + up postgres healthy)

**Tests**: none (camada Docker/compose — matriz diz none, build gate decide)
**Gate**: build

**Status**: ✅ Complete — config OK, health healthy, bancos ritmo + ritmo_test verificados via psql (2026-10-14)

**Commit**: `feat(infra): add postgres service with healthcheck, volume and test db init`

---

#### T4: Suite de testes no Postgres do compose

**What**: Apontar `DATABASE_URL` do conftest para `ritmo_test`, com estado limpo por teste (drop/create + seed via lifespan) e fail-fast claro; criar helper `ensure_postgres_available` (em `backend/tests/helpers.py`) e 3 testes novos em `backend/tests/test_infra.py` (dialeto, estado limpo, fail-fast).
**Where**: `backend/tests/conftest.py`
**Depends on**: T1, T2, T3
**Reuses**: padrão do conftest atual (env antes dos imports da app); fixture autouse para estado limpo
**Requirement**: INFRA-05, INFRA-06, INFRA-09 (dialeto), INFRA-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `uv run pytest` roda contra `ritmo_test` (localhost:5432) e termina verde — 9 tests (5 + 4 novos)
- [x] Teste novo: engine conectado ao dialeto `postgresql+psycopg` (INFRA-09)
- [x] Teste novo: cada teste vê só o usuário seed (estado limpo — INFRA-05; par de testes polui → verifica)
- [x] Teste novo: `ensure_postgres_available` em URL morta levanta erro citando `docker compose up -d postgres` (INFRA-06)
- [x] Com postgres fora do ar: pytest falha imediatamente com a mensagem de instrução (demostrado: `docker compose stop postgres` → RuntimeError com hint, teto de 3s/endereço)
- [x] Gate check passes: full — 9 tests pass em ~10s

**Tests**: integration (4 novos)
**Gate**: full

**Status**: ✅ Complete — gate 9/9 em 9.62s; demo com banco fora do ar OK (2026-10-14)

**Commit**: `test(backend): run pytest against compose postgres with clean state per test`

---

### Phase 3: Containers do app + docs

#### T5: Backend em container + serviço no compose

**What**: Criar Dockerfile do backend (python slim, uv sync, uvicorn na 8000) com `.dockerignore`; adicionar serviço `backend` ao compose com `depends_on: postgres (service_healthy)`, `DATABASE_URL` via environment e porta 8000.
**Where**: `backend/Dockerfile`
**Depends on**: T2, T3
**Reuses**: pyproject/uv.lock como fonte única de dependências
**Requirement**: INFRA-01 (parte backend), INFRA-02, INFRA-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `docker compose up -d --build` sobe o backend só após postgres `healthy`
- [x] `curl -fsS http://localhost:8000/api/health` retorna 200 (backend conectado ao Postgres por env)
- [x] Nenhuma URL de banco no Dockerfile (vem 100% de environment)
- [x] Gate check passes: build (compose config + up + curl 200)

**Tests**: none (camada Docker/compose — matriz diz none, build gate decide)
**Gate**: build

**Status**: ✅ Complete — health 200 `{"status":"ok"}`, seed no Postgres do container, startup após `service_healthy` (2026-10-14)

**Commit**: `feat(infra): containerize backend and wire it to postgres via compose`

---

#### T6: Frontend standalone em container + serviço no compose

**What**: Habilitar `output: 'standalone'` no next.config, criar Dockerfile multi-stage do frontend (build standalone) com `.dockerignore`, e adicionar serviço `frontend` ao compose na porta 3000.
**Where**: `frontend/Dockerfile`
**Depends on**: T3
**Reuses**: regras do `frontend/AGENTS.md` (Next.js 16 — conferir docs locais antes de tocar config)
**Requirement**: INFRA-02 (frontend 200 na 3000), INFRA-01 (parte frontend)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `npm run build` gera build standalone (`.next/standalone` — `server.js` confirmado)
- [x] `npm run lint` passa
- [x] `docker compose up -d --build` sobe o frontend e `curl -fsSI http://localhost:3000` retorna 200
- [x] Gate check passes: build (npm build + lint + compose up + curl 3000)

**Tests**: none (camada Docker/compose — matriz diz none, build gate decide)
**Gate**: build

**Status**: ✅ Complete — HTTP/1.1 200 OK na :3000; 3 serviços Up (2026-10-14)

**Commit**: `feat(infra): containerize frontend with standalone next build`

---

#### T7: Env example e README do setup local

**What**: Atualizar o env example do backend (URL postgres + notas de porta) e o README com a seção "Subindo local": compose up, pytest contra `ritmo_test`, dev diário (`compose up -d postgres` + `uvicorn --reload`), override de porta 5432.
**Where**: `README.md`
**Depends on**: T5, T6
**Reuses**: n/a (docs)
**Requirement**: INFRA-03 (documentação do env), edge case porta 5432

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Env example mostra `DATABASE_URL=postgresql+psycopg://ritmo:ritmo@localhost:5432/ritmo` (sem `sqlite://`)
- [x] README cobre: primeiro `up`, dev diário, pytest, override de porta
- [x] Gate check passes: build-lite (`docker compose config -q`)

**Tests**: none (camada docs — matriz diz none)
**Gate**: build

**Status**: ✅ Complete — env example UTF-8 limpo, README com stack/dev/testes/porta; também atualizadas as menções a SQLite que esta feature invalidou (2026-10-14)

**Commit**: `docs(readme): document local postgres setup via docker compose`

---

### Phase 4: Verificação de ponta a ponta

#### T8: Verificação de ponta a ponta do stack

**What**: Levantar o stack completo do zero (`down -v` → `up -d --build`), validar healthchecks, curls 200 (8000/3000), suite verde contra o Postgres, e persistência do volume após `down`/`up`; registrar os resultados aqui.
**Where**: nenhum arquivo novo (verificação E2E; atualiza este tasks.md)
**Depends on**: T5, T6, T7
**Reuses**: Gate Check Commands (nível Build)
**Requirement**: INFRA-01, INFRA-02, INFRA-08 (evidência de execução)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `docker compose down -v && docker compose up -d --build`: 3 serviços saudáveis, backend após postgres healthy
- [ ] `curl -fsS http://localhost:8000/api/health` → 200 com `"status": "ok"`; `curl -fsSI http://localhost:3000` → 200
- [ ] `uv run pytest` → 9 tests pass contra o Postgres do compose
- [ ] `docker compose down && docker compose up -d`: schema e usuário default persistem (volume)
- [ ] Resultados registrados neste tasks.md (evidência do gate Build)

**Tests**: none (tarefa de verificação — o gate Build é a verificação)
**Gate**: build

**Commit**: `chore(infra): verify full stack end to end on postgres`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 ------→ T2
Phase 2:  T3 ------→ T4
Phase 3:  T5 ──────→ T7
          T6 ──────→ T7
Phase 4:  T8
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Como a execução por fases funciona:**

O total são 8 tasks — cabe num único lote (~7-8), portanto a execução é **inline na janela principal, sem sub-agents**.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Driver + default de config | 1 config + dependência | ✅ Granular |
| T2: Engine sem código SQLite | 1 arquivo | ✅ Granular |
| T3: Serviço postgres no compose | 1 compose + 1 init script | ✅ Granular |
| T4: Suite de testes no Postgres | conftest + helpers + test_infra (coesos, mesma entrega) | ✅ Granular |
| T5: Backend em container | 1 Dockerfile + serviço | ✅ Granular |
| T6: Frontend em container | 1 Dockerfile + config standalone | ✅ Granular |
| T7: Env example + README | docs | ✅ Granular |
| T8: Verificação E2E | verificação (sem código novo) | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | (início da Phase 1) | ✅ Match |
| T2 | T1 | T1 → T2 (Execution Plan e Phase Map) | ✅ Match |
| T3 | None | (início da Phase 2) | ✅ Match |
| T4 | T1, T2, T3 | T3 → T4 (intra-fase); T1/T2 são cross-phase (não exigem seta) | ✅ Match |
| T5 | T2, T3 | (sem seta intra-fase; T2/T3 cross-phase) | ✅ Match |
| T6 | T3 | (sem seta intra-fase; T3 cross-phase) | ✅ Match |
| T7 | T5, T6 | T5 → T7, T6 → T7 (Execution Plan e Phase Map) | ✅ Match |
| T8 | T5, T6, T7 | (única task da Phase 4; deps cross-phase) | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Config (Settings) | integration | integration (2 novos) | ✅ OK |
| T2 | Engine/bootstrap | integration | integration (suite existente) | ✅ OK |
| T3 | Docker/compose | none | none | ✅ OK |
| T4 | Conftest/helpers + testes | integration | integration (3 novos) | ✅ OK |
| T5 | Dockerfile/compose | none | none | ✅ OK |
| T6 | Dockerfile/compose | none | none | ✅ OK |
| T7 | Docs/env example | none | none | ✅ OK |
| T8 | Nenhum (verificação) | none | none | ✅ OK |
