# Tênis no Ritmo — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tenis/design.md`
**Spec**: `.specs/features/tenis/spec.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` (seção Testes: suite roda 100% no Postgres do compose, `uv run pytest`, nada em SQLite); docs-site `docs/backend/` (padrões de teste por domínio). Sem `AGENTS.md`/`CONTRIBUTING.md` no repo. Frontend não tem suite JS — gate é o build.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Service / funções puras (shoes service, strava matching, strava client) | unit | 1:1 com as ACs da spec; todo edge case listado tem teste | `backend/tests/test_*.py` | `uv run pytest tests/<arquivo> -q` (no `backend/`) |
| API router (TestClient + Postgres real) | integration | Todas as rotas: happy + edge + 401 + isolamento A×B | `backend/tests/test_*_api.py` | `uv run pytest` (no `backend/`) |
| Migração de schema (idempotência) | integration | Base nova + base velha emendada; re-run não duplica | `backend/tests/test_*_models.py` | `uv run pytest tests/<arquivo> -q` |
| CLI backfill (orquestração) | integration | Happy + idempotência + abort consistente + checksum; client Strava falso injetado | `backend/tests/test_strava_backfill.py` | `uv run pytest tests/test_strava_backfill.py -q` |
| Frontend (components) | none | - (sem suite JS no projeto) | - | gate `npm run build` (no `frontend/`) |
| Docs | none | - | - | build gate only |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com testes unit pontuais | `cd backend && uv run pytest tests/<arquivo> -q` (Postgres do compose de pé) |
| Full | Tasks com testes de API/integration | `cd backend && uv run pytest` |
| Build | Fim de fase, tasks de frontend, fechamento | `cd backend && uv run pytest` + `cd frontend && npm run build` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend estrutura

Fundação: modelo, migração e CRUD — o que o backfill e a UI consomem.

```
T1 → T2 → T3
```

### Phase 2: Backfill Strava

Domínio novo: client httpx, matching puro e o CLI one-shot.

```
T4 → T6
T5 → T6
T3 → T6
```

### Phase 3: Frontend gestão

Seção Tênis na página Treinos.

```
T2 → T7
T3 → T7
T7 → T8
```

### Phase 4: Frontend modal

Atribuição pós-atividade no detalhe.

```
T2 → T9
T9 → T10
T3 → T10
```

### Phase 5: Docs

Doc técnica no docs-site.

```
T10 → T11
```

---

## Task Breakdown

### T1: Modelo Shoe + coluna shoe_id + migração idempotente

**What**: Cria `class Shoe` no ORM, adiciona `Activity.shoe_id` (FK `ondelete="SET NULL"`, index) e refatora `_migrate_schema()` em blocos independentes por tabela — o early-return atual de `users` bloquearia a emenda nova.
**Where**: `backend/app/db/models.py`
**Depends on**: None
**Reuses**: padrão `Race`/`Sleep` (`UniqueConstraint` nomeado `uq_shoe_user_strava`); espírito AD-019 do `_migrate_schema` existente; teste no estilo de `test_auth_models.py` (DROP COLUMN → init_db → coluna volta)
**Requirement**: TEN-01

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `Shoe` com todas as colunas do design; `uq_shoe_user_strava`; `created_at` default `_utcnow`
- [x] `Activity.shoe_id` nullable, FK `shoes.id` com `ondelete="SET NULL"`, index
- [x] `_migrate_schema` refatorado em `_migrate_users_columns()` (comportamento preservado) + `_migrate_activities_shoe_id()`, cada bloco condicional ao próprio objeto
- [x] `init_db()` idempotente: re-run em base nova e em base velha não duplica
- [x] Gate: quick (`uv run pytest tests/test_shoes_migration.py -q`) — Test count: 7

**Tests**: integration
**Gate**: quick
**Commit**: `feat(shoes): modelo Shoe + coluna shoe_id em activities com migração idempotente`

---

### T2: CRUD de tênis (service + router + registro)

**What**: `shoes/service.py` (`list_shoes` com km derivada em query agregada única, `create_shoe`, `update_shoe`) e `shoes/router.py` (`GET ""`, `POST ""`, `PATCH "/{shoe_id}"`, schemas pydantic inline), registrado no `main.py`; resposta em envelope `{items: [...], attribution_30d_pct: null}` (campo calculado só na T8).
**Where**: `backend/app/shoes/router.py`
**Depends on**: T1
**Reuses**: padrão de router/service de `app/profile` e `app/activities`; `require_session`/`get_db`; isolamento textual do projeto ("tênis não encontrado")
**Requirement**: TEN-02, TEN-03, TEN-04, TEN-05, TEN-06

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] `GET /api/shoes` devolve `current_km = initial_km + Σ distance_m`, `run_count`, `last_use`, `life_pct` (null sem `max_km`), ordenado: ativos primeiro, `last_use` desc
- [ ] `POST` cria com status "ativo" default; `user_id` explícito (nunca o default do modelo)
- [ ] `PATCH` edita campos e status; sem rota de DELETE (405 se chamada)
- [ ] 422: nome vazio, `initial_km < 0`, status inválido; 404: tênis de outro usuário; 401: sem sessão
- [ ] Gate: full (`uv run pytest`) — Test count: ≥ 12

**Tests**: integration
**Gate**: full
**Commit**: `feat(shoes): CRUD de tênis na API com km derivada agregada`

---

### T3: Associação de tênis por atividade

**What**: `shoes/service.associate()` (valida atividade do usuário em `RUNNING_TYPES` + posse do tênis; `AssociationError` com code → 404/422), rota `PATCH /api/activities/{id}/shoe` e campo `shoe` (resumo) no `get_activity_detail` — o gatilho do modal.
**Where**: `backend/app/activities/router.py`
**Depends on**: T2
**Reuses**: `RUNNING_TYPES` de `app.garmin.mappers`; padrão de exceção de domínio de `profile/service.py` (service não commita — quem commita é o endpoint)
**Requirement**: TEN-21, TEN-22

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] `PATCH /api/activities/{id}/shoe` com `{"shoe_id": int | null}` associa e responde `{shoe: ShoeSummary | None}`; desassociação com null funciona
- [ ] 422 em atividade não-corrida; 404 em atividade/tênis de outro usuário; 401 sem sessão
- [ ] `GET /api/activities/{id}` detail expõe `shoe: {id, name, brand, model, status} | null`
- [ ] Gate: full (`uv run pytest`) — Test count: ≥ 8 (neste arquivo)

**Tests**: integration
**Gate**: full
**Commit**: `feat(shoes): associação de tênis por atividade e campo shoe no detail`

---

### T4: Cliente Strava (httpx) com backoff

**What**: `core/config.py` ganha `STRAVA_CLIENT_ID`/`STRAVA_CLIENT_SECRET`; `app/strava/client.py` com `exchange_code`, `fetch_athlete_shoes`, `fetch_run_activities` (paginação até vazio, `per_page=200`, filtra `type == "Run"`), backoff `(2, 4, 8)` em 429/5xx com 3 tentativas; seam `http` injetável para testes (httpx MockTransport).
**Where**: `backend/app/strava/client.py`
**Depends on**: None
**Reuses**: espírito de retry de `app/garmin/client.py::_call`; `httpx` (já dependência direta)
**Requirement**: TEN-09

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] `exchange_code` troca code por token via POST oauth; `fetch_*` autenticam via header Bearer
- [ ] Paginação para em página vazia; filtro `type == "Run"` no cliente
- [ ] 429/5xx → backoff (2, 4, 8) e até 3 tentativas, depois erro de domínio com o que faltou buscar
- [ ] Token nunca é gravado em banco ou log
- [ ] Gate: quick (`uv run pytest tests/test_strava_client.py -q`) — Test count: ≥ 5

**Tests**: unit
**Gate**: quick
**Commit**: `feat(strava): cliente Strava com backoff para o backfill one-shot`

---

### T5: Matching Strava↔Garmin (funções puras)

**What**: `app/strava/matching.py`: `garmin_id_from_external_id` (regex `^garmin_push_(\d+)$`), `find_match` (fallback: `|Δdistance| ≤ 2%` e `|Δmoving_time| ≤ 2%` e `|Δstart| ≤ 5h`; 0 ou 2+ candidatos → não casa; ambiguidade é resultado explícito, nunca inventa).
**Where**: `backend/app/strava/matching.py`
**Depends on**: None
**Reuses**: estilo de mappers puros de `app/garmin/mappers.py` (sem DB, 100% testável)
**Requirement**: TEN-23, TEN-24, TEN-25

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] `garmin_id_from_external_id` casa `garmin_push_<id>` e devolve o id como string; None para outros formatos/ausente
- [ ] `find_match` casa dentro das tolerâncias (±2%, ±2%, 5h); 2+ candidatos → `"ambiguous"`; 0 → None
- [ ] Distância 0 (esteira sem GPS) não casa por distância
- [ ] Gate: quick (`uv run pytest tests/test_strava_matching.py -q`) — Test count: ≥ 8

**Tests**: unit
**Gate**: quick
**Commit**: `feat(strava): matching Strava-Garmin via external_id com fallback heurístico`

---

### T6: Backfill CLI one-shot com decomposição e checksum

**What**: `app/strava/backfill.py` no padrão CLI de `import_tokens.py`: `--code` XOR `--token`, `--user-id` (default 1), `--yes`; preview + confirmação; upsert por `strava_gear_id`; associação retroativa via matching; `initial_km = max(0, km_strava − Σ casadas)`; commit único no fim; relatório com criados/atualizados, casadas/sem match/sem gear_id e checksum por tênis. Docstring com o passo-a-passo do OAuth manual (app em strava.com/settings/api, escopos `profile:read_all,activity:read_all`, URL de autorização).
**Where**: `backend/app/strava/backfill.py`
**Depends on**: T3, T4, T5
**Reuses**: padrão CLI de `app/garmin/import_tokens.py` (argparse + `SessionLocal()` + exceção de domínio + `sys.exit(1)`); funções de T4/T5; modelo de T1
**Requirement**: TEN-07, TEN-08, TEN-10, TEN-11, TEN-12, TEN-26, TEN-27

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] Execução cria/atualiza cada tênis do Strava com km derivada = `distance` do gear (±0,1 km)
- [ ] Corrida com `gear_id` + match → associação retroativa; sem `gear_id` → fica null e entra no relatório como não alocada
- [ ] Ambíguas e sem match ficam null e listadas; nenhuma associação inventada
- [ ] Re-run não duplica tênis nem associações (idempotente)
- [ ] Token inválido/expirado aborta antes de qualquer escrita; erro 429/5xx persistente aborta com estado consistente (commit único)
- [ ] Relatório final imprime checksum: `initial_km + Σ casadas + não alocada = total Strava` por tênis
- [ ] Gate: full (`uv run pytest`) — Test count: ≥ 8 (neste arquivo; client Strava falso injetado)

**Tests**: integration
**Gate**: full
**Commit**: `feat(strava): backfill one-shot por CLI com decomposição histórica e checksum`

---

### T7: Seção Tênis na página Treinos

**What**: `lib/api.ts` ganha types (`Shoe`, `ShoeCreate`, `ShoeUpdate`, `ShoeSummary`) e funções (`getShoes`, `createShoe`, `updateShoe`); `ShoesSection.tsx` (PanelState loading/error/empty/ready) com grid de cards, barra de vida (marcos 75%/90%), form inline de criar/editar (sugere `max_km = 800` na criação), montada no fim de `treinos/page.tsx`.
**Where**: `frontend/src/components/workouts/ShoesSection.tsx`
**Depends on**: T2, T3
**Reuses**: `apiFetch`/`parseError` de `lib/api.ts`; padrão PanelState de `HomePanel.tsx`; `PanelSection.tsx`, `Skeleton.tsx`; `formatKm`/`formatDateTime` de `lib/format.ts`
**Requirement**: TEN-13, TEN-14, TEN-16

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] Cards com nome, marca/modelo, km atual vs `max_km` (barra com marcos 75/90%), status, último uso, contagem de corridas
- [ ] Criar/editar inline com os campos do design; criação sugere 800 km
- [ ] Estado vazio com atalho para cadastro; loading com Skeleton; erro com card textual do padrão
- [ ] `ActivityDetail` type ganha `shoe: ShoeSummary | null`
- [ ] Gate: build (`cd frontend && npm run build`)

**Tests**: none (frontend sem suite — build gate)
**Gate**: build
**Commit**: `feat(treinos): seção Tênis com barra de vida e CRUD`

---

### T8: Aposentar com confirmação + badge de higiene

**What**: Aposentadoria de tênis com `confirm()` explícito na `ShoesSection`; `shoes/service.list_shoes` calcula `attribution_30d_pct` (corridas dos últimos 30 dias com tênis / total de corridas dos últimos 30 dias; null sem corridas) e o card exibe o badge.
**Where**: `frontend/src/components/workouts/ShoesSection.tsx`
**Depends on**: T7
**Reuses**: envelope de resposta da T2 (`attribution_30d_pct` já presente como null); padrão de confirmação do projeto (não há action destructiva sem confirm)
**Requirement**: TEN-15, TEN-28

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] Aposentar pede confirmação; após confirmar, o tênis permanece listável (status "aposentado") e sai das sugestões
- [ ] `GET /api/shoes` responde `attribution_30d_pct` correto (com e sem corridas na janela) — backend testado
- [ ] Badge visível na seção
- [ ] Gate: full (`uv run pytest` + `cd frontend && npm run build`) — Test count backend: ≥ 2 (novos)

**Tests**: integration
**Gate**: full
**Commit**: `feat(treinos): aposentar tênis com confirmação e badge de higiene`

---

### T9: Modal de seleção de tênis

**What**: `ShoePickerModal.tsx` novo (overlay `fixed inset-0 z-50` + `backdrop-blur`, linguagem visual do TabBar): lista ordenada por padrão-do-tipo (`localStorage["shoe-default-by-type"][inferredType]`) e depois `last_use` desc; ações: escolher, "Definir como padrão para [tipo]", "Agora não"; aposentados em seção separada.
**Where**: `frontend/src/components/workouts/ShoePickerModal.tsx`
**Depends on**: T2
**Reuses**: `getShoes` (data já traz `last_use`/`status`); pills/cards do sistema v0.3; sem biblioteca de modal (não existe reutilizável — criar do zero)
**Requirement**: TEN-18, TEN-19

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] Modal renderiza sobre overlay com blur; fecha ao escolher, ao dispensar e ao clicar fora
- [ ] Ordenação: padrão do tipo primeiro, depois último uso; aposentados em bloco separado e visíveis
- [ ] "Definir como padrão para [tipo]" grava no localStorage e afeta a próxima ordenação
- [ ] Props: `activityId`, `inferredType`, `onAssigned(shoe)`, `onDismiss`
- [ ] Gate: build (`cd frontend && npm run build`)

**Tests**: none (frontend sem suite — build gate)
**Gate**: build
**Commit**: `feat(treinos): modal de seleção de tênis`

---

### T10: Gatilho do modal no detalhe de corrida

**What**: `WorkoutDetail.tsx`: quando `detail.shoe == null` e a atividade é corrida, renderiza `ShoePickerModal` no máximo 1× por visita (`useRef` guarda dispensa); após associar via `setActivityShoe`, refetch do detail e badge `shoe.name` no header; o modal nunca abre para não-corridas.
**Where**: `frontend/src/components/workouts/WorkoutDetail.tsx`
**Depends on**: T3, T9
**Reuses**: `setActivityShoe` (nova em `lib/api.ts`, espelhando as demais); padrão de refetch com flag `cancelled` do próprio WorkoutDetail
**Requirement**: TEN-17, TEN-19, TEN-20

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] Abrir corrida sem tênis → modal 1×; dispensar → não reabre na mesma visita; navegar de volta e abrir de novo → pergunta de novo
- [ ] Confirmar sugestão em um toque associa; badge com o nome do tênis aparece no header do detalhe
- [ ] Não-corridas nunca disparam o modal
- [ ] Gate: build (`cd frontend && npm run build`)

**Tests**: none (frontend sem suite — build gate)
**Gate**: build
**Commit**: `feat(treinos): gatilho do modal no detalhe de corrida sem tênis`

---

### T11: Doc técnica no docs-site

**What**: Novo `docs/backend/tenis.md` (API de tênis, modelo, km derivada, passo-a-passo do OAuth manual + CLI backfill com o relatório e o checksum) e atualização de `docs/backend/banco-de-dados.md` (tabela `shoes`, coluna `activities.shoe_id`) + `mkdocs.yml` no nav.
**Where**: `docs-site/docs/backend/tenis.md`
**Depends on**: T10
**Reuses**: formato das docs existentes (`garmin-sync.md`, `auth.md`); padrão de Mermaid dos fluxos
**Requirement**: n/a (documentação do produto finalizado — todas as ACs)

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [ ] `tenis.md` cobre: endpoints com exemplos de payload, km derivada, OAuth manual passo-a-passo, CLI com flags e saída do relatório
- [ ] `banco-de-dados.md` atualizado com `shoes` e `activities.shoe_id`
- [ ] `mkdocs.yml` navegação atualizada
- [ ] Gate: build (suite backend + build frontend — fechamento da feature)

**Tests**: none (docs — build gate only)
**Gate**: build
**Commit**: `docs(tenis): doc técnica de tênis no docs-site`

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in order:

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
```

```
T1 → T2
T2 → T3
T3 → T6
T4 → T6
T5 → T6
T2 → T7
T3 → T7
T7 → T8
T2 → T9
T9 → T10
T3 → T10
T10 → T11
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**How phase-based execution works:**

At Execute, the agent counts total tasks and packs phases into **task-budgeted batches** (~7 tasks
per worker, whole phases - the benchmarked sweet spot is ~20 tasks → ~3 workers). A **phase** is the
semantic/dependency unit; a **batch** is one or more *consecutive whole phases* assigned to one
worker. The cut only ever lands on a phase boundary - a phase is never split across workers. When
packing yields more than one batch (> ~8 tasks), the agent offers to dispatch batch sub-agents.
Batches run sequentially: each worker executes ALL its tasks in order, then reports a compact summary
before the next batch starts. When the whole feature fits a single batch (≤ ~8 tasks), execution
happens inline in the main window with no sub-agents spawned.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Modelo + migração | 1 entrega coesa (schema) | ✅ Granular |
| T2: CRUD service+router | 1 endpoint group (3 rotas, 1 domínio) | ✅ Granular |
| T3: Associação | 1 endpoint + 1 campo no detail | ✅ Granular |
| T4: Cliente Strava | 1 módulo (client httpx) | ✅ Granular |
| T5: Matching | 1 módulo (funções puras) | ✅ Granular |
| T6: Backfill CLI | 1 CLI (orquestração) | ✅ Granular |
| T7: Seção Tênis | 1 component (+ client API) | ⚠️ 3 arquivos, coesos (api types + section + page mount) |
| T8: Aposentar + badge | 1 feature pequena (modify) | ✅ Granular |
| T9: Modal | 1 component | ✅ Granular |
| T10: Integração no detalhe | 1 component (modify) | ✅ Granular |
| T11: Docs | 1 doc nova + updates | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | (nenhuma entrada — sem setas incidentes) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | (nenhuma entrada) | ✅ Match |
| T5 | None | (nenhuma entrada) | ✅ Match |
| T6 | T3, T4, T5 | T3 → T6, T4 → T6, T5 → T6 | ✅ Match |
| T7 | T2, T3 | T2 → T7, T3 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T2 | T2 → T9 | ✅ Match |
| T10 | T3, T9 | T9 → T10, T3 → T10 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Models + migração | integration | integration | ✅ OK |
| T2 | Service + router (API) | integration | integration | ✅ OK |
| T3 | Service (regra) + router (API) | integration | integration | ✅ OK |
| T4 | Client httpx (funções) | unit | unit | ✅ OK |
| T5 | Matching (funções puras) | unit | unit | ✅ OK |
| T6 | CLI backfill | integration | integration | ✅ OK |
| T7 | Frontend components | none | none (build gate) | ✅ OK |
| T8 | Service (1 campo) + frontend | integration (camada backend) | integration | ✅ OK |
| T9 | Frontend component | none | none (build gate) | ✅ OK |
| T10 | Frontend component | none | none (build gate) | ✅ OK |
| T11 | Docs | none | none (build gate) | ✅ OK |
