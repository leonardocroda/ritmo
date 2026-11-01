# Equipamentos/Tênis UX Improvements Specification

## Problem Statement

The current "Equipamentos" screen has several fundamental UX problems:

1. **Mysterious index number "5"** - The panel shows `index={5}` (displayed as "5 Tênis") but there's no visible 1, 2, 3, 4 - makes no sense to users.

2. **"Aposentar" button on the card** - Retiring a shoe is a one-time destructive action. Having it prominently on every card creates accidental-retirement risk and clutters the UI. It should only live inside the edit form where the status dropdown already exists.

3. **Analysis section is completely incomprehensible:**
   - **"Perfil" cards show things like "facil - tempo", "facil - limiar"** - users don't understand what these mean. They represent (tipo_treino, banda_pace) pairs but this is never explained.
   - **One shoe has more cards than another** - because it has runs in different pace bands/types, but users can't tell why.
   - **Comparison shows multiple lines (pairs) instead of one shoe-vs-shoe summary** - users want to compare shoes, not individual activity pairs.
   - **Inconsistent selectors** - Perfil and Degradação require selecting a shoe from the sidebar, but Comparação has two dropdowns. The mental model is broken.
   - **Pace bands are hardcoded** - They ignore the user's personalized VDOT zones (which have `valid_from` history). The `inferred_type` already classifies runs correctly using the user's zones.

4. **Comparison is rarely useful** - Hard to compare directly, low value. Better to have clear per-shoe detail.

## Goals

- [ ] Remove the confusing index number "5" from the panel title
- [ ] Move "Aposentar" action exclusively into the edit form (status dropdown)
- [ ] **Remove "Comparar" tab entirely**
- [ ] Create **Detail Page per shoe** (`/equipamentos/[id]`) with two sections:
  - **Visão Geral**: Group by `inferred_type` — human-readable labels, stats per type
  - **Degradação**: Clean signals table with human-readable labels, tooltips, color-coded direction
- [ ] Make shoe cards **clickable** (no edit button) → navigate to detail page
- [ ] Ensure all interactions are intuitive without requiring domain knowledge
- [ ] Mobile-first responsive design

## Out of Scope

| Feature | Reason |
|---------|--------|
| Changing the backend analysis algorithms | Backend logic is sound; only presentation/UX needs fixing |
| Adding new analysis metrics | Stick to existing metrics; improve how they're shown |
| Changing shoe CRUD operations | Only the "Aposentar" button position changes; edit still exists in detail page |
| Pace band / VDOT zone cross-tabulation | `inferred_type` already encodes the zone info; no second classification needed |
| Comparison tab | Removed - low value, confusing |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|----------------------|----------------|-----------|------------|
| Panel index numbering | Remove the index entirely from title | The "5" is a leftover from a multi-panel layout that no longer exists | y |
| "Aposentar" in edit form | Keep status dropdown with "ativo"/"aposentado" | Already exists; just remove the card button | y |
| Analysis structure | **No tabs** — Detail page per shoe with 2 sections | Simpler mental model; full page for each section | y |
| Shoe card interaction | Click card → navigate to `/equipamentos/[id]` | No edit button on card; edit lives in detail page | y |
| "inferred_type" labels | Human-readable mapping (see below) | Self-explanatory; shows corresponding VDOT zone | y |
| Empty states | Show helpful guidance instead of "no data" | Guide user to action (add runs, associate shoes) | y |
| Mobile-first | All layouts mobile-first, desktop enhanced | Project standard | y |
| Color coding | Use existing VDOT zone colors (green/blue/orange/red/purple) | Consistency with rest of app | y |
| Edit form location | In detail page, not list | Keeps list clean; detail page has space | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Clean Shoe Management (MVP) ⭐

**User Story**: As a runner, I want a clean, uncluttered shoe management screen so I can quickly see my shoes' status and mileage without visual noise.

**Why P1**: This is the primary screen for shoe management; the current "5 Tênis" and card-level "Aposentar" button are actively confusing.

**Acceptance Criteria** (each line is one EARS pattern):

1. The system SHALL display the panel title as "Tênis" without any index number
2. WHEN viewing a shoe card THEN the system SHALL NOT show an "Aposentar" button on the card
3. WHEN viewing a shoe card THEN the system SHALL NOT show an "Editar" button on the card
4. WHEN clicking a shoe card THEN the system SHALL navigate to `/equipamentos/[id]` (detail page)
5. The system SHALL show a visual life-bar (0-100%) on each shoe card with color coding (green/yellow/red)
6. The system SHALL show current km / max km and run count on each shoe card
7. The system SHALL be fully usable on mobile (320px+ viewport)

**Independent Test**: Navigate to /equipamentos on mobile and desktop, verify title is "Tênis" (no number), verify no buttons on cards, click a card → navigates to detail page.

---

### P2: Shoe Detail Page — Visão Geral ⭐

**User Story**: As a runner, I want to see a clear overview of how I use a specific shoe by workout type so I understand which shoe I use for what.

**Why P2**: The current "Perfil" tab shows cryptic "facil - tempo" cards that nobody understands.

**Acceptance Criteria**:

1. WHEN navigating to `/equipamentos/[id]` THEN the system SHALL show the detail page for that shoe
2. The page SHALL have two sections: "Visão Geral" and "Degradação" (tabs or stacked on mobile)
3. FOR the shoe THEN the system SHALL group runs by `inferred_type` (workout type) with human-readable labels:
   - "Rodagem fácil" (tipo `facil`) — zona Easy
   - "Tempo (maratona)" (tipo `tempo`) — zona Marathon
   - "Limiar" (tipo `limiar`) — zona Threshold
   - "Intervalado" (tipo `intervalado`) — zonas Interval/Repetition
   - "Repetições" (tipo `repeticao`) — zona Repetition
   - "Longão" (tipo `longao`) — zona Easy
   - "Progressivo" (tipo `progressivo`) — zona Marathon/Easy
   - "Prova" (tipo `prova`) — qualquer zona
4. FOR each type with data THEN the system SHALL show a card with: run count, total km, avg pace, avg HR, avg cadence (when available)
5. IF a shoe has no runs in a type THEN the system SHALL NOT show that type (don't show empty groups)
6. The system SHALL show a summary header: shoe name, brand/model, status badge, total runs, total km, current km, life-bar, acquired date
7. IF the shoe has no analysis data THEN the system SHALL show a helpful empty state: "Nenhuma corrida associada a este tênis. Associe corridas na tela de Treinos para ver o perfil."
8. Cards SHALL use VDOT zone colors (green/blue/orange/red/purple) as left border or badge
9. Layout SHALL be mobile-first: stacked cards on mobile, 2-column grid on desktop
10. An "Editar" button in header opens inline form or modal with status dropdown (includes "Aposentar")

**Independent Test**: Navigate to `/equipamentos/1`, verify Visão Geral shows types with readable labels and zone colors, verify empty types hidden, verify summary header, test edit button.

---

### P2: Shoe Detail Page — Degradação ⭐

**User Story**: As a runner, I want to see clear degradation signals for a shoe so I know when it might be time to replace it.

**Why P2**: Current degradation view shows raw signals without context - users don't know what GCT, vertical oscillation, EF mean or what values are concerning.

**Acceptance Criteria**:

1. WHEN the "Degradação" section is visible THEN the system SHALL show for the shoe:
   - **Header**: shoe name, total km, runs in initial window, runs in final window
   - **Status badge**: "Dados suficientes" (green) or "Dados insuficientes" (amber) with km threshold explanation
2. IF insufficient data (< 150 km) THEN the system SHALL show: "Mínimo ~150 km acumulados para análise (tem X km). Continue correndo com este tênis para ver sinais de degradação."
3. IF sufficient data but no signals THEN the system SHALL show: "Nenhum sinal de degradação detectado. O tênis mantém comportamento estável."
4. IF signals exist THEN the system SHALL show a table with columns: Sinal (human-readable), Inicial, Final, Δ, Direção (piorou/melhorou/estável com cor)
   - Human-readable labels: "Tempo de contato no solo (GCT)", "Oscilação vertical", "Cadência", "Fator de eficiência (EF)", "Deriva de FC", "Percepção de esforço (RPE)"
   - Tooltip/explanation for each metric: what it means, what "piorou" implies
5. The system SHALL show a persistent disclaimer: "Sinais, não veredito — esta análise não recomenda aposentadoria."
6. Layout SHALL be mobile-first: horizontal scroll table on mobile, full-width on desktop

**Independent Test**: Navigate to shoe with >150km, verify signals show with readable labels and tooltips, verify shoe with <150km shows helpful guidance.

---

### P3: Polish & Navigation

**User Story**: As a runner, I want consistent interaction patterns so I don't have to relearn the UI.

**Acceptance Criteria**:

1. The system SHALL use clickable cards (no buttons) on list page
2. Detail page SHALL have breadcrumb: Equipamentos > Tênis > [Nome]
3. Detail page SHALL have back button / browser back works
4. All loading states SHALL show skeleton screens matching final layout
5. All error states SHALL show user-friendly messages with retry option
6. All touch targets SHALL meet 44x44px minimum on mobile
7. Edit form in detail page SHALL include status dropdown with "Aposentar"

**Independent Test**: Navigate list → detail → back, verify breadcrumb, verify edit form works.

---

## Edge Cases

- IF user has 0 shoes THEN list shows empty state directing to add shoes
- IF API fails for detail page THEN show error with retry
- WHEN shoe is retired THEN it SHALL still appear in list and detail (historical data preserved)
- IF `inferred_type` values change in backend THEN frontend SHALL use a mapping config (not hardcoded)
- Viewport < 320px: horizontal scroll with shadow indicator
- IF shoe ID not found THEN 404 page

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|----------------|-------|-------|--------|
| SHOE-01 | P1: Clean Shoe Management | Design | Pending |
| SHOE-02 | P1: Clean Shoe Management | Design | Pending |
| SHOE-03 | P1: Clean Shoe Management | Design | Pending |
| SHOE-04 | P1: Clean Shoe Management | Design | Pending |
| SHOE-05 | P1: Clean Shoe Management | Design | Pending |
| SHOE-06 | P1: Clean Shoe Management | Design | Pending |
| SHOE-07 | P1: Clean Shoe Management | Design | Pending |
| DET-01 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-02 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-03 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-04 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-05 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-06 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-07 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-08 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-09 | P2: Detail Page - Visão Geral | Design | Pending |
| DET-10 | P2: Detail Page - Visão Geral | Design | Pending |
| DEG-01 | P2: Detail Page - Degradação | Design | Pending |
| DEG-02 | P2: Detail Page - Degradação | Design | Pending |
| DEG-03 | P2: Detail Page - Degradação | Design | Pending |
| DEG-04 | P2: Detail Page - Degradação | Design | Pending |
| DEG-05 | P2: Detail Page - Degradação | Design | Pending |
| DEG-06 | P2: Detail Page - Degradação | Design | Pending |
| NAV-01 | P3: Polish & Navigation | Design | Pending |
| NAV-02 | P3: Polish & Navigation | Design | Pending |
| NAV-03 | P3: Polish & Navigation | Design | Pending |
| NAV-04 | P3: Polish & Navigation | Design | Pending |
| NAV-05 | P3: Polish & Navigation | Design | Pending |
| NAV-06 | P3: Polish & Navigation | Design | Pending |
| NAV-07 | P3: Polish & Navigation | Design | Pending |

**Coverage:** 30 total, 0 mapped to tasks ⚠️

---

## Success Criteria

- [ ] User can navigate to /equipamentos and immediately understand the screen without explanation
- [ ] No buttons on shoe cards — click navigates to detail page
- [ ] "Aposentar" action only accessible via edit form in detail page (zero accidental retirements)
- [ ] Detail page has clear Visão Geral and Degradação sections
- [ ] Degradation signals have human-readable labels with tooltips
- [ ] All empty/error states guide the user to next action
- [ ] Fully functional and beautiful on mobile (320px+) and desktop
- [ ] Zero console errors or warnings in production build