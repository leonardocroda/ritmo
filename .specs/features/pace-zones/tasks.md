# Pace Zones (VDOT) Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/pace-zones/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase sampling (`backend/tests/test_hr_zones_api.py`, `backend/tests/test_vdot_calibration.py`, `backend/tests/test_profile_connection_api.py`) and spec - confirm before Execute. Guidelines found: project uses **pytest + FastAPI TestClient on real Postgres** for API tests; unit tests for pure functions; no frontend test framework configured (typecheck + build gate only).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| SQLAlchemy Model | unit | Create/read instance; FK constraints; index exists | `backend/tests/test_vdot_zone_configs_model.py` | `pytest backend/tests/test_vdot_zone_configs_model.py` |
| Migration / Seed | integration | Table created; seed data matches `vdot_zones.json`; idempotent re-run | `backend/tests/test_vdot_migration.py` | `pytest backend/tests/test_vdot_migration.py` |
| Calibration Script | integration | Dual-write (DB + JSON); upsert on re-run; error rollback | `backend/tests/test_vdot_calibration_db.py` | `pytest backend/tests/test_vdot_calibration_db.py` |
| API Endpoint | e2e | Happy path (200 + shape); 401 no session; 500 no config; user isolation | `backend/tests/test_pace_zones_api.py` | `pytest backend/tests/test_pace_zones_api.py` |
| Frontend Page | none | Build gate only (typecheck + lint) | `frontend/src/app/(app)/pace-zones/page.tsx` | `cd frontend && npm run build && npm run lint` |
| Frontend Card | none | Build gate only | `frontend/src/app/(app)/perfil/page.tsx` | `cd frontend && npm run build && npm run lint` |
| Frontend Modal | none | Build gate only | `frontend/src/components/profile/RecalibrateModal.tsx` | `cd frontend && npm run build && npm run lint` |

**Coverage Expectation values** - from project patterns (strong defaults where no guideline):

| Layer type | Strong default (no guideline) |
| ---------- | ----------------------------- |
| Domain / business-logic (service, use-case, domain model) | All branches; 1:1 to spec ACs; every listed edge case has a test |
| Route / controller / e2e / integration | All routes in scope: happy path + every listed edge case + error/failure paths |
| Repository / data-access | Key query paths + error handling; infer from existing repo tests |
| Entity / config / schema | none - build gate only |

---

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After tasks with unit tests only | `pytest backend/tests/test_vdot_zone_configs_model.py -v` |
| Full | After tasks with e2e/integration tests | `pytest backend/tests/test_vdot_migration.py backend/tests/test_vdot_calibration_db.py backend/tests/test_pace_zones_api.py -v` |
| Build | After phase completion or config/entity-only tasks | `cd backend && python -m py_compile $(find app -name "*.py") && cd ../frontend && npm run build && npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Database Foundation

Tasks that must be done first, in order.

```
T1
T2
T3
```

### Phase 2: Calibration Script Update

Builds on the foundation.

```
T4
```

### Phase 3: API Endpoint

Brings data layer to HTTP.

```
T5
```

### Phase 4: Frontend Integration

User-facing pieces.

```
T6
T7
T8
```

---

## Task Breakdown

### T1: Create VdotZoneConfig SQLAlchemy Model

**What**: Add new `VdotZoneConfig` model to `backend/app/db/models.py` with table `vdot_zone_configs`, user-scope, structured fields for VDOT calibration data.

**Where**: `backend/app/db/models.py`

**Depends on**: None

**Reuses**: Pattern from `HrZoneConfig` (lines 373-389), `DEFAULT_USER_ID`, `_utcnow`, `Index`

**Requirement**: PZ-01 (table creation)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [x] Model class defined with all fields: id, user_id, vdot, source, test_date, distance_m, time_s, zones (JSON), equivalencias (JSON), valid_from, created_at
- [x] `__tablename__ = "vdot_zone_configs"`
- [x] Index on (user_id, valid_from)
- [x] ForeignKey to users with DEFAULT_USER_ID default
- [x] No TypeScript/SQLAlchemy errors on import

**Tests**: unit
**Gate**: quick

---

### T2: Create Idempotent Migration + Seed in init_db()

**What**: Add `_migrate_vdot_zone_configs()` function in `backend/app/db/engine.py` that creates the table and seeds from `vdot_zones.json` (idempotent: checks if table/row exists). Call it from `_migrate_schema()`.

**Where**: `backend/app/db/engine.py`

**Depends on**: T1

**Reuses**: Pattern from `_migrate_users_columns()` and `_migrate_activities_shoe_id()` (idempotent ALTER TABLE + index); seed pattern from `HrZoneConfig` seed (lines 150-164)

**Requirement**: PZ-01, PZ-02 (migration + seed)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] Function `_migrate_vdot_zone_configs()` added
- [ ] Creates table if not exists (raw SQL idempotent)
- [ ] Creates index if not exists
- [ ] Seeds one row for DEFAULT_USER_ID from `vdot_zones.json` (reads via `get_settings().vdot_zones_path`)
- [ ] Idempotent: re-running doesn't duplicate
- [ ] Added to `_migrate_schema()` call chain
- [ ] `init_db()` works without errors

**Tests**: integration
**Gate**: full

---

### T3: Add VdotZoneConfig Model Tests

**What**: Create unit test file for the new model covering instantiation, FK, constraints.

**Where**: `backend/tests/test_vdot_zone_configs_model.py`

**Depends on**: T1

**Reuses**: Pattern from `test_hr_zones_models.py` (lines 19-155)

**Requirement**: PZ-01

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] Test file created
- [ ] Tests: model instantiation, FK to user, JSON fields accept dict, index exists, valid_from date
- [ ] All tests pass
- [ ] Gate: `pytest backend/tests/test_vdot_zone_configs_model.py -v` passes

**Tests**: unit
**Gate**: quick

---

### T4: Update calibrate_vdot.py for Dual-Write (DB + JSON)

**What**: Modify `backend/app/vdot/calibrate_vdot.py` to write calibration to `vdot_zone_configs` table (upsert by user_id) in addition to writing `vdot_zones.json`. Use `SessionLocal` directly.

**Where**: `backend/app/vdot/calibrate_vdot.py`

**Depends on**: T1, T2

**Reuses**: Existing `gerar_zonas()`, `calculate_vdot()`, `equivalent_time()`, `load_calibration()`; DB session pattern from `engine.py`

**Requirement**: PZ-03 (calibration writes to DB)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] New function `save_calibration_to_db(user_id: int, calibration_data: dict)` added
- [ ] Upsert logic: if row exists for user, update; else insert
- [ ] JSON file still written (backward compatibility)
- [ ] Transaction: DB commit + JSON write (JSON last, append-only)
- [ ] CLI still works: `python calibrate_vdot.py` runs end-to-end
- [ ] Gate: `pytest backend/tests/test_vdot_calibration_db.py -v` passes (new test file)

**Tests**: integration
**Gate**: full

---

### T5: Create GET /api/profile/pace-zones Endpoint

**What**: Add endpoint in `backend/app/profile/router.py` that reads `VdotZoneConfig` for current user and returns structured response (Pydantic models inline).

**Where**: `backend/app/profile/router.py`

**Depends on**: T1, T2

**Reuses**: Pattern from `get_hr_zones()` (lines 147-155); `require_session`, `get_db`; error handling like `ZoneConfigError` → 500

**Requirement**: PZ-04 (API endpoint)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] Endpoint `GET /api/profile/pace-zones` added
- [ ] Returns `PaceZonesOut` with all fields from spec (vdot, source, test_date, distancia_metros, tempo_segundos, zones dict, equivalencias dict)
- [ ] 500 "zonas VDOT não configuradas" if no row for user
- [ ] 401 if no session (via `require_session`)
- [ ] User-scope: only returns current user's data
- [ ] Gate: `pytest backend/tests/test_pace_zones_api.py -v` passes (new test file)

**Tests**: e2e
**Gate**: full

---

### T6: Add Frontend API Types + Function

**What**: Add `PaceZone`, `PaceZonesOut` types and `getPaceZones()` function to `frontend/src/lib/api.ts`.

**Where**: `frontend/src/lib/api.ts`

**Depends on**: T5

**Reuses**: Pattern from `HrZonesOut`/`getHrZones()` (lines 728-829); `apiFetch`, `parseError`

**Requirement**: PZ-01 (frontend types)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] TypeScript types match backend response shape exactly
- [ ] `getPaceZones()` function added with proper error handling
- [ ] No TypeScript errors
- [ ] Build gate passes: `cd frontend && npm run build`

**Tests**: none
**Gate**: build

---

### T7: Create PaceZonesPage (/pace-zones)

**What**: Create page component at `frontend/src/app/(app)/pace-zones/page.tsx` displaying VDOT, 5 zones with pace/description/color, equivalences table, and "Recalibrar" button opening modal.

**Where**: `frontend/src/app/(app)/pace-zones/page.tsx`

**Depends on**: T6

**Reuses**: Exact pattern from `/zonas-fc/page.tsx` (useEffect + 3 states loading/error/ready); `PanelSection`, `Skeleton`, `Link`; modal import

**Requirement**: PZ-01, PZ-02 (frontend page)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] Page renders VDOT + source + test_date
- [ ] 5 zones displayed with: label, pace range/pace, description, color badge
- [ ] Equivalences table: 5K, 10K, Meia, Maratona with paces
- [ ] "Recalibrar" button opens modal
- [ ] Loading skeleton + error state handled
- [ ] Build gate passes: `cd frontend && npm run build && npm run lint`

**Tests**: none
**Gate**: build

---

### T8: Create RecalibrateModal Component

**What**: Create `frontend/src/components/profile/RecalibrateModal.tsx` - modal with CLI command `python calibrate_vdot.py` and brief explanation.

**Where**: `frontend/src/components/profile/RecalibrateModal.tsx`

**Depends on**: T6

**Reuses**: Pattern from `ShoePickerModal.tsx` (modal structure, close button, backdrop)

**Requirement**: PZ-09, PZ-10, PZ-11 (recalibrate button)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] Modal component accepts `isOpen` + `onClose` props
- [ ] Shows command `python calibrate_vdot.py` in code block
- [ ] Brief explanation: "Execute este comando no terminal do servidor para recalibrar seu VDOT"
- [ ] Close button + backdrop click closes modal
- [ ] Build gate passes: `cd frontend && npm run build && npm run lint`

**Tests**: none
**Gate**: build

---

### T9: Add Card to Profile Page

**What**: Add "Zonas de Ritmo" card to `frontend/src/app/(app)/perfil/page.tsx` (after Equipamentos card), linking to `/pace-zones` with stopwatch icon.

**Where**: `frontend/src/app/(app)/perfil/page.tsx`

**Depends on**: T7

**Reuses**: Exact pattern from existing "Zonas de FC" and "Equipamentos" cards (lines 65-118); `Link`, SVG icon

**Requirement**: PZ-06, PZ-07, PZ-08 (profile card)

**Tools**:
- MCP: `filesystem`
- Skill: NONE

**Done when**:
- [ ] Third card added in `PanelSection` with index={3}
- [ ] Title: "Zonas de Ritmo", subtitle: "Seu VDOT e zonas de ritmo (Easy, Maratona, Limiar, Intervalado, Repetição) calculados pela calibração de Jack Daniels"
- [ ] Icon: stopwatch/clock SVG (distinct from heart and shoe)
- [ ] Link to `/pace-zones`
- [ ] Build gate passes: `cd frontend && npm run build && npm run lint`

**Tests**: none
**Gate**: build

---

## Phase Execution Map

Visual representation of task ordering. Phases run in sequence, and tasks within a phase run in order:

```mermaid
Phase 1:  T1 -> T2
          T1 -> T3
Phase 2:  T1 -> T4
          T2 -> T4
Phase 3:  T1 -> T5
          T2 -> T5
Phase 4:  T5 -> T6
          T6 -> T7
          T6 -> T8
          T7 -> T9
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent works one task at a time, in order.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Create VdotZoneConfig Model | 1 model in 1 file | ✅ Granular |
| T2: Migration + Seed in init_db | 1 function in 1 file | ✅ Granular |
| T3: Model Tests | 1 test file | ✅ Granular |
| T4: Update calibrate_vdot.py | 1 function + CLI integration | ✅ Granular |
| T5: API Endpoint | 1 endpoint in router | ✅ Granular |
| T6: Frontend API Types | Types + 1 function in api.ts | ✅ Granular |
| T7: PaceZonesPage | 1 page component | ✅ Granular |
| T8: RecalibrateModal | 1 component | ✅ Granular |
| T9: Profile Card | 1 card in existing page | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | None | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1 | T1 → T3 | ✅ Match |
| T4 | T1, T2 | T2 → T4 | ✅ Match |
| T5 | T1, T2 | T2 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T6 | T6 → T8 | ✅ Match |
| T9 | T7 | T7 → T9 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | SQLAlchemy Model | unit | unit | ✅ OK |
| T2 | Migration / Seed | integration | integration | ✅ OK |
| T3 | Model Tests (test file) | unit | unit | ✅ OK |
| T4 | Calibration Script | integration | integration | ✅ OK |
| T5 | API Endpoint | e2e | e2e | ✅ OK |
| T6 | Frontend API Layer | none | none | ✅ OK |
| T7 | Frontend Page | none | none | ✅ OK |
| T8 | Frontend Modal | none | none | ✅ OK |
| T9 | Frontend Card | none | none | ✅ OK |

---

**Total Tasks**: 9 | **Estimated batches**: 1 (fits in single ~7-task batch with T1-T3 packed, T4-T9 second batch) → Will offer sub-agents if user accepts.