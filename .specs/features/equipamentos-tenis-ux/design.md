# Equipamentos/Tênis UX Improvements - Design

## Architecture Overview

```
frontend/src/
├── app/(app)/equipamentos/
│   ├── page.tsx                    # List page (cleaned up)
│   └── [id]/page.tsx               # Detail page per shoe
├── components/workouts/
│   ├── ShoesSection.tsx            # P1: Clean shoe management (list)
│   ├── shoes/
│   │   ├── ShoeCard.tsx            # Clickable card (no buttons)
│   │   ├── ShoeForm.tsx            # Form with status dropdown (for detail page edit)
│   │   ├── ShoeLifeBar.tsx         # Reusable life bar component
│   │   ├── ShoeEditForm.tsx        # Inline edit form for detail page
│   │   ├── detail/
│   │   │   ├── DetailTabs.tsx      # Tab navigation (Visão Geral / Degradação)
│   │   │   ├── OverviewSection.tsx # Visão Geral section
│   │   │   ├── WorkoutTypeCard.tsx # Card per workout type
│   │   │   ├── OverviewEmptyState.tsx
│   │   │   ├── DegradationSection.tsx # Degradação section
│   │   │   ├── DegradationTable.tsx
│   │   │   ├── SignalRow.tsx       # Row with tooltip
│   │   │   ├── DegradationEmptyStates.tsx
│   │   │   └── ShoeEditForm.tsx    # Edit form in detail page header
│   └── common/
│       ├── PanelSection.tsx        # Existing
│       ├── Skeleton.tsx            # Existing
│       └── Tooltip.tsx             # Reusable tooltip
├── lib/
│   ├── api.ts                      # API types & functions (verify existing)
│   ├── format.ts                   # Format helpers (existing)
│   └── shoes/
│       ├── workoutTypeLabels.ts    # Mapping config
│       ├── signalLabels.ts         # Mapping config
│       └── zoneColors.ts           # VDOT zone colors
└── hooks/
    └── shoes/
        ├── useShoes.ts             # Existing (reuse)
        ├── useShoeAnalysis.ts      # New: overview data
        └── useShoeDegradation.ts   # New: degradation data
```

---

## Type Definitions

### `lib/api.ts` - Extended Types (Already Exist)

The existing types in `lib/api.ts` already match our needs:
- `Shoe` - shoe entity
- `AnalysisShoeProfile` / `AnalysisGroup` - overview data
- `DegradationOut` / `DegradationSignal` - degradation data
- `getShoes()`, `createShoe()`, `updateShoe()`, `getAnalysisShoes()`, `getDegradation(shoeId)` - API functions

**Zero new types needed** - just verify existing ones match.

---

### `lib/shoes/workoutTypeLabels.ts` - Mapping Config

```typescript
// Single source of truth for workout type labels and zone colors
// If backend changes inferred_type values, update ONLY here

export type WorkoutTypeKey =
  | "facil"
  | "tempo"
  | "limiar"
  | "intervalado"
  | "repeticao"
  | "longao"
  | "progressivo"
  | "prova"
  | "outro";

export type ZoneKey = "easy" | "marathon" | "threshold" | "interval" | "repetition";

export interface WorkoutTypeInfo {
  label: string;
  zoneKey: ZoneKey;
  zoneLabel: string;
}

export const WORKOUT_TYPE_LABELS: Record<WorkoutTypeKey, WorkoutTypeInfo> = {
  facil: { label: "Rodagem fácil", zoneKey: "easy", zoneLabel: "Easy" },
  tempo: { label: "Tempo (maratona)", zoneKey: "marathon", zoneLabel: "Maratona" },
  limiar: { label: "Limiar", zoneKey: "threshold", zoneLabel: "Limiar" },
  intervalado: { label: "Intervalado", zoneKey: "interval", zoneLabel: "Intervalado" },
  repeticao: { label: "Repetições", zoneKey: "repetition", zoneLabel: "Repetição" },
  longao: { label: "Longão", zoneKey: "easy", zoneLabel: "Easy" },
  progressivo: { label: "Progressivo", zoneKey: "marathon", zoneLabel: "Maratona" },
  prova: { label: "Prova", zoneKey: "interval", zoneLabel: "Intervalado" },
  outro: { label: "Outro", zoneKey: "easy", zoneLabel: "Easy" },
};

export const ZONE_COLORS: Record<ZoneKey, string> = {
  easy: "#22c55e",      // green-500
  marathon: "#3b82f6",  // blue-500
  threshold: "#f97316", // orange-500
  interval: "#ef4444",  // red-500
  repetition: "#a855f7", // purple-500
} as const;

export function getWorkoutTypeInfo(tipo: string): WorkoutTypeInfo {
  return WORKOUT_TYPE_LABELS[tipo as WorkoutTypeKey] ?? WORKOUT_TYPE_LABELS.outro;
}

export function getZoneColor(zoneKey: ZoneKey): string {
  return ZONE_COLORS[zoneKey];
}

// Priority order for sorting workout types in overview
export const WORKOUT_TYPE_PRIORITY: WorkoutTypeKey[] = [
  "facil", "tempo", "limiar", "intervalado", "repeticao", "longao", "progressivo", "prova", "outro"
];

export function compareWorkoutTypes(a: string, b: string): number {
  const idxA = WORKOUT_TYPE_PRIORITY.indexOf(a as WorkoutTypeKey);
  const idxB = WORKOUT_TYPE_PRIORITY.indexOf(b as WorkoutTypeKey);
  if (idxA === -1 && idxB === -1) return 0;
  if (idxA === -1) return 1;
  if (idxB === -1) return -1;
  return idxA - idxB;
}
```

---

### `lib/shoes/signalLabels.ts` - Degradation Signal Mapping

```typescript
// Degradation signal labels and tooltips
// Maps backend signal keys to human-readable labels with explanations

export type SignalKey =
  | "gct_ms"
  | "vert_osc_cm"
  | "avg_cadence"
  | "ef"
  | "hr_drift"
  | "rpe";

export interface SignalInfo {
  label: string;
  tooltip: string;
  higherIsWorse: boolean;
  unit: string;
}

export const SIGNAL_LABELS: Record<SignalKey, SignalInfo> = {
  gct_ms: {
    label: "Tempo de contato no solo (GCT)",
    tooltip: "Tempo que o pé fica no chão a cada passada. Aumento = menos eficiência, possível fadiga do tênis.",
    higherIsWorse: true,
    unit: "ms",
  },
  vert_osc_cm: {
    label: "Oscilação vertical",
    tooltip: "Quanto o corpo sobe/desce a cada passada. Aumento = mais desperdício de energia vertical.",
    higherIsWorse: true,
    unit: "cm",
  },
  avg_cadence: {
    label: "Cadência",
    tooltip: "Passadas por minuto. Queda = passadas mais longas/forçadas, possível perda de responsividade.",
    higherIsWorse: false,  // lower is worse
    unit: "spm",
  },
  ef: {
    label: "Fator de eficiência (EF)",
    tooltip: "Relação velocidade/FC. Queda = coração trabalha mais pela mesma velocidade.",
    higherIsWorse: false,  // lower is worse
    unit: "",
  },
  hr_drift: {
    label: "Deriva de FC",
    tooltip: "Aumento da FC durante a corrida em pace constante. Aumento = menos eficiência cardiovascular.",
    higherIsWorse: true,
    unit: "bpm",
  },
  rpe: {
    label: "Percepção de esforço (RPE)",
    tooltip: "Esforço percebido (1-10). Aumento = sente mais difícil no mesmo pace.",
    higherIsWorse: true,
    unit: "pontos",
  },
};

export function getSignalInfo(sinal: string): SignalInfo {
  return SIGNAL_LABELS[sinal as SignalKey] ?? {
    label: sinal,
    tooltip: "",
    higherIsWorse: true,
    unit: "",
  };
}

export function getDirection(delta: number, higherIsWorse: boolean): "piorou" | "melhorou" | "estável" {
  const threshold = 0.01;
  if (Math.abs(delta) <= threshold) return "estável";
  if (higherIsWorse) {
    return delta > 0 ? "piorou" : "melhorou";
  }
  return delta > 0 ? "melhorou" : "piorou";
}

export function getDirectionColor(direction: "piorou" | "melhorou" | "estável"): string {
  switch (direction) {
    case "piorou": return "text-coral";
    case "melhorou": return "text-lime";
    default: return "text-muted";
  }
}

export function getDirectionBg(direction: "piorou" | "melhorou" | "estável"): string {
  switch (direction) {
    case "piorou": return "bg-coral/15 text-coral border-coral/30";
    case "melhorou": return "bg-lime/15 text-lime border-lime/30";
    default: return "bg-border text-muted border-border";
  }
}
```

---

## Component Design

### 1. `ShoesSection.tsx` (P1 - Minimal Changes)

```tsx
// Changes from current:
// - PanelSection title: "Tênis" (no index prop)
// - ShoeCard: REMOVE onRetire/onEdit props and buttons
// - ShoeCard: WRAP in Link to `/equipamentos/${shoe.id}`
// - handleRetire: REMOVE
// - handleEdit: REMOVE
```

### 2. `app/(app)/equipamentos/page.tsx`

```tsx
// Entry point - just renders ShoesSection
// Title: "Tênis" (no index)
```

### 3. `app/(app)/equipamentos/[id]/page.tsx` - Detail Page

```tsx
// Dynamic route - fetches shoe, profile, degradation
// Renders breadcrumb + back link
// Renders DetailTabs with OverviewSection + DegradationSection
// Loading skeletons for both sections
// Error states with retry
```

### 4. `components/workouts/shoes/detail/DetailTabs.tsx`

```tsx
// Props: activeTab, onChange, shoe, profile, degradation, degradationLoading
// Two tabs: "Visão Geral", "Degradação" (with badges)
// Mobile: stacked tabs; Desktop: inline tabs
// Renders OverviewSection or DegradationSection based on activeTab
// Breadcrumb: Equipamentos > Tênis > [Nome]
// Back button / link to /equipamentos
```

### 5. `components/workouts/shoes/detail/OverviewSection.tsx`

```tsx
// Props: { shoe: Shoe; profile: AnalysisShoeProfile }
// Renders:
// - Header: shoe name, brand/model, status badge, total runs, total km, current km, life-bar, acquired date
// - Edit button in header (opens ShoeEditForm modal/inline)
// - Maps profile.groups → WorkoutTypeCard array (filters n_corridas > 0)
// - Empty state: OverviewEmptyState when no groups
// - Responsive: mobile stacked, desktop grid-cols-1 md:grid-cols-2
```

### 6. `components/workouts/shoes/detail/WorkoutTypeCard.tsx`

```tsx
// Props: tipo, pace_medio_s, fc_media, cadencia_media, n_corridas, km_totais
// Left border: 4px zone color from getZoneColor(info.zoneKey)
// Title: info.label + small zone badge (e.g., "Easy")
// Stats row: "N corridas • X km"
// Metrics row: pace, FC, cadência (only if not null)
// Hover elevation increase
```

### 7. `components/workouts/shoes/detail/OverviewEmptyState.tsx`

```tsx
// Message: "Nenhuma corrida associada a este tênis. Associe corridas na tela de Treinos para ver o perfil."
// Icon: shoe or chart
// Centered, muted styling
```

### 8. `components/workouts/shoes/detail/ShoeEditForm.tsx`

```tsx
// Props: shoe, onSave, onClose
// Fields: name, brand, model, acquired_date, initial_km, max_km, status (ativo/aposentado)
// Status dropdown includes "Aposentar" option
// Validation: name required, initial_km >= 0
// Calls updateShoe API on save
// Closes on cancel or successful save
// Opens from "Editar" button in OverviewSection header
```

### 9. `components/workouts/shoes/detail/DegradationSection.tsx`

```tsx
// Props: degradation, degradationLoading, shoeName
// Renders:
// - Header: shoe name, total km, initial/final runs
// - Status badge: green "Dados suficientes" / amber "Dados insuficientes"
// - Composes: DegradationTable or DegradationEmptyStates
// - Disclaimer: "Sinais, não veredito — esta análise não recomenda aposentadoria."
// - Skeleton: 5 SignalRow skeletons when loading
```

### 10. `components/workouts/shoes/detail/DegradationTable.tsx`

```tsx
// Props: signals array
// Header: Sinal | Inicial | Final | Δ | Direção | Conf.
// Maps signals → SignalRow with enriched labels
// Wrapper: overflow-x-auto for mobile scroll
```

### 11. `components/workouts/shoes/detail/SignalRow.tsx`

```tsx
// Props: signal (enriched with label, tooltip, higherIsWorse)
// Columns: Sinal (with Tooltip), Inicial, Final, Δ, Direção, Conf.
// Δ formatted: + prefix for positive, unit from signal
// Direção badge: red=piorou, green=melhorou, gray=estável
// Confidence badge: "baixa"/"media" (amber/green)
```

### 12. `components/workouts/shoes/detail/DegradationEmptyStates.tsx`

```tsx
// Variants:
// - insufficient: "Mínimo ~150 km acumulados para análise (tem X km). Continue correndo..."
// - noSignals: "Nenhum sinal de degradação detectado. O tênis mantém comportamento estável."
// Icons: amber warning / green check
```

### 13. `components/common/Tooltip.tsx`

```tsx
// Accessible tooltip for hover + focus, keyboard dismissible
// Props: children, content, position (top/bottom), delay
// Shows on hover + focus, hides on leave/blur/Escape
// Accessible: aria-describedby, keyboard dismiss
// Z-index above modals
```

### 14. `components/workouts/ShoesSection.tsx` - List Page

```tsx
// ShoeCard wrapped in Link to `/equipamentos/${shoe.id}`
// No onRetire, onEdit props
// No "Aposentar" or "Editar" buttons
// Card has hover/focus styles indicating clickable
// Touch target ≥ 44px (entire card)
```

---

## Hooks

### `hooks/shoes/useShoeAnalysis.ts`

```typescript
interface UseShoeAnalysisReturn {
  profiles: Map<number, AnalysisShoeProfile>;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Fetches /api/tenis/analysis/shoes
// Transforms: array -> Map by shoe_id
// Sorts groups by workout type priority
```

### `hooks/shoes/useShoeDegradation.ts`

```typescript
interface EnrichedSignal extends DegradationSignal {
  label: string;
  tooltip: string;
  higherIsWorse: boolean;
  direction: "piorou" | "melhorou" | "estável";
  directionColor: string;
  directionBg: string;
}

interface UseShoeDegradationReturn {
  degradation: DegradationOut | null;
  enrichedSignals: EnrichedSignal[];
  loading: boolean;
  error: string | null;
  refetch: (shoeId: number) => Promise<void>;
}

// Calls /api/tenis/degradation/{shoeId}
// Enriches signals with labels/tooltips from SIGNAL_LABELS
// Auto-fetch effect when shoeId changes
```

---

## Mobile-First Responsive Strategy

| Component | Mobile (< 640px) | Tablet (640-1024px) | Desktop (> 1024px) |
|-----------|------------------|---------------------|-------------------|
| Shoe cards (list) | 1 column | 2 columns | 2 columns |
| Overview cards (detail) | 1 column | 2 columns | 2-3 columns |
| Degradation table | Horizontal scroll | Horizontal scroll | Full table |
| Detail tabs | Stacked | Inline | Inline |

---

## Loading & Error States

```tsx
// Skeletons per section:
OverviewSection: header skeleton + 4 WorkoutTypeCard skeletons
DegradationSection: header skeleton + 5 SignalRow skeletons

// Error pattern:
<div className="rounded-card border border-destructive/30 bg-destructive/10 p-4">
  <p className="text-sm text-destructive">{message}</p>
  <button onClick={retry} className="mt-2 text-sm underline">Tentar novamente</button>
</div>
```

---

## Accessibility

- All interactive elements: focus-visible rings
- Color coding never sole indicator (always + icon/text)
- Tooltips: keyboard accessible (focus + hover)
- Tables: proper `<th scope="col">`, `<thead>`/`<tbody>`
- Status badges: `aria-label` for screen readers
- Minimum touch target: 44x44px
- Breadcrumb with proper `nav` + `aria-label`

---

## Backend API Contract (No Changes Needed)

| Endpoint | Used By | Notes |
|----------|---------|-------|
| `GET /api/shoes` | ShoesSection, Detail page | Existing ✓ |
| `POST /api/shoes` | ShoeForm (create) | Existing ✓ |
| `PATCH /api/shoes/{id}` | ShoeEditForm (edit/status) | Existing ✓ |
| `GET /api/tenis/analysis/shoes` | useShoeAnalysis | Returns `inferred_type` groups ✓ |
| `GET /api/tenis/degradation/{shoeId}` | useShoeDegradation | Returns signals ✓ |

**Zero backend changes required.** Frontend transforms/presents existing data.

---

## Implementation Sequence

1. **P1 - Shoe List Cleanup** (T01-T03)
   - Remove index from PanelSection title
   - Remove buttons from ShoeCard, make clickable
   - Mobile verification

2. **Foundation** (T04-T07)
   - Mapping configs
   - Verify API types
   - useShoeAnalysis hook
   - useShoeDegradation hook

3. **Detail Page - Overview** (T08-T12)
   - Detail page route
   - OverviewSection, WorkoutTypeCard, OverviewEmptyState
   - ShoeEditForm
   - DetailTabs

4. **Detail Page - Degradation** (T13-T16)
   - SignalRow, DegradationTable, DegradationEmptyStates
   - DegradationSection

5. **Integration & Polish** (T17-T24)
   - Wire detail page
   - Verify clickable cards
   - Remove comparison code
   - Tooltip, skeletons, error states
   - Responsive verification, a11y audit