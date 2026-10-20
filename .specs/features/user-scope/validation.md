# user-scope Validation

**Date**: 2026-10-20
**Spec**: `.specs/features/user-scope/spec.md`
**Diff range**: `e70fb94..233e51f` (8 commits: 67bac81, 97f0368, f4a428b, 1d0ccff, 7f825b5, f44d75c, 736706e, 233e51f)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | `session_client` + `login_client` fixtures in `backend/tests/conftest.py:60-95`; no override added (override was still present at T1 per plan, removed in T7) |
| T2 | ✅ Done | activities service+router on session `user_id` (`backend/app/activities/service.py:88,158-165,188`; `backend/app/activities/router.py:110-118,128-133`); tests migrated to real sessions |
| T3 | ✅ Done | health service+router (`backend/app/health/service.py:58,121,129,232`; `backend/app/health/router.py:174,183`) |
| T4 | ✅ Done | potential service+router (`backend/app/potential/service.py:30,104,142,148`; `backend/app/potential/router.py:112,130`) |
| T5 | ✅ Done | garmin: `create_job(db, user_id)` required (`backend/app/garmin/service.py:112`), router passes `user.id` (`backend/app/garmin/router.py:70,95,111`) |
| T6 | ✅ Done | evaluation service+payload+router (`backend/app/evaluation/service.py:84,102,204,218`; `backend/app/evaluation/payload.py:179,213,230`; `backend/app/evaluation/router.py:51,77`) |
| T7 | ✅ Done | global override removed — only defensive `pop` remains (`backend/tests/conftest.py:71`); full suite green without it |
| T8 | ✅ Done | `backend/tests/test_user_isolation.py` — 7 A×B tests across all data endpoints, all green |

All 8 tasks marked complete in `tasks.md`; commit messages match the plan 1:1.

---

## Spec-Anchored Acceptance Criteria

### P1: Leituras de dados por usuário da sessão

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| USR-01: WHEN `GET /api/activities` com sessão válida de X THEN retorna apenas atividades `user_id = X` | Only X's activities in items AND total | `backend/tests/test_activities_api.py:160` - `assert body["total"] == 1` (X has 1, alien Y has 1; line 161 `len(body["items"]) == 1`); impl `backend/app/activities/service.py:88` `filters = [Activity.user_id == user_id]`, router passes `user.id` (`backend/app/activities/router.py:118`); also `backend/tests/test_user_isolation.py:110-111` | ✅ PASS |
| USR-02: WHEN `GET /api/activities/{id}` sessão X, atividade `user_id = Y ≠ X` THEN 404 "atividade não encontrada" | 404 + exact message, no data leak | `backend/tests/test_activities_api.py:184-185` - `assert response.status_code == 404` + `assert response.json()["detail"] == "atividade não encontrada"`; impl `backend/app/activities/service.py:188` (`Activity.user_id == user_id` in detail select) → `backend/app/activities/router.py:135`; also `backend/tests/test_user_isolation.py:114-116` | ✅ PASS |
| USR-03: WHEN `GET /api/health/summary` sessão X THEN todos os blocos (sono, HRV, RHR, estresse, dose-response, lifestyle) de linhas `user_id = X` | Every block built only from X's rows | `backend/tests/test_health_api.py:383-415` - `test_other_users_rows_never_leak_into_panel`: sleep dates `== [13,14,15/10]` (383-385), `below_floor == {"nights": 2, "pct": 66.7}` (386), dose_response exact (387-391), alien HRV day `value is None/avg7 None` (398-401), `rhr is None` (408), `stress is None` (409), lifestyle zeros (411-415); impl `backend/app/health/service.py:58` (`model.user_id == user_id`), `:121,129` (HRV), `:232` (activities); HTTP-level `backend/tests/test_user_isolation.py:138-145` | ✅ PASS |
| USR-04: WHEN `GET /api/potential` sessão X THEN VDOT, predições, PMC e decaimento de linhas `user_id = X` | Predictions/PMC/decay/timeline from X's rows only | `backend/tests/test_potential_api.py:151` - `assert body["predictions"]["5K"]["garmin_s"] == 1165.0` (alien 999 never), `:154-155` alien PR date not in timeline, `:157-158` `decay_events == {"5K"}`, `:160` `assert body["pmc"] is None`; impl `backend/app/potential/service.py:30,104,142,148`; also `backend/tests/test_user_isolation.py:160-168` (exact per-user PMC points both sides) | ✅ PASS |
| USR-05: WHEN o endpoint de sync estado (`sync_state` por tipo de dado) é consultado com sessão X THEN devolve apenas o estado de X | Only X's sync state | No HTTP endpoint exposes per-type `sync_state` (routes: `backend/app/garmin/router.py:61,87,102`). Nearest public surface `GET /api/sync/jobs/latest` is user-scoped (`backend/app/garmin/router.py:95` `SyncJob.user_id == user.id`) — `backend/tests/test_user_isolation.py:218-224` - latest job belongs to session user + `assert client.get(f"/api/sync/jobs/{alien_job_id}").status_code == 404`; internal per-type state is user-scoped at the seam (`backend/app/garmin/upserts.py:150-154` `SyncState.user_id == user_id`), exercised `backend/tests/test_garmin_service.py:170-171` - `assert get_sync_state(s, job.user_id, data_type) == TODAY` | ⚠️ Spec-precision gap |
| USR-06: WHILE endpoint de leitura chamado com sessão válida THEN usa o `user_id` do usuário autenticado, nunca `DEFAULT_USER_ID` | Session user's id in every read query | Grep over `backend/app`: `DEFAULT_USER_ID` remains only in column defaults (`backend/app/db/models.py:73-343`, kept by explicit spec assumption) + user-1 seed (`backend/app/db/engine.py:65-72`, allowed by Success Criteria) + pre-existing CLI `backend/app/auth/set_password.py` — zero in domain queries. All 5 routers pass `user.id` (`backend/app/activities/router.py:118,133`; `backend/app/health/router.py:183`; `backend/app/potential/router.py:130`; `backend/app/garmin/router.py:70`; `backend/app/evaluation/router.py:51,77`). Empirical: every A×B test runs with session users id>1 (`backend/tests/conftest.py:48`) and asserts data flows only to/from session user — `backend/tests/test_user_isolation.py:190` `assert job.user_id == user_id`, `:247` `assert row.user_id == user_id` | ✅ PASS |
| USR-07: IF leitura sem sessão válida THEN 401 JSON sem nenhum dado | 401 `{"detail": "não autenticado"}` on every data endpoint | `backend/tests/test_user_isolation.py:285-286` - `assert response.status_code == 401` + `assert response.json() == {"detail": "não autenticado"}` across all 6 GET endpoints (`:276-283`), POST sync `:287-288` and POST evaluate `:289-290` also 401; impl `backend/app/auth/deps.py:40-43` applied via `backend/app/main.py:58-62` | ✅ PASS |

### P1: Isolamento A×B

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| USR-08: WHEN X e Y têm atividades/sono/HRV/carga/avaliações THEN `GET /api/activities` de X retorna só X e de Y só Y | Each session lists only its owner's activities | `backend/tests/test_user_isolation.py:109-111` - `assert body_x["total"] == 1` + ids `== [own_id]`; cookie swapped to Y: `:120-122` - `assert body_y["total"] == 1` + ids `== [alien_id]`; also `backend/tests/test_activities_api.py:159-161` | ✅ PASS |
| USR-09: WHEN X tem atividade A com avaliação vinculada THEN `GET /api/activities/{A}` na sessão de Y não lista a avaliação de X | X's evaluation never listed to Y | `backend/tests/test_user_isolation.py:123` - `assert client.get(f"/api/activities/{own_id}").status_code == 404` (Y's session on X's activity → the resource carrying the evaluation is invisible); defense-in-depth: evaluations user-filtered in the detail — impl `backend/app/activities/service.py:253` `list_evaluations(db, activity.id, user_id)` + `backend/app/evaluation/service.py:218` `Evaluation.user_id == user_id`; exercised `backend/tests/test_user_isolation.py:259-260` (`detail_y["evaluations"] == []`) and polling 404 `:262-263` | ✅ PASS (note: the `evaluations == []` assertion at `:260` is on Y's own activity which never had an evaluation — the discriminating guarantee for the AC's outcome is the tested 404 on X's activity plus the user filter in code) |
| USR-10: WHEN `POST /api/sync` na sessão de X THEN cria `SyncJob` com `user_id = X` e grava atividades/sono/HRV/etc. com `user_id = X` | Job + all synced rows owned by X | `backend/tests/test_user_isolation.py:190` - `assert job.user_id == user_id`; `:194-195` X sees the 12 synced activities; `:198-199` Y sees `total == 0`; `:200` Y's `jobs/latest` is `{"job": None}`; impl `backend/app/garmin/router.py:70` `create_job(db, user.id)`, `backend/app/garmin/service.py:346` `user_id = job.user_id` drives all phases; also `backend/tests/test_sync_api.py:71` | ✅ PASS |
| USR-11: WHEN `POST /api/evaluation` na sessão X para atividade A de X THEN grava `Evaluation` com `user_id = X`; Y não avalia atividade de X | Evaluation owned by X; alien activity → rejected | `backend/tests/test_user_isolation.py:243` - `assert response.status_code == 201`; `:247` - `assert row.user_id == user_id`; `:250-255` alien activity → 404 and `len(...Evaluation...) == 1` (no new row); also `backend/tests/test_evaluation_api.py:135` (`assert row.user_id == user_id`) and `:226-230` | ✅ PASS |
| USR-12: IF usuário Y tenta acessar qualquer recurso de X THEN 404 ou 401, nunca os dados | 404/401 for every alien resource | activity: `backend/tests/test_activities_api.py:184-185`; evaluation status: `backend/tests/test_evaluation_api.py:261-262` (`assert response.status_code == 404` + `detail == "avaliação não encontrada"`); sync job: `backend/tests/test_sync_api.py:123-124` (`assert response.status_code == 404` + `"job não encontrado"`); latest job: `backend/tests/test_user_isolation.py:218-222` (latest is X's, not Y's); no session: `backend/tests/test_user_isolation.py:285-290` (401) | ✅ PASS |

### P1: Writes (sync e avaliação) por usuário da sessão

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| USR-13: WHEN `POST /api/sync` sessão X THEN job `user_id = X` e ao concluir grava cada atividade/sono/HRV/RHR/stress/body_battery/record com `user_id = X` | All written rows owned by X | `backend/tests/test_sync_api.py:71` - `assert job.user_id == user_id  # USR-13` (job done, 12 activities, stats `:73-82`); `backend/tests/test_user_isolation.py:190-199` (X's data only visible to X, Y empty); full happy-path counters `backend/tests/test_garmin_service.py:117-136` + per-user sync_state `:170-171`; impl `backend/app/garmin/service.py:112-127` (user_id obrigatório), upserts carry user_id (`backend/app/garmin/upserts.py:53,92,108,128`) | ✅ PASS |
| USR-14: WHEN sync re-puxa últimos 3 dias + atividades novas para X THEN upsert por chave natural `(user_id, data)`/`(user_id, evento)`/`(activity_id, idx)` isolado por usuário | Idempotent upserts, natural keys include user_id, no duplicates | `backend/tests/test_garmin_service.py:186` - `assert _table_counts(s) == counts_after_first` (2× sync same user, zero duplicates); `:212` re-pull window `[(REPULL_START, TODAY)]` (last_date − 3d); `:191-193` second sync only updates; predictions no duplicates `:471-474`; keys: `backend/app/garmin/upserts.py:48-50` (user_id, garmin_id), `:89` (user_id, date), `:103-105`/`:123-125` (user_id, event), `:70-72` (activity_id, idx) + `:80` user_id from parent; unique constraints `backend/app/db/models.py:119,136,147,157,167,179,308,326,340` all include user_id | ✅ PASS (note: a both-users-sync-overlapping-natural-keys scenario is not directly exercised; isolation of writes is proven by USR-10/13 A×B — X's sync leaves Y's tables empty) |
| USR-15: WHEN `POST /api/evaluation` sessão X THEN grava `Evaluation.user_id = X` e vincula apenas a atividades `user_id = X` | Row owned by X, linked to X's activity only | `backend/tests/test_evaluation_api.py:135` - `assert row.user_id == user_id  # USR-15: linha do dono da sessão`; `backend/tests/test_user_isolation.py:247`; linking: `backend/tests/test_evaluation_api.py:226-230` (alien activity → 404, `db.execute(select(Evaluation)).scalars().all() == []`); impl `backend/app/evaluation/service.py:84` (activity select by user_id), `:102` (`Evaluation(user_id=user_id, ...)`) | ✅ PASS |
| USR-16: IF usuário da sessão não tem a atividade A THEN criar avaliação para A → 404 | 404, no NIM call, no row | `backend/tests/test_evaluation_api.py:226-230` - `assert response.status_code == 404` + detail message + `assert calls == []` + no Evaluation row; `backend/tests/test_user_isolation.py:250-255`; impl `backend/app/evaluation/service.py:82-88` → None, `backend/app/evaluation/router.py:62-63` → 404 | ✅ PASS |

### P2: Testes de sessão real e isolamento

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| USR-17: WHEN teste de API de dados roda sem configurar sessão THEN 401 (conftest SHALL não injetar usuário 1) | No auto-injected user; 401 without session | No `dependency_overrides[require_session] = ...` anywhere in the suite (grep: only defensive pops at `backend/tests/conftest.py:71`, `backend/tests/test_activities_api.py:139`, `backend/tests/test_auth_api.py:47`); `backend/tests/test_user_isolation.py:285-286` - `assert response.status_code == 401` + `{"detail": "não autenticado"}`; also `backend/tests/test_activities_api.py:141-143`; full suite (427) green proves no test depends on user-1 injection | ✅ PASS |
| USR-18: WHEN teste cria sessões X e Y com dados separados THEN teste de isolamento A×B passa | X não lê Y, Y não lê X, all endpoints | `backend/tests/test_user_isolation.py` — 7/7 green in the full suite: list/detail `:98-124`, health `:127-145`, potential `:148-168`, sync data `:176-200`, latest job `:203-224`, evaluation `:227-263`, 401 `:271-290` | ✅ PASS |
| USR-19: WHILE testes de auth existentes rodam THEN exercem a proteção real (401/cookie/sliding) sem o override global | Auth tests on real protection, suite green without override | `backend/tests/test_auth_api.py:41-49` - `client` fixture `app.dependency_overrides.pop(require_session, None)` + real-cookie TestClient (register/login/sliding/401 suite green in the 427 run); liveness stays public: `backend/tests/test_auth_api.py:286` - `assert client.get("/api/health").status_code == 200  # público` | ✅ PASS |

**Status**: ⚠️ Spec-precision gaps flagged — 18/19 ACs matched the spec-defined outcome with `file:line` evidence; USR-05 flags a wording imprecision (see below), not a missing protection.

**USR-05 detail (honest flag, non-blocking):** the spec names "o endpoint de sync estado (`sync_state` por tipo de dado)" — no such HTTP endpoint exists in the API (before or after this feature; the sync surface is `POST /api/sync`, `GET /api/sync/jobs/latest`, `GET /api/sync/jobs/{job_id}` — `backend/app/garmin/router.py:61,87,102`). Per-type `sync_state` is internal (incremental windows) with no HTTP surface, so it cannot leak; it is user-scoped at its only reader (`backend/app/garmin/upserts.py:150-154`). The public state endpoint the UI polls (`/api/sync/jobs/latest`) is user-scoped (`backend/app/garmin/router.py:95`) and A×B-tested (`backend/tests/test_user_isolation.py:203-224`, whose docstring maps USR-05). The requirement's substance — sync state is per-user and never leaks — is enforced and tested; the AC's literal wording should be amended by the orchestrator to cite the real surfaces.

---

## Discrimination Sensor

Method: file-backup fallback (validate.md §5 allows it; safer than a fresh worktree on Windows — a worktree would need its own `uv sync`). Baseline `git status --porcelain` = clean (recorded before sensor). For each mutation: file copied to `%TEMP%\opencode\user-scope-sensor\<name>.bak`, edit applied to the real file, targeted test file run in full (no `-k`), file restored from backup, porcelain re-checked. `git stash` was NOT used at any point.

| Mutation | File:line | Description | Killed? |
| -------- | --------- | ----------- | ------- |
| M1 | `backend/app/activities/service.py:88` | `filters = [Activity.user_id == user_id]` → `filters = [Activity.user_id == 1]` (hardcode user 1) | ✅ Killed — `uv run pytest tests/test_activities_api.py`: **8 failed**, 19 passed. Target `test_list_returns_only_own_user_activities` failed at `backend/tests/test_activities_api.py:160` (`assert 0 == 1`); 7 more list tests failed (hardcoded user 1 sees an empty dataset) |
| M2 | `backend/app/garmin/router.py:111` | `if job is None or job.user_id != user.id:` → `if job is None:` (remove ownership check) | ✅ Killed — `uv run pytest tests/test_sync_api.py`: **1 failed**, 8 passed. Target `test_get_job_404_for_other_users_job` failed at `backend/tests/test_sync_api.py:123` (`assert 200 == 404` — the alien job would have leaked with full stats) |
| M3 | `backend/app/evaluation/service.py:101-102` | `evaluation = Evaluation(user_id=user_id,` → `evaluation = Evaluation(` (drop user_id — column default 1 applies) | ✅ Killed — `uv run pytest tests/test_evaluation_api.py tests/test_user_isolation.py`: **3 failed**, 17 passed. `test_post_201_pending_e_worker_conclui` at `backend/tests/test_evaluation_api.py:135` (`assert 1 == 2` on `row.user_id == user_id`); `test_evaluation_scoped_to_session_user` at `backend/tests/test_user_isolation.py:247` (`assert 1 == 2`); bonus: `test_get_status_do_polling` at `backend/tests/test_evaluation_api.py:188` (session user can no longer poll the mis-owned evaluation → 404) |

**Sensor depth**: lightweight (3 mutations — data-integrity-adjacent but not payment/auth P0, per tiering table)
**Result**: 3/3 killed - PASS ✅

**Isolation verification**: `git status --porcelain` returned to the clean baseline after each restore (checked after M1, M2, M3 and after temp-dir cleanup). The real tree is byte-identical to `233e51f`. No mutant survives; no fix tasks required from the sensor.

---

## Interactive UAT Results (if performed)

Not performed — `user-scope` is purely backend (spec Out of Scope: "Mudança no frontend… `user-scope` é puramente backend"). Per validate.md §7, automated checks are sufficient for backend-only work.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ — diff strictly swaps `DEFAULT_USER_ID` for the session `user_id` and adds two test fixtures; no new abstractions (`session_client` reuses existing `create_session`/`login`) |
| Surgical changes | ✅ — only the 12 mapped source files + 9 test files + README status note; nothing else touched |
| No scope creep | ✅ — README diff is docs-only (interim note replaced by user-scope status); no frontend changes; zonas still read from `vdot_zones.json` (`backend/app/evaluation/payload.py:199`, untouched — reserved for `zones-db`); no new endpoints |
| No abstractions for single-use code / no unnecessary flexibility | ✅ — `user_id` threading is positional parameters, matching the existing service signatures |
| Matches patterns | ✅ — all 5 routers use the same `user: User = Depends(require_session)` → `user.id` pattern; PT-BR error messages and inline output models unchanged |
| Spec-anchored outcome check (asserted values match spec) | ✅ — 18/19 exact (404 messages, `user_id` ownership, per-user payloads asserted literally); 1 wording imprecision flagged (USR-05) |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ — services exercised directly (`test_health_api.py`, `test_potential_api.py`, `test_garmin_service.py`, `test_evaluation_service.py`, `test_evaluation_payload.py`) and every modified route has happy + 401 + 404-alien + domain errors (409/422/500/503) |
| Every test maps to a spec requirement - no unclaimed tests | ✅ — 15 new tests map to USR-01..18; migrated tests keep mapping to their original features' ACs (TRN/HLT/POT/SYNC/EVAL); the 3 "never imports Garmin" tests map to those features' Success Criteria (pre-existing, kept intact) |
| Documented guidelines followed: `README.md` §Testes ("suite roda no Postgres do compose, nada em SQLite") | ✅ — suite ran on compose Postgres (`ritmo_test`, forced at `backend/tests/conftest.py:10-16`, fail-fast via `ensure_postgres_available`); nothing in SQLite |

Spot-check of the A×B story (`backend/tests/test_user_isolation.py:227-263`): non-shallow — it drives the full HTTP path with two real cookie sessions, asserts the persisted `Evaluation.user_id` straight from the DB (`:247`), proves the alien POST creates no row (`:255`), and verifies the leak paths (alien detail `evaluations == []`, alien polling 404 `:262-263`). The cookie-swap pattern (one TestClient, two devices, same bank) is a faithful simulation of the threat model.

Minor observations (cosmetic, non-blocking, no fix task required):
1. Stale docstring `backend/tests/test_activities_api.py:12-14` — still says evaluations are "semeadas SEM `user_id` explícito (default 1) … interim DEFAULT_USER_ID até a T6"; T6 landed and `_seed_evaluation` now passes `user_id` explicitly (`backend/tests/test_activities_api.py:657-674`).
2. Stale docstring `backend/tests/test_auth_api.py:3-4` — still says the fixture "limpa o override do conftest"; the conftest override no longer exists, the pop at `:47` is now defensive (kept deliberately by `session_client` too, `backend/tests/conftest.py:71`).

---

## Edge Cases

- [x] `GET /api/activities` com sessão válida mas sem atividades → lista vazia com `total = 0`: Handled — `backend/tests/test_activities_api.py:217-219` - `assert response.json() == {"items": [], "total": 0, "limit": 30, "offset": 0}` (Y's empty view also asserted at `backend/tests/test_user_isolation.py:198-199`)
- [x] Sync re-executado para o mesmo usuário → sem duplicatas (upsert por chave natural incluindo `user_id`): Handled — `backend/tests/test_garmin_service.py:174-194` (2× sync, identical table counts); unique constraints include user_id (`backend/app/db/models.py:119,136,147,157,167,179,308,326,340`)
- [x] Duas sessões simultâneas do mesmo usuário disparam sync → lock de um job ativo por usuário: Handled — 409 with the active job's state: `backend/tests/test_sync_api.py:95-100` (`assert response.status_code == 409`, detail id/status/started_at); `JobConflictError` at `backend/tests/test_garmin_service.py:104-105`; enforced by the partial unique index `backend/app/db/models.py:284-291` (`uq_syncjobs_user_active` on `user_id` WHERE status IN ('pending','running')) — no check-then-insert race window
- [x] `user_id` inválido (não existe em `users`) → FK impede o insert: Handled by the DB — every `user_id` column is `ForeignKey("users.id")` (`backend/app/db/models.py:73,100,122,…,343`). No direct test seeds an invalid `user_id`, but the scenario is unreachable through the API: every write takes `user_id` from a resolved session whose user exists (`backend/app/auth/deps.py:33-43`). Precision note recorded; no fix task (a direct FK-violation test would test Postgres, not this feature)
- [x] Teste cria usuário sem e-mail → sem sessão; sessão exige login: Handled by design — `session_client`/`login_client` create users with e-mail+hashed password and a real session cookie (`backend/tests/conftest.py:41-57,60-95`); service-level tests that create e-mail-less users call the service directly, never the API

---

## Gate Check

- **Gate command** (Build+Full, final — tasks.md §Gate Check Commands): `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build`
- **Result**: 427 passed, 0 failed, 0 skipped (backend, `uv run pytest -q`, 4:22 on compose Postgres; 1 pre-existing StarletteDeprecationWarning, no skips). Frontend: `npm run lint` clean (0 errors); `npm run build` compiled successfully (Next.js 16.4.0, TypeScript OK, 10/10 static pages).
- **Test count before feature**: 412
- **Test count after feature**: 427
- **Delta**: +15 new tests — 7 in new `backend/tests/test_user_isolation.py` + 8 new user-scoping tests migrated into existing files (`test_list_401_without_session`, `test_list_returns_only_own_user_activities`, `test_detail_404_for_other_users_activity`, `test_detail_context_isolated_per_user` in test_activities_api.py; `test_potential_data_isolated_per_user`; `test_get_job_404_for_other_users_job`; `test_post_404_atividade_de_outro_usuario`, `test_get_status_404_avaliacao_de_outro_usuario` in test_evaluation_api.py)
- **Skipped tests**: none
- **Failures**: none
- **Integrity check**: no test deleted — every removed `def test_` line in the diff is a fixture-signature migration (`client` → `session_client`/`sync_client`) with a matching added line; one rename (`test_post_creates_job_and_runs_sync_to_done` → `test_post_creates_job_for_session_user_and_runs_to_done`, count-neutral); assertions were strengthened, not weakened (every migrated data test now also proves ownership). `test_other_users_rows_never_leak_into_panel` (`backend/tests/test_health_api.py:344`) pre-existed and was kept intact. Success Criterion "`/api/health` continua 200 sem sessão" holds (`backend/tests/test_auth_api.py:286`).

---

## Fix Plans (if issues found)

None required. The sensor killed all mutants, all 19 ACs have evidence, and the gate is green. The two flagged items are dispositions for the orchestrator, not code fixes:

1. **USR-05 wording (Spec-precision gap)** — recommend the orchestrator amend the AC text to name the real surfaces (`GET /api/sync/jobs/latest` user-scoped + internal `get_sync_state` seam). No code change: the protection exists and is tested (`backend/tests/test_user_isolation.py:203-224`).
2. **Stale docstrings** (`backend/tests/test_activities_api.py:12-14`, `backend/tests/test_auth_api.py:3-4`) — cosmetic; fold into any future touch of these files.

---

## Requirement Traceability Update

Update spec.md requirement statuses:

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| USR-01 | Implementing | ✅ Verified |
| USR-02 | Implementing | ✅ Verified |
| USR-03 | Implementing | ✅ Verified |
| USR-04 | Implementing | ✅ Verified |
| USR-05 | Implementing | ✅ Verified (spec wording imprecision flagged — substance verified at the real surfaces; see Spec-Anchored section) |
| USR-06 | Implementing | ✅ Verified |
| USR-07 | Implementing | ✅ Verified |
| USR-08 | Implementing | ✅ Verified |
| USR-09 | Implementing | ✅ Verified |
| USR-10 | Implementing | ✅ Verified |
| USR-11 | Implementing | ✅ Verified |
| USR-12 | Implementing | ✅ Verified |
| USR-13 | Implementing | ✅ Verified |
| USR-14 | Implementing | ✅ Verified |
| USR-15 | Implementing | ✅ Verified |
| USR-16 | Implementing | ✅ Verified |
| USR-17 | Implementing | ✅ Verified |
| USR-18 | Implementing | ✅ Verified |
| USR-19 | Implementing | ✅ Verified (auth tests exercise real 401/cookie/sliding protection without the override; suite green) |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 18/19 ACs matched spec outcome with `file:line` evidence | 1 spec-precision gap flagged (USR-05 — spec names a sync-state endpoint that does not exist; the requirement's substance is verified at the real surfaces)
**Sensor**: 3/3 mutations killed
**Gate**: 427 passed (backend full suite, 0 failed, 0 skipped) + frontend lint clean + frontend build OK

**What works**:
- Every read query (activities list/detail/context, health 6 blocks, potential 5 blocks, evaluation payload, sync state) filters by the session user's `user_id`; zero `DEFAULT_USER_ID` in domain queries (only column defaults + user-1 seed remain, both explicitly allowed by the spec)
- Every write (sync job + all upserts, evaluation creation) carries the session user's `user_id`; `create_job` lost its default — callers must pass the user
- A×B isolation proven end-to-end on all data endpoints with two real cookie sessions; alien resources 404 with exact spec messages; no session → 401 JSON everywhere; liveness `/api/health` stays public
- The suite migrated off the user-1 override: 427 tests on real sessions, +15 new, zero deletions, assertions strengthened
- The discrimination sensor confirms the tests bite: hardcoding user 1, dropping the job ownership check, and dropping the evaluation `user_id` each fail targeted tests immediately

**Issues found**: none blocking. Flagged for the orchestrator: (1) USR-05 spec wording should cite the real surfaces — no code change; (2) FK edge case has no direct test (DB-enforced, unreachable via API — acceptable); (3) two stale test docstrings (cosmetic).

**Next steps**: orchestrator applies the traceability table to `spec.md`, optionally amends the USR-05 wording, and may close the feature. No fix tasks.
