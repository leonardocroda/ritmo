# Spec: VDOT Recalibration via API

**Feature:** VDOT Recalibration via API (POST /api/profile/pace-zones/recalibrate)
**Scope:** Medium
**Date:** 2026-11-01

---

## Problem Statement

Currently, the frontend shows a modal telling users to run `python calibrate_vdot.py` in the server terminal to recalibrate their VDOT zones. This is poor UX — users should be able to recalibrate directly from the UI by entering distance and time of their latest test.

---

## User Stories

- **US-001:** As a runner, I want to recalibrate my VDOT zones from the web UI by entering my latest test distance and time, so I don't need SSH access to the server.
- **US-002:** As a runner, I want to select from standard race distances (5K, 10K, Half, Marathon) or enter a custom distance, so I can quickly input my test.
- **US-003:** As a runner, I want to see the new zones immediately after recalibration, so I can verify they look correct.

---

## Requirements

### REQ-001: POST endpoint to recalculate VDOT zones
**EARS:** WHEN a logged-in user sends a POST request to `/api/profile/pace-zones/recalibrate` with distance (km) and time (HH:MM:SS) THEN the system SHALL calculate VDOT using Jack Daniels formula, generate the 5 pace zones, compute race equivalencies, save to database (upsert), and return the updated PaceZonesOut.

### REQ-002: Input validation
**EARS:** WHEN the request body has invalid distance (≤0) or invalid time format THEN the system SHALL return 422 with field-specific error message.

### REQ-003: Frontend modal uses API
**EARS:** WHEN the user clicks "Recalibrar VDOT" in the pace-zones page THEN the modal SHALL show a form with distance dropdown (standard distances + custom) and time input, and on submit call the API and refresh the page data.

### REQ-004: Reuse existing calculation logic
**EARS:** The endpoint SHALL reuse `calculate_vdot`, `pace_for_fraction`, `equivalent_time` from `app.vdot.daniels` and zone generation logic from `calibrate_vdot.py` (function `gerar_zonas`).

### REQ-005: Database upsert
**EARS:** WHEN recalibration succeeds THEN the system SHALL upsert `VdotZoneConfig` for the current user with `valid_from = test_date` (default today).

---

## Acceptance Criteria

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| AC-001 | POST with distance_km=10, time_str="00:40:12" | Returns 200 with PaceZonesOut containing vdot≈50.2, 5 zones, equivalencies |
| AC-002 | POST with distance_km=0 | Returns 422 "distance_km: deve ser maior que 0" |
| AC-003 | POST with time_str="invalid" | Returns 422 "time_str: formato inválido, use HH:MM:SS" |
| AC-004 | Frontend form submit | Calls API, on success closes modal and refreshes pace-zones data |
| AC-005 | Database row created/updated | VdotZoneConfig row exists for user with new vdot, zones, equivalencias |

---

## Assumptions & Open Questions

| ID | Assumption / Question | Resolution |
|----|----------------------|------------|
| A-001 | User is authenticated via session (existing `require_session` dep) | Confirmed - existing pattern |
| A-002 | Standard test distances: 1500m, 3K, 5K, 10K, Half Marathon (21.0975km), Marathon (42.195km), plus custom | Confirmed - matches calibrate_vdot.py |
| A-003 | Time input accepts HH:MM:SS or MM:SS format | Confirmed - matches calibrate_vdot.py |
| A-004 | Test date defaults to today if not provided | Confirmed |
| A-005 | Frontend uses existing `getPaceZones()` to refresh after recalibration | Confirmed |

Open questions: None

---

## Requirement Traceability

| Requirement | User Story | Acceptance Criteria |
|-------------|------------|---------------------|
| REQ-001 | US-001, US-002 | AC-001, AC-005 |
| REQ-002 | US-001 | AC-002, AC-003 |
| REQ-003 | US-001, US-002, US-003 | AC-004 |
| REQ-004 | US-001 | AC-001, AC-005 |
| REQ-005 | US-001 | AC-005 |

---

## Out of Scope

- Historical VDOT timeline (separate feature)
- Garmin auto-sync of test results
- Multiple user support beyond current session user
- Editing existing calibration history