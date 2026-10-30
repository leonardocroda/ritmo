# Análise comparativa entre tênis — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tenis-analise-comparativa/design.md`
**Spec**: `.specs/features/tenis-analise-comparativa/spec.md`
**Context**: `.specs/features/tenis-analise-comparativa/context.md`
**Status**: Draft

---

## Test Coverage Matrix

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domain functions (profile, comparison, metrics) | unit | 1:1 com ACs; tipo×banda, pares ±5%, confiança, RD ajustados, EF, drift, janela | `backend/tests/test_tenis_analysis_*.py` | `uv run pytest tests/test_tenis_analysis_*.py -q` |
| API router (TestClient + Postgres real) | integration | Todos os endpoints: happy + 401 + 404 + isolamento A×B + sem dados | `backend/tests/test_tenis_analysis_api.py` | `uv run pytest tests/test_tenis_analysis_api.py -q` |

---

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com testes unit pontuais | `cd backend && uv run pytest tests/test_<arquivo> -q` (Postgres do compose de pé) |
| Full | Tasks com testes de API/integration | `cd backend && uv run pytest` |

---

## Execution Plan

Phases are ordered and run sequentially.

```
T1 → T4
T2 → T4
T3 → T4
T1 → T6
T2 → T6
T3 → T6
T4 → T5
T4 → T6
T5 → T6
```

---

## Task Breakdown

### T1: Domínio de perfil por tênis (tipo × banda de pace)

**What**: `app/tenis_analysis/profile.py` com `build_shoe_profile(runs)`. Agrupa corridas por tipo de treino inferido × banda de pace, retorna médias de pace, FC, cadência e contagem por grupo. Nunca expõe pace bruto agregado sem fatiamento.

**Where**: `backend/app/tenis_analysis/profile.py` (novo módulo)

**Depends on**: None

**Reuses**: `RUNNING_TYPES` de `app/garmin/mappers.py`; helpers `_pace_s` de `app/activities/service.py`

**Requirement**: TRD-01, TRD-02, TRD-03

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `build_shoe_profile` agrupa por tipo de treino × banda de pace
- [x] Cada grupo: média de pace, FC média, cadência média, contagem de corridas
- [x] Sem pace bruto agregado sem fatiamento
- [x] Gate: quick (`uv run pytest tests/test_tenis_analysis_profile.py -q`) — Test count: 6

**Tests**: unit
**Gate**: quick
**Commit**: `feat(tenis-analysis): domínio de perfil por tipo × banda de pace`

---

### T2: Domínio de comparação pareada + nível de confiança

**What**: `app/tenis_analysis/comparison.py` com `build_matched_pairs(runs_a, runs_b)` (distância ±5%, pace ±5%, data livre) e `confidence_level(n_pairs)` (<3=baixo, 3–5=médio, >5=alto).

**Where**: `backend/app/tenis_analysis/comparison.py` (novo módulo)

**Depends on**: None

**Reuses**: nenhum (funções puras)

**Requirement**: TRD-04, TRD-05, TRD-06, TRD-07, TRD-08, TRD-09, TRD-10

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `build_matched_pairs` forma pares distância ±5% E pace ±5% entre tênis A e B
- [x] Data livre (não é critério de proximidade)
- [x] Sem pares → lista vazia + confiança "baixa"
- [x] Cada par: tênis A/B, distância, pace A/B, delta pace, FC A/B, delta FC
- [x] `confidence_level`: <3=baixo, 3–5=médio, >5=alto
- [x] Gate: quick (`uv run pytest tests/test_tenis_analysis_comparison.py -q`) — Test count: 8

**Tests**: unit
**Gate**: quick
**Commit**: `feat(tenis-analysis): domínio de comparação pareada e nível de confiança`

---

### T3: Domínio de métricas derivadas (RD ajustados, EF, drift, janela)

**What**: `app/tenis_analysis/metrics.py` com: running dynamics ajustados por ritmo (resíduo de regressão), EF (velocidade/FC), HR drift (só se pace estável), janela fresco vs fadiga (~30% inicial vs final).

**Where**: `backend/app/tenis_analysis/metrics.py` (novo módulo)

**Depends on**: None

**Reuses**: colunas running dynamics da `Split` (feature B); AD-005 (drift só a ritmo constante)

**Requirement**: TRD-11, TRD-12, TRD-13, TRD-14, TRD-15, TRD-16, TRD-17

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Running dynamics ajustados: resíduo de regressão linear vs pace (por tipo); None sem dado
- [x] EF = velocidade / FC média; null sem FC
- [x] HR drift: FC 2ª metade − 1ª metade, só se pace estável entre metades
- [x] Janela fresco vs fadiga: primeiros ~30% vs últimos ~30% da distância
- [x> Delta pace/FC das janelas por tênis
- [x] Blocos omitidos (não inventados) quando o dado faltar
- [x] Gate: quick (`uv run pytest tests/test_tenis_analysis_metrics.py -q`) — Test count: 10

**Tests**: unit
**Gate**: quick
**Commit**: `feat(tenis-analysis): domínio de métricas derivadas (RD, EF, drift, janela)`

---

### T4: Endpoints de leitura da análise

**What**: Novo router `app/tenis_analysis/router.py` com `GET /api/tenis/analysis/shoes`, `GET /api/tenis/analysis/shoes/{shoe_id}`, `GET /api/tenis/analysis/compare?shoe_a=X&shoe_b=Y`. Consome o domínio de T1/T2/T3 com leitura do banco (user-scope).

**Where**: `backend/app/tenis_analysis/router.py` (novo), registro em `backend/app/main.py`

**Depends on**: T1, T2, T3

**Reuses**: padrão de router do projeto; `require_session`; `get_db`; isolamento textual

**Requirement**: Todas TRD-01 a TRD-17 (exposição via API)

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `GET /api/tenis/analysis/shoes` devolve perfil de todos os tênis do usuário
- [x] `GET /api/tenis/analysis/shoes/{id}` devolve perfil detalhado de um tênis
- [x] `GET /api/tenis/analysis/compare` devolve pares + nível de confiança
- [x] 401 sem sessão; 404 tênis inexistente/de outro usuário; isolamento A×B
- [x] Sem dados → retorno vazio + confiança baixa (não erro)
- [x] Gate: full (`uv run pytest`) — Test count: 12

**Tests**: integration
**Gate**: full
**Commit**: `feat(tenis-analysis): endpoints de leitura da análise comparativa`

---

### T5: Testes de integração da API

**What**: `backend/tests/test_tenis_analysis_api.py` cobrindo happy path, 401, 404, isolamento A×B, sem dados, confiança por quantidade de pares.

**Where**: `backend/tests/test_tenis_analysis_api.py`

**Depends on**: T4

**Reuses**: `session_client` fixture de `conftest.py`; padrão de teste de `test_shoes_api.py`

**Requirement**: Todas TRD-01 a TRD-17 (via API)

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Happy path de perfil, comparação e confiança via API
- [x] 401 sem sessão; 404 tênis de outro usuário; isolamento A×B
- [x] Sem dados → vazio + confiança baixa
- [x] Gate: full (`uv run pytest tests/test_tenis_analysis_api.py -q`) — Test count: 10

**Tests**: integration
**Gate**: full
**Commit**: `feat(tenis-analysis): testes de integração da API de análise`

---

### T6: Validação final e fechamento da feature A

**What**: Rodar suíte completa dos domínios afetados (tenis-analysis + shoes/strava/activities existentes), confirmar sem regressão, fechar traceability (todas TRD → Verified).

**Where**: `backend/tests/` (suite completa)

**Depends on**: T1, T2, T3, T4, T5

**Reuses**: suíte existente

**Requirement**: Todas TRD-01 a TRD-17

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Todos os testes de T1-T5 passam
- [x] Sem regressão nos testes existentes (tenis, shoes, strava, activities)
- [x] Traceability: 17/17 TRDs Verified
- [x] Gate: full (`uv run pytest` nos domínios afetados)
- [x] Commit: `feat(tenis-analysis): feature A completa — validação final`

**Tests**: integration (suite completa dos domínios)
**Gate**: full
**Commit**: `feat(tenis-analysis): feature A completa — validação final`

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | (nenhuma entrada) | ✅ Match |
| T2 | None | (nenhuma entrada) | ✅ Match |
| T3 | None | (nenhuma entrada) | ✅ Match |
| T4 | T1, T2, T3 | T1/T2/T3 → TA → EP | ✅ Match |
| T5 | T4 | T4 → EP (testes) | ✅ Match |
| T6 | T1-T5 | (validação final) | ✅ Match |

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Domínio profile | 1 função pura (agrupamento) | ✅ Granular |
| T2: Domínio comparison | 2 funções puras (pares + confiança) | ✅ Granular |
| T3: Domínio metrics | 4 funções puras (RD, EF, drift, janela) | ✅ Granular |
| T4: Endpoints | 1 router (3 rotas GET) | ✅ Granular |
| T5: Testes API | 1 arquivo de teste integração | ✅ Granular |
| T6: Validação final | 1 suíte completa | ✅ Granular |

Total: 6 tasks — cabe em um único batch (≤ ~8), execução inline sem sub-agentes.
