# Sync do Garmin — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/garmin-sync/design.md`
**Status**: In Progress (Lote 1 de 3 — T1–T5)

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes (`uv run pytest` + `docker compose up -d postgres` obrigatório); `frontend/AGENTS.md` (ler docs do Next 16 antes de codar frontend); lição L-001 embutida em `backend/tests/test_infra.py:60` (afirmar literais definidos no spec, nunca constantes compartilhadas com a implementação). Sem CONTRIBUTING/CI/lint de backend — fortes defaults aplicados onde não há padrão.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domain puro (`mappers.py`, cálculo `pmc.py`) | unit | 1:1 com ACs; todos os edges listados no spec; valores conferidos contra cálculo manual (Independent Test do spec) | `backend/tests/test_garmin_*.py` | `cd backend; uv run pytest` |
| Gateway Garmin (`client.py`) | unit (lib stubada; `time.sleep` monkeypatchado) | contagem, intervalo, retry 2/4/8, sem retry em auth, teto, paginação por 20 — 1:1 com SYNC-03/07/09/25 | `backend/tests/test_garmin_gateway.py` | `cd backend; uv run pytest` |
| Config (`Settings`) | unit | defaults + override por env (padrão do `test_infra.py`) | `backend/tests/test_sync_config.py` | `cd backend; uv run pytest` |
| Data-access (`upserts.py`, `pmc.recompute`) | integration (Postgres real) | chaves de dedup, contagens estáveis 2×, prune, janela preservada | `backend/tests/test_garmin_*.py` | `cd backend; uv run pytest` |
| Service + Router (API) | integration (TestClient + FakeGateway) | máquina de estados completa; todas as rotas happy+edge+error; idempotência; warnings; reauth | `backend/tests/test_garmin_service.py`, `backend/tests/test_sync_api.py` | `cd backend; uv run pytest` |
| Models / schema | none | cobertos por `test_schema_created` estendido (T1) + build gate | - | build gate only |
| Infra (compose, Dockerfile, `.env.example`) | none | `docker compose config -q` + stack sobe | - | build gate only |
| Frontend | none | `npm run build` + `npm run lint`; UAT manual na T15 (botão é um componente simples) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (a suite roda no banco `ritmo_test`; falha rápido instruindo a subida se o banco estiver fora).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks com testes unitários | `cd backend; uv run pytest` |
| Full | Após tasks com testes de integração (mesma suite; a distinção é o escopo dos testes da task) | `cd backend; uv run pytest` |
| Build | Conclusão de fase / tasks entity / infra / frontend | backend: `cd backend; uv run pytest` · compose: `docker compose config -q` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação (schema + config + infra)

Tasks independentes entre si; ordem fixa de execução.

```
T1   T2   T3
```

### Phase 2: Gateway + mapeamento

```
T2 -> T4
T5
```

### Phase 3: Persistência + PMC

```
T1 -> T6
T7
```

### Phase 4: Orquestração

```
T2 -> T8
T4 -> T8
T5 -> T8
T6 -> T8
T7 -> T8
T8 -> T9
T8 -> T10
```

### Phase 5: Frontend

```
T11 -> T12 -> T13
```

### Phase 6: Operação

```
T10 -> T15
T13 -> T15
T14 -> T15
```

---

## Task Breakdown

### T1: Models de sync (personal_records, sync_state, constraints)

**What**: Adicionar `PersonalRecord` e `SyncState` ao ORM, `UniqueConstraint(activity_id, idx)` no `Split` e o índice parcial único de `SyncJob` por usuário ativo.
**Where**: `backend/app/db/models.py`
**Depends on**: None
**Reuses**: Padrões de `models.py` (`Base`, `DEFAULT_USER_ID`, `UniqueConstraint`, `_utcnow`)
**Requirement**: SYNC-02, SYNC-11, SYNC-13, SYNC-16, SYNC-21
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `personal_records` com `(user_id, event)` único, `value`, `pr_date`, `raw_json`, `user_id` com default
- [x] `sync_state` com `(user_id, data_type)` único e `last_date`
- [x] `splits` com `UniqueConstraint("activity_id", "idx", name="uq_split_activity_idx")`
- [x] `sync_jobs` com índice parcial único `(user_id) WHERE status IN ('pending', 'running')`
- [x] `test_schema_created` estendido: expected set passa a incluir `personal_records` e `sync_state`
- [x] Gate: suite completa passa (contagem de testes inalterada: 9 — só a asserção existente cresce)

**Tests**: none (entity layer — matriz; schema coberto pela extensão do `test_schema_created` acima)
**Gate**: build
**Commit**: `feat(sync): add personal_records and sync_state tables with dedup constraints`

---

### T2: Config SYNC_* por env vars

**What**: Adicionar as 6 configurações de sync ao `Settings` e documentá-las no `.env.example`.
**Where**: `backend/app/core/config.py`
**Depends on**: None
**Reuses**: Padrão `Settings`/pydantic-settings + padrões de teste do `test_infra.py`
**Requirement**: SYNC-03, SYNC-07, SYNC-09, SYNC-10, SYNC-15, SYNC-18
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `sync_repull_days=3`, `sync_backfill_activities_days=180`, `sync_backfill_health_days=60`, `sync_call_interval_s=1.0`, `sync_max_calls=1500`, `sync_retry_max=3`
- [x] `.env.example` lista as 6 `SYNC_*` com comentários
- [x] Testes: defaults exatos (literais do spec, não constantes compartilhadas — L-001) + overrides por env
- [x] Gate: `uv run pytest` passa com ≥ 13 testes (9 baseline + ≥ 4 novos)

**Tests**: unit (`backend/tests/test_sync_config.py`)
**Gate**: quick
**Commit**: `feat(sync): add sync env configuration`

---

### T3: Compose com tokens, TZ e API URL do frontend

**What**: Montar `~/.garminconnect` no backend do compose com `GARMINTOKENS` e `TZ`, e repassar `NEXT_PUBLIC_API_URL` como build arg do frontend.
**Where**: `docker-compose.yml`
**Depends on**: None
**Reuses**: Estrutura atual do compose + Dockerfiles existentes
**Requirement**: SYNC-25 (login com tokens no container), Success Criteria (config 100% env)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Serviço `backend`: volume `~/.garminconnect` montado em caminho interno + `GARMINTOKENS` apontando para ele + `TZ=America/Sao_Paulo`
- [x] Serviço `frontend`: build arg `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`); `frontend/Dockerfile` declara o `ARG` antes do build
- [x] `docker compose config -q` passa
- [x] Stack sobe: `docker compose up -d` → `/api/health` 200 e frontend responde em `:3000`

**Tests**: none (infra layer — matriz: build gate only)
**Gate**: build
**Commit**: `chore(infra): mount garmin tokens and set tz in compose`

---

### T4: GarminGateway (sequência, intervalo, retry, teto)

**What**: Criar o gateway — único ponto de acesso à API do Garmin — com login por tokenstore, contagem, intervalo mínimo, retry 3× (2/4/8s), teto e paginação própria de atividades.
**Where**: `backend/app/garmin/client.py`
**Depends on**: T2
**Reuses**: `token_utils` (`resolve_token_path`, `secure_token_dir`); lib `garminconnect` 0.3.2 (`get_sleep_data`, `get_hrv_data`, `get_rhr_day`, `get_stress_data`, `get_body_battery`, `get_activity_splits`, `get_personal_record`, `connectapi`)
**Requirement**: SYNC-03, SYNC-07, SYNC-09, SYNC-25
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `GarminGateway.from_settings()` faz login pelo tokenstore e expõe os 8 métodos de dados do design
- [x] Toda chamada passa pelo `_call()`: incrementa `calls_made`, dorme `sync_call_interval_s`, retenta `GarminConnectTooManyRequestsError`/erros transitórios com backoff 2s/4s/8s até `sync_retry_max`
- [x] `GarminConnectAuthenticationError` → `GarminAuthExpiredError` sem retry
- [x] `calls_made >= sync_max_calls` → `SyncBudgetExceededError` antes da chamada
- [x] `get_activities` pagina por 20 via `connectapi` com contagem + sleep por página (nunca a paginação interna da lib)
- [x] Testes com lib stubada e `time.sleep` monkeypatchado: contagem, intervalo, backoff exato, sem-retry-em-auth, teto, 2 páginas de atividades (≥ 10 novos; total ≥ 24)

**Tests**: unit (`backend/tests/test_garmin_gateway.py`)
**Gate**: quick
**Commit**: `feat(sync): add garmin gateway with sequential call budget`

---

### T5: Mappers puros (payload → ORM)

**What**: Criar as funções puras que convertem JSON do Garmin em dicts prontos para o ORM, com fixtures de payload por endpoint.
**Where**: `backend/app/garmin/mappers.py`
**Depends on**: None
**Reuses**: Mapa de campos do design + shape das colunas de `models.py`
**Requirement**: SYNC-11, SYNC-12, SYNC-18, SYNC-19
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `map_activity` cobre todos os campos de `Activity` + `raw_json` preservado
- [x] `is_running` aceita `running`/`trail_running` (base de SYNC-12)
- [x] `map_splits` normaliza dict-com-lista e lista direta; vazio/`None` → `[]` sem warning (edge do spec)
- [x] Mappers de saúde devolvem `None` quando não há dado (skip do dia, SYNC-19)
- [x] `map_battery` gera 1 linha por `calendarDate`; `map_stress` produz a média diária
- [x] `map_personal_records` filtra para corrida e extrai `event`/`value`/`pr_date`
- [x] Fixtures de payload por endpoint em `backend/tests/` (≥ 12 novos; total ≥ 36)

**Tests**: unit (`backend/tests/test_garmin_mappers.py`)
**Gate**: quick
**Commit**: `feat(sync): add pure garmin payload mappers`

---

### T6: Upserts idempotentes

**What**: Criar as funções de escrita idempotente por chave natural (atividade, splits+prune, saúde genérica, recordes, sync_state).
**Where**: `backend/app/garmin/upserts.py`
**Depends on**: T1
**Reuses**: Models + constraints de T1; `SessionLocal` do engine
**Requirement**: SYNC-11, SYNC-13, SYNC-16, SYNC-18, SYNC-21
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `upsert_activity` por `garmin_id` retorna `"new"`/`"updated"`
- [x] `upsert_splits` por `(activity_id, idx)` + prune de `idx >= len(rows)`
- [x] `upsert_health_rows` genérico por `(user_id, date)` para sleep/hrv/rhr/battery/stress
- [x] `upsert_records` por `(user_id, event)`
- [x] `set_sync_state`/`get_sync_state` por `(user_id, data_type)`
- [x] Testes no Postgres real: reexecutar 2× → contagens estáveis (Independent Test do spec) (≥ 10 novos; total ≥ 46)

**Tests**: integration (`backend/tests/test_garmin_upserts.py`)
**Gate**: full
**Commit**: `feat(sync): add idempotent upserts for sync tables`

---

### T7: PMC determinística (CTL/ATL/TSB/ACWR)

**What**: Criar o cálculo de carga — agregação diária de `training_load` e recompute de janela afetada com EWMA.
**Where**: `backend/app/garmin/pmc.py`
**Depends on**: None
**Reuses**: Models existentes `Activity` e `DailyLoad` (sem models novos)
**Requirement**: SYNC-22, SYNC-23, SYNC-24
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `aggregate_daily_loads`: soma de `training_load` por data local; atividade sem load conta 0 (SYNC-24)
- [x] CTL = EWMA α=1/42, ATL = EWMA α=1/7, TSB = CTL−ATL (SYNC-22)
- [x] ACWR = soma(7d)/(soma(28d)/4); `None` até a janela de 28d existir completa
- [x] `recompute(from_date)` recalcula só da janela afetada até hoje; semente CTL/ATL vem da última linha anterior de `load`; linhas anteriores intocadas (SYNC-23)
- [x] Valores de ≥ 3 dias conferidos contra cálculo manual em fixtures (Independent Test do spec) (≥ 8 novos; total ≥ 54)

**Tests**: unit + integration (`backend/tests/test_garmin_pmc.py`)
**Gate**: full
**Commit**: `feat(sync): add deterministic pmc computation`

---

### T8: Orquestrador do sync (máquina de estados + stats)

**What**: Criar o serviço: `create_job` com lock, `run_sync` com máquina de estados, fases sequenciais, `stats_json` parciais/finais e política de erros por tipo.
**Where**: `backend/app/garmin/service.py`
**Depends on**: T2, T4, T5, T6, T7
**Reuses**: Gateway (T4), mappers (T5), upserts (T6), pmc (T7), `SyncJob`, `SessionLocal`
**Requirement**: SYNC-04, SYNC-05, SYNC-06, SYNC-10, SYNC-13, SYNC-14, SYNC-15, SYNC-17, SYNC-18, SYNC-19, SYNC-20, SYNC-21, SYNC-24, SYNC-25, SYNC-27
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `pending → running` grava `started_at`; fim → `done|error` grava `finished_at`; transições fora dessa sequência levantam (SYNC-04)
- [x] Job ativo existente → `IntegrityError` → `JobConflictError` (base do 409)
- [x] Janelas: sem `sync_state` → backfill (180d/60d); senão `last_date − repull` até hoje (SYNC-10/15)
- [x] Falha de atividades após retries → `error` (SYNC-14); falha de tipo de saúde/recordes → `done` + `warnings` e os demais tipos continuam (SYNC-20)
- [x] `sync_state` atualizado só em tipo bem-sucedido (SYNC-13/21)
- [x] `stats_json` com todos os contadores do design + `calls_made` + `duration_s` + `message` PT-BR (ex.: "Puxando 12 atividades…") (SYNC-05/06/17)
- [x] `GarminAuthExpiredError` → `error` + `reauth_needed: true` (SYNC-25); `SyncBudgetExceededError` → `error` com stats das chamadas feitas (SYNC-09)
- [x] `FakeGateway` em `backend/tests/fake_garmin.py` + testes: happy path completo, idempotência (2× sync → contagens idênticas), incremental após backfill (SYNC-27) (≥ 12 novos; total ≥ 66)

**Tests**: integration (`backend/tests/test_garmin_service.py`)
**Gate**: full
**Commit**: `feat(sync): add sync orchestrator with job state machine`

---

### T9: Recuperação de jobs órfãos no startup

**What**: No lifespan, marcar jobs `pending|running` órfãos como `error` na subida do servidor.
**Where**: `backend/app/main.py`
**Depends on**: T8
**Reuses**: Padrão do lifespan + `SessionLocal`
**Requirement**: SYNC-02 (nenhum 409 eterno pós-restart)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Lifespan marca jobs ativos como `error` com mensagem "interrompido por restart do servidor"
- [x] Jobs `done|error` não são tocados
- [x] Testes: job `running` pré-existente vira `error` após startup; job `done` permanece (≥ 2 novos; total ≥ 68)

**Tests**: integration (estende `backend/tests/test_garmin_service.py`)
**Gate**: full
**Commit**: `fix(sync): recover stale jobs on startup`

---

### T10: Endpoints de sync

**What**: Criar o router `POST /api/sync`, `GET /api/sync/jobs/{id}`, `GET /api/sync/jobs/latest` e montá-lo na app.
**Where**: `backend/app/garmin/router.py`
**Depends on**: T8
**Reuses**: `get_db`, `create_job`/`run_sync` do service; `BackgroundTasks`
**Requirement**: SYNC-01, SYNC-02, SYNC-05
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `POST /api/sync` cria job `pending` + agenda background task → 201 `{id, status}` (SYNC-01)
- [x] Job ativo → 409 com id/status/started_at do corrente (SYNC-02)
- [x] `GET /jobs/{id}` → `JobOut` completo; 404 para id inexistente
- [x] `GET /jobs/latest` → último job; `{job: null}` quando nunca houve sync
- [x] Router montado no `app/main.py`
- [x] TestClient + FakeGateway: POST executa o sync de fundo sincronamente → job `done` com stats (≥ 7 novos; total ≥ 75)

**Tests**: integration (`backend/tests/test_sync_api.py`)
**Gate**: full
**Commit**: `feat(sync): expose sync api endpoints`

---

### T11: Cliente de API tipado no frontend

**What**: Criar o helper de fetch com base `NEXT_PUBLIC_API_URL` e tipos do `JobOut`.
**Where**: `frontend/src/lib/api.ts`
**Depends on**: None
**Reuses**: Contrato `JobOut`/`stats_json` do design
**Requirement**: SYNC-08 (suporte)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Base lê `process.env.NEXT_PUBLIC_API_URL` com fallback `http://localhost:8000`
- [x] `startSync()` e `getLatestJob()` tipados (`JobOut` espelhando o schema de stats do design)
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add typed sync api client`

---

### T12: SyncButton com progresso e estados

**What**: Criar o componente `"use client"` com estados idle/running/done/error/reauth e polling de 2s no job latest.
**Where**: `frontend/src/components/SyncButton.tsx`
**Depends on**: T11
**Reuses**: `lib/api.ts`
**Requirement**: SYNC-08, SYNC-26
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Docs do Next 16 lidos antes de codar (`frontend/node_modules/next/dist/docs/` — aviso do `frontend/AGENTS.md`)
- [x] Botão desabilita durante `pending|running` e exibe `stats.message` ("Puxando 12 atividades…") (SYNC-08)
- [x] `done` → resumo PT-BR dos contadores; `error` → mensagem do erro
- [x] `reauth_needed` → estado "Reconectar Garmin" com o comando CLI no lugar do resumo (SYNC-26)
- [x] Polling para quando o job chega a estado final; retoma ao clicar de novo
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add sync button with live progress`

---

### T13: Header global com o botão

**What**: Criar o Header e montá-lo no layout raiz, tornando o botão visível de qualquer painel.
**Where**: `frontend/src/components/Header.tsx`
**Depends on**: T12
**Reuses**: `SyncButton` (T12) + `layout.tsx` + tema do `globals.css`
**Requirement**: SYNC-08 (botão global, desktop e mobile)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Header renderiza nome do app + `SyncButton`, responsivo (desktop e mobile)
- [x] Montado no `frontend/src/app/layout.tsx` (server component wrapper)
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): mount global header with sync button`

---

### T14: CLI de re-auth dos tokens

**What**: Criar `python -m app.garmin.login` — login interativo com credenciais/MFA que grava e protege os tokens.
**Where**: `backend/app/garmin/login.py`
**Depends on**: None
**Reuses**: `token_utils` (`get_token_path`, `secure_token_dir`), `Garmin(prompt_mfa)`
**Requirement**: SYNC-25, SYNC-26, SYNC-27
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Pede email/senha via `input`/`getpass`; MFA via prompt quando a lib sinaliza
- [x] Grava tokens no path de `GARMINTOKENS` e aplica `secure_token_dir`
- [x] Testes com `Garmin` stubado: fluxo direto, fluxo MFA, dump no path (≥ 3 novos; total ≥ 78)

**Tests**: unit (`backend/tests/test_garmin_login.py`)
**Gate**: quick
**Commit**: `feat(sync): add cli login for garmin re-auth`

---

### T15: Primeira sync real + documentação

**What**: Executar a primeira sync com tokens reais no banco de dev, validar mapeamentos contra `raw_json` e documentar o uso no README.
**Where**: `README.md`
**Depends on**: T10, T13, T14
**Reuses**: Stack do compose + suite como regressão
**Requirement**: Success Criteria (todas as caixas), SYNC-17 (calls_made auditável)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Sync real termina `done` com dados em todas as tabelas e `calls_made` registrado
- [ ] Spot-check de mapeamentos contra `raw_json` (mitigação do risco #3 do design); divergência → correção de mapper + teste de fixture
- [ ] PMC de 3 dias conferida contra cálculo manual em Python puro (Independent Test do spec)
- [ ] Segundo sync usa janela incremental (`calls_made` muito menor que o backfill)
- [ ] Logs comprovam sequência com intervalo (nenhuma chamada paralela)
- [ ] README ganha seção "Sync do Garmin": botão, primeira sync, re-auth via CLI, acesso pela LAN
- [ ] Suite completa passa: ≥ 78 testes

**Tests**: none (UAT real com evidência; o Verificador independente roda depois por contrato da skill)
**Gate**: build
**Commit**: `docs(sync): document real sync validation and usage`

---

## Phase Execution Map

```
Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6
```

Fases em sequência estrita; dentro da fase, tasks na ordem definida acima.

**How phase-based execution works:**

15 tasks → packing em lotes de fases inteiras (~7 tasks/lote): Lote 1 = Fases 1+2 (T1–T5) · Lote 2 = Fases 3+4 (T6–T10) · Lote 3 = Fases 5+6 (T11–T15). Se o usuário aceitar sub-agentes, cada lote vira um worker sequencial; senão, execução inline no chat principal, uma task por vez.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Models + constraints | 1 arquivo (entity) | ✅ Granular |
| T2: Config SYNC_* | 1 arquivo + .env.example coeso | ✅ Granular |
| T3: Compose tokens/TZ/build arg | 1 arquivo (infra) | ✅ Granular |
| T4: GarminGateway | 1 componente (1 arquivo) | ✅ Granular |
| T5: Mappers | 1 arquivo de funções puras | ✅ Granular |
| T6: Upserts | 1 arquivo (data-access) | ✅ Granular |
| T7: PMC | 1 arquivo (cálculo) | ✅ Granular |
| T8: Orquestrador | 1 componente (1 arquivo) | ✅ Granular |
| T9: Recovery no startup | 1 arquivo | ✅ Granular |
| T10: Router | 1 arquivo | ✅ Granular |
| T11: api.ts | 1 arquivo | ✅ Granular |
| T12: SyncButton | 1 componente | ✅ Granular |
| T13: Header + layout | 1 componente | ✅ Granular |
| T14: CLI login | 1 módulo | ✅ Granular |
| T15: UAT + docs | 1 entrega (validação) | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | Fase 1 sem setas | ✅ Match |
| T2 | None | Fase 1 sem setas | ✅ Match |
| T3 | None | Fase 1 sem setas | ✅ Match |
| T4 | T2 | Fase 2: `T2 -> T4` | ✅ Match |
| T5 | None | Fase 2: nó solto | ✅ Match |
| T6 | T1 | Fase 3: `T1 -> T6` | ✅ Match |
| T7 | None | Fase 3: nó solto | ✅ Match |
| T8 | T2, T4, T5, T6, T7 | Fase 4: 5 setas entrando em `T8` | ✅ Match |
| T9 | T8 | Fase 4: `T8 -> T9` | ✅ Match |
| T10 | T8 | Fase 4: `T8 -> T10` | ✅ Match |
| T11 | None | Fase 5: origem da cadeia | ✅ Match |
| T12 | T11 | Fase 5: `T11 -> T12` | ✅ Match |
| T13 | T12 | Fase 5: `T12 -> T13` | ✅ Match |
| T14 | None | Fase 6: origem | ✅ Match |
| T15 | T10, T13, T14 | Fase 6: `T10 -> T15`, `T13 -> T15`, `T14 -> T15` | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Models/schema | none | none | ✅ OK |
| T2 | Config | unit | unit | ✅ OK |
| T3 | Infra (compose) | none | none | ✅ OK |
| T4 | Gateway | unit | unit | ✅ OK |
| T5 | Domain puro | unit | unit | ✅ OK |
| T6 | Data-access | integration | integration | ✅ OK |
| T7 | Domain + data-access | integration (mais alta) | unit + integration | ✅ OK |
| T8 | Service | integration | integration | ✅ OK |
| T9 | API wiring | integration | integration | ✅ OK |
| T10 | Router | integration | integration | ✅ OK |
| T11 | Frontend | none | none | ✅ OK |
| T12 | Frontend | none | none | ✅ OK |
| T13 | Frontend | none | none | ✅ OK |
| T14 | CLI (domain) | unit | unit | ✅ OK |
| T15 | Docs/UAT | none | none | ✅ OK |
