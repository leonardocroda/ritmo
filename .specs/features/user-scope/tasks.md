# user-scope Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/user-scope/spec.md` (confirmado pelo usuário)
**Status**: Draft

---

## Test Coverage Matrix

> Gerado a partir do spec, do código existente e das diretrizes do projeto. Diretrizes encontradas: `README.md` (§Testes — suite no Postgres do compose, nada em SQLite), `backend/tests/conftest.py` (schema dropado por teste, lifespan re-semeia), `backend/pyproject.toml` (pytest, sem thresholds), `frontend/package.json` (sem test runner — lint/build apenas). Sem thresholds de cobertura configurados → strong defaults aplicados na profundidade.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Serviços de domínio (activities, health, potential, garmin, evaluation/payload) | integration | 1:1 aos ACs USR-01..16; happy path com sessão real, 401 sem sessão, 404 recurso de outro usuário, upsert sem duplicata | `backend/tests/test_{atividade}_api.py`, `backend/tests/test_{atividade}_service.py` | `uv run pytest tests/test_activities_api.py ...` (workdir `backend/`) |
| Routers de dados (activities, health, potential, sync, evaluation) | integration | Toda rota modificada: happy path com sessão, 401 sem cookie, 404 recurso alheio | `backend/tests/test_*_api.py` | `uv run pytest tests/test_*_api.py` (workdir `backend/`) |
| Test infra (conftest) | none | Fixture `session_client` + remoção do override global; nenhum comportamento muda | `backend/tests/conftest.py` | Gate full — suíte inteira verde antes e depois |
| Isolamento A×B | integration | Usuário X não lê nem escreve dados de Y em todos os endpoints de leitura + gravação | `backend/tests/test_user_isolation.py` (novo) | `uv run pytest tests/test_user_isolation.py` + full |
| Config/docs (README, .env.example) | none | - (build gate only) | - | build gate only |

## Gate Check Commands

> Pré-requisito de todo gate backend: `docker compose up -d postgres` (a suite falha rápido sem ele — padrão do repo).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após task com testes novos em arquivo(s) de domínio | `cd backend && uv run pytest tests/test_activities_api.py tests/test_health_api.py tests/test_potential_api.py tests/test_sync_api.py tests/test_evaluation_api.py tests/test_user_isolation.py` (rode só os arquivos da task) |
| Full | Após task que toca conftest/modelos/roteadores (o suite inteiro deve continuar verde) | `cd backend && uv run pytest` |
| Build+Full (final) | Última task da feature | `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Test infra — fixture de sessão real (override global mantido temporariamente)

```
T1
```

### Phase 2: Domains — serviço e roteador usam `user_id` do usuário da sessão

```
T1 → T2
T2 → T3 → T4 → T5 → T6
```

### Phase 3: Remover override global + isolamento A×B

```
T6 → T7
T7 → T8
```

---

## Task Breakdown

### T1: conftest — fixture `session_client` (sessão real por usuário)

**What**: Adicionar ao `conftest.py` uma fixture `session_client(db, user)` que cria um `User` (com email/senha) + `UserSession`, retorna um `TestClient` com o cookie de sessão setado. Manter o `dependency_overrides[require_session] = _seed_user` temporariamente (para não quebrar a suíte enquanto os domínios não são migrados). Manter `ensure_postgres_available`, `_clean_database` e `init_db` no lifespan.

**Where**: `backend/tests/conftest.py`

**Depends on**: None

**Reuses**: `User`, `UserSession`, `SessionLocal`, `TestClient`, `require_session` existentes; padrão de `test_auth_api.py` (limpar override + cookie)

**Requirement**: USR-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Fixture `session_client` disponível: recebe `user` (dict com email/senha), cria usuário+sessão, devolve TestClient com cookie `ritmo_session`
- [ ] Helper `login_client(db, email, password)` disponível (faz POST /api/auth/login e devolve client com cookie)
- [ ] Override global de `require_session` ainda presente (suíte pré-auth continua verde)
- [ ] Gate check passes: `uv run pytest` full suite — 0 falhas (override ainda mascara user 1)
- [ ] Test count: 0 novos (infra apenas); nenhuma exclusão silenciosa

**Tests**: none

**Gate**: full

**Commit**: `refactor(test): add session_client fixture for real user sessions`

---

### T2: activities — serviço e roteador usam `user_id`

**What**: `list_activities(db, user_id, activity_type, limit, offset)`, `get_activity_detail(db, activity_id, user_id, zone_config)`, `_context(db, activity, splits, user_id)` trocam `DEFAULT_USER_ID` por `user_id` em todas as queries (Activity, Split, Sleep, Hrv, Rhr). Router endpoints recebem `user: User = Depends(require_session)` e passam `user.id` ao service. Testes de activities (API + diretos) criam usuário+sessão reais via `session_client`/`login_client`; dados semeados com `user_id` do usuário de teste.

**Where**: `backend/app/activities/service.py`, `backend/app/activities/router.py`, `backend/tests/test_activities_api.py`

**Depends on**: T1

**Reuses**: padrão `require_session` → `user.id` (mesmo do auth); `ZoneConfig` inalterado (lê arquivo — `zones-db` é feature seguinte)

**Requirement**: USR-01, USR-02, USR-03, USR-06, USR-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Zero `DEFAULT_USER_ID` em queries de `activities/service.py` (apenas defaults de coluna e seed do usuário 1 no engine)
- [ ] Endpoints recebem `user` e passam `user.id` para o service
- [ ] `GET /api/activities` sem sessão → 401; com sessão do usuário X → só atividades `user_id = X`
- [ ] `GET /api/activities/{id}` de atividade de outro usuário → 404
- [ ] Testes usam `session_client`/usuário real; 0 ocorrências de `DEFAULT_USER_ID` nos testes de activities
- [ ] Gate check passes: quick (test_activities_api.py) + full suite verde
- [ ] Test count: ~0 novos (migração de testes existentes) + existentes; nenhuma exclusão silenciosa

**Tests**: integration

**Gate**: quick + full

**Commit**: `feat(user-scope): activities leitura por user_id da sessão`

---

### T3: health — serviço e roteador usam `user_id`

**What**: `_series(db, model, days, user_id)`, `_hrv_history(db, days, user_id)`, `get_health(db, days, user_id, tz)` trocam `DEFAULT_USER_ID` por `user_id` em todas as queries (Sleep, Hrv, Rhr, Stress, Activity). Router endpoint `GET /api/health/summary` recebe `user: User = Depends(require_session)` e passa `user.id`. Testes de health criam sessão real por usuário.

**Where**: `backend/app/health/service.py`, `backend/app/health/router.py`, `backend/tests/test_health_api.py`, `backend/tests/test_health.py`

**Depends on**: T2

**Reuses**: padrão T2; `calc.py` inalterado (funções puras, recebem dados já filtrados)

**Requirement**: USR-01, USR-03, USR-06, USR-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Zero `DEFAULT_USER_ID` em queries de `health/service.py`
- [ ] Endpoint `GET /api/health/summary` recebe `user` e passa `user.id`
- [ ] Blocos sono/HRV/RHR/estresse/dose-response/lifestyle montam a partir de `user_id = X`
- [ ] Testes usam usuário real; 0 `DEFAULT_USER_ID` nos testes de health
- [ ] Gate check passes: quick (test_health_api.py, test_health.py) + full suite verde
- [ ] Test count: ~0 novos (migração) + existentes

**Tests**: integration

**Gate**: quick + full

**Commit**: `feat(user-scope): health leitura por user_id da sessão`

---

### T4: potential — serviço e roteador usam `user_id`

**What**: `_garmin_by_event(db, user_id)`, `_pmc_block(db, user_id)`, `get_potential(db, user_id, calibration)` trocam `DEFAULT_USER_ID` por `user_id` em todas as queries (RacePrediction, DailyLoad, PersonalRecord, Activity). Router endpoint `GET /api/potential` recebe `user: User = Depends(require_session)` e passa `user.id`. Testes de potential criam sessão real por usuário.

**Where**: `backend/app/potential/service.py`, `backend/app/potential/router.py`, `backend/tests/test_potential_api.py`, `backend/tests/test_potential_calc.py`

**Depends on**: T3

**Reuses**: padrão T2/T3; `calc.py`/`calibration.py` inalterados (puro, recebem dados já filtrados)

**Requirement**: USR-01, USR-04, USR-06, USR-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Zero `DEFAULT_USER_ID` em queries de `potential/service.py`
- [ ] Endpoint `GET /api/potential` recebe `user` e passa `user.id`
- [ ] VDOT, predições, PMC, decaimento a partir de `user_id = X`
- [ ] Testes usam usuário real; 0 `DEFAULT_USER_ID` nos testes de potential
- [ ] Gate check passes: quick (test_potential_api.py) + full suite verde
- [ ] Test count: ~0 novos (migração) + existentes

**Tests**: integration

**Gate**: quick + full

**Commit**: `feat(user-scope): potential leitura por user_id da sessão`

---

### T5: garmin — serviço e roteador usam `user_id`

**What**: `create_job(db, user_id)` perde o default `DEFAULT_USER_ID` (parâmetro obrigatório). Queries de `SyncJob`, `SyncState` no router e service usam `user_id`. Router `POST /api/sync` e `GET /api/sync/jobs/latest` recebem `user` e passam `user.id`. `run_sync(job_id)` grava upserts com `user_id` do job. Testes de garmin (service + API) criam sessão real por usuário e passam `user_id` explicitamente em chamadas diretas ao service.

**Where**: `backend/app/garmin/service.py`, `backend/app/garmin/router.py`, `backend/tests/test_garmin_service.py`, `backend/tests/test_sync_api.py`, `backend/tests/test_garmin_upserts.py`

**Depends on**: T4

**Reuses**: padrão T2; lock de um job ativo por usuário (índice parcial existente em `sync_jobs`) segue válido

**Requirement**: USR-05, USR-09, USR-10, USR-13, USR-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `create_job(db, user_id)` — `user_id` obrigatório, sem default
- [ ] Zero `DEFAULT_USER_ID` em queries de `garmin/service.py` e `garmin/router.py`
- [ ] Endpoints sync recebem `user` e passam `user.id`
- [ ] Upserts de sync gravam com `user_id` do usuário da sessão
- [ ] Testes passam `user_id` explicitamente em chamadas diretas; 0 `DEFAULT_USER_ID` nos testes de garmin/sync
- [ ] Gate check passes: quick (test_garmin_service.py, test_sync_api.py) + full suite verde
- [ ] Test count: ~0 novos (migração) + existentes

**Tests**: integration

**Gate**: quick + full

**Commit**: `feat(user-scope): garmin sync por user_id da sessão`

---

### T6: evaluation — serviço, payload e roteador usam `user_id`

**What**: Consultas de `Activity` e `Evaluation` em `evaluation/service.py` (list_evaluations, get_activity_detail via evaluation, criação de avaliação) e `evaluation/payload.py` (DailyLoad, PersonalRecord, Pattern) trocam `DEFAULT_USER_ID` por `user_id`. Router endpoints de evaluation recebem `user` e passam `user.id`. Criação de avaliação grava `Evaluation.user_id = X` e vincula apenas a atividades com `user_id = X`. Testes de evaluation criam sessão real por usuário.

**Where**: `backend/app/evaluation/service.py`, `backend/app/evaluation/payload.py`, `backend/app/evaluation/router.py`, `backend/tests/test_evaluation_api.py`, `backend/tests/test_evaluation_service.py`, `backend/tests/test_evaluation_payload.py`

**Depends on**: T5

**Reuses**: padrão T2; `list_evaluations` já é reusado por `get_activity_detail` (EVAL-17) — uma única implementação

**Requirement**: USR-08, USR-11, USR-12, USR-15, USR-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Zero `DEFAULT_USER_ID` em queries de `evaluation/service.py` e `evaluation/payload.py`
- [ ] Endpoints de evaluation recebem `user` e passam `user.id`
- [ ] Criação de avaliação grava `user_id = X`; usuário Y não avalia atividade de X (404)
- [ ] Testes usam usuário real; 0 `DEFAULT_USER_ID` nos testes de evaluation
- [ ] Gate check passes: quick (test_evaluation_api.py, test_evaluation_service.py, test_evaluation_payload.py) + full suite verde
- [ ] Test count: ~0 novos (migração) + existentes

**Tests**: integration

**Gate**: quick + full

**Commit**: `feat(user-scope): evaluation por user_id da sessão`

---

### T7: conftest — remover override global de `require_session`

**What**: Remover `fastapi_app.dependency_overrides[require_session] = _seed_user` do conftest. Agora todo teste de dados deve criar sua própria sessão (via `session_client`/`login_client` de T1). A suíte inteira deve continuar verde porque todos os domínios (T2-T6) já usam sessões reais.

**Where**: `backend/tests/conftest.py`

**Depends on**: T6

**Reuses**: `session_client`/`login_client` criados na T1; `test_auth_api.py` já limpa o override por teste (padrão a seguir)

**Requirement**: USR-17, USR-18

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sem `dependency_overrides[require_session]` no conftest
- [ ] Todo teste de dados usa sessão real (usuário criado + login + cookie)
- [ ] Gate check passes: `uv run pytest` full suite — 100% verde (nenhum teste depende mais do override de user 1)
- [ ] Test count: 0 novos (remoção apenas); nenhuma exclusão silenciosa

**Tests**: none

**Gate**: full

**Commit**: `refactor(test): remove global session override — todos os testes usam sessão real`

---

### T8: teste de isolamento A×B (novo arquivo)

**What**: Criar `backend/tests/test_user_isolation.py` com testes de ponta a ponta: usuário X e usuário Y, cada um com sessão própria, atividades/sono/HRV/carga/avaliações separadas. Verificar que X não lê dados de Y e Y não lê dados de X em `GET /api/activities`, `GET /api/activities/{id}`, `GET /api/health/summary`, `GET /api/potential`, `GET /api/sync/jobs/latest`; e que X não grava sobre dados de Y (sync cria job com `user_id = X`, avaliação vincula `user_id = X`). Incluir edge cases: 401 sem sessão, 404 recurso alheio.

**Where**: `backend/tests/test_user_isolation.py` (novo)

**Depends on**: T7

**Reuses**: `session_client`/`login_client` do conftest (T1); padrões de seed dos testes de activities/health/potential

**Requirement**: USR-08, USR-09, USR-10, USR-11, USR-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Usuário X e Y com sessões separadas; cada um insere dados próprios
- [ ] `GET /api/activities` na sessão de X retorna só atividades de X; na de Y, só de Y
- [ ] `GET /api/activities/{id_Y}` na sessão de X → 404; vice-versa
- [ ] `GET /api/health/summary` e `GET /api/potential` de X não contêm dados de Y
- [ ] `POST /api/sync` na sessão de X cria `SyncJob.user_id = X`; upserts com `user_id = X`
- [ ] `POST /api/evaluation` na sessão de X para atividade de X → `Evaluation.user_id = X`; para atividade de Y → 404
- [ ] Sem sessão → 401 em todos os endpoints de dados
- [ ] Gate check passes: `uv run pytest tests/test_user_isolation.py` + full suite verde
- [ ] Test count: ~8-12 novos (isolamento) + existentes

**Tests**: integration

**Gate**: quick + full

**Commit**: `feat(user-scope): teste de isolamento A×B entre usuários`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1

Phase 2:  T2 → T3 → T4 → T5 → T6

Phase 3:  T7 → T8
```

Arestas cross-phase (backward, permitidas): T1 → T2 (T2 depende de T1), T6 → T7 (T7 depende de T6). Dentro de uma fase a execução é sequencial.

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Batch sizing:** 8 tasks total, 3 phases → fits a single batch (≤ ~8 tasks). Execute inline, no sub-agent delegation required.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: conftest fixture | 1 arquivo (conftest.py) | ✅ Granular |
| T2: activities service+router+tests | 1 domínio (2 src + 1 test) | ✅ Granular |
| T3: health service+router+tests | 1 domínio (2 src + 2 test) | ✅ Granular |
| T4: potential service+router+tests | 1 domínio (2 src + 2 test) | ✅ Granular |
| T5: garmin service+router+tests | 1 domínio (2 src + 3 test) | ✅ Granular |
| T6: evaluation service+payload+router+tests | 1 domínio (3 src + 3 test) | ✅ Granular |
| T7: conftest remover override | 1 arquivo (conftest.py) | ✅ Granular |
| T8: isolamento A×B | 1 arquivo de teste novo | ✅ Granular |

**Granularity check**: ✅ 1 domínio por tarefa (T2-T6 coesivos: service+router+testes do mesmo domínio); T1/T7/T8 infra/isolamento isolados.

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | raiz da Phase 1 | ✅ Match |
| T2 | T1 | T2 ──→ T3 (início da Phase 2) | ✅ Match |
| T3 | T2 | T3 depois de T2 | ✅ Match |
| T4 | T3 | T4 depois de T3 | ✅ Match |
| T5 | T4 | T5 depois de T4 | ✅ Match |
| T6 | T5 | T6 depois de T5 | ✅ Match |
| T7 | T6 | T7 depois de T6 (início da Phase 3) | ✅ Match |
| T8 | T7 | T8 depois de T7 | ✅ Match |

**Rules:**
- Every `Depends on` in a task body has a corresponding arrow in the diagram. ✅
- Every arrow in the diagram corresponds to a `Depends on` in the target task's body. ✅
- No task depends on a task in a later phase. ✅

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Test infra (conftest) | none | none | ✅ OK |
| T2 | Serviço+router+testes activities | integration | integration | ✅ OK |
| T3 | Serviço+router+testes health | integration | integration | ✅ OK |
| T4 | Serviço+router+testes potential | integration | integration | ✅ OK |
| T5 | Serviço+router+testes garmin/sync | integration | integration | ✅ OK |
| T6 | Serviço+payload+router+testes evaluation | integration | integration | ✅ OK |
| T7 | Test infra (conftest) | none | none | ✅ OK |
| T8 | Isolamento A×B (novo teste) | integration | integration | ✅ OK |

**Rules:**
- "Tested in another task" is NOT a valid justification for `Tests: none`. ✅ (none only where matrix says none)
- `Tests: none` is only valid when the coverage matrix says "none" for that code layer. ✅
- If a task creates MULTIPLE code layers, use the HIGHEST test type required. ✅ (all integration where tests exist)

---

## Status

| Task | Status | Commit |
| ---- | ------ | ------ |
| T1 | ✅ Complete | refactor(test): add session_client fixture for real user sessions |
| T2 | ✅ Complete | feat(user-scope): activities reads by session user_id |
| T3 | ✅ Complete | feat(user-scope): health reads by session user_id |
| T4 | ✅ Complete | feat(user-scope): potential reads by session user_id |
| T5 | Pending | - |
| T6 | Pending | - |
| T7 | Pending | - |
| T8 | Pending | - |
