# Painel Saúde — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/health-panel/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes (`uv run pytest` no Postgres do compose, suite no host); `frontend/AGENTS.md` (ler docs do Next 16 em `node_modules/next/dist/docs/` antes de codar frontend); AD-001..008 no `STATE.md`. Sem CONTRIBUTING/CI/lint de backend — fortes defaults onde não há padrão. Base atual: 228 testes coletados (suite do potential-panel).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Config (`app/core/config.py` — `app_timezone`) | none | build gate only (o comportamento do fuso é testado na camada de API: fallback + conversão) | - | `cd backend; uv run pytest` |
| Domain puro (`health/calc.py`) | unit | 1:1 com ACs (HLT-04/09/10/11/12); pins literais contra o banco real (dose-resposta 69,5/81,3; sexta 5,74h); truque ±12h; virada de ano ISO; bucket vazio → None | `backend/tests/test_health_calc.py` | `cd backend; uv run pytest` |
| Service + Router (`health/`) | integration (TestClient + banco real) | payload completo pinado (HLT-01..12); `days` 6/366 → 422; blocos null; `APP_TIMEZONE` inválido → fallback; zero import do gateway no domínio | `backend/tests/test_health_api.py` | `cd backend; uv run pytest` |
| Frontend (`lib/`, `components/health/`, `app/saude/`) | none | `npm run build` + `npm run lint`; UAT manual na Phase 5 (mesmo padrão do workouts-list/potential-panel) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (suite roda no banco `ritmo_test` do compose, a partir do host).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks com testes unitários | `cd backend; uv run pytest` |
| Full | Após tasks com testes de integração (mesma suite) | `cd backend; uv run pytest` |
| Build | Conclusão de fase / config / frontend | backend: `cd backend; uv run pytest` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação (config + cálculo puro)

```
T1
T2
```

### Phase 2: Backend de leitura

```
T1 -> T4
T2 -> T3
T3 -> T4
```

### Phase 3: Frontend base (contratos)

```
T4 -> T5
T6
```

### Phase 4: Componentes de gráfico

```
T5 -> T7
T6 -> T7
T7 -> T8
T7 -> T9
T7 -> T10
T7 -> T11
T7 -> T12
T7 -> T13
T7 -> T14
```

### Phase 5: Composição do painel

```
T13 -> T15
T8 -> T16
T9 -> T16
T10 -> T16
T11 -> T16
T12 -> T16
T14 -> T16
T15 -> T16
```

---

## Task Breakdown

### T1: Env `APP_TIMEZONE` na configuração

**What**: Adicionar `app_timezone: str = "America/Sao_Paulo"` ao `Settings` e documentá-la no `.env.example`.
**Where**: `backend/app/core/config.py`
**Depends on**: None
**Reuses**: padrão dos campos existentes (`sync_backfill_health_days` etc.)
**Requirement**: HLT-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Campo adicionado com default `America/Sao_Paulo` (100% env var — requisito Fase 1)
- [x] `backend/.env.example` ganha a linha `APP_TIMEZONE` comentada (fuso da conversão de deitar/acordar)
- [x] `docker-compose.yml` não muda (TZ do container já casa com o default — design §Integrações)

**Tests**: none
**Gate**: quick

**Commit**: `feat(config): add app_timezone setting`

---

### T2: Funções puras do painel (`health/calc.py`)

**What**: Criar o módulo de cálculo puro: `SLEEP_FLOOR_S`/`REM_BAND`/`SHORT_MAX_S`/`ADEQUATE_MIN_S`, `dose_response`, `weekday_pattern`, `regularity`, `local_minute`, `below_floor`, `strength_weeks` (design §Components).
**Where**: `backend/app/health/calc.py`
**Depends on**: None
**Reuses**: postura pura do `potential/calc.py` (sem DB, sem ORM)
**Requirement**: HLT-04, HLT-09, HLT-10, HLT-11, HLT-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `dose_response` cruza sono↔HRV/score da mesma data; buckets `<6h`/`≥6h45`; médias None em bucket vazio; noites sem HRV fora (neutra só se 6h–6h45)
- [x] `weekday_pattern` devolve 7 entradas seg..dom (avg + nights; dia vazio → None/0)
- [x] `regularity` usa minutos locais com o truque ±12h (meia-noite não vira meio-dia); noite sem horário fica fora; sem elegíveis → None
- [x] `local_minute` converte naive UTC → minuto local via `ZoneInfo` (01:16 GMT → 1336)
- [x] `strength_weeks`: semana ISO ≥2 sessões; streak de semanas completas até a última completa (pode exceder janela); `weeks_hit`/`weeks_total` na janela; `current_week_sessions` separado
- [x] `below_floor` com nights + pct (1 casa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(health): pure health panel calculations`

---

### T3: Service de leitura (`health/service.py`)

**What**: Criar `get_health(db, days, tz)` — 4 queries de série (sleep/hrv/rhr/stress, janela ASC) + 1 de atividades; blocos null quando vazios; conversão de fuso dos horários de sono.
**Where**: `backend/app/health/service.py`
**Depends on**: T2
**Reuses**: padrão de query/janela do `potential/service.py`; `DEFAULT_USER_ID`; filtro de typeKey em Python (AD-001)
**Requirement**: HLT-01, HLT-02, HLT-04..HL12 (montagem)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Payload monta os 6 blocos conforme design §Contrato (pontos de sono com deep_pct/light_pct/awakenings/bed_local/wake_local)
- [x] Séries vazias → bloco `null`; `dose_response`/`lifestyle` sempre presentes com zeros honestos
- [x] `bed_time`/`wake_time` GMT naive → local via `ZoneInfo` injetada; NULL fica fora da regularity
- [x] Nenhuma importação do gateway Garmin no domínio (AD-002)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(health): read-only health service`

---

### T4: Router `GET /api/health/summary`

**What**: Criar o router com modelos Pydantic inline, `days: Query(60, ge=7, le=365)` (422 fora), resolução de tz com fallback (`APP_TIMEZONE` inválido → `America/Sao_Paulo` + warning) e montagem em `app.main`.
**Where**: `backend/app/health/router.py`
**Depends on**: T1, T3
**Reuses**: padrão do `potential/router.py` (Query bounds + modelos inline + `include_router` no main)
**Requirement**: HLT-01, HLT-02, HLT-03, HLT-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `GET /api/health/summary?days=60` responde o payload do design §Contrato
- [x] `days` fora de [7, 365] → 422 antes de qualquer query
- [x] `APP_TIMEZONE` inválido → fallback default + warning log (sem crash)
- [x] `include_router(health_router)` em `app/main.py`; `/api/health` de infra intocado
- [x] TestClient: payload pinado com seeds; 422; blocos null; fallback de tz; série completa cortada pela janela

**Tests**: integration
**Gate**: quick

**Commit**: `feat(health): health summary endpoint`

---

### T5: Contrato frontend (`api.ts`)

**What**: Tipos espelhando `HealthSummaryOut` (SleepBlock/HrvBlock/RhrBlock/StressBlock/DoseResponse/Lifestyle) + `getHealthSummary(days = 60)`.
**Where**: `frontend/src/lib/api.ts`
**Depends on**: T4
**Reuses**: padrão do bloco Potencial no mesmo arquivo (`getPotential`)
**Requirement**: HLT-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Tipos completos (null atravessa o contrato: blocos e médias opcionais)
- [x] `getHealthSummary` com `cache: "no-store"` e `parseError`

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): health summary api client`

---

### T6: Formatadores de sono (`format.ts`)

**What**: Adicionar `formatHours` (s → "6,3 h"), `formatClock` (min do dia → "22:16") e `formatWeekday` (0..6 → "seg".."dom").
**Where**: `frontend/src/lib/format.ts`
**Depends on**: None
**Reuses**: postura PT-BR/vírgula dos formatadores existentes
**Requirement**: HLT-04, HLT-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `formatHours` com vírgula PT-BR e 1 casa
- [x] `formatClock` HH:MM a partir de minutos do dia (1336 → "22:16")
- [x] `formatWeekday` mapeia 0..6 para seg..dom (rótulo PT-BR — padrão ASCII na API)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): sleep time formatters`

---

### T7: `SleepChart` (duração vs piso + % abaixo)

**What**: Componente do gráfico de duração por noite com `ReferenceLine` no piso e resumo "% das noites abaixo do piso"; tooltip com score e REM%.
**Where**: `frontend/src/components/health/SleepChart.tsx`
**Depends on**: T5, T6
**Reuses**: padrão `ComposedChart`/`ReferenceLine`/Tooltip do `PmcChart.tsx` (AD-008)
**Requirement**: HLT-13, HLT-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Barras de duração (h) + linha de referência do `floor_s` visível
- [x] Resumo `{below_floor.pct}% das noites abaixo do piso` acima do gráfico
- [x] Tooltip: score + REM% da noite
- [x] Eixos/tooltip no padrão visual do PmcChart (cores/labels)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): sleep duration chart with 7h floor`

---

### T8: `SleepStagesChart` (fases empilhadas + despertares)

**What**: Componente da composição de fases por noite — barras empilhadas leve/profundo/REM (domínio 0–100) com despertares no tooltip.
**Where**: `frontend/src/components/health/SleepStagesChart.tsx`
**Depends on**: T7
**Reuses**: padrão de Bar/Tooltip do `PmcChart.tsx`
**Requirement**: HLT-30

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] 3 `Bar` com `stackId` único (light base + deep + rem), domínio Y 0–100
- [x] Tooltip com as 3 fases + "N despertares" (omitido quando null)
- [x] Sem normalização dos pcts (passam como gravados)
- [x] Legenda com rótulos PT-BR (leve/profundo/REM)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): stacked sleep stages chart`

---

### T9: `RemChart` (REM% com banda ideal)

**What**: Componente da linha de REM% por noite com `ReferenceArea` da banda 21–31 visível e domínio Y fixo 0–40.
**Where**: `frontend/src/components/health/RemChart.tsx`
**Depends on**: T7
**Reuses**: padrão Line/Tooltip do `PmcChart.tsx`; `rem_band` do payload (a UI não inventa régua)
**Requirement**: HLT-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Linha de rem_pct + banda sombreada de `rem_band` visível
- [ ] Domínio Y 0–40 fixo (a média real ~14% não colapsa na base)
- [ ] Tooltip com o valor da noite

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): rem percentage chart with ideal band`

---

### T10: `WeekdayPattern` (regularidade + média semanal)

**What**: Componente com os cards de regularidade (deitar/acordar médios via `formatClock`) + gráfico de barras da média de duração por dia da semana.
**Where**: `frontend/src/components/health/WeekdayPattern.tsx`
**Depends on**: T7
**Reuses**: padrão StatCard do `PmcChart.tsx`; `formatClock`/`formatWeekday`
**Requirement**: HLT-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cards: deitar médio e acordar médio em horário local (minutos → HH:MM)
- [ ] Barras de média por weekday com rótulos PT-BR (seg..dom) e domínio começando em 0
- [ ] `regularity` null → cards "—" sem quebrar o gráfico

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): weekday sleep pattern with regularity`

---

### T11: `HrvChart` (linha + status do último dia)

**What**: Componente da linha de HRV com o status do último dia (BALANCED/UNBALANCED/LOW) como destaque textual.
**Where**: `frontend/src/components/health/HrvChart.tsx`
**Depends on**: T7
**Reuses**: padrão LineChart/Tooltip do `PmcChart.tsx`
**Requirement**: HLT-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Linha dos valores por data + valor atual em destaque
- [ ] `current.status` exibido como badge textual (status cru da API, sem tradução inventada)
- [ ] Tooltip com valor e status da noite

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): hrv trend with status badge`

---

### T12: `RhrChart` (linha vs baseline)

**What**: Componente da linha de RHR com `ReferenceLine` no `baseline` da janela.
**Where**: `frontend/src/components/health/RhrChart.tsx`
**Depends on**: T7
**Reuses**: padrão LineChart/ReferenceLine do `PmcChart.tsx`
**Requirement**: HLT-18

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Linha dos valores + linha de referência do baseline visível e rotulada
- [ ] Tooltip com o valor do dia

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): resting heart rate chart with baseline`

---

### T13: `StressChart` (linha + média da janela)

**What**: Componente da linha de estresse médio diário com a média da janela em card ("—" quando null).
**Where**: `frontend/src/components/health/StressChart.tsx`
**Depends on**: T7
**Reuses**: padrão StatCard/LineChart do `PmcChart.tsx`
**Requirement**: HLT-25, HLT-26

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Linha da média diária + card "média da janela"
- [ ] `avg_window` null → "—" (nenhum número inventado)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): daily stress chart with window average`

---

### T14: `DoseResponse` (o comparativo que convence a dormir)

**What**: Componente com os dois buckets lado a lado (`<6h` vs `≥6h45`: noites, HRV média, score médio) + nota da faixa neutra.
**Where**: `frontend/src/components/health/DoseResponse.tsx`
**Depends on**: T7
**Reuses**: padrão StatCard/Section; `formatVdot` não — formatação de média com vírgula (padrão format.ts)
**Requirement**: HLT-20, HLT-21, HLT-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cards "Noites <6h" e "Noites ≥6h45" com `{nights, avg_hrv, avg_score}` cada
- [ ] Nota "N noites fora da comparação (6h–6h45)" com `neutral_nights`
- [ ] Média null → "—" (bucket vazio)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): sleep dose response cards`

---

### T15: `Lifestyle` (checklist força + yoga)

**What**: Componente do checklist de vida — força (streak em semanas, `weeks_hit`/`weeks_total`, sessões da semana corrente "em andamento") e yoga (sessões + média/semana).
**Where**: `frontend/src/components/health/Lifestyle.tsx`
**Depends on**: T13
**Reuses**: padrão StatCard/Section; `StressChart` (T13) renderizado na mesma seção de equilíbrio de vida
**Requirement**: HLT-23, HLT-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Card força: streak atual, "x/y semanas na janela", sessões da semana corrente separadas
- [ ] Card yoga: sessões na janela + média por semana (1 casa, vírgula)
- [ ] Sem inventar número: zeros e ausências exibidos como estão (streak 0 é recado, não erro)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): lifestyle checklist cards`

---

### T16: `HealthPanel` (page-shell) + rota `/saude`

**What**: Compor o painel — fetch de `getHealthSummary`, estados loading/error/empty, seções condicionais por bloco — e trocar o placeholder da rota `/saude`.
**Where**: `frontend/src/components/health/HealthPanel.tsx`
**Depends on**: T8, T9, T10, T11, T12, T14, T15
**Reuses**: padrão page-shell do `PotentialPanel.tsx` (estados + `Section` + empty state apontando o sync)
**Requirement**: HLT-19, HLT-27, HLT-28, HLT-29

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Seções: Sono (SleepChart + SleepStagesChart + RemChart + WeekdayPattern), Recuperação (HrvChart + RhrChart), Dose-resposta (DoseResponse), Equilíbrio de vida (Lifestyle + StressChart)
- [ ] Bloco `null` → estado vazio próprio do bloco (orientando o sync, sem erro)
- [ ] Painel inteiro vazio (todas as séries null) → estado vazio apontando o "Puxar do Garmin"
- [ ] Falha da API → mensagem inline sem quebrar a navegação
- [ ] `frontend/src/app/saude/page.tsx` renderiza `<HealthPanel />` (placeholder sai)
- [ ] Layout legível em 390px sem scroll horizontal (padrão dos painéis anteriores)

**Tests**: none
**Gate**: build

**Commit**: `feat(ui): assemble health panel page`

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in order:

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1: T1 e T2, independentes um do outro.
Phase 2: T3 depois T4; T4 também depende de T1 (fase anterior).
Phase 3: T5 depende de T4; T6 é independente.
Phase 4: T7 depende de T5 e T6; T8 a T14 dependem todos de T7.
Phase 5: T15 depende de T13; T16 depende de T8, T9, T10, T11, T12, T14 e T15.
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

> Dependências cross-phase (T1→T4, T5→T7, T6→T7) não aparecem como seta nos diagramas por fase — o validador as cobre pela checagem de fase anterior; o cross-check abaixo é a fonte da verdade completa.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: env app_timezone | 1 campo + 1 linha de doc | ✅ Granular |
| T2: health/calc.py | 1 módulo puro | ✅ Granular |
| T3: health/service.py | 1 arquivo | ✅ Granular |
| T4: health/router.py + mount | 1 endpoint (+1 linha no main) | ✅ Granular |
| T5: api.ts contract | 1 arquivo (extend) | ✅ Granular |
| T6: format.ts | 1 arquivo (3 funções irmãs) | ✅ Granular |
| T7..T15: um componente por task | 1 componente | ✅ Granular |
| T16: HealthPanel + page.tsx | 1 componente + swap de 1 linha na rota | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | raiz da Phase 1 | ✅ Match |
| T2 | None | raiz da Phase 1 (T1 e T2 são independentes) | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T1, T3 | T3 → T4; T1 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | None | T6 sem seta (independente, roda na Phase 3 pela ordem) | ✅ Match |
| T7 | T5, T6 | T5 → T7; T6 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T7 | T7 → T9 | ✅ Match |
| T10 | T7 | T7 → T10 | ✅ Match |
| T11 | T7 | T7 → T11 | ✅ Match |
| T12 | T7 | T7 → T12 | ✅ Match |
| T13 | T7 | T7 → T13 | ✅ Match |
| T14 | T7 | T7 → T14 | ✅ Match |
| T15 | T13 | T13 → T15 | ✅ Match |
| T16 | T8, T9, T10, T11, T12, T14, T15 | T8→T16, T9→T16, T10→T16, T11→T16, T12→T16, T14→T16, T15→T16 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Config | none | none | ✅ OK |
| T2 | Domain puro | unit | unit | ✅ OK |
| T3 | Service | integration | integration | ✅ OK |
| T4 | Router (route layer) | integration | integration | ✅ OK |
| T5 | Frontend lib | none (build gate) | none | ✅ OK |
| T6 | Frontend lib | none (build gate) | none | ✅ OK |
| T7..T15 | Frontend components | none (build gate) | none | ✅ OK |
| T16 | Frontend page composition | none (build gate) | none | ✅ OK |

> Testes de frontend: nenhum no projeto (padrão dos painéis anteriores) — a verificação é `npm run build` + `npm run lint` + UAT manual (Phase 5). Os ACs de UI (HLT-13..30) são verificados pelo Verifier via código/estrutura e pelo UAT real.

---

## Task Verification Standards

Every task MUST follow the `Done when` + `Tests` + `Gate` fields defined in the **Task Breakdown** template above. Each `Done when` entry must be specific, testable (binary pass/fail), and reference the gate check command from the **Gate Check Commands** section. Include the expected test count to prevent silent deletions.
