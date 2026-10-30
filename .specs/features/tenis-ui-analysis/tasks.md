# Análise de tênis — UI frontend Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/tenis-ui-analysis/design.md` (não criado - design inline)
**Spec**: `.specs/features/tenis-ui-analysis/spec.md`
**Context**: `.specs/features/tenis-ui-analysis/context.md` (não criado)
**Status**: Draft

---

## Test Coverage Matrix

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| API client | unit/integration | Types alinhados com backend; funções retornam shape esperado | `frontend/src/lib/api.ts` | `pnpm test` (se existir) |
| Component | visual/manual | Render states loading/error/empty/ready | `frontend/src/components/workouts/ShoesAnalysisSection.tsx` | N/A (UI manual) |
| Integration | manual | Fluxo completo Equipamentos → perfil → comparação → degradação | Browser DevTools | Manual |

---

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Type checks e lint | `cd frontend && pnpm run typecheck` |
| Full | Build final | `cd frontend && pnpm run build` |

---

## Execution Plan

```
T1 → T2
T1 → T3
T2 → T3
T3 → T4
T4 → T5
```

---

## Task Breakdown

### T1: API client types e funções para análise e degradação

**What**: Adicionar tipos TypeScript e funções fetch para endpoints /api/tenis/analysis/* e /api/tenis/degradation/* em `frontend/src/lib/api.ts`.

**Where**: `frontend/src/lib/api.ts`

**Depends on**: None

**Reuses**: `apiFetch`, `parseError` existentes

**Requirement**: TUI-01, TUI-04, TUI-07, TUI-09

**Tools**: NONE

**Done when**:
- [x] Tipos `AnalysisShoeProfile`, `AnalysisCompare`, `DegradationOut` definidos
- [x] Funções `getAnalysisShoes()`, `getAnalysisShoeDetail(id)`, `getAnalysisCompare(a,b)`, `getDegradation(id)` implementadas
- [x] Gate quick: typecheck passa sem erros

**Tests**: unit (typecheck)
**Gate**: quick
**Commit**: `feat(ui): api client para análise e degradação de tênis`

---

### T2: Componente ShoesAnalysisSection com perfil por tênis

**What**: Criar componente `frontend/src/components/workouts/ShoesAnalysisSection.tsx` que lista tênis e exibe perfil tipo × banda com PanelState.

**Where**: `frontend/src/components/workouts/ShoesAnalysisSection.tsx`

**Depends on**: T1

**Reuses**: `ShoesSection` patterns, PanelSection, Skeleton

**Requirement**: TUI-01, TUI-02, TUI-03, TUI-11, TUI-12

**Tools**: NONE

**Done when**:
- [x] Componente renderiza lista de tênis com perfil resumido
- [x] Clique abre detalhe com grupos tipo × banda
- [x] Blocos omitidos quando dado ausente
- [x] Estados loading/error/empty/ready implementados
- [x] Gate quick: typecheck

**Tests**: manual
**Gate**: quick
**Commit**: `feat(ui): seção de análise por tênis com perfil tipo × banda`

---

### T3: UI de comparação pareada

**What**: Dentro de ShoesAnalysisSection, adicionar UI de seleção de dois tênis e tabela de pares com confiança.

**Where**: `frontend/src/components/workouts/ShoesAnalysisSection.tsx`

**Depends on**: T1, T2

**Reuses**: Formatação de pace/km da lib/format

**Requirement**: TUI-04, TUI-05, TUI-06

**Tools**: NONE

**Done when**:
- [x] Dois selects para tênis A e B
- [x] Botão comparar chama getAnalysisCompare
- [x] Exibe número de pares, confiança, tabela com deltas
- [x] Estado vazio quando sem pares
- [x] Gate quick: typecheck

**Tests**: manual
**Gate**: quick
**Commit**: `feat(ui): comparação pareada de tênis com confiança`

---

### T4: UI de alerta de degradação

**What**: Adicionar tab/seção de degradação no detalhe do tênis, consumindo getDegradation.

**Where**: `frontend/src/components/workouts/ShoesAnalysisSection.tsx`

**Depends on**: T3

**Reuses**: Pattern do detalhe

**Requirement**: TUI-07, TUI-08, TUI-09, TUI-10

**Tools**: NONE

**Done when**:
- [x] Exibe aviso de dados insuficientes quando <150 km
- [x] Exibe baseline (primeiros vs últimos) e lista de sinais com valores
- [x] Nunca exibe veredicto de aposentadoria
- [x] Blocos omitidos sem dado
- [x] Gate full: build passa

**Tests**: manual
**Gate**: full
**Commit**: `feat(ui): alerta de degradação por tênis`

---

### T5: Integração na página Equipamentos e teste manual

**What**: Importar ShoesAnalysisSection na página Equipamentos e garantir layout consistente.

**Where**: `frontend/src/app/(app)/equipamentos/page.tsx`

**Depends on**: T4

**Reuses**: Layout existente

**Requirement**: TUI-11, TUI-12, TUI-13

**Tools**: NONE

**Done when**:
- [x] Página Equipamentos renderiza ShoesSection + ShoesAnalysisSection
- [x] Build completa sem erros
- [x] Fluxo manual testado: perfil, comparação, degradação

**Tests**: manual
**Gate**: full
**Commit**: `feat(ui): integra análise de tênis na página Equipamentos`

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | (início) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1, T2 | T1/T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: API client | 1 arquivo, 4 funções + types | ✅ Granular |
| T2: Perfil UI | 1 componente, estados PanelState | ✅ Granular |
| T3: Comparação | Seleção + tabela | ✅ Granular |
| T4: Degradação | Tab de sinais | ✅ Granular |
| T5: Integração | Página Equipamentos | ✅ Granular |

Total: 5 tasks — cabe em um batch (≤ ~8), execução inline sem sub-agentes.
