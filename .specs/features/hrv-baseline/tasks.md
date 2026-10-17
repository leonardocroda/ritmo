# HRV Baseline Científico (hrv-baseline) — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Spec**: `.specs/features/hrv-baseline/spec.md`
**Design**: `.specs/features/hrv-baseline/design.md`
**Context**: `.specs/features/hrv-baseline/context.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes (`uv run pytest` no Postgres do compose, a partir do host); `frontend/AGENTS.md` (Next 16 tem breaking changes — ler `node_modules/next/dist/docs/` antes de codar frontend); AD-008/AD-009 no `STATE.md` (Recharts; payload-espelha-render); AD-003 (matemática determinística em funções puras, pinável). Sem CONTRIBUTING/CI — fortes defaults onde não há padrão. Base atual: **268 testes** (suite pós panel-clarity, STATE.md Handoff) — a contagem nunca cai dentro de uma task.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend calc (`health/calc.py`) | unit (função pura — padrão AD-003) | 1:1 com HRV-01..HRV-06/08 (matemática): média 7d com/sem lacuna, janela vazia, banda ≥14/<14 pinada, borda inclusiva, truncamento, janela de exibição | `backend/tests/test_health_calc.py` | `cd backend; uv run pytest` |
| Backend service (`health/service.py`) | integration (db fixture) | janela de datas (exibição + lookback 59d), filtro `user_id` (lição L-005 preventiva), arredondamento só no payload | `backend/tests/test_health_api.py` | `cd backend; uv run pytest` |
| Backend router (`health/router.py`) | integration (TestClient/db) | contrato novo pinado: pontos dias corridos, `current` com banda/status, `status` Garmin ausente; cenários 119d/UNBALANCED/days=7 | `backend/tests/test_health_api.py` | `cd backend; uv run pytest` |
| Backend sync (`garmin/`, `core/config.py`) | integration (fake_garmin) | backfill 120 → ≥119 dias de HRV persistidos em base sem sync_state (HRV-15) | `backend/tests/test_garmin_*.py` | `cd backend; uv run pytest` |
| Frontend (`lib/api.ts`, `components/health/`) | none | Sem runner de teste no projeto (`frontend/package.json`) — `npm run build` + `npm run lint` por task; UAT real 390px ao final (padrão panel-clarity) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |
| Docs (`PLANO_PLATAFORMA.md`, `.specs/STATE.md`) | none | build gate only (plano honesto sobre o novo modelo; AD-010 registrada) | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (suite roda no banco `ritmo_test` do compose, a partir do host).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks backend (calc/service/router/sync + testes) | `cd backend; uv run pytest` |
| Full | Fechamento com integração completa | `cd backend; uv run pytest` |
| Build | Tasks frontend / docs | backend da task mudou: `cd backend; uv run pytest` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Modelo puro (calc)

```
T1
```

### Phase 2: Service + contrato (backend)

```
T1 → T2

T2 → T3
```

### Phase 3: Sync (backfill)

```
T4
```

### Phase 4: Frontend (gráfico + tabela)

```
T3 → T5

T5 → T6
```

### Phase 5: Fechamento

```
T1 → T7
T2 → T7
T3 → T7
T4 → T7
T5 → T7
T6 → T7
```

---

## Task Breakdown

### T1: `hrv_model` — réguas + média móvel 7d + banda por dia + status (calc puro)

**What**: Constantes `HRV_AVG_DAYS=7`, `HRV_BASELINE_DAYS=60`, `HRV_BASELINE_MIN_VALUES=14`, `HRV_BASELINE_SD_FACTOR=0.75` + `hrv_model(rows, days)` em `calc.py`: série de **dias corridos** terminando na última data com dado `L` (primeira = `L−(days−1)`); por dia `d`: `avg7` = média dos valores disponíveis em `[d−6, d]` (janela vazia → `None`), banda = `(média−0,75×DP, média+0,75×DP)` com DP amostral (`statistics.stdev`, n−1) dos valores em `[d−59, d]` quando ≥14 valores; `current` = último dia com dado; `status` = BALANCED (limites inclusos) / UNBALANCED / None — **comparação sem arredondar** (design §Components.1). Não reusar `_avg` (arredonda).
**Where**: `backend/app/health/calc.py` (modify), `backend/tests/test_health_calc.py` (modify)
**Depends on**: None
**Reuses**: padrão de réguas `SLEEP_FLOOR_S`/`REM_BAND` (`calc.py:19-22`); docstrings citando ACs
**Requirement**: HRV-01, HRV-02, HRV-03, HRV-04, HRV-05, HRV-06, HRV-08 (matemática) + edges (truncamento, borda inclusiva)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Média 7d com lacuna de captura preenchida pela janela disponível (HRV-02) — pinada com valores à mão
- [ ] Janela 7d vazia (>7 dias sem captura) → `avg7` None (HRV-03)
- [ ] Banda pinada com média/DP calculados à mão (≥14 valores) e `<14` → None (HRV-04/05)
- [ ] Status: média igual ao limite → BALANCED; fora → UNBALANCED; sem banda → None (HRV-06/08)
- [ ] Janela de exibição: `days` dias corridos terminando em `L`; truncamento no início do histórico usa o disponível
- [ ] Gate passa; contagem da suite sobe (baseline 268, nunca cai)

**Tests**: unit (função pura)
**Gate**: quick

**Commit**: `feat(health): hrv rolling model in calc`

---

### T2: `_hrv_history` + `_hrv_block` novo no service + isolamento user_id

**What**: `_hrv_history(db, days)` — `max(date)` do usuário → linhas com `date ≥ L−(days+58)` ASC (exibição + lookback de banda 59d), **filtro `user_id`** (AD-001); `_hrv_block` reescrito via `hrv_model` com arredondamento de 1 casa só no payload (`avg7`, `band_low`, `band_high`). `_series(db, Hrv, days)` segue alimentando o `hrv_by_date` do dose-resposta — intocado (design §Components.2).
**Where**: `backend/app/health/service.py` (modify), `backend/tests/test_health_api.py` (modify)
**Depends on**: T1
**Reuses**: `_hrv_block` atual (`service.py:115-122`) como ponto de partida; `_series` permanece para dose-response
**Requirement**: HRV-02 (base da série), suporte a HRV-04..06; lição candidata L-005 aplicada preventivamente

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Query por janela de datas (não por nº de linhas) cobrindo exibição + lookback; sem linhas → `[]` → bloco `None`
- [ ] Teste de isolamento: HRV de **outro usuário** não entra em série/banda/status (padrão do teste existente `test_health_api.py:327-337`)
- [ ] Dose-resposta sem mudança de comportamento (teste existente verde sem edição)
- [ ] Gate passa; contagem sobe

**Tests**: integration
**Gate**: quick

**Commit**: `feat(health): hrv history window service`

---

### T3: Contrato novo no router + pins + cenários de API

**What**: `HrvPoint {date, value|None, avg7|None, band_low|None, band_high|None}`, `HrvCurrent {date, value, avg7, band_low|None, band_high|None, status|None}`, `HrvBlock {points, current}` — `status` Garmin **sai do payload** (continua na tabela). Atualizar os 3 pins existentes (linhas ~190-197, 364-369, 509-511) para o formato dias corridos + `current.status: null` (3 dias semeados → coletando); adicionar cenários: **119 dias determinístico** (banda presente nos 60 dias exibidos, valores pinados em dias-chave), **UNBALANCED** (queda recente derruba média 7d abaixo da banda), `days=7` (banda mantém lookback de 60d) (design §Components.3).
**Where**: `backend/app/health/router.py` (modify), `backend/tests/test_health_api.py` (modify)
**Depends on**: T2
**Reuses**: padrão de modelos inline com docstrings citando ACs; `_seed_hrv` (`test_health_api.py:76-77`)
**Requirement**: HRV-01..HRV-09 (contrato), HRV-15 (efeito de leitura)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET /api/health/summary` responde bloco `hrv` novo; nenhum campo `status` por ponto; `current` com banda/status do último dia com dado
- [ ] Pins antigos atualizados (janela dias corridos, `current.status` null no cenário de 3 dias); cenários novos 119d/UNBALANCED/days=7 pinados
- [ ] `days` fora de [7, 365] segue 422 (HLT-03 sem regressão)
- [ ] Gate passa; contagem sobe

**Tests**: integration
**Gate**: quick

**Commit**: `feat(health): scientific hrv contract`

---

### T4: Backfill de saúde 60 → 120 dias

**What**: `sync_backfill_health_days: 60 → 120` (`config.py:48`) — HRV-15: exibição 60 + lookback de banda 59 = 119 dias. Verificar pins de janela em `tests/test_garmin_*` (adaptar se pinarem 60); teste de sync completo em base sem `sync_state` → **≥119 dias de HRV** persistidos; adaptar `fake_garmin.py` se ela limitar a janela servida (design §Components.4).
**Where**: `backend/app/core/config.py` (modify), `backend/tests/test_garmin_service.py` + `backend/tests/fake_garmin.py` (modify se preciso)
**Depends on**: None
**Reuses**: `_window_start` (`garmin/service.py:129-136`) — sem sync_state usa backfill (comportamento já testado)
**Requirement**: HRV-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Default 120 com comentário citando HRV-15; env var `SYNC_BACKFILL_HEALTH_DAYS` segue override (100% env vars)
- [ ] Teste: sync full em base nova persiste ≥119 dias de HRV (fake garmin servindo janela suficiente); pins existentes de sync verdes
- [ ] Teto de chamadas conferido (120 × 4 tipos diários ≈ 480 < `sync_max_calls=1500`)
- [ ] Gate passa; contagem sobe

**Tests**: integration
**Gate**: quick

**Commit**: `feat(sync): health backfill to 120 days`

---

### T5: `api.ts` + `HrvChart` rewrite (banda + linha 7d + noites + card local)

**What**: Tipos espelho do contrato novo em `api.ts` (linhas 335-338). `HrvChart.tsx` rewrite (design §Components.5): dados = `points` + derivados de render `bandBase`/`bandSpan`; banda com 2 `<Area stackId="band">` (base transparente + span `fillOpacity≈0.12`, nulls quebram); `<Line dataKey="avg7" connectNulls={false}>`; `<Scatter dataKey="value">` círculos r≈2, noites fora da banda em âmbar (HRV-13, P2) via `shape` custom; card: valor da última noite + badge status local ("coletando linha de base…" quando `status` null, HRV-08) + linha de contexto `média 7d X ms · banda L–H ms` (HRV-07); tooltip (noite ou "sem captura", média 7d, banda); legenda padrão `SeriesLegend` (noite / média 7 dias / banda normal). Cor HRV `#38bdf8` e eixos padrão do arquivo seguem.
**Where**: `frontend/src/lib/api.ts` (modify), `frontend/src/components/health/HrvChart.tsx` (rewrite)
**Depends on**: T3
**Reuses**: `RemChart.tsx:58-81` (SeriesLegend) e `:110-115` (banda); `RhrChart` (régua do payload); `PmcChart` (ComposedChart multi-série)
**Requirement**: HRV-01..HRV-05, HRV-06..HRV-09 (render), HRV-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Gráfico renderiza banda por dia (2 Areas empilhadas), linha de média 7d e pontos das noites; dias sem banda não desenham banda
- [ ] Card exibe status local + média 7d + limites da banda (1 casa, `formatVdot`); "coletando linha de base…" quando `status` null; status Garmin ausente na UI (HRV-09)
- [ ] Noites fora da banda com cor diferenciada (HRV-13); legenda e tooltip com os 3 elementos
- [ ] Nenhuma API nova do Next (AGENTS.md) — client components no padrão existente; se tocar rota/suspense, ler `node_modules/next/dist/docs/` antes
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): scientific hrv chart`

---

### T6: `HrvTable` + mount no HealthPanel

**What**: `HrvTable.tsx` (novo): pontos com `value ≠ null` em ordem desc, **7 linhas/página** client-side; controles Anterior/Próxima + indicador `atual/total` **só** quando >7 dias com dado (HRV-12); colunas Data (`20/04/2026`), HRV, média 7d — 1 casa, `tabular-nums`; estilo espelha `PredictionsTable`/`DecayTable`. Mount dentro do card do HRV no `HealthPanel.tsx:152-155`, abaixo do gráfico (mesma seção Recuperação). Janela da UI segue fixa em 60 dias (`getHealthSummary()` sem mudança).
**Where**: `frontend/src/components/health/HrvTable.tsx` (new), `frontend/src/components/health/HealthPanel.tsx` (modify)
**Depends on**: T5
**Reuses**: estilo das tabelas do potential (`PredictionsTable`/`DecayTable`); card container existente do HRV
**Requirement**: HRV-10, HRV-11, HRV-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Tabela exibe até 7 dias com dado mais recentes (desc) com Data/HRV/média 7d; paginação de 7 em 7 com indicador `atual/total` sobre a janela; ≤7 dias → sem controles
- [ ] Tabela dentro do card do HRV (abaixo do gráfico), sem quebra em 390px
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): hrv daily table with pagination`

---

### T7: Docs + memory + suíte completa

**What**: `docs/PLANO_PLATAFORMA.md` §4.5 (linha ~109): bloco HRV atualizado para o modelo científico (linha = média 7d; banda = 60d ± 0,75 DP com threshold 14; status local). `.specs/STATE.md`: **AD-010** (modelo de avaliação de HRV — design §Decisões.6) + Handoff atualizado (feature hrv-baseline; ops-note: base existente ganha os 60 dias extras no próximo sync completo com `sync_state` dos tipos de saúde limpa). Traceability da spec → Verified nos ACs implementados; este arquivo com todos os checkboxes marcados.
**Where**: `docs/PLANO_PLATAFORMA.md` (modify), `.specs/STATE.md` (modify), `.specs/features/hrv-baseline/spec.md` (traceability), `.specs/features/hrv-baseline/tasks.md` (checkboxes)
**Depends on**: T1, T2, T3, T4, T5, T6
**Reuses**: formato das ADs existentes no STATE.md; padrão de handoff do panel-clarity
**Requirement**: fechamento (HRV-01..HRV-13, HRV-15); Success Criteria da spec

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Plano §4.5 descreve o modelo novo (sem menção a "linha 60d + status" antiga no bloco HRV)
- [ ] AD-010 registrada (decision/reason/trade-off/scope/date/status active); Handoff com feature, fase e ops-note do re-sync
- [ ] Traceability da spec: HRV-01..HRV-13 + HRV-15 → Verified (HRV-14 fica Pending — P3 deferred)
- [ ] `cd backend; uv run pytest` completo verde (contagem final > 268) + `cd frontend; npm run build; npm run lint` verdes

**Tests**: none (docs/memory) — gate de suíte completa como verificação
**Gate**: full + build

**Commit**: `docs(hrv): record hrv baseline model and plan update`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1
Phase 2:  T2 → T3
Phase 3:  T4
Phase 4:  T5 → T6
Phase 5:  T7 (após T1..T6)
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**How phase-based execution works:**

At Execute, the agent counts total tasks and packs phases into **task-budgeted batches** (~7 tasks
per worker, whole phases - the benchmarked sweet spot is ~20 tasks → ~3 workers). A **phase** is the
semantic/dependency unit; a **batch** is one or more *consecutive whole phases* assigned to one
worker. The cut only ever lands on a phase boundary - a phase is never split across workers. When
packing yields more than one batch (> ~8 tasks), the agent offers to dispatch batch sub-agents.
Batches run sequentially: each worker executes ALL its tasks in order, then reports a compact summary
before the next batch starts.

Packing desta feature: **7 tasks → 1 lote** (5 fases inteiras, dentro do orçamento de ~7 — execução inline, sem sub-agents).

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: hrv_model no calc | 1 função pura + constantes + testes co-localizados | ✅ Granular |
| T2: service history/block | 2 funções + 1 teste de isolamento | ✅ Granular |
| T3: contrato router | 3 modelos + pins/cenários co-localizados (inseparáveis: contrato e testes da mesma forma) | ⚠️ Coeso — mesmo padrão de tasks multi-arquivo do panel-clarity |
| T4: backfill config | 1 default + testes de sync | ✅ Granular |
| T5: api.ts + HrvChart rewrite | tipos + 1 componente (mesmo contrato, inseparáveis) | ⚠️ Coeso — tipos sem render seriam commit morto |
| T6: HrvTable + mount | 1 componente novo + 1 linha de mount | ✅ Granular |
| T7: docs + memory | 2 docs + traceability (fechamento) | ✅ Granular |

**Granularity check**:

- ✅ 1 component / 1 function / 1 config = Good
- ⚠️ T3 e T5 = mudanças multi-arquivo onde o corte intermediário deixa artefato morto (contrato sem teste / tipos sem render) — coesas e justificadas
- ❌ Multiple components or files = MUST split

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | Phase 1: T1 sem seta de entrada | ✅ Match |
| T2 | T1 | Phase 2: `T1 → T2` | ✅ Match |
| T3 | T2 | Phase 2: `T2 → T3` | ✅ Match |
| T4 | None | Phase 3: T4 sem seta | ✅ Match |
| T5 | T3 | Phase 4: `T3 → T5` | ✅ Match |
| T6 | T5 | Phase 4: `T5 → T6` | ✅ Match |
| T7 | T1, T2, T3, T4, T5, T6 | Phase 5: `T1..T6 → T7` | ✅ Match |

**Rules check**: nenhuma dependência aponta para fase posterior — T5 depende de T3 (Phase 2), T6 de T5 (Phase 4), T7 de T1..T6 (todas anteriores à Phase 5). ✅

---

## Test Co-Location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | backend calc | unit | unit | ✅ OK |
| T2 | backend service | integration | integration | ✅ OK |
| T3 | backend router | integration | integration | ✅ OK |
| T4 | backend sync/config | integration | integration | ✅ OK |
| T5 | frontend client + component | none | none | ✅ OK |
| T6 | frontend component | none | none | ✅ OK |
| T7 | docs/memory | none | none (gate full) | ✅ OK |

**Rules check**: nenhum `Tests: none` em camada backend; frontend/docs `none` conforme a matriz (sem runner de teste no projeto — verificação por build/lint + UAT ao final). ✅
