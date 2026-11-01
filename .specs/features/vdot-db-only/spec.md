# Spec: VDOT Database as Single Source of Truth

**Feature:** Migrate all VDOT zone/calibration readers from JSON file to database
**Scope:** Large
**Date:** 2026-11-01

---

## Problem Statement

Currently there are two sources of truth for VDOT data:
1. **Database** (`VdotZoneConfig` table) - used by `/api/profile/pace-zones` GET/POST
2. **JSON file** (`data/vdot_zones.json`) - used by Performance panel, Home page, activities, tênis analysis, evaluation

This creates inconsistency risk and doesn't scale for multi-user. The database should be the single source of truth.

---

## User Stories

- **US-001:** As a developer, I want all VDOT readers to use the database so there's one source of truth
- **US-002:** As a developer, I want to remove the JSON file dependency to simplify deployment
- **US-003:** As a user, I want my VDOT zones to be consistent across all panels (Performance, Home, Workouts, Profile)

---

## Requirements

### REQ-001: Database-backed calibration loader
**EARS:** WHEN any code needs the current VDOT calibration THEN it SHALL call a new `load_calibration_from_db(db, user_id)` function that reads from `VdotZoneConfig` table instead of the JSON file.

### REQ-002: Database-backed zone config loader
**EARS:** WHEN any code needs zone boundaries for pace classification THEN it SHALL call a new `load_zone_config_from_db(db, user_id)` function that builds `ZoneConfig` from `VdotZoneConfig.zones` JSON column.

### REQ-003: Migrate Performance panel (potential)
**EARS:** The `/api/potential` endpoint SHALL use the database loader instead of `load_calibration(settings.vdot_zones_path)`.

### REQ-004: Migrate Home page predictions
**EARS:** The Home service SHALL use the database loader instead of `load_calibration(settings.vdot_zones_path)`.

### REQ-005: Migrate Activities (workouts-list)
**EARS:** The activities service/router SHALL use the database zone config loader instead of `load_zone_config(settings.vdot_zones_path)`.

### REQ-006: Migrate Tênis Analysis
**EARS:** The tênis analysis router SHALL use the database zone config loader.

### REQ-007: Migrate Evaluation payload
**EARS:** The evaluation payload SHALL read zones from database instead of directly opening the JSON file.

### REQ-008: Update calibrate_vdot.py
**EARS:** The calibration script SHALL continue to write to BOTH database and JSON (for backward compatibility during transition), but JSON write SHALL be last.

### REQ-009: Remove JSON file from repo
**EARS:** After all readers migrated, the `data/vdot_zones.json` file and `VDOT_ZONES_PATH` config SHALL be removed.

### REQ-010: Update tests
**EARS:** All tests that mock or seed the JSON file SHALL be updated to seed the database instead.

---

## Acceptance Criteria

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| AC-001 | GET /api/potential returns VDOT from database | 200 with current user's VDOT from VdotZoneConfig |
| AC-002 | Home page predictions use database VDOT | Digest shows predictions based on DB calibration |
| AC-003 | Workouts list classifies splits using DB zones | Split zone colors match user's calibrated zones |
| AC-004 | Tênis analysis uses DB zones | Analysis uses user's pace zones |
| AC-005 | Evaluation uses DB zones | AI evaluation uses user's zones |
| AC-006 | calibrate_vdot.py still works | Running script updates DB and JSON |
| AC-007 | No code references vdot_zones_path | Grep returns zero matches (except tests) |
| AC-008 | data/vdot_zones.json removed | File no longer exists |
| AC-009 | All existing tests pass | pytest passes without modification to test logic |

---

## Assumptions & Open Questions

| ID | Assumption / Question | Resolution |
|----|----------------------|------------|
| A-001 | All callers have access to `db: Session` and `user_id` | Confirmed - all are in authenticated endpoints |
| A-002 | Default user (id=1) has seeded config in DB | Confirmed - `engine.py` seeds from JSON on init |
| A-003 | ZoneConfig can be built from stored `zones` JSON column | Confirmed - same structure as file |
| A-004 | Performance panel needs full calibration (vdot, source, test_date, distance, time) | All stored in VdotZoneConfig |
| A-005 | Migration can be done incrementally per endpoint | Yes, each endpoint independently |

---

## Requirement Traceability

| Requirement | User Story | Acceptance Criteria |
|-------------|------------|---------------------|
| REQ-001 | US-001, US-002 | AC-001, AC-002 |
| REQ-002 | US-001, US-002 | AC-003, AC-004, AC-005 |
| REQ-003 | US-001, US-003 | AC-001 |
| REQ-004 | US-001, US-003 | AC-002 |
| REQ-005 | US-001, US-003 | AC-003 |
| REQ-006 | US-001, US-003 | AC-004 |
| REQ-007 | US-001, US-003 | AC-005 |
| REQ-008 | US-001 | AC-006 |
| REQ-009 | US-002 | AC-007, AC-008 |
| REQ-010 | US-001 | AC-009 |

---

## Out of Scope

- Multi-user VDOT isolation (already handled by user_id FK)
- Historical VDOT timeline (separate feature)
- Garmin auto-sync of test results
- Frontend changes (reads from API, unchanged)

---

## Migration Plan (Phases)

### Phase 1: Core Loaders (Foundation)
- Add `load_calibration_from_db(db, user_id)` in `app/vdot/calibration.py`
- Add `load_zone_config_from_db(db, user_id)` in `app/vdot/zones.py`
- Both raise `ZoneConfigError` if no config found (consistent with file loaders)

### Phase 2: Migrate Consumers (One by One)
1. `app/potential/router.py` - Performance panel
2. `app/home/service.py` - Home predictions
3. `app/activities/service.py` + `app/activities/router.py` - Workouts list
4. `app/tenis_analysis/router.py` - Tênis analysis
5. `app/evaluation/payload.py` - AI evaluation

### Phase 3: Update Calibration Script
- Keep dual write (DB first, JSON last for backward compat)
- Add comment about JSON being deprecated

### Phase 4: Cleanup
- Remove `vdot_zones_path` from config
- Remove `data/vdot_zones.json`
- Remove file-based `load_calibration` and `load_zone_config` (or mark deprecated)
- Update tests to seed DB instead of mocking file

---

## Technical Details

### New Functions

```python
# app/vdot/calibration.py
def load_calibration_from_db(db: Session, user_id: int) -> Calibration:
    """Load current calibration from VdotZoneConfig table."""
    config = db.query(VdotZoneConfig).filter(
        VdotZoneConfig.user_id == user_id
    ).order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc()).first()
    if not config:
        raise ZoneConfigError("zonas VDOT não configuradas")
    return Calibration(
        vdot=config.vdot,
        source=config.source,
        test_date=config.test_date,
        distance_m=config.distance_m,
        time_s=config.time_s,
    )

# app/vdot/zones.py
def load_zone_config_from_db(db: Session, user_id: int) -> ZoneConfig:
    """Load zone config from VdotZoneConfig table."""
    config = db.query(VdotZoneConfig).filter(
        VdotZoneConfig.user_id == user_id
    ).order_by(VdotZoneConfig.valid_from.desc(), VdotZoneConfig.id.desc()).first()
    if not config:
        raise ZoneConfigError("zonas VDOT não configuradas")
    return ZoneConfig(config.zones)
```