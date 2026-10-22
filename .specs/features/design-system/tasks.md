# design-system Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/design-system/design.md`
**Spec**: `.specs/features/design-system/spec.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `frontend/AGENTS.md` (Next 16 com breaking changes — guias em `node_modules/next/dist/docs/`, ler o guia relevante antes de escrever código) e README §Testes (backend pytest — fora do escopo desta feature). **Nenhum framework de teste frontend no repo** (package.json: apenas `dev`/`build`/`lint`) → frontend segue o precedente da casa (garmin-tokens-db T10): build gate + verificação estrutural por grep + UAT visual no fim.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Frontend — tokens/tipografia/sweeps (globals.css, layout.tsx, varreduras) | none - build gate | `npm run lint` + `npm run build` verdes; greps estruturais do spec (zero `border-white/10`, zero hex fora do tema em `src/components`) | `frontend/src/**` | `cd frontend && npm run lint && npm run build` |
| Frontend — tema de gráfico (chartTheme + 11 charts) | none - build gate | idem + `grep` de hex retorna só `chartTheme.ts`; dados/eixos/contratos intocados | `frontend/src/components/**` | idem |
| Frontend — shell responsivo + skeletons | none - build gate | idem + UAT visual 390px↔desktop no fim da feature (Sucesso do spec) | `frontend/src/**` | idem |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após cada task | `cd frontend && npm run lint && npm run build` |
| Build | Ao fim de cada fase | Quick **e** greps estruturais: `git grep -n "border-white/10" -- frontend/src` → vazio; `git grep -nE "#[0-9a-fA-F]{6}" -- frontend/src/components` → apenas `chartTheme.ts` |

---

## Execution Plan

> **Pré-Execute (orquestrador, antes da T1):** (1) `git merge main` no branch `design-system` — o T10 do garmin-tokens-db (ConnectionCard no `/perfil`) pode ter aterrissado; (2) `npm ci` no `frontend/` do worktree — o worktree novo nasce sem `node_modules` (gates não rodam sem isso). Nenhum dos dois produz commit.

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação visual (tokens, fonte, sweeps)

A re-pele inteira sem tocar um componente de lógica.

```
T1 → T2 → T3 → T4
```

### Phase 2: Tema de gráfico

O módulo e a migração dos 11 charts.

```
T4 → T5 → T6 → T7 → T8 → T9
```

### Phase 3: Shell e estados

Navegação responsiva, marca e skeletons.

```
T9 → T10 → T11 → T12
```

---

## Task Breakdown

### T1: Tokens v0.3 no globals.css

**What**: Substituir o bloco `:root` pelos tokens v0.3 (12 cores + semânticas de saúde) e estender o `@theme inline` (novas cores, `--radius-card: 16px`, `--radius-ctl: 12px`) conforme o design — a linha `--font-sans` permanece apontando `--font-geist-sans` até a T2. Zero componente tocado: a re-pele é automática via utilitários existentes.
**Where**: `frontend/src/app/globals.css`
**Depends on**: None
**Reuses**: padrão `:root` + `@theme inline` do próprio arquivo
**Requirement**: DSN-01, DSN-02, DSN-03, DSN-05

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `:root` com os tokens v0.3 e comentários de referência (v0.3 "Night"/"Surface"/"Lime"); semânticas `--good`/`--attention`/`--alert` presentes
- [x] `@theme inline` mapeia todas as novas cores + `--radius-card`/`--radius-ctl`; nomes canônicos (`--background`/`--card`/`--accent`/`--muted`/`--foreground`) preservados
- [x] App re-pelado sem edição de componente (conferir no dev: fundo `#0B0F12`, cartões `#121815`, accent `#B7F36B`)
- [x] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): tokens v0.3 — paleta, semântica e raio`

---

### T2: Instrument Sans + themeColor

**What**: Trocar `Geist` → `Instrument_Sans` no root layout (variable `--font-instrument-sans`, `subsets: ["latin"]`, `display: "swap"`, fonte variável 400–700 sem pesos declarados), apontar `--font-sans` do `@theme` para a nova variável e atualizar `viewport.themeColor` para `#0B0F12`. `Geist_Mono` permanece.
**Where**: `frontend/src/app/layout.tsx`
**Depends on**: T1
> Dependência de ordem da fase — o @theme da T1 fica estável antes da troca da fonte.
**Reuses**: padrão de configuração do Geist atual (`layout.tsx:6-14`); guia `node_modules/next/dist/docs/01-app/01-getting-started/13-fonts.md`
**Requirement**: DSN-07, DSN-08, DSN-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `Instrument_Sans` configurada com `display: swap`; `--font-sans` aponta `--font-instrument-sans`; `Geist_Mono` intocada
- [x] `themeColor` `#0B0F12`
- [x] Computed style do body = "Instrument Sans" no dev; peso 650 renderiza (fonte variável)
- [x] Offline no runtime não quebra a renderização (self-hosting do build + swap)
- [x] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): Instrument Sans e themeColor v0.3`

---

### T3: Sweep de bordas para tokens

**What**: Varredura do padrão `border-white/10` → `border-border` em todo o `frontend/src`; elementos interativos com borda (pills do seletor de janela, botão Sair, segmentados, inputs, tabs) ganham `hover:border-border-hover` — a borda decorativa a 1,8:1 nunca é o único sinal de interatividade.
**Where**: `frontend/src/**` (varredura por padrão de classe)
**Depends on**: T2
> Ordem da fase — sweep com a baseline de fonte já estável.
**Reuses**: tokens de T1 (`--color-border`, `--color-border-hover`)
**Requirement**: DSN-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `git grep -n "border-white/10" -- frontend/src` retorna vazio
- [ ] Interativos com hover/focus na borda token (pelo menos: pill do seletor do Saúde, botão Sair, um input do /perfil)
- [ ] Estados de erro/vazio seguem com a borda nova, contratos visuais intactos
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): bordas em tokens com hover em interativos`

---

### T4: Sweep de raio + números tabulares

**What**: Varredura contextual de `rounded-xl` → `rounded-card` (16px) em contêineres de cartão e `rounded-ctl` (12px) em controles (pills, inputs, botões, badges); adicionar `tabular-nums` aos números de dado que ainda não usam (valores em destaque, tabelas, chips numéricos).
**Where**: `frontend/src/**` (varredura contextual)
**Depends on**: T3
> Ordem da fase — mesmos arquivos que a T3, em sequência.
**Reuses**: `--radius-card`/`--radius-ctl` da T1; classe `tabular-nums` já usada no HrvChart
**Requirement**: DSN-05, DSN-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cartões 16px e controles 12px conferidos nas 4 telas (treinos, performance, saúde, perfil)
- [ ] `tabular-nums` presente nos números de dado (HrvTable, DecayTable, PredictionsTable, valores display dos charts)
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): raio v0.3 nos cartões e números tabulares`

---

### T5: Módulo chartTheme

**What**: Criar `lib/chartTheme.ts` com `chart` (axis/muted/context/subject/attention/alert/bandOpacity), `tick`, `axisLine`, as classes `tooltipCard`/`legendCaption` e o comentário-cabeçalho com a regra de coexistência das zonas VDOT (cores vêm do backend — fonte única; lime da marca ≠ verde-easy de zona; zonas nunca fora de contexto de treino).
**Where**: `frontend/src/lib/chartTheme.ts`
**Depends on**: T4
> Ordem da fase — o módulo nasce depois dos sweeps para não ser varrido.
**Reuses**: padrões de tick/tooltip/legenda dos charts existentes (`HrvChart.tsx:49,95,164`)
**Requirement**: DSN-11, DSN-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Módulo exporta `chart`, `tick`, `axisLine`, `tooltipCard`, `legendCaption` conforme o design
- [ ] Regra de coexistência documentada no cabeçalho
- [ ] Build segue verde (módulo ainda não importado por ninguém)
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): módulo de tema de gráfico (chartTheme)`

---

### T6: Tema nos gráficos de sono

**What**: Aplicar o tema nos 4 charts do bloco de sono — SleepChart (duração lime + piso 7h `ReferenceLine` dashed `context`), SleepStagesChart (leve muted · profunda lime · REM attention), RemChart (REM% attention + banda 21–31% attention 6% + bordas dashed `context`), WeekdayPattern (barras `context`, dia de hoje lime) — todos com remoção do `CartesianGrid` (linha de base = `axisLine` do XAxis), `tick`/`axisLine` do tema, `tooltipCard`/`legendCaption` e zero hex local.
**Where**: `frontend/src/components/health/`
**Depends on**: T5
**Reuses**: `chart`/`tick`/`axisLine`/`tooltipCard`/`legendCaption` da T5
**Requirement**: DSN-12, DSN-13, DSN-14, DSN-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 4 charts sem `CartesianGrid`, com linha de base hairline e ticks 9–10px muted
- [ ] Cores por entidade conforme a tabela do design; tooltips e legendas nas classes do tema
- [ ] `git grep -nE "#[0-9a-fA-F]{6}"` nos 4 arquivos → vazio (cores só do chartTheme)
- [ ] Dados, formatos e estados vazios intocados (CLR/HLT)
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): tema nos gráficos de sono`

---

### T7: Tema nos gráficos de recuperação

**What**: Aplicar o tema nos 3 charts de recuperação — HrvChart (média 7d lime, banda pessoal lime 6% — AD-010 intacta, noites `context`, fora-da-banda attention — HRV-13 intacto), RhrChart (FC repouso alert), StressChart (estresse alert) — mesma receita da T6 (sem `CartesianGrid`, ticks do tema, tooltip/legenda do tema, zero hex local).
**Where**: `frontend/src/components/health/`
**Depends on**: T6
> Ordem da fase — mesma receita, bloco seguinte.
**Reuses**: receita da T6 + chartTheme
**Requirement**: DSN-12, DSN-13, DSN-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] HrvChart: status do card, banda e outliers preservados; cores do tema
- [ ] RhrChart/StressChart na família alert; zero hex local nos 3 arquivos
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): tema nos gráficos de recuperação`

---

### T8: Tema nos gráficos de performance

**What**: Aplicar o tema nos 3 charts de performance — PmcChart (CTL lime · ATL alert · TSB barras `context` com o dia atual lime — DSN-13), Vo2maxTrend (linha lime, selo "estimativa" preservado — AD-009), VdotTimeline (VDOT lime + faixa honesta lime 6% — AD-004) — mesma receita das T6/T7.
**Where**: `frontend/src/components/performance/`
**Depends on**: T7
> Ordem da fase — mesma receita, painel seguinte.
**Reuses**: receita da T6/T7 + chartTheme
**Requirement**: DSN-12, DSN-13, DSN-14, DSN-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] PMC com 3 séries legíveis nas famílias semânticas; destaques do último dia intactos
- [ ] Vo2max/Vdot com sujeito lime e selos/faixas preservados; zero hex local nos 3 arquivos
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): tema nos gráficos de performance`

---

### T9: SplitsChart no tema

**What**: Aplicar o tema no SVG próprio — eixo/labels/tooltip/legenda do tema, fills locais trocados por tokens (`#18181b` → card, `#ffffff` → foreground), linha de FC em `foreground` — **cores das zonas VDOT intocadas** (vêm do backend via `ZoneMeta`, fonte única; DSN-16).
**Where**: `frontend/src/components/workouts/SplitsChart.tsx`
**Depends on**: T8
> Acoplamento real é só com a T5; T8 é ordem da fase.
**Reuses**: chartTheme (axis/muted/tooltip/legendCaption); `ZoneMeta` inalterado
**Requirement**: DSN-15, DSN-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Cores de zona vindas do `ZoneMeta` renderizam idênticas (antes/depois no detalhe de um treino)
- [ ] Geometria, clamp de pace e largura proporcional intocados
- [ ] `git grep -nE "#[0-9a-fA-F]{6}" -- frontend/src/components` → apenas `chartTheme.ts`
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): SplitsChart no tema, zonas VDOT intactas`

---

### T10: Navegação responsiva (tab bar + top bar)

**What**: `Nav.tsx` vira a fonte de verdade da navegação — `PANELS` com href/label/ícone SVG line 22px inline (Treinos, Saúde, Performance, Perfil), `activePanel` compartilhado — com duas renderizações CSS-only: `Nav` desktop (ícone + label, ativo `bg-accent/15 text-accent`, `hidden md:flex`) e `TabBar` mobile (`md:hidden`, `fixed bottom-0`, `border-t border-border`, `bg-background/92 backdrop-blur`, alvo ≥44px, `pb-[max(18px,env(safe-area-inset-bottom))]`); `(app)/layout.tsx` ganha o `<TabBar />` e o wrapper de respiro `pb-24 md:pb-0`.
**Where**: `frontend/src/components/Nav.tsx`
**Depends on**: T9
> Ordem da fase — shell depois do conteúdo re-pelado.
**Reuses**: `activePanel`/`usePathname`/boundary Suspense do Nav atual (`Nav.tsx:25,67`); pill ativo `bg-accent/15`
**Requirement**: DSN-17, DSN-18, DSN-19, DSN-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Viewport <768px: tab bar fixa com 4 itens, ativo lime + pill, `aria-current`, sem scroll horizontal em 390px
- [ ] Viewport ≥768px: nav no header com os mesmos ícones e labels; tab bar some
- [ ] Resize 390px↔1280px não perde o item ativo (mesma rota, duas renderizações)
- [ ] Conteúdo não fica sob a barra (wrapper de respiro; lista paginada do Treinos confere)
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): navegação responsiva — tab bar e top bar`

---

### T11: Wordmark com pulso + header enxuto

**What**: Header com wordmark "ritmo" lowercase + glyph de pulso lime (SVG inline); favicon `frontend/src/app/icon.svg` (pulso lime sobre night, convenção Next 16 de auto-detect); `UserMenu` troca o `Link` do `display_name` por texto simples (o `/perfil` vive na navegação agora — DSN-21).
**Where**: `frontend/src/components/Header.tsx`
**Depends on**: T10
> Ordem da fase — header enxuto depois da nav existir nos dois lugares.
**Reuses**: composição server-component do Header atual; convenção `app/icon.svg` (docs `01-app/03-api-reference/03-file-conventions/01-metadata/app-icons.md`)
**Requirement**: DSN-20, DSN-21, DSN-25, DSN-26

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Wordmark "ritmo" + pulso no header; favicon do pulso na aba do browser
- [ ] `display_name` sem link; "Sair" preservado com hover token; `/perfil` alcançável pela nav nos dois breakpoints
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): wordmark com pulso e header enxuto`

---

### T12: Skeletons na linguagem v0.3

**What**: Criar `Skeleton.tsx` + keyframes `skeleton-pulse` (1,6s, neutro `raised`→`deep`) no `globals.css`; substituir os estados de loading textuais dos painéis ("Carregando…") por composições de skeleton (HealthPanel, PerformancePanel, WorkoutsList, WorkoutDetail, `/perfil`) — contratos de erro intocados (DSN-24).
**Where**: `frontend/src/components/Skeleton.tsx`
**Depends on**: T11
> Ordem da fase — estados por último, sobre o shell pronto.
**Reuses**: estados de loading existentes dos painéis; tokens `--raised`/`--deep` da T1
**Requirement**: DSN-23, DSN-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `<Skeleton />` renderiza com pulso no neutro (nenhum spinner)
- [ ] Toda tela de loading textual dos painéis virou skeleton (`git grep -n "Carregando" -- frontend/src` → sem estados de loading; textos de erro permanecem)
- [ ] Erro/empty states intocados (fluxo CLR-11/HLT-19 no dev)
- [ ] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: quick

**Commit**: `feat(frontend): skeletons na linguagem v0.3`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 → T2 → T3 → T4
Phase 2:  T4 → T5 → T6 → T7 → T8 → T9
Phase 3:  T9 → T10 → T11 → T12
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Batching**: 12 tasks → 3 batches (Batch 1 = Phase 1, T1-T4; Batch 2 = Phase 2, T5-T9; Batch 3 = Phase 3, T10-T12). A Verifier roda automaticamente após o Batch 3.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Tokens v0.3 | 1 arquivo (fundação de tudo) | ✅ Granular |
| T2: Instrument Sans + themeColor | 1 arquivo | ✅ Granular |
| T3: Sweep de bordas | 1 padrão de classe (varredura coesa) | ✅ Granular |
| T4: Sweep de raio + tabulares | 1 padrão + 1 utilitário (varredura coesa) | ✅ Granular |
| T5: chartTheme | 1 módulo | ✅ Granular |
| T6: Tema nos charts de sono | 1 receita aplicada a 4 componentes do mesmo bloco | ⚠️ Coeso |
| T7: Tema nos charts de recuperação | 1 receita aplicada a 3 componentes do mesmo bloco | ⚠️ Coeso |
| T8: Tema nos charts de performance | 1 receita aplicada a 3 componentes do mesmo painel | ⚠️ Coeso |
| T9: SplitsChart no tema | 1 componente | ✅ Granular |
| T10: Navegação responsiva | 1 componente + wiring | ✅ Granular |
| T11: Wordmark + header enxuto | 1 componente + acessórios de marca | ⚠️ Coeso |
| T12: Skeletons | 1 componente + aplicação | ⚠️ Coeso |

> As 5 tasks "coeso" aplicam um único padrão a arquivos irmãos — split por arquivo multiplicaria 11 tasks de chart em micro-edits idênticas sem ganho de verificabilidade (cada chart tem checkbox próprio no Done when).

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | início da Fase 1 (sem seta de entrada) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |

Nenhuma dependência aponta para fase posterior (validado pelo script).

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Frontend (tokens) | none - build gate | none | ✅ OK |
| T2 | Frontend (tipografia) | none - build gate | none | ✅ OK |
| T3 | Frontend (sweep) | none - build gate | none | ✅ OK |
| T4 | Frontend (sweep) | none - build gate | none | ✅ OK |
| T5 | Frontend (módulo) | none - build gate | none | ✅ OK |
| T6 | Frontend (charts) | none - build gate | none | ✅ OK |
| T7 | Frontend (charts) | none - build gate | none | ✅ OK |
| T8 | Frontend (charts) | none - build gate | none | ✅ OK |
| T9 | Frontend (chart) | none - build gate | none | ✅ OK |
| T10 | Frontend (shell) | none - build gate | none | ✅ OK |
| T11 | Frontend (marca/header) | none - build gate | none | ✅ OK |
| T12 | Frontend (estados) | none - build gate | none | ✅ OK |

---

## Requirement Traceability (tasks)

| Requirement | Tasks |
| ----------- | ----- |
| DSN-01 | T1 |
| DSN-02 | T1 |
| DSN-03 | T1 |
| DSN-04 | T3 |
| DSN-05 | T1, T4 |
| DSN-06 | T3, T5, T6, T7, T8, T9 |
| DSN-07 | T2 |
| DSN-08 | T2 |
| DSN-09 | T4 |
| DSN-10 | T2 |
| DSN-11 | T5 |
| DSN-12 | T6, T7, T8 |
| DSN-13 | T6, T7, T8 |
| DSN-14 | T6, T8 |
| DSN-15 | T6, T7, T8, T9 |
| DSN-16 | T5, T9 |
| DSN-17 | T10 |
| DSN-18 | T10 |
| DSN-19 | T10 |
| DSN-20 | T11 |
| DSN-21 | T11 |
| DSN-22 | T10 |
| DSN-23 | T12 |
| DSN-24 | T12 |
| DSN-25 | T11 |
| DSN-26 | T11 |

**Coverage:** 26 total, 26 mapped to tasks, 0 unmapped ✅
