# Alerta de degradação por tênis — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tenis-alerta-degradacao/design.md` (não existe ainda — criar se necessário)
**Spec**: `.specs/features/tenis-alerta-degradacao/spec.md`
**Context**: `.specs/features/tenis-alerta-degradacao/context.md`
**Status**: Draft

---

## Test Coverage Matrix

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domain functions (baseline, signals, degradation) | unit | 1:1 com ACs; baseline 100/50km, gate de mix, sinais Δ | `backend/tests/test_tenis_degradation_*.py` | `uv run pytest tests/test_tenis_degradation_*.py -q` |
| API router (TestClient + Postgres real) | integration | Endpoints: happy + 401 + 404 + isolamento A×B + sem dados | `backend/tests/test_tenis_degradation_api.py` | `uv run pytest tests/test_tenis_degradation_api.py -q` |

---

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks com testes unit pontuais | `cd backend && uv run pytest tests/test_<arquivo> -q` (Postgres do compose de pé) |
| Full | Tasks com testes de API/integration | `cd backend && uv run pytest` |

---

## Execution Plan

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

### T1: Domínio de baseline (primeiros ~100 km vs últimos ~50 km)

**What**: `app/tenis_degradation/baseline.py` com `build_baseline(runs)`. Ordena corridas por distância acumulada (km derivada), separa em janela inicial (~100 km) e final (~50 km). Menos de ~150 km totais → "dados insuficientes".

**Where**: `backend/app/tenis_degradation/baseline.py` (novo módulo)

**Depends on**: None

**Reuses**: `build_shoe_profile` convenções de tipo/banda de A

**Requirement**: TDE-01, TDE-02, TDE-03, TDE-04

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `build_baseline` ordena corridas por distância acumulada (não data)
- [x] Janela inicial = primeiros ~100 km acumulados; janela final = últimos ~50 km
- [x] Menos de ~150 km → "dados insuficientes"
- [x] Gate: quick (`uv run pytest tests/test_tenis_degradation_baseline.py -q`) — Test count: 6

**Tests**: unit
**Gate**: quick
**Commit**: `feat(tenis-degradation): domínio de baseline 100km vs 50km`

---

### T2: Domínio de gate de mix de tipos (tipo × banda)

**What**: `app/tenis_degradation/mix_gate.py` com `group_by_type_band(runs)`. Agrupa corridas por tipo de treino × banda de pace (mesma convenção de A). Grupos sem pares válidos são omitidos. Nunca compara tipos diferentes.

**Where**: `backend/app/tenis_degradation/mix_gate.py` (novo módulo)

**Depends on**: None

**Reuses**: `build_shoe_profile` / `_band_for_pace` de `app.tenis_analysis.profile`

**Requirement**: TDE-05, TDE-06, TDE-07, TDE-08

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Agrupa por tipo × banda de pace
- [x] Só running/trail_running com shoe_id
- [x] Grupo sem pares válidos → omitido
- [x] Nunca compara tipos de treino diferentes
- [x] Gate: quick (`uv run pytest tests/test_tenis_degradation_mix_gate.py -q`) — Test count: 6

**Tests**: unit
**Gate**: quick
**Commit**: `feat(tenis-degradation): domínio de gate de mix de tipos`

---

### T3: Domínio de sinais de degradação (Δ entre janelas)

**What**: `app/tenis_degradation/signals.py` com `compute_signals(initial_runs, final_runs)`. Calcula ΔGCT, Δoscilação, Δcadência, ΔEF, ΔHR drift, Δ feel-RPE entre janela inicial e final. Sinal sem dado → omitido. Cada sinal com valor inicial/final/delta/direção/confiança. "Sinais, não veredito".

**Where**: `backend/app/tenis_degradation/signals.py` (novo módulo)

**Depends on**: None

**Reuses**: métricas de A (ef_factor, hr_drift), running dynamics de B

**Requirement**: TDE-09, TDE-10, TDE-11, TDE-12, TDE-13

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Calcula ΔGCT, Δoscilação, Δcadência, ΔEF, ΔHR drift, Δ feel-RPE
- [x] Sinal sem dado → omitido (não zero)
- [x] Cada sinal: valor inicial, final, delta, direção, confiança
- [x] Resultado = sinais + confiança, nunca "aposentar"
- [x] Sem sinal relevante → lista vazia + confiança
- [x] Gate: quick (`uv run pytest tests/test_tenis_degradation_signals.py -q`) — Test count: 10

**Tests**: unit
**Gate**: quick
**Commit**: `feat(tenis-degradation): domínio de sinais de degradação`

---

### T4: Endpoints de leitura da degradação

**What**: `app/tenis_degradation/router.py` com `GET /api/tenis/degradation/{shoe_id}`. Consome baseline (T1), mix gate (T2), signals (T3). User-scope.

**Where**: `backend/app/tenis_degradation/router.py` (novo), registro em `backend/app/main.py`

**Depends on**: T1, T2, T3

**Reuses**: padrão de router do projeto; `require_session`; `get_db`

**Requirement**: Todas TDE-01 a TDE-15 (exposição via API)

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] `GET /api/tenis/degradation/{id}` devolve sinais de degradação de um tênis
- [x] 401 sem sessão; 404 tênis inexistente/de outro usuário; isolamento A×B
- [x] Sem dados → vazio + "dados insuficientes" (não erro)
- [x] Gate: full (`uv run pytest`) — Test count: 8

**Tests**: integration
**Gate**: full
**Commit**: `feat(tenis-degradation): endpoints de leitura da degradação`

---

### T5: Testes de integração da API

**What**: `backend/tests/test_tenis_degradation_api.py` cobrindo happy path, 401, 404, isolamento A×B, sem dados, dados insuficientes.

**Where**: `backend/tests/test_tenis_degradation_api.py`

**Depends on**: T4

**Reuses**: `session_client` fixture de `conftest.py`; padrão de `test_tenis_analysis_api.py`

**Requirement**: Todas TDE-01 a TDE-15 (via API)

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Happy path de degradação via API
- [x] 401 sem sessão; 404 tênis de outro usuário; isolamento A×B
- [x] Sem dados → vazio + confiança/insuficiente
- [x] Gate: full (`uv run pytest tests/test_tenis_degradation_api.py -q`) — Test count: 8

**Tests**: integration
**Gate**: full
**Commit**: `feat(tenis-degradation): testes de integração da API de degradação`

---

### T6: Validação final e fechamento da feature C

**What**: Rodar suíte completa dos domínios afetados (tenis-degradation + existentes), confirmar sem regressão, fechar traceability (todas TDE → Verified).

**Where**: `backend/tests/` (suite completa)

**Depends on**: T1, T2, T3, T4, T5

**Reuses**: suíte existente

**Requirement**: Todas TDE-01 a TDE-15

**Tools**:

- MCP: NONE
- Skill: tlc-spec-driven (fluxo Execute)

**Done when**:

- [x] Todos os testes de T1-T5 passam
- [x] Sem regressão nos testes existentes (tenis, analysis, shoes, strava, activities)
- [x] Traceability: 15/15 TDEs Verified
- [x] Gate: full (`uv run pytest` nos domínios afetados)
- [x] Commit: `feat(tenis-degradation): feature C completa — validação final`

**Tests**: integration (suite completa dos domínios)
**Gate**: full
**Commit**: `feat(tenis-degradation): feature C completa — validação final`

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | (nenhuma entrada) | ✅ Match |
| T2 | None | (nenhuma entrada) | ✅ Match |
| T3 | None | (nenhuma entrada) | ✅ Match |
| T4 | T1, T2, T3 | T1/T2/T3 → router | ✅ Match |
| T5 | T4 | T4 → testes API | ✅ Match |
| T6 | T1-T5 | (validação final) | ✅ Match |

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Domínio baseline | 1 função pura (baseline) | ✅ Granular |
| T2: Domínio mix gate | 1 função pura (agrupamento) | ✅ Granular |
| T3: Domínio signals | 1 função pura (sinais Δ) | ✅ Granular |
| T4: Endpoints | 1 router (1 rota GET) | ✅ Granular |
| T5: Testes API | 1 arquivo de teste integração | ✅ Granular |
| T6: Validação final | 1 suíte completa | ✅ Granular |

Total: 6 tasks — cabe em um único batch (≤ ~8), execução inline sem sub-agentes.
