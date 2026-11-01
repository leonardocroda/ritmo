# Equipamentos/Tênis UX Improvements - Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/equipamentos-tenis-ux/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `frontend/AGENTS.md` (Next.js agent rules), `package.json` (vitest, playwright), `.github/workflows` (CI). No explicit testing guidelines doc found - strong defaults applied.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Hooks (useShoeAnalysis, useShoeDegradation) | unit | All branches; 1:1 to spec ACs; loading/error/data states; cancellation | `frontend/src/hooks/shoes/__tests__/*.test.ts` | `yarn test:unit` |
| Components (Detail page, Overview, Degradation, ShoeCard) | unit | All props combinations; empty/error/loading states; user interactions (click, edit) | `frontend/src/components/workouts/shoes/__tests__/*.test.tsx` | `yarn test:unit` |
| Mapping configs (workoutTypeLabels, signalLabels, zoneColors) | unit | All keys covered; fallback behavior; TypeScript types | `frontend/src/lib/shoes/__tests__/*.test.ts` | `yarn test:unit` |
| API types/functions (lib/api.ts extensions) | unit | Type correctness; fetch error handling; response parsing | `frontend/src/lib/__tests__/api.test.ts` | `yarn test:unit` |
| Integration (full detail page with sections) | e2e | Detail page renders; data flows; edit form works; navigation | `frontend/__tests__/e2e/shoes-detail.e2e.test.ts` | `yarn test:e2e` |
| Visual regression (mobile/desktop layouts) | e2e | No layout shift; touch targets ≥44px; horizontal scroll indicators | `frontend/__tests__/visual/*.spec.ts` | `yarn test:visual` |
| Entity / Config / Schema | none | - (build gate only) | - | `yarn build` |

---

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After tasks with unit tests only | `yarn test:unit --run` |
| Full | After tasks with e2e/integration tests | `yarn test:unit --run && yarn test:e2e` |
| Build | After phase completion or config/entity-only tasks | `yarn build && yarn lint && yarn test:unit --run` |
| Visual | After UI/layout tasks | `yarn test:visual` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in dependency order (see Phase Execution Map below for full dependency graph).

### Phase 1: P1 - Shoe List Cleanup (MVP)
Tasks: T01, T02, T03

### Phase 2: Foundation - Config, API Types, Hooks
Tasks: T04, T05, T06, T07

### Phase 3: Detail Page - Overview Section
Tasks: T08, T09, T10, T11, T11b, T12

### Phase 4: Detail Page - Degradation Section
Tasks: T13, T14, T15, T16

### Phase 5: Integration & Polish
Tasks: T17, T18, T19, T20, T21, T22, T23, T24

---

## Task Breakdown

### T01: Remove index from PanelSection title

**What**: Remove `index={5}` prop from PanelSection in equipamentos page
**Where**: `frontend/src/app/(app)/equipamentos/page.tsx`
**Depends on**: None
**Reuses**: Existing PanelSection component
**Requirement**: SHOE-01

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] `index` prop removed from `<PanelSection>` call
- [ ] Title renders as "Tênis" without numbers
- [ ] No TypeScript errors

**Tests**: unit (component renders without index)
**Gate**: quick

---

### T02: Remove buttons from ShoeCard, make clickable

**What**: Remove "Aposentar" and "Editar" buttons from ShoeCard; make entire card clickable to navigate to detail page
**Where**: `frontend/src/components/workouts/ShoesSection.tsx`
**Depends on**: T01
**Reuses**: Existing router/navigation
**Requirement**: SHOE-02, SHOE-03, SHOE-04

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] `onRetire` prop removed from ShoeCard interface
- [ ] "Aposentar" button JSX removed from ShoeCard render
- [ ] "Editar" button JSX removed from ShoeCard render
- [ ] `handleRetire` function removed from ShoesSection
- [ ] `handleEdit` function removed from ShoesSection
- [ ] ShoeCard wrapped in `<Link href="/equipamentos/${shoe.id}">` or onClick handler
- [ ] Card has hover/focus styles indicating clickable
- [ ] Manual test: clicking card navigates to `/equipamentos/[id]`

**Tests**: unit (ShoeCard renders without buttons; click navigates)
**Gate**: quick

---

### T03: Mobile-first responsive verification for ShoesSection

**What**: Verify ShoeCard grid, touch targets work on mobile (320px+)
**Where**: `frontend/src/components/workouts/ShoesSection.tsx`
**Depends on**: T01, T02
**Reuses**: Existing responsive classes
**Requirement**: SHOE-07

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Grid: `grid-cols-1 sm:grid-cols-2` verified at 320px, 375px, 768px
- [ ] Card clickable area ≥ 44px touch target
- [ ] No horizontal overflow
- [ ] No console errors

**Tests**: unit (responsive classes present); visual (manual at breakpoints)
**Gate**: quick + visual

---

### T04: Create mapping config files

**What**: Create workoutTypeLabels.ts, signalLabels.ts with all mappings and helpers
**Where**: 
- `frontend/src/lib/shoes/workoutTypeLabels.ts`
- `frontend/src/lib/shoes/signalLabels.ts`
**Depends on**: None
**Reuses**: ZONE_COLORS from design.md
**Requirement**: DET-03, DEG-04

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] `WORKOUT_TYPE_LABELS` covers all 8 backend `inferred_type` values + fallback
- [ ] `ZONE_COLORS` has 5 VDOT zone colors
- [ ] `getWorkoutTypeInfo()`, `getZoneColor()`, `compareWorkoutTypes()` helpers exported
- [ ] `SIGNAL_LABELS` covers all 6 signal keys with label, tooltip, higherIsWorse
- [ ] `getSignalInfo()`, `getDirection()`, `getDirectionColor()`, `getDirectionBg()` helpers exported
- [ ] Unit tests: all keys mapped, fallbacks work, types strict

**Tests**: unit (all mappings covered, helpers type-safe)
**Gate**: quick

---

### T05: Verify API types in lib/api.ts

**What**: Confirm existing types match needs (AnalysisShoeProfile, DegradationOut, etc.)
**Where**: `frontend/src/lib/api.ts`
**Depends on**: T04 (for type references)
**Reuses**: Existing getShoes, getAnalysisShoes, getDegradation
**Requirement**: DET-01, DEG-01

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] `AnalysisShoeProfile`, `AnalysisGroup` interfaces exist and match backend
- [ ] `DegradationOut`, `DegradationSignal` interfaces exist and match backend
- [ ] `getAnalysisShoes()`, `getDegradation(shoeId)` functions exist
- [ ] No `any` types
- [ ] TypeScript compiles

**Tests**: unit (types compile, fetch functions handle errors)
**Gate**: quick

---

### T06: Create useShoeAnalysis hook

**What**: Fetch `/api/tenis/analysis/shoes`, transform to Map keyed by shoe_id, sort groups by workout priority
**Where**: `frontend/src/hooks/shoes/useShoeAnalysis.ts`
**Depends on**: T05
**Reuses**: Existing useShoes pattern, SWR/fetch pattern
**Requirement**: DET-01, DET-08

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Fetches on mount, returns `{ profiles: Map, loading, error, refetch }`
- [ ] Transforms array → `Map<number, AnalysisShoeProfile>`
- [ ] Groups sorted: facil, tempo, limiar, intervalado, repeticao, longao, progressivo, prova
- [ ] Cancellation on unmount
- [ ] Unit tests: mock API, verify Map structure, sorting, loading/error states

**Tests**: unit (all states, sorting, cancellation)
**Gate**: quick

---

### T07: Create useShoeDegradation hook

**What**: refetch(shoeId) calls API, enriches signals with labels/tooltips from SIGNAL_LABELS
**Where**: `frontend/src/hooks/shoes/useShoeDegradation.ts`
**Depends on**: T04, T05
**Reuses**: Fetch pattern, effect for auto-fetch on shoeId change
**Requirement**: DEG-01, DEG-04, DEG-05

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] `refetch(shoeId)` calls `/api/tenis/degradation/{shoeId}`
- [ ] Enriches each signal with label, tooltip, direction color from SIGNAL_LABELS
- [ ] Auto-fetch effect when shoeId changes
- [ ] Returns `{ degradation, enrichedSignals, loading, error, refetch }`
- [ ] Unit tests: mock API, enrichment, insufficient data, direction colors

**Tests**: unit (enrichment, direction, insufficient handling)
**Gate**: quick

---

### T08: Create Detail Page route

**What**: Create `/equipamentos/[id]/page.tsx` with dynamic route
**Where**: `frontend/src/app/(app)/equipamentos/[id]/page.tsx`
**Depends on**: T06, T07
**Reuses**: PanelSection, existing layout
**Requirement**: DET-01, NAV-02

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Dynamic route `[id]/page.tsx` created
- [ ] Fetches shoe by ID (using getShoes + filter or new endpoint)
- [ ] Fetches analysis profile for that shoe
- [ ] Fetches degradation for that shoe
- [ ] Renders breadcrumb: Equipamentos > Tênis > [Nome]
- [ ] 404 if shoe not found
- [ ] Unit test: route params, 404 handling

**Tests**: unit (route params, data fetching, 404)
**Gate**: quick

---

### T09: Create OverviewSection component

**What**: Container for Visão Geral section - header + WorkoutTypeCard grid + empty state + edit button
**Where**: `frontend/src/components/workouts/shoes/detail/OverviewSection.tsx`
**Depends on**: T06, T10, T11, T12
**Reuses**: PanelSection pattern, format helpers
**Requirement**: DET-01, DET-03, DET-04, DET-05, DET-06, DET-07, DET-08, DET-09, DET-10

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: `{ shoe: Shoe; profile: AnalysisShoeProfile }`
- [ ] Header: shoe name, brand/model, status badge, total runs, total km, current km, life-bar, acquired date
- [ ] Edit button in header (opens inline form/modal)
- [ ] Maps profile.groups → WorkoutTypeCard array (filters n_corridas > 0)
- [ ] Empty state: OverviewEmptyState when no groups
- [ ] Responsive: mobile stacked, desktop grid-cols-1 md:grid-cols-2
- [ ] Unit tests: render with mock profile, all groups show, empty state, edit button

**Tests**: unit (render, filter, empty, responsive classes, edit button)
**Gate**: quick

---

### T10: Create WorkoutTypeCard component

**What**: Card per workout type with zone color border, label, stats, metrics
**Where**: `frontend/src/components/workouts/shoes/detail/WorkoutTypeCard.tsx`
**Depends on**: T04
**Reuses**: formatPace, formatKm from @/lib/format
**Requirement**: DET-03, DET-08, DET-09

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: tipo, pace_medio_s, fc_media, cadencia_media, n_corridas, km_totais
- [ ] Left border: 4px zone color from getZoneColor(info.zoneKey)
- [ ] Title: info.label + small zone badge (e.g., "Easy")
- [ ] Stats row: "N corridas • X km"
- [ ] Metrics row: pace, FC, cadência (only if not null)
- [ ] Hover elevation increase
- [ ] Unit tests: all 8 types render with correct colors/labels, null metrics hidden

**Tests**: unit (all types, colors, null handling, formatting)
**Gate**: quick

---

### T11: Create OverviewEmptyState component

**What**: Helpful empty state when shoe has no analysis data
**Where**: `frontend/src/components/workouts/shoes/detail/OverviewEmptyState.tsx`
**Depends on**: None
**Reuses**: Existing empty state patterns
**Requirement**: DET-07

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Message: "Nenhuma corrida associada a este tênis. Associe corridas na tela de Treinos para ver o perfil."
- [ ] Icon: shoe or chart
- [ ] Centered, muted styling
- [ ] Unit test: renders with correct message

**Tests**: unit (message, icon)
**Gate**: quick

---

### T11b: Create ShoeEditForm component (for detail page)

**What**: Inline edit form with status dropdown (includes "Aposentar") for detail page header
**Where**: `frontend/src/components/workouts/shoes/detail/ShoeEditForm.tsx`
**Depends on**: T04, existing ShoeForm patterns
**Reuses**: Format helpers, validation
**Requirement**: DET-10, SHOE-03, SHOE-04

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: shoe, onSave, onCancel
- [ ] Fields: name, brand, model, acquired_date, initial_km, max_km, status (ativo/aposentado)
- [ ] Status dropdown includes "Aposentar" option
- [ ] Validation: name required, initial_km >= 0
- [ ] Calls updateShoe API on save
- [ ] Closes on cancel or successful save
- [ ] Unit tests: validation, save, cancel, status change

**Tests**: unit (validation, save, cancel, status change)
**Gate**: quick

---

### T12: Create OverviewTab wrapper (for detail page tabs)

**What**: Tab wrapper that shows OverviewSection or DegradationSection
**Where**: `frontend/src/components/workouts/shoes/detail/DetailTabs.tsx`
**Depends on**: T09, T16
**Reuses**: Tab patterns
**Requirement**: NAV-01 (sections), NAV-02 (breadcrumb)

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: activeTab, onChange, shoe, profile, degradation, degradationLoading
- [ ] Two tabs: "Visão Geral", "Degradação" (with badges if applicable)
- [ ] Mobile: stacked tabs; Desktop: inline tabs
- [ ] Renders OverviewSection or DegradationSection based on activeTab
- [ ] Breadcrumb: Equipamentos > Tênis > [Nome]
- [ ] Back button / link to /equipamentos
- [ ] Unit tests: tab switching, breadcrumb, back link

**Tests**: unit (tabs, breadcrumb, conditional render)
**Gate**: quick

---

### T13: Create SignalRow component

**What**: Table row for degradation signal with tooltip, delta, direction badge, confidence
**Where**: `frontend/src/components/workouts/shoes/detail/SignalRow.tsx`
**Depends on**: T04, T18 (Tooltip)
**Reuses**: Badge patterns, format helpers
**Requirement**: DEG-04, DEG-05

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: signal (enriched with label, tooltip, higherIsWorse)
- [ ] Columns: Sinal (with Tooltip), Inicial, Final, Δ, Direção, Conf.
- [ ] Δ formatted: + prefix for positive, unit from signal
- [ ] Direção badge: red=piorou, green=melhorou, gray=estável
- [ ] Confidence badge: "baixa"/"media" (amber/green)
- [ ] Unit tests: all signal types, tooltips, colors, formatting

**Tests**: unit (all signals, tooltips, colors, badges)
**Gate**: quick

---

### T14: Create DegradationTable component

**What**: Table wrapper with header and SignalRow mapping
**Where**: `frontend/src/components/workouts/shoes/detail/DegradationTable.tsx`
**Depends on**: T13
**Reuses**: Table patterns, overflow-x-auto for mobile
**Requirement**: DEG-04

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: signals array
- [ ] Header: Sinal | Inicial | Final | Δ | Direção | Conf.
- [ ] Maps signals → SignalRow with enriched labels
- [ ] Wrapper: overflow-x-auto for mobile scroll
- [ ] Unit tests: renders all signals, mobile scroll, headers

**Tests**: unit (render, scroll, mapping)
**Gate**: quick

---

### T15: Create DegradationEmptyStates component

**What**: Two empty state variants for degradation section
**Where**: `frontend/src/components/workouts/shoes/detail/DegradationEmptyStates.tsx`
**Depends on**: None
**Reuses**: Empty state patterns
**Requirement**: DEG-02, DEG-03

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Variant `insufficient`: "Mínimo ~150 km acumulados para análise (tem X km). Continue correndo..."
- [ ] Variant `noSignals`: "Nenhum sinal de degradação detectado. O tênis mantém comportamento estável."
- [ ] Icons: amber warning / green check
- [ ] Unit tests: correct variant shows based on degradation.insufficient and signals.length

**Tests**: unit (two variants, conditional render)
**Gate**: quick

---

### T16: Create DegradationSection component

**What**: Container with header, status badge, table/empty, disclaimer, skeleton
**Where**: `frontend/src/components/workouts/shoes/detail/DegradationSection.tsx`
**Depends on**: T07, T14, T15
**Reuses**: Skeleton, badge patterns
**Requirement**: DEG-01, DEG-02, DEG-05, DEG-06

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: degradation, degradationLoading, shoeName
- [ ] Header: shoe name, total km, initial/final runs
- [ ] Status badge: green "Dados suficientes" / amber "Dados insuficientes"
- [ ] Composes: DegradationTable or DegradationEmptyStates
- [ ] Disclaimer: "Sinais, não veredito — esta análise não recomenda aposentadoria."
- [ ] Skeleton: 5 SignalRow skeletons when loading
- [ ] Unit tests: loading, insufficient, no signals, signals present

**Tests**: unit (all states, skeleton, disclaimer)
**Gate**: quick

---

### T17: Wire Detail Page with sections

**What**: Update detail page to use OverviewSection and DegradationSection via DetailTabs
**Where**: `frontend/src/app/(app)/equipamentos/[id]/page.tsx`
**Depends on**: T08, T09, T12, T16
**Reuses**: Layout, PanelSection
**Requirement**: All DET, DEG, NAV

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Page fetches shoe, profile, degradation
- [ ] Renders breadcrumb + back link
- [ ] Renders DetailTabs with OverviewSection and DegradationSection
- [ ] Passes shoe/profile to OverviewSection
- [ ] Passes degradation to DegradationSection
- [ ] Loading skeletons for both sections
- [ ] Error states with retry
- [ ] Integration test: page loads, tabs switch, data displays

**Tests**: integration (full page), e2e (navigation, tabs, data)
**Gate**: full

---

### T18: Update ShoesSection to use clickable cards (no buttons)

**What**: Ensure ShoeCard in list page is clickable, no edit/retire buttons
**Where**: `frontend/src/components/workouts/ShoesSection.tsx`
**Depends on**: T02 (already done), T03
**Reuses**: Router navigation
**Requirement**: SHOE-02, SHOE-03, SHOE-04

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] ShoeCard has no onRetire, onEdit props
- [ ] ShoeCard wrapped in Link or onClick → `/equipamentos/${shoe.id}`
- [ ] Card has hover/focus ring styles
- [ ] Touch target ≥ 44px (entire card)
- [ ] Manual test: click card → navigates to detail page

**Tests**: unit (no buttons, click navigates); visual (touch target)
**Gate**: quick + visual

---

### T19: Remove Comparison tab/components

**What**: Delete unused comparison components and hooks
**Where**: Multiple files
**Depends on**: T06, T07 (keep hooks for other uses)
**Reuses**: N/A (cleanup)
**Requirement**: Out of Scope - Comparison removed

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Delete `hooks/shoes/useShoeComparison.ts`
- [ ] Delete `components/workouts/shoes/compare/` directory
- [ ] Delete `components/workouts/shoes/ShoeSelectorDual.tsx`
- [ ] Remove ComparisonTab import/usage from ShoesAnalysisSection (already removed)
- [ ] Verify no imports of comparison types in remaining code
- [ ] Build passes

**Tests**: build passes; no dead code
**Gate**: build

---

### T20: Create Tooltip component (reusable)

**What**: Accessible tooltip for hover + focus, keyboard dismissible
**Where**: `frontend/src/components/common/Tooltip.tsx`
**Depends on**: None
**Reuses**: Floating-ui or CSS-only pattern
**Requirement**: DEG-05

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Props: children, content, position (top/bottom), delay
- [ ] Shows on hover + focus, hides on leave/blur/Escape
- [ ] Accessible: aria-describedby, keyboard dismiss
- [ ] Z-index above modals
- [ ] Unit tests: hover/focus show, keyboard dismiss, a11y attributes

**Tests**: unit (trigger, dismiss, a11y)
**Gate**: quick

---

### T21: Loading skeletons per section

**What**: Add skeleton loaders matching final layout for OverviewSection and DegradationSection
**Where**: OverviewSection, DegradationSection (modify)
**Depends on**: T09, T16
**Reuses**: Existing Skeleton component
**Requirement**: NAV-04

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] OverviewSection: header skeleton + 4 WorkoutTypeCard skeletons
- [ ] DegradationSection: header skeleton + 5 SignalRow skeletons
- [ ] No layout shift when loading → loaded
- [ ] Visual test: loading states match final layout

**Tests**: visual (layout match)
**Gate**: visual

---

### T22: Error states with retry

**What**: Error banners with retry button in detail page sections
**Where**: Detail page, OverviewSection, DegradationSection, hooks
**Depends on**: T06, T07, T09, T16
**Reuses**: Existing error banner pattern
**Requirement**: NAV-05

**Tools**: MCP: `filesystem`

**Done when**:
- [ ] Hooks return `error: string | null`
- [ ] Components render error banner with "Tentar novamente" button
- [ ] Button calls refetch()
- [ ] Per-section isolation (one section error doesn't break other)
- [ ] Unit test: simulate API failure, verify retry works

**Tests**: unit (error state, retry), integration (per-section isolation)
**Gate**: quick

---

### T23: Cross-browser responsive verification

**What**: Test all new components at all breakpoints, verify touch targets, scroll indicators
**Where**: All new components
**Depends on**: T03, T09, T10, T11, T13, T14, T16, T17, T18
**Reuses**: Playwright visual regression (if available)
**Requirement**: SHOE-07, NAV-06, Success Criteria mobile

**Tools**: MCP: `filesystem`, `playwright`

**Done when**:
- [ ] Tested at: 320px, 375px, 428px, 768px, 1024px, 1440px
- [ ] No horizontal overflow
- [ ] Touch targets ≥ 44px
- [ ] Text readable (no zoom needed)
- [ ] Tables: horizontal scroll with shadow gradient indicator
- [ ] Detail page: breadcrumb, tabs, edit form work on mobile
- [ ] Visual regression tests pass (if Playwright configured)

**Tests**: visual (manual + automated)
**Gate**: visual

---

### T24: Accessibility audit

**What**: Verify a11y compliance across all new components
**Where**: All new components
**Depends on**: T10, T13, T16, T18, T20
**Reuses**: axe-core, NVDA/VoiceOver
**Requirement**: All specs (implicit)

**Tools**: MCP: `filesystem`, `playwright` (axe-core)

**Done when**:
- [ ] Focus rings on all interactive elements
- [ ] Color + icon/text for all status indicators
- [ ] Tooltips: keyboard accessible (T20)
- [ ] Tables: proper semantics (thead, tbody, th scope)
- [ ] ARIA labels on icon-only buttons
- [ ] Screen reader test: NVDA/VoiceOver - all content announced
- [ ] axe-core automated: zero critical violations

**Tests**: unit (axe-core), manual (screen reader)
**Gate**: full

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in dependency order.

**Phase 1 (P1 - Shoe List Cleanup):**
- T01 (no deps)
- T02 depends on T01
- T03 depends on T01, T02

**Phase 2 (Foundation):**
- T04 (no deps)
- T05 depends on T04
- T06 depends on T05
- T07 depends on T04, T05

**Phase 3 (Detail Page - Overview):**
- T08 depends on T06, T07
- T09 depends on T06, T10, T11, T11b
- T10 depends on T04
- T11 depends on None
- T11b depends on T04
- T12 depends on T09, T16

**Phase 4 (Detail Page - Degradation):**
- T13 depends on T04, T20
- T14 depends on T13
- T15 depends on None
- T16 depends on T07, T14, T15

**Phase 5 (Integration & Polish):**
- T17 depends on T08, T09, T12, T16
- T18 depends on T02, T03
- T19 (cleanup)
- T20 (Tooltip)
- T21 depends on T09, T16
- T22 depends on T06, T07, T09, T16
- T23 depends on T03, T09-T18
- T24 depends on T10, T13, T16, T18, T20

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T01: Remove index prop | 1 file, 1 line | ✅ Granular |
| T02: Remove buttons, add click | 1 file, ~30 lines | ✅ Granular |
| T03: Mobile verification | 1 file, CSS check | ✅ Granular |
| T04: Mapping configs | 2 files, pure TS | ✅ Granular |
| T05: Verify API types | 1 file, verify | ✅ Granular |
| T06: useShoeAnalysis hook | 1 file, 1 hook | ✅ Granular |
| T07: useShoeDegradation hook | 1 file, 1 hook | ✅ Granular |
| T08: Detail page route | 1 file, 1 page | ✅ Granular |
| T09: OverviewSection | 1 file, 1 component | ✅ Granular |
| T10: WorkoutTypeCard | 1 file, 1 component | ✅ Granular |
| T11: OverviewEmptyState | 1 file, 1 component | ✅ Granular |
| T11b: ShoeEditForm | 1 file, 1 component | ✅ Granular |
| T12: DetailTabs | 1 file, 1 component | ✅ Granular |
| T13: SignalRow | 1 file, 1 component | ✅ Granular |
| T14: DegradationTable | 1 file, 1 component | ✅ Granular |
| T15: DegradationEmptyStates | 1 file, 1 component | ✅ Granular |
| T16: DegradationSection | 1 file, 1 component | ✅ Granular |
| T17: Wire detail page | 1 file, modification | ✅ Granular |
| T18: Verify clickable cards | 1 file, verify | ✅ Granular |
| T19: Remove comparison | Multiple file deletions | ✅ Granular (cohesive cleanup) |
| T20: Tooltip component | 1 file, 1 component | ✅ Granular |
| T21: Skeletons | 2 files, related | ✅ Granular |
| T22: Error states | 4 files, related | ✅ Granular |
| T23: Responsive verification | Cross-cutting | ✅ Granular |
| T24: Accessibility audit | Cross-cutting | ✅ Granular |

---

## Diagram-Definition Cross-Check

All dependencies point backward or within the same phase. No task depends on a later phase.

---

## Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
| ---- | ---------- | --------------- | --------- | ------ |
| T01 | Component (page) | none | unit | ✅ OK |
| T02 | Component | unit | unit | ✅ OK |
| T03 | Component (responsive) | visual | visual | ✅ OK |
| T04 | Config (lib/shoes) | unit | unit | ✅ OK |
| T05 | API types (lib/api) | unit | unit | ✅ OK |
| T06 | Hook | unit | unit | ✅ OK |
| T07 | Hook | unit | unit | ✅ OK |
| T08 | Page (route) | unit | unit | ✅ OK |
| T09 | Component | unit | unit | ✅ OK |
| T10 | Component | unit | unit | ✅ OK |
| T11 | Component | unit | unit | ✅ OK |
| T11b | Component | unit | unit | ✅ OK |
| T12 | Component | unit | unit | ✅ OK |
| T13 | Component | unit | unit | ✅ OK |
| T14 | Component | unit | unit | ✅ OK |
| T15 | Component | unit | unit | ✅ OK |
| T16 | Component | unit | unit | ✅ OK |
| T17 | Page (integration) | integration | integration | ✅ OK |
| T18 | Component | unit | unit | ✅ OK |
| T19 | Cleanup | build | build | ✅ OK |
| T20 | Component | unit | unit | ✅ OK |
| T21 | Components (skeletons) | visual | visual | ✅ OK |
| T22 | Components (error states) | integration | integration | ✅ OK |
| T23 | Cross-cutting (visual) | visual | visual | ✅ OK |
| T24 | Cross-cutting (a11y) | full (e2e) | full | ✅ OK |

---

## Notes

- **Total tasks**: 24 (reduced from 32 by removing comparison)
- **Estimated phases**: 5
- **Largest phase**: Phase 3 (6 tasks) - manageable
- **Sub-agent delegation**: ~24 tasks → ~3-4 batches of ~7 tasks → offer sub-agents after Phase 2
- **Zero backend changes** - all work is frontend presentation layer
- **Comparison completely removed** - hooks, components, types deleted