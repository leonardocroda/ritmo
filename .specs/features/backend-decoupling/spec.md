# Spec: Backend Decoupling from Frontend Screens

## Feature ID
BACKEND-DECOUPLE

## Title
Decouple backend API from frontend screen names — introduce domain-driven API layer

## Problem Statement
The current backend is effectively a BFF (Backend for Frontend) with **zero domain layer**. Every endpoint mirrors a frontend screen:
- `/api/home/today` → Home screen
- `/api/health/summary` → Health screen
- `/api/potential` → Performance screen
- `/api/activities` + detail → Treinos list + detail screens
- `/api/profile/hr-zones`, `/api/profile/pace-zones` → Profile/Zonas screens
- `/api/shoes`, `/api/tenis/...` → Equipamentos screens

The frontend `api.ts` **mirrors every backend contract 1:1** (1086 lines of TypeScript types). Any screen rename, field addition, or structural change requires coordinated changes in **both** frontend and backend. This is unnecessary coupling that prevents:
- Independent evolution of frontend screens
- Multiple frontend clients (mobile, third-party)
- Proper domain modeling and reuse
- Testing domain logic in isolation

## Scope
**Large** — Affects entire API surface (~15 routers, ~40 endpoints), requires new domain layer, migration strategy, and contract versioning.

## Assumptions & Open Questions

| ID | Assumption | Chosen Default | Rationale |
|----|------------|----------------|-----------|
| A1 | Current backend uses FastAPI with Pydantic models inline in routers | Yes | Verified in codebase |
| A2 | Frontend consumes API via `frontend/src/lib/api.ts` (single typed client) | Yes | Verified in codebase |
| A3 | Database models (`app/db/models.py`) represent the domain entities | Yes | Verified in codebase |
| A4 | Business logic lives in `service.py` files per domain | Yes | Verified in codebase |
| A5 | No external consumers of the API yet (only the Next.js frontend) | Yes | Confirmed by team |
| A6 | Authentication/session management (`auth/`) stays unchanged | Yes | Out of scope |
| A7 | Garmin sync (`garmin/`) stays unchanged — it's an integration layer | Yes | Out of scope |
| A8 | Migration must be zero-downtime for the frontend (strangler fig pattern) | Yes | Required for production |

Open questions: none

## User Stories

| ID | Story |
|----|-------|
| US-01 | As a frontend developer, I want to rename a screen without touching backend code, so that UI changes are independent |
| US-02 | As a backend developer, I want to add a new domain endpoint (e.g., `/api/v1/activities/{id}/laps`) without creating a screen for it |
| US-03 | As a mobile app developer (future), I want to consume domain APIs directly to build custom screens |
| US-04 | As a QA engineer, I want contract tests that fail when domain/screen APIs drift from spec |

## Requirements

### DEC-01: Domain Layer Extraction
The backend SHALL expose a domain-driven API organized by business capability, not by frontend screen.

### DEC-02: Domain Module Structure
Each domain module SHALL have: `schemas.py` (Pydantic response models), `service.py` (business logic), `repository.py` (data access), `router.py` (thin HTTP adapter).

### DEC-03: Domain RESTful Naming
Domain routers SHALL use RESTful resource naming: `/api/v1/activities`, `/api/v1/activities/{id}`, `/api/v1/training-load/pmc`, `/api/v1/health/sleep`, etc.

### DEC-04: Domain Services Screen-Agnostic
Domain services SHALL be screen-agnostic — return normalized data, not pre-composed screen payloads.

### DEC-05: Screen Composition Layer
The backend SHALL provide a thin composition layer for frontend screens that aggregates domain data.

### DEC-06: Screen Router Structure
Create `app/screens/` package with routers per screen: `home_router.py`, `health_router.py`, `performance_router.py`, `activities_router.py`, `profile_router.py`, `shoes_router.py`.

### DEC-07: Screen Composition Only
Screen routers SHALL compose calls to domain services, not duplicate logic.

### DEC-08: Screen Payload Isolation
Screen routers SHALL be the **only** place where screen-specific payload shapes exist.

### DEC-09: Screen API Versioning
Screen endpoints SHALL be versioned under `/api/v1/screens/` to distinguish from domain API.

### DEC-10: Old Endpoints Functional During Migration
Old endpoints (`/api/home/today`, `/api/health/summary`, etc.) SHALL remain functional during transition.

### DEC-11: Old Endpoints Delegate to Screen Layer
Old endpoints SHALL delegate to new screen composition layer (no logic duplication).

### DEC-12: Frontend Migrates Screen-by-Screen
Frontend SHALL be migrated screen-by-screen to new `/api/v1/screens/...` endpoints.

### DEC-13: Old Endpoints Deprecated After Migration
After full frontend migration, old endpoints SHALL be deprecated with 410 responses.

### DEC-14: Domain API Versioned Independently
Domain API (`/api/v1/...`) SHALL be stable and versioned independently from screen API.

### DEC-15: TypeScript Generation from OpenAPI
Generate TypeScript types from OpenAPI schema (Pydantic → OpenAPI → TypeScript).

### DEC-16: Split Frontend API Client
Split `api.ts` into: `domain-api.ts` (domain resources) + `screen-api.ts` (screen compositions).

### DEC-17: Screens Use Screen API
Screens SHALL use `screen-api.ts`; components needing granular data SHALL use `domain-api.ts`.

### DEC-18: Remove Manual Type Mirroring
Remove manual type mirroring — types come from codegen.

### DEC-19: Domain API Contract Tests
Domain API contract tests (snapshot OpenAPI schema).

### DEC-20: Screen API Contract Tests
Screen API contract tests (snapshot response shapes per screen).

### DEC-21: Frontend Type Generation CI
Frontend type generation CI step validates types compile.

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | No breaking changes to frontend during migration (strangler fig) |
| NFR-02 | Domain services unit-testable without HTTP layer |
| NFR-03 | OpenAPI schema auto-generated from Pydantic models |
| NFR-04 | Response times ≤ current (composition adds <10ms) |
| NFR-05 | Clear separation: domain logic ≠ screen composition |

## Acceptance Criteria (EARS)

### Domain Layer
- **AC-01**: WHEN a new domain endpoint is added THEN it follows `/api/v1/{domain}/{resource}` pattern AND has no screen-specific logic
- **AC-02**: WHEN domain service is unit tested THEN it requires no HTTP mocking, only repository mocking
- **AC-03**: WHEN OpenAPI schema is generated THEN domain endpoints are grouped by tag (domain name)

### Screen Composition
- **AC-04**: WHEN a screen endpoint is called THEN it composes 2+ domain service calls AND returns screen-specific shape
- **AC-05**: WHEN screen payload changes THEN only screen router + schema change, no domain service changes
- **AC-06**: WHEN old endpoint `/api/home/today` is called THEN it returns identical payload to new `/api/v1/screens/home/today`

### Migration
- **AC-07**: WHEN frontend migrates Home screen THEN it uses `/api/v1/screens/home/today` AND old endpoint still works
- **AC-08**: WHEN all screens migrated THEN old endpoints return 410 Gone with migration guide link

### Frontend
- **AC-09**: WHEN `npm run generate-api` runs THEN TypeScript types match backend OpenAPI schema exactly
- **AC-10**: WHEN a domain field is renamed THEN only backend domain schema + frontend regeneration needed (no manual `api.ts` edits)

## Requirement Traceability

| Requirement | Acceptance Criteria | Tests |
|-------------|---------------------|-------|
| DEC-01 | AC-01, AC-02, AC-03 | Unit tests for domain services; OpenAPI snapshot test |
| DEC-02 | AC-01, AC-02 | Unit tests per domain module |
| DEC-03 | AC-01, AC-03 | Router tests + OpenAPI tag verification |
| DEC-04 | AC-02 | Service unit tests with repository mocks |
| DEC-05 | AC-04, AC-06 | Screen router integration tests |
| DEC-06 | AC-04 | Screen router tests verify domain service calls |
| DEC-07 | AC-05 | Screen schema tests |
| DEC-08 | AC-03, AC-06 | Route prefix verification test |
| DEC-09 | AC-06, AC-07 | Old endpoint integration tests |
| DEC-10 | AC-06 | Old endpoint tests verify delegation |
| DEC-11 | AC-07 | Frontend migration checklist |
| DEC-12 | AC-08 | Deprecation endpoint tests |
| DEC-13 | AC-03 | OpenAPI versioning test |
| DEC-14 | AC-09 | CI type generation step |
| DEC-15 | AC-10 | Generated types structure test |
| DEC-16 | AC-10 | Frontend build with generated types |
| DEC-17 | AC-10 | No manual types in `api.ts` verification |
| DEC-18 | AC-03 | OpenAPI snapshot test in CI |
| DEC-19 | AC-05 | Screen response snapshot tests |
| DEC-20 | AC-09 | TypeScript compilation in CI |

## Out of Scope
- GraphQL adoption (REST is fine for now)
- Microservices split (monolith stays)
- Authentication/authorization changes
- Garmin/Strava integration changes
- Database schema changes (only API layer)