# Lista de Treinos + Splits — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/workouts-list/design.md`
**Status**: In Progress (Lote 1: T1–T7 em execução)

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes (`uv run pytest` no Postgres do compose); `frontend/AGENTS.md` (ler docs do Next 16 antes de codar frontend); lições L-001/L-002 (literais do spec nos testes; critérios com números são tetos exatos). Sem CONTRIBUTING/CI/lint de backend — fortes defaults onde não há padrão.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Config (`Settings.vdot_zones_path`) | unit | default + override por env (padrão `test_infra.py`; literais do spec — L-001) | `backend/tests/test_workouts_config.py` | `cd backend; uv run pytest` |
| Domain puro (`vdot/zones.py`, `activities/metrics.py`, `activities/infer.py`) | unit | 1:1 com ACs; cortes de fronteira exatos; valores fixados contra cálculo manual (Independent Test); regras de prioridade completas | `backend/tests/test_vdot_zones.py`, `test_activity_metrics.py`, `test_activity_infer.py` | `cd backend; uv run pytest` |
| Mapper/upserts (campos novos de split) | unit + integration (Postgres real) | `averageRunCadence`/`averageTemperature` mapeados; NULL quando ausentes; idempotência 2× | `backend/tests/test_garmin_mappers.py`, `test_garmin_upserts.py` | `cd backend; uv run pytest` |
| Service + Router (`activities/`) | integration (TestClient + banco real) | todas as rotas happy+edge+error (422/404/500 zonas); paginação; filtro; payload completo | `backend/tests/test_activities_api.py` | `cd backend; uv run pytest` |
| Models / schema | none | colunas novas cobertas pelos testes de mapper/upserts | - | build gate only |
| Infra (Dockerfile `COPY data`) | none | imagem contém `data/vdot_zones.json`; endpoint de zonas responde no container | - | build gate only |
| Frontend (`lib/`, `components/`, `app/`) | none | `npm run build` + `npm run lint`; UAT manual nas tasks de tela (mesmo padrão do garmin-sync) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (suite roda no banco de teste do compose).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks com testes unitários | `cd backend; uv run pytest` |
| Full | Após tasks com testes de integração (mesma suite) | `cd backend; uv run pytest` |
| Build | Conclusão de fase / infra / frontend | backend: `cd backend; uv run pytest` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação (dados + zonas)

```
T2 -> T3
```

### Phase 2: Domínio de leitura (funções puras)

```
T4
T5
```

### Phase 3: API de leitura

```
T3 -> T6
T4 -> T6
T5 -> T6
T1 -> T7
T3 -> T7
T4 -> T7
T5 -> T7
```

### Phase 4: Frontend

```
T7 -> T8
T8 -> T10
T9 -> T10
T8 -> T11
T10 -> T11
T11 -> T12
```

### Phase 5: Validação real

```
T6 -> T13
T7 -> T13
T10 -> T13
T11 -> T13
T12 -> T13
```

---

## Task Breakdown

### T1: Cadência e temperatura por volta (model + mapper)

**What**: Adicionar `avg_cadence` e `avg_temperature` (FLOAT NULL) ao `Split`, mapear `averageRunCadence`/`averageTemperature` em `map_splits` e garantir o upsert idempotente com os campos novos.
**Where**: `backend/app/db/models.py`, `backend/app/garmin/mappers.py` (modify)
**Depends on**: None
**Reuses**: `map_splits` (normalização lapDTOs), `upsert_splits` (dedup por `(activity_id, idx)`), padrão de teste do `test_garmin_mappers.py`
**Requirement**: TRN-29, TRN-30, TRN-31
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `Split` com `avg_cadence`/`avg_temperature` nullable
- [x] `map_splits` extrai os 2 campos; payload sem eles → `None` (nomes aterrissados pela sonda real, não pelos da listagem)
- [x] `upsert_splits` grava os campos e mantém contagens estáveis ao reexecutar
- [x] Testes: mapper com/sem os campos + upsert 2× no Postgres (≥ 5 novos; total ≥ 102)

**Tests**: unit + integration (`test_garmin_mappers.py`, `test_garmin_upserts.py`)
**Gate**: full
**Commit**: `feat(sync): store cadence and temperature per split`

---

### T2: Caminho do arquivo de zonas (config + imagem)

**What**: Adicionar `vdot_zones_path` ao `Settings` (default `data/vdot_zones.json`) e copiar `data/` para a imagem do backend.
**Where**: `backend/app/core/config.py`, `backend/Dockerfile` (modify)
**Depends on**: None
**Reuses**: Padrão `Settings`/pydantic-settings; Dockerfile existente
**Requirement**: TRN-14, TRN-15 (suporte de infra), Success Criteria
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `vdot_zones_path: str = "data/vdot_zones.json"` com override por env `VDOT_ZONES_PATH`
- [x] `COPY data ./data` no Dockerfile (imagem contém o JSON calibrado)
- [x] Testes: default + override (≥ 2 novos; total ≥ 104)

**Tests**: unit (`backend/tests/test_workouts_config.py`)
**Gate**: quick
**Commit**: `chore(infra): ship vdot zones file in backend image`

---

### T3: Configuração de zonas VDOT (load + classify + meta)

**What**: Criar `app/vdot/zones.py`: carregar o JSON calibrado, classificar pace em zona pelos cut points de midpoint e expor metadados (rótulo, faixa exibível, cor) para legenda e frontend.
**Where**: `backend/app/vdot/zones.py` (new)
**Depends on**: T2
**Reuses**: `backend/data/vdot_zones.json` (VDOT 50.2); espírito de função pura do `calibrate_vdot.py`
**Requirement**: TRN-14, TRN-15, TRN-17 (cores no backend)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `load_zone_config(path)` parseia o JSON; arquivo ausente/inválido → `ZoneConfigError`
- [x] `classify(speed_ms)` aplica os 4 cut points de midpoint; abaixo do primeiro → easy, acima do último → repetition; pace inválido → `None`
- [x] Cortes exatos com VDOT 50.2 fixados em testes (4:41 / 4:29 / 4:07 / 3:45 por km — literais do spec, L-001)
- [x] `meta()` devolve as 5 zonas com chave, rótulo, faixa e cor; cor de `interval` ≠ cor reservada à linha de FC
- [x] Testes (≥ 8 novos; total ≥ 112)

**Tests**: unit (`backend/tests/test_vdot_zones.py`)
**Gate**: quick
**Commit**: `feat(vdot): add zone config loading and pace classification`

---

### T4: Métricas de consistência (funções puras)

**What**: Criar `app/activities/metrics.py`: metades por distância acumulada e o bloco `consistency` (equilíbrio, drift cardíaco, decoupling, fade de cadência) com gate ≥8000m e ≥4 voltas.
**Where**: `backend/app/activities/metrics.py` (new)
**Depends on**: None
**Reuses**: Convenções numéricas de `app/garmin/pmc.py`; `__init__.py` de pacote do `app/garmin/`
**Requirement**: TRN-21, TRN-22, TRN-23, TRN-25
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `split_halves` divide por distância acumulada (≥50% fecha a 1ª metade; volta que atravessa fica na 1ª)
- [x] `consistency_metrics` devolve Δ pace (s/km + %), Δ FC (bpm), decoupling (%) e Δ cadência (spm) — cálculo conferido contra valores manuais em fixtures
- [x] Gate: `distance_m < 8000` ou `< 4` voltas → `None`; cadência só quando ≥2 voltas com cadência por metade
- [x] Determinismo: mesma entrada → mesmos valores (teste repete e compara)
- [x] Testes (≥ 8 novos; total ≥ 120)

**Tests**: unit (`backend/tests/test_activity_metrics.py`)
**Gate**: quick
**Commit**: `feat(activities): add consistency metrics engine`

---

### T5: Tipo inferido + estrutura (funções puras)

**What**: Criar `app/activities/infer.py`: `infer_type` com as 7 regras na ordem de prioridade do spec e `derive_structure` (port do validado).
**Where**: `backend/app/activities/infer.py` (new)
**Depends on**: None
**Reuses**: Lógica de grupos do `_count_run_groups` + `derive_structure` (`garmin_mcp/.opencode/skills/generate-run-summary-image/generate_image.py`, referência somente leitura)
**Requirement**: TRN-07, TRN-32
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Prioridade: prova (eventType race) > intervalado (≥2 grupos interval/repetition com recuperação entre eles) > limiar (bloco ≥3 voltas threshold somando ≥2000m) > tempo (bloco ≥3 marathon somando ≥2000m) > progressivo (2ª metade ≤92% do pace da 1ª) > longao (≥16000m) > facil
- [x] Voltas sem pace/zona não contam para blocos; grupos consideram recovery por zona OU intensityType REST/RECOVERY/WALK
- [x] `derive_structure` soma passos consecutivos por intensity_type ("Aquecimento 2,0km + Corrida 7,1km…")
- [x] Um teste por regra + um de prioridade + edges (strides reais da sonda como fixture) (≥ 8 novos; total ≥ 128)

**Tests**: unit (`backend/tests/test_activity_infer.py`)
**Gate**: quick
**Commit**: `feat(activities): add workout type inference`

---

### T6: Endpoint de lista `GET /api/activities`

**What**: Criar service + router do domínio `activities` e montar na app: lista paginada, filtro corridas/todas, ordenação estável, tipo inferido sem N+1.
**Where**: `backend/app/activities/__init__.py`, `service.py`, `router.py` (new); `backend/app/main.py` (modify)
**Depends on**: T3, T4, T5
**Reuses**: `get_db`, padrão Pydantic do `garmin/router.py`, `DEFAULT_USER_ID`
**Requirement**: TRN-04, TRN-05, TRN-06, TRN-07, TRN-09, TRN-28
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Default = corridas (`running`/`trail_running`), `start_time DESC` com desempate `id DESC`; `activity_type=all` inclui as demais
- [x] `limit` (default 30, máx 100) + `offset`; fora de [1,100] ou offset<0 → 422 antes da query; resposta `{items, total, limit, offset}`
- [x] `pace_s` derivado (`duration_s×1000/distance_m` quando >0, senão `null`); não-corrida com `inferred_type=null`
- [x] Voltas da página em 1 query `IN` (sem N+1); nenhuma importação do gateway Garmin neste domínio
- [x] TestClient + banco real: happy, filtro, paginação além do fim (`items=[]`), 422, vazio (≥ 8 novos; total ≥ 136)

**Tests**: integration (`backend/tests/test_activities_api.py`)
**Gate**: full
**Commit**: `feat(activities): expose activities list api`

---

### T7: Endpoint de detalhe `GET /api/activities/{id}`

**What**: Completar service + router com o payload do detalhe: voltas classificadas por zona, metadados de zonas, consistência, contexto (sono/HRV/RHR/temperatura) e estrutura.
**Where**: `backend/app/activities/service.py`, `router.py` (extend)
**Depends on**: T1, T3, T4, T5
**Reuses**: `zones.classify`/`meta` (T3), `metrics` (T4), `infer` (T5), colunas novas de split (T1)
**Requirement**: TRN-13, TRN-15, TRN-19, TRN-21, TRN-22, TRN-26, TRN-27, TRN-28, TRN-32
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] 404 para id inexistente; 500 "zonas VDOT não configuradas" quando o arquivo falha
- [x] Cada volta com pace válido em exatamente 1 zona; pace inválido → `zone=null`; `km_label` acumulado
- [x] `zones` com as 5 metas (chave/rótulo/faixa/cor); `consistency` com gate do T4 (`null` quando <8000m ou <4 voltas)
- [x] Contexto: sono/HRV/RHR da data local de início (cada um `null` quando ausente); `temperature_c` média ponderada por duração quando ≥1 volta tem temperatura
- [x] `structure` derivada quando há intensity_type; nenhuma chamada ao gateway Garmin
- [x] TestClient + banco real: corrida fácil, corrida com strides (voltas curtas), sem splits, não-corrida, 404, zonas ausentes (≥ 10 novos; total ≥ 146)

**Tests**: integration (`backend/tests/test_activities_api.py`)
**Gate**: full
**Commit**: `feat(activities): expose activity detail api`

---

### T8: Cliente de API tipado + formatadores

**What**: Estender `lib/api.ts` com tipos e fetchers de lista/detalhe; criar `lib/format.ts` (pace, duração, distância, cadência, temperatura em PT-BR).
**Where**: `frontend/src/lib/api.ts` (modify), `frontend/src/lib/format.ts` (new)
**Depends on**: T7
**Reuses**: `parseError`, `API_BASE`; port de `format_pace`/`format_duration` do validado
**Requirement**: TRN-06, TRN-11, TRN-12 (suporte)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Tipos espelham os contratos do design (`ActivityListOut`, `ActivityDetailOut` — zonas, consistência, contexto)
- [x] `getActivities({activityType, limit, offset})` e `getActivityDetail(id)` com tratamento de erro do padrão existente
- [x] Formatadores: pace `M:SS`, duração `H:MM:SS`/`M:SS`, km com vírgula, cadência, °C
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add typed activities api client and formatters`

---

### T9: Navegação dos 4 painéis + placeholders

**What**: Criar `Nav` (client, `usePathname`), montar no Header, criar `/hoje`, `/potencial`, `/saude` como placeholders e redirecionar `/` para `/treinos`.
**Where**: `frontend/src/components/Nav.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/{hoje,potencial,saude}/page.tsx`, `frontend/src/components/Header.tsx` (new/modify)
**Depends on**: None
**Reuses**: `Header.tsx`, tokens do `globals.css`; `redirect` do `next/navigation`
**Requirement**: TRN-01, TRN-02, TRN-03
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Docs do Next 16 relidos antes de codar (`frontend/node_modules/next/dist/docs/` — aviso do `frontend/AGENTS.md`)
- [x] Nav com os 4 painéis visível em qualquer página, ativo marcado (`pathname` === href ou `startsWith(href+"/")`), legível em 390px (linha rolável)
- [x] Placeholders com nome do painel + "em construção"; `/` redireciona para `/treinos`
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add panel navigation with placeholders`

---

### T10: Lista de treinos `/treinos`

**What**: Criar a página da lista com filtro corridas/todas, paginação "Carregar mais", badges e estados (vazio/erro).
**Where**: `frontend/src/app/treinos/page.tsx`, `frontend/src/components/workouts/WorkoutsList.tsx` (new)
**Depends on**: T8, T9
**Reuses**: `getActivities`, `formatPace`/`formatKm`, padrão de fetch/estado do `SyncButton`, `Nav`
**Requirement**: TRN-04, TRN-05, TRN-08, TRN-10, TRN-11, TRN-12
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Itens = Link para `/treinos/{id}` com data, nome, tipo inferido (rótulo PT-BR), distância, pace (ou duração no modo `all`), FC, badge "Avaliado" quando `evaluated`
- [x] Filtro corridas/todas reseta paginação; "Carregar mais" anexa a próxima página sem duplicatas
- [x] Banco vazio → estado vazio apontando o botão "Puxar do Garmin"; falha de API → mensagem inline sem quebrar a nav
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add workouts list page`

---

### T11: Detalhe do treino `/treinos/[id]`

**What**: Criar a página do detalhe: cabeçalho de métricas, faixa de contexto, tabela de consistência, estrutura — com o gráfico integrado na T12.
**Where**: `frontend/src/app/treinos/[id]/page.tsx`, `frontend/src/components/workouts/WorkoutDetail.tsx` (new)
**Depends on**: T8, T10
**Reuses**: `getActivityDetail`, formatadores, padrão `PageProps<"/treinos/[id]">` (params Promise, Next 16)
**Requirement**: TRN-16 (integração), TRN-18 (clamp no dado do gráfico), TRN-19, TRN-20, TRN-24, TRN-26, TRN-27
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `await params` no server page; id numérico validado (não-numérico → not found)
- [x] Cabeçalho: data, nome, tipo, distância, duração, pace, FC média/máx, cadência, elevação — cada métrica omitida quando `null`
- [x] Faixa de contexto: sono, HRV, RHR, temperatura — só o que existir; tabela de consistência com Δ pace ao lado do drift (TRN-24); oculta quando `consistency=null`
- [x] Sem splits → resumo + nota "sem voltas registradas", sem gráfico; 404 → "Treino não encontrado" + volta à lista; erro de API → mensagem inline
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add workout detail page`

---

### T12: Gráfico de splits (SVG próprio, largura proporcional)

**What**: Portar o renderer validado para `SplitsChart.tsx` (React SVG): barras de pace com largura proporcional à duração, cor por zona VDOT, linha de FC, relevo, legenda e tooltip.
**Where**: `frontend/src/components/workouts/SplitsChart.tsx` (new); integrado em `WorkoutDetail.tsx` (modify)
**Depends on**: T11
**Reuses**: Matemática de `calculate_chart_dimensions`/`generate_svg`/`generate_legend` (validado); cores vindas do payload (`zones.meta`)
**Requirement**: TRN-16, TRN-17, TRN-18
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Largura da barra = fração da duração da volta na área útil (pausa de 30s ≠ tiro de 3km); altura por pace clampado a [180, 420] s/km com mínimo de 2,5px
- [x] Linha de FC com ponto no meio de cada barra, na cor reservada (≠ cor de interval — TRN-17, vinda do payload); relevo atrás em eixo próprio
- [x] Rótulos: pace por volta (oculto quando a barra é estreita demais), km acumulado no eixo X nas marcas proporcionais, legenda das zonas presentes + FC
- [x] Tooltip por hover/tap com pace real (não clampado), FC, elevação, duração e zona; responsivo via viewBox; legível em 390px
- [x] `npm run build` e `npm run lint` passam

**Tests**: none (frontend sem infra de testes — matriz: build + UAT)
**Gate**: build
**Commit**: `feat(ui): add proportional splits chart`

---

### T13: Validação real + documentação

**What**: Validar lista e detalhe contra os dados reais do banco (compose no ar), conferir o gráfico com um treino fácil e um de strides, e documentar o painel no README.
**Where**: `README.md`
**Depends on**: T6, T7, T10, T11, T12
**Reuses**: Stack do compose; suite como regressão
**Requirement**: Success Criteria (todas as caixas)
**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `GET /api/activities` e `/api/activities/{id}` respondem com dados reais; tipo inferido bate com a expectativa em 3 treinos conhecidos (fácil, strides, longão)
- [ ] Gráfico renderiza com voltas de 100m (strides) e auto-lap 1km — larguras proporcionais visíveis; FC e relevo alinhados *(payload e rotas verificados; conferência visual pendente do usuário)*
- [x] Consistência de um longão ≥8km confere com cálculo manual; treino <8km sem tabela
- [x] Nenhuma chamada ao Garmin nos logs durante o uso dos painéis
- [x] Suite completa passa (≥ 146 testes); README ganha seção "Painel Treinos"
- [ ] UAT manual navegando em 390px (celular/DevTools) *(pendente conferência visual do usuário)*

**Tests**: none (UAT real com evidência; o Verificador independente roda depois por contrato da skill)
**Gate**: build
**Commit**: `docs(activities): document workouts panel validation`

---

## Phase Execution Map

```
Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5
```

Fases em sequência estrita; dentro da fase, tasks na ordem definida acima. Resumo em palavras: T2 abre caminho para T3; o domínio puro (T4, T5) alimenta os endpoints (T6, T7); T7 alimenta o cliente frontend (T8); a navegação (T9) e o cliente alimentam a lista (T10), que alimenta o detalhe (T11) e o gráfico (T12); tudo converge na validação real (T13).

**How phase-based execution works:**

13 tasks → packing em lotes de fases inteiras (~7 tasks/lote): **Lote 1 = Fases 1+2+3 (T1–T7, 7 tasks)** · **Lote 2 = Fases 4+5 (T8–T13, 6 tasks)**. Se o usuário aceitar sub-agentes, cada lote vira um worker sequencial; senão, execução inline no chat principal, uma task por vez. Verifier independente ao final, por contrato da skill.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Cadência/temperatura por volta | 2 arquivos coesos (entity+mapper) | ✅ Granular |
| T2: Config + imagem do arquivo de zonas | 2 arquivos de infra coesos | ✅ Granular |
| T3: zones.py | 1 arquivo (funções puras) | ✅ Granular |
| T4: metrics.py | 1 arquivo (funções puras) | ✅ Granular |
| T5: infer.py | 1 arquivo (funções puras) | ✅ Granular |
| T6: Endpoint de lista | 1 endpoint (service+router+wiring) | ✅ Granular |
| T7: Endpoint de detalhe | 1 endpoint | ✅ Granular |
| T8: api.ts + format.ts | 2 arquivos coesos de suporte | ✅ Granular |
| T9: Nav + placeholders + redirect | 1 entrega de navegação (6 mini-arquivos) | ✅ Granular |
| T10: Página da lista | 1 página + 1 componente | ✅ Granular |
| T11: Página do detalhe | 1 página + 1 componente | ✅ Granular |
| T12: SplitsChart | 1 componente | ✅ Granular |
| T13: UAT + docs | 1 entrega (validação) | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | Fase 1, nó solto | ✅ Match |
| T2 | None | Fase 1, origem | ✅ Match |
| T3 | T2 | Fase 1: `T2 -> T3` | ✅ Match |
| T4 | None | Fase 2, nó solto | ✅ Match |
| T5 | None | Fase 2, nó solto | ✅ Match |
| T6 | T3, T4, T5 | Fase 3: `T3, T4, T5 -> T6` | ✅ Match |
| T7 | T1, T3, T4, T5 | Fase 3: `T1, T3, T4, T5 -> T7` | ✅ Match |
| T8 | T7 | Fase 4: `T7 -> T8` | ✅ Match |
| T9 | None | Fase 4, origem | ✅ Match |
| T10 | T8, T9 | Fase 4: `T8, T9 -> T10` | ✅ Match |
| T11 | T10 | Fase 4: `T10 -> T11` | ✅ Match |
| T12 | T11 | Fase 4: `T11 -> T12` | ✅ Match |
| T13 | T6, T7, T10, T11, T12 | Fase 5: 5 setas entrando em `T13` | ✅ Match |

> Dependências apontam sempre para trás (T6/T7 dependem da Fase 1–2; T8–T13 da Fase 3–4) — nenhum forward-phase dependency.

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Mapper (unit) + upserts (integration) | unit + integration | unit + integration | ✅ OK |
| T2 | Config (unit) + infra (none) | unit | unit | ✅ OK |
| T3 | Domain puro | unit | unit | ✅ OK |
| T4 | Domain puro | unit | unit | ✅ OK |
| T5 | Domain puro | unit | unit | ✅ OK |
| T6 | Service + Router | integration | integration | ✅ OK |
| T7 | Service + Router | integration | integration | ✅ OK |
| T8 | Frontend | none | none | ✅ OK |
| T9 | Frontend | none | none | ✅ OK |
| T10 | Frontend | none | none | ✅ OK |
| T11 | Frontend | none | none | ✅ OK |
| T12 | Frontend | none | none | ✅ OK |
| T13 | Docs/UAT | none | none | ✅ OK |
