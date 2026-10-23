# design-system Validation

## Validation: design-system — PASS ✅

**Date**: 2026-10-22
**Spec**: `.specs/features/design-system/spec.md`
**Design**: `.specs/features/design-system/design.md` (sanctioned refinements: per-entity chart color table; REM=attention as DSN-14 refinement)
**Diff range**: `8263fa1..c0a8fd3` (15 commits, 41 files, +695/−383)
**Verifier**: independent sub-agent (author ≠ verifier)
**Test framework**: none in frontend repo — build-gate feature. Instruments: `npm run lint && npm run build`, structural greps, code-evidence checks (`file:line`).

---

## Task Completion

All 13 tasks (T1–T13) marked complete in `tasks.md` with commit hashes; each verified against the current code below.

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 tokens v0.3 | ✅ Done | globals.css:7-41 matches design block verbatim |
| T2 Instrument Sans + themeColor | ✅ Done | layout.tsx:6-10,24 |
| T3 sweep de bordas | ✅ Done | `border-white/` grep = 0; 9 `hover:border-border-hover` sites |
| T4 raio + tabulares | ✅ Done | `rounded-xl` grep = 0; 36 `tabular-nums` sites |
| T5 chartTheme | ✅ Done | lib/chartTheme.ts:12-31 |
| T6 charts de sono | ✅ Done | 4/4 no CartesianGrid, theme imports |
| T7 charts de recuperação | ✅ Done | 3/3 theme, HRV-13 intact |
| T8 charts de performance | ✅ Done | 3/3 theme, selos AD-009/AD-004 intact |
| T9 SplitsChart | ✅ Done | zonas from payload; see note on hrColor |
| T10 navegação responsiva | ✅ Done | Nav.tsx 95-218, (app)/layout.tsx:16-17 |
| T11 wordmark + header | ✅ Done | Header.tsx:16-31, icon.svg, UserMenu sem Link |
| T12 skeletons | ✅ Done | `Carregando` grep = 0; 6 application sites |
| T13 polimento | ✅ Done | 4 `bg-accent` buttons all `text-on-accent` |

---

## Spec-Anchored Acceptance Criteria

| AC | Spec-defined outcome | `file:line` + what I found | Result |
| -- | -------------------- | -------------------------- | ------ |
| DSN-01 | All surfaces on v0.3 tokens; themeColor `#0B0F12` | `frontend/src/app/globals.css:7-20` — literal values verified: `#0B0F12` (background), `#F5F7F2` (foreground), `#B7F36B` (accent), `#A1AAA9` (muted), `#121815` (card), `#1B241A` (raised), `#273323` (deep), `#354039` (border), `#4A574E` (border-hover), `#182014` (on-accent); `layout.tsx:24` `themeColor: "#0B0F12"`. Whole-src hex audit: only globals.css, chartTheme.ts, icon.svg (app/), layout.tsx — all sanctioned. **Note 1**: AC lists v0.3 token *names* (--night/--surface/--lime/--on-lime/--text); implementation carries the v0.3 *values* on canonical names per design Approach A + spec assumption row 2 — sanctioned, values exact. **Note 2**: 7 pre-existing `text-red-400` error-text sites (login/registrar/HrMethodCard/HrValuesCard) untouched — preserved under DSN-24; not hex, not in charts (Success Criterion scopes red-400 ban to charts). | ✅ PASS |
| DSN-02 | Canonical names (`--background/--foreground/--accent/--muted/--card`) survive as aliases, nothing breaks | `globals.css:7-11` + `@theme inline:24-28`; 100+ `bg-card`/`text-muted`/`accent` usages intact (spot: PanelSection.tsx:37); lint+build green = no component broke | ✅ PASS |
| DSN-03 | `--good #B7F36B`, `--attention #E9B44C`, `--alert #EF6757` in theme | `globals.css:18-20` (:root) + `:34-36` (@theme inline) — values exact | ✅ PASS |
| DSN-04 | Interactives use `--border-hover` on hover/focus; `#354039` never the only signal | 9 `hover:border-border-hover` sites: `login/page.tsx:19`, `registrar/page.tsx:21`, `HrvTable.tsx:75,86` (pills do seletor Saúde), `HrMethodCard.tsx:35`, `UserMenu.tsx:48` (Sair), `HrValuesCard.tsx:30`, `EvaluateForm.tsx:81,101`; `border-white/` grep = 0 | ✅ PASS |
| DSN-05 | Radius scale: card 16px, control 12px, pill 999px | `globals.css:37-38` (`--radius-card: 16px`, `--radius-ctl: 12px`); `rounded-xl` grep = 0; 79 `rounded-card`/`rounded-ctl` uses; pills `rounded-full` (Nav.tsx:132, UserMenu:48) | ✅ PASS |
| DSN-06 | No hex in `src/components` — grep returns only theme module | `git grep -nE "#[0-9a-fA-F]{6}" -- frontend/src/components` → **empty** (chartTheme lives in `src/lib` per design). Whole-src audit clean (see DSN-01) | ✅ PASS |
| DSN-07 | Instrument Sans 400–700 via next/font, `display: swap`, system fallback | `layout.tsx:2,6-10` — `Instrument_Sans({ variable: "--font-instrument-sans", subsets: ["latin"], display: "swap" })`, variable font (no weights declared — sanctioned by design/T2); `globals.css:39` `--font-sans: var(--font-instrument-sans)`; fallback stack `globals.css:46`. Computed-style = browser (UAT-pending); config evidence complete | ✅ PASS (structure) |
| DSN-08 | Geist Mono unchanged | `layout.tsx:12-15` (`Geist_Mono`, `--font-geist-mono`), `globals.css:40` | ✅ PASS |
| DSN-09 | Tabular-nums on every displayed number | 36 sites: HrvTable:54,58,61,79; DecayTable:68,71,75; PredictionsTable:73-77; display values HrvChart:128,139, StressChart:54, PerformancePanel:43, WorkoutsList:61; SplitsChart:44 `NUMERIC_LABEL="tabular-nums"` on all SVG numeric labels | ✅ PASS |
| DSN-10 | Font failure → fallback, never blocks render | `display: "swap"` (layout.tsx:9) + system stack (globals.css:46) + **self-hosted at build**: 8 `.woff2` in `.next/static/media/` — runtime does not depend on Google CDN. Offline runtime = browser (UAT-pending); build-time self-hosting verified | ✅ PASS (structure) |
| DSN-11 | Central chart theme: semantic set, axis/baseline `#354039`, tick 9–10px muted, tooltip card surface r12 + border | `lib/chartTheme.ts:12-31` — `chart` (axis #354039, muted #A1AAA9, context #4A574E, subject #B7F36B, attention #E9B44C, alert #EF6757, bandOpacity 0.06), `tick` {muted, fontSize:10}, `axisLine`, `tooltipCard = "rounded-ctl border border-border bg-card px-3 py-2 text-xs"`, `legendCaption` | ✅ PASS |
| DSN-12 | Baseline hairline only — no CartesianGrid, no vertical grid | `CartesianGrid` grep = **0** in frontend/src; all 10 Recharts charts: `axisLine={axisLine}` on X + `axisLine={false}`/`tickLine={false}` on Y (SleepChart:113,119 · SleepStages:100,107 · Rem:92,100 · Weekday:91,99 · Hrv:156,162 · Rhr:62,68 · Stress:66,72 · Pmc:119,125 · Vo2max:67,74 · Vdot:82,90); SplitsChart baseline line :344-350 | ✅ PASS |
| DSN-13 | "Hoje/último" highlighted lime where it exists | WeekdayPattern:107-112 — today cell `chart.subject` (bars); PmcChart:133-139 — current-day TSB bar `chart.subject`. Charts without a today/last concept: conditional (WHERE), N/A | ✅ PASS |
| DSN-14 | Single series → lime subject; area gradient lime→transparent when chart type supports area | Lime subjects: SleepChart:133, Vo2maxTrend:82, VdotTimeline:117, HrvChart:196. Sanctioned refinements (design mapping table + Tech Decisions, user-approved): REM=attention (RemChart:119, SleepStages:116), RHR/Stress=alert family (RhrChart:90, StressChart:81). **⚠️ Note**: "gradiente lime→transparente" is not literally implemented anywhere — `linearGradient` grep = 0; band fills use flat `bandOpacity` 0.06 (HrvChart:184, RemChart:109, VdotTimeline:101) per the design table, and no current single-series chart renders an Area-type series (the "quando suportar área" condition is not triggered) | ✅ PASS with ⚠️ note (see Gaps #4) |
| DSN-15 | Theme applied to all 11 charts; zero local hex | 11 × `from "@/lib/chartTheme"` imports (Hrv, Rem, Rhr, Sleep, SleepStages, Stress, Weekday, Pmc, Vo2max, Vdot, Splits — one each); components hex grep = 0 | ✅ PASS |
| DSN-16 | VDOT zone colors kept, backend-sourced, coexistence documented in module | chartTheme.ts:6-10 (coexistence rule); SplitsChart:302 — `zoneByKey.get(...)?.color ?? chart.muted` (payload `ZoneMeta.color`, backend source single: `backend/app/vdot/zones.py`, pinned by `test_activities_api.py:450-451`). **Note**: design table sketched HR line = `foreground`; implementation keeps pre-existing payload `hr_color` (`#f8fafc`, backend contract, untouched by this diff — near-identical neutral to `--foreground #F5F7F2`). Design-table detail yielded to the API contract (spec: "zero mudança de contratos"); AC itself says nothing about the HR line | ✅ PASS with note (see Gaps #5) |
| DSN-17 | <768px: fixed bottom tab bar, 4 items, icon 22px + label 10px, active lime + pill lime/12 | Nav.tsx:95-100 (PANELS: Treinos/Saúde/Performance/Perfil), :207-218 (`TabBar` — `fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/92 backdrop-blur md:hidden`), :146-180 (icons 22px svg, `text-[10px]` labels, active `text-accent` + `bg-accent/12` pill); rendered at `(app)/layout.tsx:17`. ⚠️ Sensor: no instrument guards the *render* (Gap #2) | ✅ PASS (structure) |
| DSN-18 | Active tab: touch target ≥44px, `aria-current="page"`, startsWith activePanel | Nav.tsx:155 (aria-current, TabBar) + :129 (top bar); target ≈ 97px × 58px at 390px (grid cell × pt-2 + size-9 + label); `activePanel` startsWith preserved :102-108 (deep route `/treinos/123` keeps Treinos active — edge case verified) | ✅ PASS (structure) |
| DSN-19 | 4 tabs fit at 390px, no horizontal scroll | Nav.tsx:148 `grid grid-cols-4` in `fixed inset-x-0` nav; no fixed widths/min-widths; labels 10px. Verified by code structure; pixel-truth is the spec's own UAT item (Success Criteria) | ✅ PASS (structure, UAT-pending) |
| DSN-20 | ≥768px: nav in header, same items/icons/labels/active; tab bar disappears | Nav.tsx:196 `hidden ... md:block`; :210 `md:hidden`; same PANELS + same `bg-accent/15 text-accent` active pattern; Header.tsx:32 `<Nav />` | ✅ PASS |
| DSN-21 | Header keeps wordmark + sync + Sair only; name link out | UserMenu.tsx:42-44 — display_name as plain `<span>` (Link removed); Header.tsx:16-31 wordmark, :33-36 UserMenu+SyncButton; `/perfil` via nav in both breakpoints | ✅ PASS |
| DSN-22 | 18px fixed bottom breathing + safe-area | Nav.tsx:210 `pb-[max(18px,env(safe-area-inset-bottom))]` | ✅ PASS |
| DSN-23 | Skeleton ~1.6s neutral pulse, no spinner, replaces loading text | Skeleton.tsx:7-13; globals.css:52-66 (`skeleton-pulse 1.6s`, gradient raised→deep); `Carregando` grep = **0**; `animate-spin` grep = 0 (only `animate-pulse` = 2px live-dot in EvaluationCard:54, a processing badge, not a loading state); applied: HealthPanel:143-146, PerformancePanel:87-89, WorkoutsList:172-174,211, WorkoutDetail:162-165, perfil:70-73, treinos/[id]:18-21 | ✅ PASS |
| DSN-24 | Error states unchanged | Diffs show error copy identical; only skin classes swapped. Branches preserved: HealthPanel:153, PerformancePanel:96, WorkoutsList:179, perfil:77, WorkoutDetail:193; pre-existing `text-red-400` error text untouched (7 sites, present at 8263fa1) | ✅ PASS |
| DSN-25 | Wordmark "ritmo" lowercase + lime pulse glyph | Header.tsx:16-31 — `stroke-accent` pulse SVG + `ritmo` | ✅ PASS |
| DSN-26 | Pulse as favicon (metadata icon) | `frontend/src/app/icon.svg` (pulse `#B7F36B` on `#0B0F12`, rounded square); build output generates `○ /icon.svg` route (auto-detect convention works) | ✅ PASS |

**Status**: ✅ 26/26 ACs with located evidence (21 full PASS, 5 PASS-by-structure with noted UAT-pending visual claims per the spec's own Success Criteria). 0 ACs without evidence. 2 instrument gaps + 3 notes flagged below — none contradicts an AC outcome.

### Edge cases (from spec)

- [x] Font offline → fallback stack, swap, self-hosted build (DSN-10) — build artifacts verified
- [x] Deep panel (`/treinos/123`) keeps Treinos tab active — `startsWith(href + "/")` Nav.tsx:102-108
- [x] Viewport crosses 768px both ways — same PANELS + same activePanel, two CSS-only renderizations; runtime = UAT
- [x] Chart without data → existing empty state (CLR-11/HLT-19 preserved — HealthPanel BlockEmpty:49-53, panels diff)
- [x] Multi-series (PMC, sleep stages) — colors from central semantic set (PmcChart:78-80 subject/alert/context; SleepStages:114-116 muted/subject/attention)

---

## Discrimination Sensor

Scratch: `git worktree add %TEMP%\opencode\ds-sensor HEAD` (c0a8fd3) + `npm ci` (junction to real node_modules rejected by Turbopack sandbox — real install used). Real tree never mutated; baseline porcelain clean; post-cleanup porcelain clean and scratch removed.

| # | Mutation | File:line (scratch) | Instrument | Killed? |
| - | -------- | ------------------- | --------- | ------- |
| 1 | `border border-border` → `border border-white/10` reintroduced | `WorkoutsList.tsx:41` | structural grep `border-white/` | ✅ Killed (grep hit) |
| 2 | Skeleton block → `Carregando treinos…` text reintroduced | `WorkoutsList.tsx:170` | structural grep `Carregando` | ✅ Killed (grep hit) |
| 3 | `--accent: #B7F36B` → `#a3e635` (old lime-400) | `globals.css:9` | greps + lint + build | ❌ **Survived** — lint 0, build 0, both structural greps blind (they don't assert token values) |
| 4 | `<TabBar />` + its import removed from app layout | `(app)/layout.tsx` | lint + build | ❌ **Survived** — lint 0, build 0 (no instrument asserts the tab bar renders) |
| 5 | `<Suspense>` boundary removed around `usePathname()` | `Nav.tsx:197-199` | lint + build | ✅ Killed — build fails: `CLIENT_HOOK_DYNAMIC` "usePathname() ... outside of <Suspense>" on `/treinos/[id]` (cacheComponents PPR enforcement) |

**Sensor depth**: lightweight-plus (5 mutations, build-gate feature — no mutation tooling applies without a test framework)
**Result**: 3/5 killed, 2 survived → both survivors are **instrument gaps**, not implementation defects (the real tree was independently verified by code evidence at those exact sites: globals.css:9 has `#B7F36B`; (app)/layout.tsx:17 renders `<TabBar />`). Suggested fix tasks in Gaps #1/#2.

---

## Gate Check

- **Gate command**: `cd frontend && npm run lint && npm run build`
- **Result**: lint ✅ (0 warnings), build ✅ — 12/12 pages, `/treinos/[id]` ◐ PPR, `/icon.svg` route generated
- **Known quirk**: first real-tree build aborted once with `SecurityFatalError` (one-time Next.js security-upgrade nudge; retry passed, as documented). The nudge also fired intermittently in the scratch worktree — retries passed. **Not run** per Verifier constraints: `next upgrade` (would touch package.json — outside this feature's authority). ⚠️ The advisory is real: **this Next.js version has a known security vulnerability and an upgrade is recommended** — surfaced to the orchestrator for an explicit go-ahead decision.
- **Test counts**: no frontend test framework (build-gate feature per tasks.md Test Coverage Matrix); backend suite untouched (zero server files in diff — 41/41 files are frontend/specs)

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| No features beyond what was asked | ✅ diff is exactly the 13 tasks' scope |
| Surgical changes (only files in scope) | ✅ 41 files all map to tasks; no unrelated "improvements" |
| Matches existing patterns | ✅ (AD-008 Recharts props pattern, activePanel, panel states preserved) |
| Data/contract integrity | ✅ zero API/format/empty-state changes (verified in panel + SplitsChart diffs) |
| Spec-anchored outcome check | ✅ 26/26 with literal-value verification where spec defines values |
| Every instrument maps to a spec AC / Done-when | ✅ (greps = DSN-04/06/23 + Success Criteria; build = tasks gate) |
| Documented guidelines followed | ✅ frontend/AGENTS.md (Next 16 conventions: icon.svg file convention, usePathname/Suspense under cacheComponents) |

---

## Gaps (ranked) — routed to orchestrator as fix tasks / decisions

1. **Instrument gap — token VALUES unprotected** (mutation 3 survived): no gate asserts the v0.3 literal values. A regression to the old `#a3e635`/zinc palette inside globals.css passes everything. Cheap deterministic fix: extend the structural gate with a literal-value grep (e.g. `git grep -n "B7F36B" -- frontend/src/app/globals.css frontend/src/lib/chartTheme.ts` must hit N sites; or a pinned token check script). Until then, only UAT against `docs/design/identidade-visual-v0.3.html` catches it.
2. **Instrument gap — TabBar render unguarded** (mutation 4 survived): removing `<TabBar />` from `(app)/layout.tsx` passes lint+build. Cheap fix: structural grep `git grep -n "<TabBar />" -- "frontend/src/app/(app)/layout.tsx"` must hit 1. — (ACs DSN-17..22).
3. **UAT-pending (spec's own Success Criterion, last checkbox)**: visual verification at 390px against the approved mock — computed style = Instrument Sans (DSN-07), offline fallback (DSN-10), no horizontal scroll (DSN-19), active-state/resize continuity (DSN-17/20 edge), skeleton pulse look (DSN-23), favicon in tab (DSN-26). Code structure supports all of them; human eyes required by the spec itself.
4. **⚠️ Spec-precision note — DSN-14 gradient clause**: "área em gradiente lime→transparente" has no literal implementation (no `linearGradient` in src); design refined band fills to flat `bandOpacity` 0.06 and no current single-series chart uses an Area-type series. Sanctioned by the design table; flagging so the spec text and code stop diverging (either amend the AC wording or accept the refinement explicitly).
5. **Note — SplitsChart HR line color**: design table sketched `foreground`; implementation preserves the pre-existing backend contract `hr_color` (`#f8fafc`, pinned by backend test). Visually near-identical neutral; keeping the payload honors "zero mudança de contratos". Recommend updating the design-table cell, not the code.
6. **Note — pre-existing `text-red-400` error text** (7 sites, present at 8263fa1, untouched): consistent with DSN-24 ("error states unchanged") but in tension with DSN-01's letter ("only v0.3 tokens"). `--alert` exists and would be the token-idiomatic choice; deferred to a future sweep — not this feature's regression.

---

## Requirement Traceability Update (proposed — for orchestrator to apply to spec.md)

| Requirement | Previous | Proposed |
| ----------- | -------- | -------- |
| DSN-01..DSN-26 | Pending | ✅ Verified (26/26 — see AC table; DSN-07/10/17/19 structure-verified, UAT pending per Success Criteria) |

---

## Summary

**Overall**: ✅ Ready (26/26 ACs evidence-verified; gates green; sensor 3/5 with 2 instrument gaps routed as fix tasks; UAT 390px pending as the spec's own final Success Criterion)

**Spec-anchored check**: 26/26 ACs with `file:line` evidence; 0 evidence-or-zero failures; 5 structure-verified ACs carry UAT-pending notes
**Sensor**: 5 mutations injected, 3 killed, 2 survived (both = instrument gaps, implementation independently verified)
**Gate**: lint + build pass (1 documented SecurityFatalError retry; Next upgrade advisory surfaced, not executed)
**Next steps**: (1) orchestrator applies traceability ✅ + routes Gaps #1/#2 as fix tasks (two one-line structural greps); (2) human UAT at 390px vs the v0.3 mock; (3) decide on the Next.js security upgrade (explicit go-ahead required — touches package.json).
