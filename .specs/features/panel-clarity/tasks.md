# Painel Clareza (panel-clarity) — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/panel-clarity/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes (`uv run pytest` no Postgres do compose, a partir do host); `frontend/AGENTS.md` (Next 16 tem breaking changes — ler `node_modules/next/dist/docs/` antes de codar frontend); AD-008/AD-009 no `STATE.md` (Recharts; padrão de clareza/payload-espelha-render). Sem CONTRIBUTING/CI — fortes defaults onde não há padrão. Base atual: **262 testes** (suite pós health-panel, STATE.md Handoff) — a contagem nunca cai dentro de uma task.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend service (`health/service.py`, `potential/service.py`) | integration (TestClient/db fixture — padrão da suite) | 1:1 com os ACs de contrato (CLR-01..06): janela `days` pedida (não inventada), `points` ASC, `current` = última linha, `pmc=null` sem `load`, payload do potencial sem `pmc`, `?days` morto → 200 sem efeito, zero recálculo | `backend/tests/test_health_api.py`, `backend/tests/test_potential_api.py` | `cd backend; uv run pytest` |
| Backend router (`health/router.py`, `potential/router.py`) | integration (mesma suite) | Payload completo com `pmc` entre `stress` e `dose_response`; bounds de `days` já verdes (HLT-03) seguem verdes | idem | `cd backend; uv run pytest` |
| Frontend (`lib/api.ts`, `components/`, painéis) | none | Sem runner de teste no projeto (`frontend/package.json`) — `npm run build` + `npm run lint` por task; UAT real 390px ao final (padrão workouts-list/potential/health) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |
| Docs (`README.md`) | none | build gate only (README honesto sobre o novo contrato) | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (suite roda no banco `ritmo_test` do compose, a partir do host).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks backend (service/router + testes) | `cd backend; uv run pytest` |
| Full | Fim de fase com integração | `cd backend; uv run pytest` |
| Build | Tasks frontend / docs | backend da task mudou: `cd backend; uv run pytest` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Contrato — PMC no health (backend)

```
T1 → T2
```

### Phase 2: Frontend base (contratos + componentes)

```
T2 → T3

T4

T5
```

### Phase 3: Painel Saúde recomposto

```
T2 → T6
T3 → T6
T4 → T6
T5 → T6
```

### Phase 4: Painel Potencial recomposto

```
T4 → T9
T5 → T9

T7

T8
```

### Phase 5: Contrato fecha — PMC sai do potencial

```
T1 → T10
T9 → T10
T10 → T11
T10 → T12
T11 → T12
```

---

## Task Breakdown

### T1: `_pmc_block` no service da Saúde

**What**: Mover a montagem do bloco PMC (hoje em `potential/service.py`, linhas 39–71) para `health/service.py` como `_pmc_block(rows, days)` — janela via `_series` com `DailyLoad`; `points` ASC; `current` = última linha; sem linhas → `None` — e montar `"pmc"` em `get_health` entre `stress` e `dose_response`.
**Where**: `backend/app/health/service.py` (modify)
**Depends on**: None
**Reuses**: `_series(db, model, days)` (janela idêntica — DESC + limit + reverse); dict `entry`/`current` da função atual (move puro da montagem)
**Requirement**: CLR-01, CLR-02, CLR-05, CLR-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `_pmc_block(_series(db, DailyLoad, days), days)` devolve `{days, points, current}` com os valores exatamente como as linhas de `load` (zero recálculo — CLR-06)
- [x] Janela maior que o histórico devolve o que existe (a pedida, não inventada); sem linhas → `None` (CLR-02)
- [x] `get_health` monta `"pmc"` entre `stress` e `dose_response`; nenhum import do gateway Garmin (CLR-05)
- [x] Testes de integração no padrão do arquivo (`db` fixture ou TestClient): janela pedida, `points` ASC pinados, `current` = última linha, `pmc=null` sem `load`, posição no payload
- [x] Gate passa; contagem da suite sobe (baseline 262, nunca cai)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(health): pmc block in health service`

---

### T2: `GET /api/health/summary` expõe `pmc`

**What**: Modelos `PmcPoint`/`PmcBlock` (hoje no router do potencial, linhas 61–72) movidos para o router da Saúde + `HealthSummaryOut` ganha `pmc: PmcBlock | None` entre `stress` e `dose_response`; docstring cita CLR-01/02.
**Where**: `backend/app/health/router.py` (modify)
**Depends on**: T1
**Reuses**: padrão de modelos inline do próprio arquivo (docstrings citando ACs)
**Requirement**: CLR-01, CLR-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET /api/health/summary?days=60` responde com `pmc` no payload, entre `stress` e `dose_response` (ordem das chaves pinada no teste)
- [ ] Sem linhas em `load` → `"pmc": null` via HTTP (estado vazio, não erro)
- [ ] `days` fora de [7, 365] continua 422 (HLT-03 verde — nenhuma regressão)
- [ ] TestClient: payload com `pmc` pinado (dias/values) + `pmc=null`; suite verde, contagem sobe

**Tests**: integration
**Gate**: quick

**Commit**: `feat(health): expose pmc in summary endpoint`

---

### T3: Contrato frontend — `pmc` na Saúde (aditivo)

**What**: `api.ts`: tipos `PmcPoint`/`PmcBlock` migrados para a seção "Painel Saúde" (comentários citando CLR) e `HealthSummaryOut` ganha `pmc: PmcBlock | null`. `PotentialOut`/`getPotential` intocados nesta task (removem só na T11 — sem quebra intermediária).
**Where**: `frontend/src/lib/api.ts` (modify)
**Depends on**: T2
**Reuses**: padrão do próprio arquivo (espelho 1:1 dos modelos do router, `cache: "no-store"`)
**Requirement**: CLR-01 (espelho no cliente)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `HealthSummaryOut.pmc: PmcBlock | null` espelhando o backend; tipos movidos com comentário atualizado (sem duplicação de tipos)
- [ ] `npm run build` + `npm run lint` verdes; `getPotential` inalterado

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): health summary pmc contract types`

---

### T4: `PanelSection` (cabeçalho forte)

**What**: Componente compartilhado `{ index?: number; title: string; subtitle: string; badge?: string; children }` — índice numeral discreto, título maior, badge pill (padrão do `Vo2maxTrend`), subtítulo sempre visível (1–2 linhas `text-muted`); espaçamento entre seções claramente maior que o interno; **sem** card wrapper (context.md D, AD-009).
**Where**: `frontend/src/components/PanelSection.tsx` (new)
**Depends on**: None
**Reuses**: classes do tema (border-white/10, bg-card, text-muted); badge do `Vo2maxTrend`
**Requirement**: CLR-12, CLR-13, CLR-14 (infraestrutura de cabeçalho)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Props conforme design; `index` opcional (Saúde usa 1–5, Potencial sem índice)
- [ ] Subtítulo sempre visível sem interação; espaçamento externo > interno
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): panel section header component`

---

### T5: `PmcChart` muda de casa (`potential/` → `health/`)

**What**: Move puro do arquivo de `components/potential/` para `components/health/` (nenhum pixel muda — AD-008) + import do `PotentialPanel` atualizado para o novo caminho; header comment cita CLR-07/08/10 (POT-23/24 viram histórico).
**Where**: `frontend/src/components/health/PmcChart.tsx` (new — move)
**Depends on**: None
**Reuses**: componente inteiro existente (move, não reescreve)
**Requirement**: CLR-07 (preparação — casa do gráfico)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Arquivo em `components/health/` com render idêntico (Recharts ComposedChart, cards, legenda, "—" em ACWR null)
- [ ] `PotentialPanel` importa do novo caminho (painel segue renderizando até a T9); `components/potential/` sem o arquivo antigo
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `refactor(ui): move pmc chart to health`

---

### T6: `HealthPanel` — 5 seções numeradas + linha-guia

**What**: Recompor o painel: linha-guia no topo (fio condutor em 1 frase), 5 `PanelSection` numerados (1 Sono · 2 Carga de treino · 3 Recuperação · 4 Dose-resposta · 5 Equilíbrio de vida) com subtítulos (pergunta que responde + o que mostra), Carga de treino renderiza `PmcChart` ou estado vazio, empty geral inclui `pmc`, estados por bloco preservados (HLT-19).
**Where**: `frontend/src/components/health/HealthPanel.tsx` (modify)
**Depends on**: T2, T3, T4, T5
**Reuses**: `PanelSection` (T4); `PmcChart` (T5); `BlockEmpty` existente; todos os gráficos intocados
**Requirement**: CLR-07, CLR-08, CLR-09, CLR-10, CLR-11, CLR-12, CLR-13, CLR-14, CLR-15, CLR-16, CLR-26

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Seções 1–5 na ordem decidida com índice, título, subtítulo (pergunta + explicação) sempre visíveis — copy PT-BR, réguas da copy vêm do payload (`floor_s`/`rem_band`), nenhum número pessoal
- [ ] Carga de treino na posição 2: `pmc != null` → `PmcChart` (subtítulo explica CTL/ATL/TSB e por que importa); `pmc === null` → estado vazio orientando sync (CLR-09); ACWR null → "—" preservado (CLR-10)
- [ ] Empty geral: `sleep && hrv && rhr && stress && pmc` todos null (CLR-11); com só `load` no banco → seção Carga renderiza com dados
- [ ] Erro de API → mensagem inline (CLR-16); `Section` local antigo removido; espaçamento entre seções > interno (CLR-14)
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): recompose health panel with strong sections`

---

### T7: `PredictionsTable` — legenda por método

**What**: Legenda sempre visível sob a tabela com 1 linha por método: **Garmin** (preditor do Garmin Connect, sincronizado), **Riegel** (extrapolação T2 = T1 × (D2/D1)^1,06 ancorada no PR de 5K), **VDOT** (equivalência de Daniels do teste corrente), **Média honesta** (média das estimativas presentes) — a nota atual da média honesta vira uma das entradas.
**Where**: `frontend/src/components/potential/PredictionsTable.tsx` (modify)
**Depends on**: None
**Reuses**: nota existente da média honesta (evolui); padrão visual `text-xs text-muted`
**Requirement**: CLR-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 4 métodos identificáveis com fonte, sem interação, além do nome da coluna; PT-BR; nenhum número inventado
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): prediction method legend`

---

### T8: `DecayTable` — explicação sempre visível

**What**: Explicação do que a tabela compara (pace real dos PRs vs pace ideal da equivalência VDOT corrente) e do sinal (negativo = gap de execução/especificidade, não de motor) — evolui a nota atual, mesmo padrão visual.
**Where**: `frontend/src/components/potential/DecayTable.tsx` (modify)
**Depends on**: None
**Reuses**: nota de sinal existente (evolui); destaque do maior gap intocado (POT-29 histórico)
**Requirement**: CLR-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Explicação sempre visível sem interação, PT-BR
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): decay table explainer`

---

### T9: `PotentialPanel` — 3 blocos narrativos + linha-guia

**What**: Recompor o painel: linha-guia no topo (pergunta do painel + régua provas/testes > estimativas), 3 `PanelSection` sem índice — "Onde estou" (GapCard com label esclarecido + VdotTimeline; subtítulo define VDOT/corrente/demonstrado/lacuna), "O que isso prevê" (PredictionsTable + DecayTable quando não vazio), "O que o relógio estima" (Vo2maxTrend, bloco inteiro ausente quando `vo2max === null`); **sem** seção de PMC; empty check recalculado sem pmc.
**Where**: `frontend/src/components/potential/PotentialPanel.tsx` (modify)
**Depends on**: T4, T5
**Reuses**: `PanelSection` (T4); GapCard/narrativa §9.5 (mantém, label melhora); `Section` local antigo removido
**Requirement**: CLR-17, CLR-18, CLR-21, CLR-22, CLR-23, CLR-24, CLR-25, CLR-27

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 3 blocos na ordem "Onde estou" → "O que isso prevê" → "O que o relógio estima"; nenhum bloco/seção de carga (CLR-22/25)
- [ ] Subtítulo do "Onde estou" explica VDOT (régua de Daniels), corrente (teste calibrado), demonstrado (melhor prova máxima) e a lacuna % (CLR-18)
- [ ] `vo2max === null` → bloco 3 inteiro ausente; `decay` vazio → sub-bloco decaimento fora (CLR-23); bloco 3 mantém selo "estimativa" + nota de hierarquia do `Vo2maxTrend` (CLR-21)
- [ ] Empty check: `timeline.length <= 1 && vo2max === null && decay.length === 0` → estado vazio orientando sync (CLR-24); uso/import de `PmcChart` removido
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): recompose potential panel narrative blocks`

---

### T10: `GET /api/potential` perde `pmc` e `days`

**What**: Endpoint deixa de expor o bloco — `get_potential(db, calibration)` sem `days` e sem `pmc` no payload; router remove `PmcPoint`/`PmcBlock`, o campo e o `Query` (`?days=90` vira query não declarada — ignorada, 200); `test_potential_api.py` adaptado com migração 1:1 (cada assert de PMC removido tem contraparte nos testes de T1/T2; novos: payload sem `pmc`, `?days=90` → 200 sem efeito). Toca `potential/service.py` + `potential/router.py` + testes num único commit (mudança de assinatura — corte intermediário deixa a suite vermelha).
**Where**: `backend/app/potential/router.py` (modify)
**Depends on**: T1, T9
**Reuses**: nada novo — só remoção; `_pmc_block` agora mora no health (T1)
**Requirement**: CLR-03, CLR-04, CLR-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `GET /api/potential` responde `{vdot, predictions, vo2max, decay}` — sem `pmc` (CLR-03); `?days=90` → 200 com payload idêntico (CLR-04)
- [ ] 500 "zonas VDOT não configuradas" sem calibração preservado (fora de escopo, sem regressão)
- [ ] Checklist de migração 1:1 executado (janela/current/null/payload-pmc do `test_potential_api.py` têm contraparte viva em `test_health_api.py`); contagem da suite não cai em relação ao início da task
- [ ] `uv run pytest` verde no Postgres do compose

**Tests**: integration
**Gate**: quick

**Commit**: `feat(potential): drop pmc block and days param`

---

### T11: Contrato frontend fecha — `PotentialOut` sem `pmc`

**What**: `api.ts`: `PotentialOut` perde `pmc`, `getPotential()` perde o param (deixa de mandar `?days=180` — param morto); comentários citam CLR-03/04; tipos `PmcPoint`/`PmcBlock` documentados como contrato exclusivo da Saúde.
**Where**: `frontend/src/lib/api.ts` (modify)
**Depends on**: T10
**Reuses**: espelho 1:1 do backend (AD-009)
**Requirement**: CLR-03, CLR-04 (lado cliente)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `PotentialOut` espelha o payload real (sem `pmc`); `getPotential()` sem param e sem query na URL
- [ ] `npm run build` + `npm run lint` verdes (nenhuma referência a `pmc` no domínio potencial)

**Tests**: none
**Gate**: build

**Commit**: `refactor(ui): mirror potential contract without pmc`

---

### T12: README — painéis refletem o novo contrato

**What**: Atualizar as seções "Painel Potencial" e "Painel Saúde" do README: PMC na Saúde (seção própria Carga de treino, janela 60d), Potencial em 3 blocos narrativos sem PMC, cabeçalhos fortes + explicações sempre visíveis (AD-009); remove a menção a `days` 1–365 no potencial.
**Where**: `README.md` (modify)
**Depends on**: T10, T11
**Reuses**: formato das seções existentes (bullets + validação real)
**Requirement**: Success Criteria (README honesto sobre o contrato; CLR-07/17 documentados)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Seção Potencial sem PMC/`days`; seção Saúde com Carga de treino e a nova composição de 5 seções
- [ ] AD-009 citada como padrão dos painéis; nenhuma menção a comportamento antigo (PMC 180d no potencial)

**Tests**: none
**Gate**: build

**Commit**: `docs(panels): update readme for panel clarity`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1 → T2
Phase 2:  T3, T4, T5 (T3 após T2; T4 e T5 sem dependências)
Phase 3:  T6 (após T2, T3, T4 e T5)
Phase 4:  T7, T8, T9 (T9 após T4 e T5; T7 e T8 sem dependências)
Phase 5:  T10, T11, T12 (T10 após T1 e T9; T11 após T10; T12 após T10 e T11)
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

Packing desta feature: **12 tasks → 2 lotes** — Lote 1 = Phases 1+2+3 (T1–T6, 6 tasks) · Lote 2 = Phases 4+5 (T7–T12, 6 tasks).

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: `_pmc_block` no health service | 1 função + montagem (1 arquivo) + testes co-localizados | ✅ Granular |
| T2: router expõe pmc | 1 endpoint (modelos + campo) + testes | ✅ Granular |
| T3: api.ts aditivo | 1 arquivo (tipos) | ✅ Granular |
| T4: PanelSection | 1 componente novo | ✅ Granular |
| T5: PmcChart move | 1 arquivo movido + 1 import | ✅ Granular |
| T6: HealthPanel recomposto | 1 arquivo (composição) | ✅ Granular |
| T7: legenda métodos | 1 componente | ✅ Granular |
| T8: decay explainer | 1 componente | ✅ Granular |
| T9: PotentialPanel recomposto | 1 arquivo (composição) | ✅ Granular |
| T10: potencial sem pmc/days | 1 endpoint (service+router+testes — inseparáveis: mudança de assinatura quebraria o gate em qualquer corte intermediário) | ⚠️ Coeso — mesmo padrão de tasks multi-arquivo do potential-panel |
| T11: api.ts fecha contrato | 1 arquivo | ✅ Granular |
| T12: README | 1 arquivo | ✅ Granular |

**Granularity check**:

- ✅ 1 component / 1 function / 1 endpoint = Good
- ⚠️ T10 = service+router+testes do MESMO endpoint em 1 commit (corte intermediário deixa a suite vermelha — assinatura `get_potential` muda) — coeso e justificado
- ❌ Multiple components or files = MUST split

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | sem seta de entrada | ✅ Match |
| T2 | T1 | Phase 1: `T1 → T2` | ✅ Match |
| T3 | T2 | Phase 2: `T2 → T3` | ✅ Match |
| T4 | None | Phase 2: T4 sem seta | ✅ Match |
| T5 | None | Phase 2: T5 sem seta | ✅ Match |
| T6 | T2, T3, T4, T5 | Phase 3: `T2 → T6` `T3 → T6` `T4 → T6` `T5 → T6` | ✅ Match |
| T7 | None | Phase 4: T7 sem seta | ✅ Match |
| T8 | None | Phase 4: T8 sem seta | ✅ Match |
| T9 | T4, T5 | Phase 4: `T4 → T9` `T5 → T9` | ✅ Match |
| T10 | T1, T9 | Phase 5: `T1 → T10` `T9 → T10` | ✅ Match |
| T11 | T10 | Phase 5: `T10 → T11` | ✅ Match |
| T12 | T10, T11 | Phase 5: `T10 → T12` `T11 → T12` | ✅ Match |

**Rules check**: nenhuma dependência aponta para fase posterior — T10 depende de T1 (Phase 1) e T9 (Phase 4), ambos anteriores à Phase 5. ✅

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | backend service | integration | integration | ✅ OK |
| T2 | backend router | integration | integration | ✅ OK |
| T3 | frontend client | none | none | ✅ OK |
| T4 | frontend component | none | none | ✅ OK |
| T5 | frontend component (move) | none | none | ✅ OK |
| T6 | frontend component | none | none | ✅ OK |
| T7 | frontend component | none | none | ✅ OK |
| T8 | frontend component | none | none | ✅ OK |
| T9 | frontend component | none | none | ✅ OK |
| T10 | backend service + router | integration (highest) | integration | ✅ OK |
| T11 | frontend client | none | none | ✅ OK |
| T12 | docs | none | none | ✅ OK |

**Rules check**: nenhum `Tests: none` em camada backend; frontend/docs `none` conforme a matriz (sem runner de teste no projeto — verificação por build/lint + UAT). ✅
