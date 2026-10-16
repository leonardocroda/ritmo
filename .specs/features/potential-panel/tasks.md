# Painel Potencial — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/potential-panel/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes (`uv run pytest` no Postgres do compose, suite no host); `frontend/AGENTS.md` (ler docs do Next 16 em `node_modules/next/dist/docs/` antes de codar frontend); AD-001..008 no `STATE.md`. Sem CONTRIBUTING/CI/lint de backend — fortes defaults onde não há padrão. Base atual: 170 testes coletados.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domain puro (`vdot/daniels.py`, `vdot/calibration.py`, `potential/calc.py`) | unit | 1:1 com ACs; pins literais contra cálculo manual (VDOT do 5K 19:23,8 ≈ 53,1; Riegel ancorado; `equivalent_time`); dedup timeline; média só das presentes; sinal do decay | `backend/tests/test_vdot_daniels.py`, `test_vdot_calibration.py`, `test_potential_calc.py` | `cd backend; uv run pytest` |
| Mapper/upserts (data dos PRs + predições) | unit + integration (Postgres real) | keys reais da sonda (15/10: `prStartTimeGmt`/`activityStartDateTimeLocal`; `time5K`/`time10K`/`timeHalfMarathon`/`timeMarathon`/`calendarDate`); NULL quando ausente; re-upsert atualiza `pr_date` (self-heal); evento ausente não apaga linha | `backend/tests/test_garmin_mappers.py`, `test_garmin_upserts.py` | `cd backend; uv run pytest` |
| Sync service (etapa de predições) | integration | exatamente 1 chamada no orçamento; warning `{tipo: "predictions"}` e sync continua; contador no stats; ordem records→predictions→pmc | `backend/tests/test_garmin_service.py` (+ `fake_garmin.py`/`helpers.py` fixtures) | `cd backend; uv run pytest` |
| Service + Router (`potential/`) | integration (TestClient + banco real) | payload completo (vdot/predictions/pmc/vo2max/decay); `days` 0/366 → 422; 500 "zonas VDOT não configuradas"; `pmc=null` sem `load`; `vo2max=null` sem `vO2MaxValue`; nenhuma importação do gateway no domínio | `backend/tests/test_potential_api.py` | `cd backend; uv run pytest` |
| Models / schema (`race_predictions`) | none | cobertos pelos testes de mapper/upserts | - | build gate only |
| Frontend (`lib/`, `components/potential/`, `app/potencial/`) | none | `npm run build` + `npm run lint`; UAT manual na Phase 5 (mesmo padrão do garmin-sync/workouts) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (suite roda no banco `ritmo_test` do compose, a partir do host).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks com testes unitários | `cd backend; uv run pytest` |
| Full | Após tasks com testes de integração (mesma suite) | `cd backend; uv run pytest` |
| Build | Conclusão de fase / infra / frontend | backend: `cd backend; uv run pytest` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação de dados (equações + sync base)

```
T1
T2
T3
T4 -> T5
```

### Phase 2: Domínio de leitura (calc puro)

```
T1 -> T6
T6 -> T7
```

### Phase 3: API de leitura

```
T1 -> T8
T2 -> T8
T6 -> T8
T7 -> T8
T8 -> T9
```

### Phase 4: Frontend

```
T9 -> T10
T10 -> T11
T10 -> T12
T10 -> T13
T10 -> T14
T10 -> T15
T11 -> T15
T12 -> T15
T13 -> T15
T14 -> T15
```

### Phase 5: Validação real

```
T9 -> T16
T15 -> T16
```

---

## Task Breakdown

### T1: Equações de Daniels em módulo próprio (`vdot/daniels.py`)

**What**: Mover (não copiar) as equações puras de `calibrate_vdot.py` para `app/vdot/daniels.py` (`vo2_cost`, `fraction_vo2max`, `calculate_vdot`, `speed_for_vo2`, `pace_for_fraction`, `equivalent_time`) e converter o script CLI em consumidor fino (imports do módulo; comportamento do CLI inalterado).
**Where**: `backend/app/vdot/daniels.py` (new); `backend/app/vdot/calibrate_vdot.py` (modify — imports)
**Depends on**: None
**Reuses**: código existente de `calibrate_vdot.py:58-102` (move puro, assinaturas idênticas)
**Requirement**: base de POT-07, POT-08, POT-10, POT-14
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `daniels.py` com as 6 funções puras; `calibrate_vdot.py` importa delas e o CLI segue gerando zonas idênticas (teste: `gerar_zonas(50.2)` produz o mesmo JSON calibrado)
- [x] Pins literais contra cálculo manual: `calculate_vdot(5000, 1163.83) ≈ 51.62`; `equivalent_time(50.2, 42.195) ≈ 11401` s (4:30,2/km — bate com o pace de maratona do `vdot_zones.json`); inversibilidade `speed_for_vo2(vo2_cost(v)) ≈ v`
- [x] Testes: ≥ 5 novos em `test_vdot_daniels.py` (total ≥ 175)

**Tests**: unit (`backend/tests/test_vdot_daniels.py`)
**Gate**: quick
**Commit**: `refactor(vdot): extract daniels equations to own module`

---

### T2: Calibração vigente (`vdot/calibration.py`)

**What**: Criar `load_calibration(path) -> Calibration` (dataclass: `vdot`, `source`, `test_date`, `distance_m`, `time_s`) lendo os campos raiz do `vdot_zones.json`; ausente/inválido → `ZoneConfigError` (mesma exceção de `zones.py` — é o mesmo arquivo).
**Where**: `backend/app/vdot/calibration.py` (new)
**Depends on**: None
**Reuses**: padrão de parse/erro de `app/vdot/zones.py`
**Requirement**: POT-07, POT-16
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `Calibration` carrega o JSON real (`vdot=50.2`, `source="10K em 41:15"`, `test_date=2026-10-03`, `distance_m=10012`, `time_s=2475`)
- [x] Arquivo ausente/inválido/sem campos raiz → `ZoneConfigError` (o endpoint vira 500 — POT-16)
- [x] Testes: ≥ 4 novos em `test_vdot_calibration.py` (total ≥ 179)

**Tests**: unit (`backend/tests/test_vdot_calibration.py`)
**Gate**: quick
**Commit**: `feat(vdot): load current calibration from zones file`

---

### T3: Data dos recordes pessoais (fix do mapper)

**What**: Corrigir `map_personal_records`: `pr_date` = data local de `activityStartDateTimeLocal` (ms, wall clock — mesma convenção de `start_time`), fallback `prStartTimeGmt` (payload real usa `Gmt`, o código lê `GMT`); fixture de `helpers.py` espelha o payload real do banco.
**Where**: `backend/app/garmin/mappers.py` (modify); `backend/tests/helpers.py` (modify — fixture com keys reais)
**Depends on**: None
**Reuses**: `_gmt_ms_to_naive_datetime` (ms → datetime naive); padrão de teste do `test_garmin_mappers.py`
**Requirement**: POT-05, POT-06
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] PR com `activityStartDateTimeLocal` → `pr_date` = data local (fixture espelha o payload real: `prStartTimeGmt` + `activityStartDateTimeLocal` + `activityStartDateTimeLocalFormatted`)
- [x] Sem `activityStartDateTimeLocal` → fallback `prStartTimeGmt`; sem nenhum → NULL
- [x] Re-upsert atualiza `pr_date` de linha existente (self-heal — teste de upsert 2×)
- [x] Testes: fixture corrigida + ≥ 4 novos/ajustados (total ≥ 183)

**Tests**: unit + integration (`test_garmin_mappers.py`, `test_garmin_upserts.py`)
**Gate**: full
**Commit**: `fix(sync): read personal record dates from real payload keys`

---

### T4: Predições de prova — model + mapper + upsert

**What**: Criar `RacePrediction` (`user_id`, `event`, `time_s`, `date`, `raw_json`; UNIQUE `(user_id, event)`), `map_race_predictions` (payload real da sonda: `time5K`→`5K`, `time10K`→`10K`, `timeHalfMarathon`→`HALF_MARATHON`, `timeMarathon`→`MARATHON`; `date` do `calendarDate`) e `upsert_race_predictions` (por evento, sem delete).
**Where**: `backend/app/db/models.py`, `backend/app/garmin/mappers.py`, `backend/app/garmin/upserts.py` (modify/extend); `backend/tests/helpers.py` (fixture `RACE_PREDICTIONS_PAYLOAD` do payload real)
**Depends on**: None
**Reuses**: convenções de `PersonalRecord` + padrão do `upsert_records`
**Requirement**: POT-02
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Mapper com o payload da sonda (15/10) → 4 eventos com `time_s` e `date`; evento ausente/inválido fica de fora; `raw_json` preservado
- [x] Upsert 2× idempotente por `(user_id, event)`; evento ausente no payload → linha existente intocada (sem delete)
- [x] Testes: ≥ 6 novos (mapper + upsert no Postgres) (total ≥ 189)

**Tests**: unit + integration (`test_garmin_mappers.py`, `test_garmin_upserts.py`)
**Gate**: full
**Commit**: `feat(sync): add race predictions model, mapper and upsert`

---

### T5: Etapa de sync de predições (gateway + service)

**What**: Adicionar `get_race_predictions()` ao gateway (1 `_call`) e `_sync_predictions` ao service — após `_sync_records`, antes de `_sync_pmc`; tolerante (warning `{tipo: "predictions"}`, sync continua); `stats["predictions"]` no `_initial_stats` e no passo; `FakeGateway` estendido com o fixture (happy + cenário de falha).
**Where**: `backend/app/garmin/client.py`, `backend/app/garmin/service.py` (modify); `backend/tests/fake_garmin.py` (extend)
**Depends on**: T4
**Reuses**: padrão tolerante do `_sync_records`; padrão `_call` do gateway; cenários de falha do `fake_garmin.py`
**Requirement**: POT-01, POT-03, POT-04
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Passo executa após records com exatamente 1 chamada do orçamento (`calls_made` conferido no teste)
- [x] Falha no passo → warning `{tipo: "predictions"}`, job termina `done`, stats com `predictions: 0`; happy path grava 4 eventos
- [x] Ordem preservada: records → predictions → pmc (teste confere `stats["step"]` final e contadores)
- [x] Testes: ≥ 5 novos (total ≥ 194)

**Tests**: integration (`test_garmin_service.py`)
**Gate**: full
**Commit**: `feat(sync): sync garmin race predictions after records`

---

### T6: `potential/calc.py` — timeline VDOT + demonstrado + Riegel

**What**: Criar as funções puras da timeline: `CANONICAL` (5K/10K/21.097,5/42.195), `riegel_time(anchor_s, anchor_m, target_m, exponent=1.06)`, `timeline_points(prs, races, calibration)` (PR canônico datado source=`pr`; prova `eventType=race` source=`prova` com dedup por data contra PR; teste de calibração source=`teste`; PR sem data/inválido fora) e `demonstrated(points)` (maior VDOT).
**Where**: `backend/app/potential/calc.py`, `backend/app/potential/__init__.py` (new)
**Depends on**: T1
**Reuses**: `calculate_vdot` de `vdot/daniels.py` (T1); postura de função pura do `activities/metrics.py`
**Requirement**: POT-07 (demonstrado/gap), POT-08, POT-09
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `riegel_time` com pins manuais (1163,83 s @5000 → 10K ≈ 2426,5 s; meia ≈ 5353,8 s; maratona ≈ 11162,4 s; expoente fixo 1.06)
- [x] Timeline com dados reais de fixture: PRs canônicos datados + prova deduplicada na data da maratona + teste de calibração; `vdot` de cada ponto = `calculate_vdot`; PR sem data fora da timeline
- [x] `demonstrated` = maior VDOT (fixture real → ≈ 51,62 do 5K; o "~53" do plano §9.5 é a tabela tabulada — a forma fechada é a fonte da verdade do app); lista vazia → `None`
- [x] Determinismo: mesma entrada → mesmos valores (teste repete)
- [x] Testes: ≥ 8 novos em `test_potential_calc.py` (total ≥ 202)

**Tests**: unit (`backend/tests/test_potential_calc.py`)
**Gate**: quick
**Commit**: `feat(potential): add vdot timeline and riegel pure calc`

---

### T7: `potential/calc.py` — predictions + decay

**What**: Completar o calc: `predictions(garmin, pr_5k_s, current_vdot, prs)` — por distância canônica: `garmin_s`, `riegel_s` ancorado no PR de 5K (NULL sem âncora), `vdot_s = equivalent_time(current_vdot, d)`, `average_s` (média aritmética só das presentes), `pr_s` + `pr_date`; e `decay(prs, current_vdot)` — `real_pace_s`, `ideal_pace_s`, `delta_pct = (ideal−real)/ideal × 100`.
**Where**: `backend/app/potential/calc.py` (extend)
**Depends on**: T6
**Reuses**: `equivalent_time` (T1); `CANONICAL`/estrutura de `predictions` de T6
**Requirement**: POT-10, POT-14
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Sem PR de 5K → `riegel_s=None` em todas as distâncias (âncora não substituída) e média recalcula com as presentes
- [x] Estimativa ausente (garmin null, pós-fix) fora da média; todas ausentes → `average_s=None`
- [x] Decay: distâncias sem PR ficam de fora; sinal pinado (real mais lento → delta negativo = gap); fixture real: maratona com maior gap
- [x] Testes: ≥ 6 novos (total ≥ 208)

**Tests**: unit (`backend/tests/test_potential_calc.py`)
**Gate**: quick
**Commit**: `feat(potential): add predictions and decay pure calc`

---

### T8: `potential/service.py` — montagem do payload

**What**: Criar `get_potential(db, days, calibration)`: PRs canônicos, predições por evento, `load` últimos `days` (ORDER BY date DESC LIMIT days, reversed; `current` = última linha), corridas `(start_time, raw_json)` → pontos VO2max + provas (filtro em Python — escala pessoal, AD-001), montagem via `calc` (T6/T7) com `vdot.current` da calibração.
**Where**: `backend/app/potential/service.py` (new)
**Depends on**: T1, T2, T6, T7
**Reuses**: padrão de query do `activities/service.py`; `load_calibration` (T2)
**Requirement**: POT-07, POT-08, POT-09, POT-10, POT-12, POT-13, POT-14, POT-15
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Payload com os 5 blocos montados a partir de seeds no Postgres (chamada direta ao service); PMC com `days` respeitado e `current` do último dia
- [x] Sem `load` → `pmc=None`; sem `vO2MaxValue` → `vo2max=None`; sem PRs canônicos → `decay=[]` e timeline só com o teste de calibração
- [x] Nenhuma importação do gateway Garmin (POT-15 — verificação por inspeção + teste de ausência de import)
- [x] Testes: ≥ 6 novos em `test_potential_api.py` (chamadas diretas ao service) (total ≥ 214)

**Tests**: integration (`backend/tests/test_potential_api.py`)
**Gate**: full
**Commit**: `feat(potential): assemble potential payload from own database`

---

### T9: `GET /api/potential` — router + mount

**What**: Criar o router (`days: int = Query(180, ge=1, le=365)` → 422 antes da query; `ZoneConfigError` → 500 "zonas VDOT não configuradas"; modelos Pydantic inline) e montar na app.
**Where**: `backend/app/potential/router.py` (new); `backend/app/main.py` (modify)
**Depends on**: T8
**Reuses**: padrão `get_zone_config`/500 do `activities/router.py`; `Query` com bounds (padrão TRN-06)
**Requirement**: POT-11, POT-16 (e superfície HTTP de POT-07..POT-15)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `GET /api/potential` responde 200 com payload completo (seeds); `days=0`/`366` → 422; `days=365` → 200
- [x] `vdot_zones.json` ausente (monkeypatch do path) → 500 "zonas VDOT não configuradas"
- [x] `pmc=null` e `vo2max=null` atravessam o HTTP como JSON null (bancos vazios)
- [x] Testes: ≥ 6 novos (TestClient) (total ≥ 220)

**Tests**: integration (`backend/tests/test_potential_api.py`)
**Gate**: full
**Commit**: `feat(potential): expose potential panel api`

---

### T10: Cliente tipado + formatadores (lib)

**What**: Estender `lib/api.ts` com os tipos de `PotentialOut` (espelho dos modelos do T9) e `getPotential(days = 180)`; adicionar `formatVdot` ao `lib/format.ts` (1 casa, vírgula PT-BR).
**Where**: `frontend/src/lib/api.ts`, `frontend/src/lib/format.ts` (modify)
**Depends on**: T9 (contrato estável; tipos espelham os modelos Pydantic)
**Reuses**: `parseError`/padrão `cache: "no-store"` do próprio `api.ts`; `formatPace`/`formatDuration` existentes
**Requirement**: base de POT-17..POT-29 (contrato)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Tipos espelham o payload do T9 (blocos nullable onde o backend manda null)
- [x] `getPotential` com `days` opcional e tratamento de erro via `parseError`
- [x] `npm run build` + `npm run lint` verdes

**Tests**: none (cobertura frontend = build gate + UAT da Phase 5, matriz)
**Gate**: build (frontend)
**Commit**: `feat(ui): add typed potential api client`

---

### T11: Timeline VDOT com faixa honesta (`VdotTimeline.tsx`)

**What**: Componente Recharts: ScatterChart com um ponto por entrada da timeline (X = data, Y = VDOT), `ReferenceLine` no VDOT corrente (tracejada, rotulada), `ReferenceArea` entre corrente e demonstrado (faixa honesta) e tooltip com label/data/distância/tempo/VDOT.
**Where**: `frontend/src/components/potential/VdotTimeline.tsx` (new)
**Depends on**: T10
**Reuses**: tokens visuais do tema (padrão do `SplitsChart`); `formatVdot` (T10); tipos `TimelinePoint` (T10)
**Requirement**: POT-17
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Pontos, linha do corrente e faixa renderizam com o payload real (dados do usuário)
- [x] Responsivo em 390px sem scroll horizontal; cores legíveis no tema escuro
- [x] `npm run build` + `npm run lint` verdes

**Tests**: none (build gate + UAT)
**Gate**: build (frontend)
**Commit**: `feat(ui): add vdot timeline chart with honest range`

---

### T12: Tabelas de previsões e decaimento

**What**: `PredictionsTable` (linhas por distância; colunas Garmin/Riegel/VDOT/média honesta/PR com data; "—" para NULL; nota explicando a média honesta) e `DecayTable` (real vs ideal por distância + Δ%; maior gap — delta mais negativo — destacado).
**Where**: `frontend/src/components/potential/PredictionsTable.tsx`, `frontend/src/components/potential/DecayTable.tsx` (new)
**Depends on**: T10
**Reuses**: padrão visual da tabela de consistência do `WorkoutDetail.tsx`; `formatDuration`/`formatPace` (T10/existentes)
**Requirement**: POT-21, POT-22, POT-28, POT-29
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Previsões: 4 linhas × 4 estimativas + PR; célula NULL → "—"; média honesta recalculada só com as presentes (nota visível)
- [x] Decay: Δ% com sinal; maior gap destacado visualmente; distâncias sem PR ausentes
- [x] `npm run build` + `npm run lint` verdes

**Tests**: none (build gate + UAT)
**Gate**: build (frontend)
**Commit**: `feat(ui): add predictions and decay tables`

---

### T13: Curva PMC (`PmcChart.tsx`)

**What**: ComposedChart Recharts: `Bar` TSB (semitransparente) + `Line` CTL + `Line` ATL, `ReferenceLine y=0`, eixos rotulados; cards do último dia (CTL/ATL/TSB/ACWR — ACWR "—" quando NULL).
**Where**: `frontend/src/components/potential/PmcChart.tsx` (new)
**Depends on**: T10
**Reuses**: padrão de rótulo de eixos (a803911); `formatVdot` para 1 casa nos cards
**Requirement**: POT-23, POT-24
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] TSB/CTL/ATL renderizados com o histórico real (182 dias) em janela de 180
- [x] Cards do último dia com ACWR "—" quando NULL (janela 28d incompleta)
- [x] Responsivo 390px; `npm run build` + `npm run lint` verdes

**Tests**: none (build gate + UAT)
**Gate**: build (frontend)
**Commit**: `feat(ui): add pmc fitness fatigue chart`

---

### T14: Tendência VO2max (`Vo2maxTrend.tsx`)

**What**: LineChart Recharts dos pontos `vo2max` com selo visual "estimativa do relógio" e nota de hierarquia (provas/testes > algoritmo — AD-005).
**Where**: `frontend/src/components/potential/Vo2maxTrend.tsx` (new)
**Depends on**: T10
**Reuses**: padrão Recharts do T11/T13
**Requirement**: POT-26
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Linha com os pontos reais + selo "estimativa" + nota de hierarquia visível
- [x] `npm run build` + `npm run lint` verdes

**Tests**: none (build gate + UAT)
**Gate**: build (frontend)
**Commit**: `feat(ui): add watch vo2max trend with estimate badge`

---

### T15: Composição do painel (`PotentialPanel.tsx` + rota)

**What**: Client component que busca `/api/potential` e compõe as seções condicionalmente: card da lacuna com narrativa §9.5 + `VdotTimeline`, `PredictionsTable`, `PmcChart` (com `pmc=null` → estado vazio orientando o sync), `Vo2maxTrend` (só se `vo2max != null`), `DecayTable` (só se não vazio); estados loading/error/empty; troca o placeholder da rota.
**Where**: `frontend/src/components/potential/PotentialPanel.tsx` (new); `frontend/src/app/potencial/page.tsx` (modify)
**Depends on**: T10, T11, T12, T13, T14
**Reuses**: padrão de estados do `WorkoutDetail.tsx`; empty state do `WorkoutsList.tsx`
**Requirement**: POT-18, POT-19, POT-20, POT-25, POT-27 (composição das seções)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Card da lacuna (`gap_pct`) com a narrativa honesta de §9.5; `pmc=null` → estado vazio apontando o sync; `vo2max=null` → bloco ausente
- [ ] Erro de API → mensagem inline sem quebrar a nav; loading visível; painel legível em 390px
- [ ] `/potencial` renderiza o painel (placeholder removido); `npm run build` + `npm run lint` verdes

**Tests**: none (build gate + UAT)
**Gate**: build (frontend)
**Commit**: `feat(ui): assemble potential panel page`

---

### T16: Validação real (sync + UAT + fechamento)

**What**: Rebuild dos containers, sync real (self-heal das datas dos PRs + snapshot de predições), UAT do `/potencial` com os dados reais contra os valores esperados, e fechamento (docs + STATE handoff).
**Where**: `docker-compose.yml` (rebuild backend/frontend); `docs/` + `.specs/STATE.md` (documentação)
**Depends on**: T9, T15
**Reuses**: procedimento de UAT do workouts-list (04dd0ba); comandos de build do README
**Requirement**: Success Criteria (todos os blocos com dados reais) + POT-01..POT-29 (verificação integrada)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Sync real conclui com `predictions` no stats e `pr_date` preenchido nas 7 PRs (self-heal do T3 confirmado no banco)
- [ ] `/potencial` real: timeline com os pontos (out/2024 → out/2026), linha 50,2, faixa até ~53, lacuna ~95%; 4 estimativas × 4 distâncias com PR datado; PMC com o histórico; VO2max com selo; decay com maratona destacada
- [ ] `GET /api/potential` sem nenhuma chamada Garmin (verificação: nenhum import do gateway em `potential/`)
- [ ] Suite completa verde (≥ 220 testes); `npm run build` + `npm run lint` verdes
- [ ] STATE.md handoff atualizado (feature concluída, pendências, próximo passo)

**Tests**: none (validação integrativa — o Verifier roda `validate_state.py` a seguir)
**Gate**: build (backend + frontend)
**Commit**: `docs(activities): document potential panel validation`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1 · T2 · T3 · T4 → T5
Phase 2:  T1 → T6 → T7
Phase 3:  T8 → T9
Phase 4:  T10 → T11 · T12 · T13 · T14 → T15
Phase 5:  T16
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**How phase-based execution works:**

At Execute, the agent counts total tasks and packs phases into **task-budgeted batches** (~7 tasks per worker, whole phases - the benchmarked sweet spot is ~20 tasks → ~3 workers). A **phase** is the semantic/dependency unit; a **batch** is one or more *consecutive whole phases* assigned to one worker. The cut only ever lands on a phase boundary. When packing yields more than one batch (> ~8 tasks), the agent offers to dispatch batch sub-agents.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: daniels.py (move + CLI fino) | 1 módulo + 1 refactor de imports | ✅ Granular |
| T2: calibration.py | 1 módulo + dataclass | ✅ Granular |
| T3: fix data dos PRs | 1 mapper + 1 fixture | ✅ Granular |
| T4: predições model+mapper+upsert | 1 tabela + mapper + upsert (padrão do T1 workouts) | ✅ Granular |
| T5: etapa de sync | 1 método gateway + 1 step service | ✅ Granular |
| T6: calc timeline | funções puras de 1 módulo | ✅ Granular |
| T7: calc predictions/decay | funções puras do mesmo módulo | ✅ Granular |
| T8: service assembly | 1 service | ✅ Granular |
| T9: router + mount | 1 endpoint | ✅ Granular |
| T10: lib api+format | extensão da lib (contrato) | ✅ Granular |
| T11: VdotTimeline | 1 componente | ✅ Granular |
| T12: 2 tabelas | 2 componentes, mesmo padrão visual | ⚠️ OK (coesos) |
| T13: PmcChart | 1 componente | ✅ Granular |
| T14: Vo2maxTrend | 1 componente | ✅ Granular |
| T15: PotentialPanel + page | composição + swap de rota | ✅ Granular |
| T16: UAT real + fechamento | validação integrativa | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | nó isolado na Phase 1 | ✅ Match |
| T2 | None | nó isolado na Phase 1 | ✅ Match |
| T3 | None | nó isolado na Phase 1 | ✅ Match |
| T4 | None | nó isolado na Phase 1 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T1 | T1 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T1, T2, T6, T7 | T1/T2/T6/T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | T9 | (Phase 4 inicia após Phase 3) T9 → T10 implícito na sequência de fases; corpo declara T9 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T10 | T10 → T12 | ✅ Match |
| T13 | T10 | T10 → T13 | ✅ Match |
| T14 | T10 | T10 → T14 | ✅ Match |
| T15 | T10..T14 | T10..T14 → T15 | ✅ Match |
| T16 | T9, T15 | T9 → T16, T15 → T16 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Domain puro (`daniels.py`) | unit | unit (`test_vdot_daniels.py`) | ✅ OK |
| T2 | Domain puro (`calibration.py`) | unit | unit (`test_vdot_calibration.py`) | ✅ OK |
| T3 | Mapper/upserts | unit + integration | unit + integration | ✅ OK |
| T4 | Mapper/upserts + model | unit + integration (model = none, coberto) | unit + integration | ✅ OK |
| T5 | Sync service | integration | integration | ✅ OK |
| T6 | Domain puro (`calc.py`) | unit | unit | ✅ OK |
| T7 | Domain puro (`calc.py`) | unit | unit | ✅ OK |
| T8 | Service (`potential/`) | integration | integration | ✅ OK |
| T9 | Router (`potential/`) | integration | integration | ✅ OK |
| T10 | Frontend lib | none (build gate) | none | ✅ OK |
| T11 | Frontend component | none (build gate) | none | ✅ OK |
| T12 | Frontend components | none (build gate) | none | ✅ OK |
| T13 | Frontend component | none (build gate) | none | ✅ OK |
| T14 | Frontend component | none (build gate) | none | ✅ OK |
| T15 | Frontend component + page | none (build gate) | none | ✅ OK |
| T16 | Infra/validação | none | none | ✅ OK |

---

**Requirement coverage**: POT-01..POT-16 (sync + endpoint) → T1..T9 · POT-17..POT-20 (timeline UI) → T11, T15 · POT-21..POT-22 (previsões UI) → T12 · POT-23..POT-25 (PMC UI) → T13, T15 · POT-26..POT-27 (VO2max) → T14, T15 · POT-28..POT-29 (decay) → T12 · Success Criteria integrados → T16. **29/29 mapeadas, 0 órfãs.**
