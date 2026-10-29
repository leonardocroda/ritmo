# Running dynamics por tênis — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tenis-running-dynamics/design.md`
**Spec**: `.specs/features/tenis-running-dynamics/spec.md`
**Context**: `.specs/features/tenis-running-dynamics/context.md`
**Status**: Draft

---

## Test Coverage Matrix

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Migration (schema idempotent) | integration | Base nova + base velha; re-run não duplica colunas | `backend/tests/test_splits_running_dynamics_migration.py` | `uv run pytest tests/test_splits_running_dynamics_migration.py -q` |
| Mapper (funções puras) | unit | 1:1 com ACs; métrica presente/ausente/lapDTO vazio | `backend/tests/test_splits_running_dynamics_mapper.py` | `uv run pytest tests/test_splits_running_dynamics_mapper.py -q` |
| Client Garmin (typed splits) | unit | httpx MockTransport; com/sem lapDTOs; 429 backoff | `backend/tests/test_splits_running_dynamics_client.py` | `uv run pytest tests/test_splits_running_dynamics_client.py -q` |
| Backfill CLI (orquestração) | integration | Happy + idempotência + atividade inexistente + só running; Strava falso injetado | `backend/tests/test_splits_running_dynamics_backfill.py` | `uv run pytest tests/test_splits_running_dynamics_backfill.py -q` |
| Router detail (SplitOut) | integration | GET detail expõe 4 campos RD; null quando ausente; isolamento A×B | `backend/tests/test_splits_running_dynamics_api.py` | `uv run pytest` (no `backend/`) |

---

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com testes unit pontuais | `cd backend && uv run pytest tests/test_<arquivo> -q` (Postgres do compose de pé) |
| Full | Tasks com testes de API/integration | `cd backend && uv run pytest` |
| Build | Fim de fase | `cd backend && uv run pytest` (+ `cd frontend && npm run build` se houver frontend) |

---

## Execution Plan

Phases are ordered and run sequentially.

```
T1 → T4
T2 → T4
T3 → T4
T1 → T5
T1 → T6
T2 → T6
T3 → T6
T4 → T6
T5 → T6
```

---

## Task Breakdown

### T1: Migração da Split — 4 colunas de running dynamics (nullable)

**What**: Adicionar `ground_contact_time_ms` (Integer), `stride_length_cm` (Float), `vertical_oscillation_cm` (Float), `vertical_ratio` (Float) à tabela `splits`, todas nullable, mantendo `uq_split_activity_idx`. Refatorar `_migrate_schema()` com bloco condicional `_migrate_splits_running_dynamics()` (sem early-return bloqueante — lição tenis T1).

**Where**: `backend/app/db/models.py`, `backend/app/db/engine.py`

**Depends on**: None

**Reuses**: padrão de migração do tenis (T1); espírito AD-019 (idempotente, zero deps)

**Requirement**: TRD-01, TRD-03

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `Split` com as 4 colunas nullable; `uq_split_activity_idx` intacto
- [x] `_migrate_schema` tem `_migrate_splits_running_dynamics()` condicional à existência das colunas
- [x] `init_db()` idempotente: re-run em base nova e em base velha não duplica colunas
- [x] Gate: quick (`uv run pytest tests/test_splits_running_dynamics_migration.py -q`) — Test count: 5

**Tests**: integration
**Gate**: quick
**Commit**: `feat(splits): 4 colunas de running dynamics (nullable) com migração idempotente`

---

### T2: Mapper enriquecido de splits (running dynamics do lapDTO)

**What**: `map_splits` em `app/garmin/mappers.py` extrai `groundContactTime`→`gct_ms`, `strideLength`→`stride_cm`, `verticalOscillation`→`vert_osc_cm`, `verticalRatio`→`vert_ratio` de cada `lapDTO`. Campo ausente → None; `lapDTO` None/vazio → `[]`.

**Where**: `backend/app/garmin/mappers.py`

**Depends on**: None

**Reuses**: estilo de mappers puros de `app/garmin/mappers.py` (sem DB, 100% testável)

**Requirement**: TRD-04, TRD-05, TRD-06

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `map_splits` com lapDTO contendo as 4 métricas devolve as 4 chaves com valores
- [x] Campo ausente no lapDTO → chave None (não falha)
- [x] `lapDTO` None/vazio → `[]` sem warning
- [x] Gate: quick (`uv run pytest tests/test_splits_running_dynamics_mapper.py -q`) — Test count: 8

**Tests**: unit
**Gate**: quick
**Commit**: `feat(garmin): map_splits extrai running dynamics do lapDTO (ausente = None)`

---

### T3: Método typed splits no client Garmin

**What**: `GarminGateway.get_activity_splits_typed(activity_id)` retorna lapDTOs completos de uma atividade via `connectapi`/`get_activity_splits`, contando 1 chamada no orçamento (`_call`) com backoff (2,4,8). Atividade sem splits → vazio/sem erro.

**Where**: `backend/app/garmin/client.py`

**Depends on**: None

**Reuses**: padrão `_call` de `GarminGateway` (orçamento + backoff); seam `http` injetável para teste

**Requirement**: TRD-07, TRD-08, TRD-09

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `get_activity_splits_typed` retorna payload com `lapDTOs` (incluindo running dynamics)
- [x] Conta 1 chamada no orçamento; 429/5xx → backoff (2,4,8) ×3, depois erro de domínio
- [x] Atividade sem splits → lista vazia/None sem erro
- [x] Token nunca gravado em banco ou log
- [x] Gate: quick (`uv run pytest tests/test_splits_running_dynamics_client.py -q`) — Test count: 8

**Tests**: unit
**Gate**: quick
**Commit**: `feat(garmin): typed splits de uma atividade com orçamento de chamadas`

---

### T4: Backfill por atividade sob demanda (CLI)

**What**: CLI `python -m app.strava.backfill_activity --activity-id X --user-id 1 [--yes]`: busca typed splits do Garmin, upsert nas linhas de `Split` por `(activity_id, idx)` preenchendo as 4 colunas, commit único no fim. Idempotente. Atividade inexistente → erro claro, sem gravação. Apenas `running`/`trail_running`.

**Where**: `backend/app/strava/backfill_activity.py` (novo módulo)

**Depends on**: T1, T2, T3

**Reuses**: padrão CLI de `app/garmin/import_tokens.py` (argparse + `SessionLocal()` + exceção de domínio + `sys.exit(1)`); funções de T2/T3; modelo de T1

**Requirement**: TRD-10, TRD-11, TRD-12, TRD-13

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Enriquece splits existentes com as 4 colunas de running dynamics
- [x] Re-run não duplica splits (idempotente por upsert `activity_id` + `idx`)
- [x] Atividade inexistente → erro claro, sem gravação
- [x] Apenas running/trail_running enriquecidos (ou pula silenciosamente outras)
- [x] Commit único no fim; abort = estado consistente
- [x] Gate: full (`uv run pytest`) — Test count: 10 (Strava falso injetado)

**Tests**: integration
**Gate**: full
**Commit**: `feat(strava): backfill por atividade sob demanda com running dynamics`

---

### T5: Expor running dynamics no detail da atividade (SplitOut)

**What**: `SplitOut` em `app/activities/router.py` ganha `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio` (todos opcionais). `get_activity_detail` passa os novos campos de cada split. Sem dado → campos null (split não omitido).

**Where**: `backend/app/activities/router.py`, `backend/app/activities/service.py`

**Depends on**: T1

**Reuses**: padrão de `ActivityDetailOut`/`SplitOut` existente; `app.shoes` (modelo Split)

**Requirement**: TRD-14, TRD-15

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `GET /api/activities/{id}` detail expõe `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio` por split
- [x] Sem running dynamics → campos null (split continua presente)
- [x] 404 para atividade inexistente; 401 sem sessão; isolamento A×B
- [x] Gate: full (`uv run pytest`) — Test count: 8

**Tests**: integration
**Gate**: full
**Commit**: `feat(activities): SplitOut expõe running dynamics no detail da atividade`

---

### T6: Validação final e fechamento da feature B

**What**: Rodar suíte completa de backend, confirmar que todos os testes de T1-T5 passam, verificar que não há regressão nos testes existentes do tenis (km derivada, associação, backfill Strava), e fechar a feature B.

**Where**: `backend/tests/` (suite completa)

**Depends on**: T1, T2, T3, T4, T5

**Reuses**: suíte existente (`uv run pytest`)

**Requirement**: Todas TRD-01 a TRD-15

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `uv run pytest` (backend completo) passa, incluindo testes de T1-T5 e existentes
- [x] Nenhuma regressão no tenis (km derivada, associação, backfill Strava)
- [x] Gate: full (`uv run pytest`)
- [x] Commit: `feat(running-dynamics): feature B completa — migração, mapper, client, backfill, detail`

**Tests**: integration (suite completa)
**Gate**: full
**Commit**: `feat(running-dynamics): feature B completa — validação final`

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | (nenhuma entrada — sem setas incidentes) | ✅ Match |
| T2 | None | (nenhuma entrada) | ✅ Match |
| T3 | None | (nenhuma entrada) | ✅ Match |
| T4 | T1, T2, T3 | CLI → client → mapper → Split | ✅ Match |
| T5 | T1 | SplitOut expõe 4 campos | ✅ Match |
| T6 | T1-T5 | (validação final, sem setas) | ✅ Match |

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Migração Split | 1 entrega coesa (schema + migração) | ✅ Granular |
| T2: Mapper | 1 função pura (extração) | ✅ Granular |
| T3: Client Garmin | 1 método (typed splits) | ✅ Granular |
| T4: Backfill CLI | 1 CLI (orquestração) | ✅ Granular |
| T5: Router detail | 1 schema + 1 campo no service | ✅ Granular |
| T6: Validação final | 1 suíte completa | ✅ Granular |

Total: 6 tasks — cabe em um único batch (≤ ~8), execução inline sem sub-agentes.
