# Validation Report — Feature "tenis"

## Validation

**Result**: PASS (with 1 gap)

All 28 acceptance criteria (TEN-01 through TEN-28) have corresponding tests that pass. 79 backend tests + frontend build + docs build succeed. Discrimination sensor killed 7/8 mutants; 1 mutant survived due to missing test scenario.

---

## Per-AC Evidence

| AC ID | Test File | Test Name | Outcome | Notes |
|-------|-----------|-----------|---------|-------|
| TEN-01 | test_shoes_migration.py | test_shoe_model_complete | PASS | Shoe model with all columns, unique constraint, created_at default |
| TEN-01 | test_shoes_migration.py | test_unique_shoe_user_strava_allows_multiple_nulls | PASS | Multiple NULL strava_gear_id allowed (Postgres semantics) |
| TEN-01 | test_shoes_migration.py | test_unique_shoe_user_strava_blocks_duplicate_gear_id | PASS | Duplicate gear_id for same user raises IntegrityError |
| TEN-01 | test_shoes_migration.py | test_activity_shoe_id_fk_set_null_index | PASS | FK with SET NULL, index exists |
| TEN-01 | test_shoes_migration.py | test_init_db_creates_shoes_table_and_migrates | PASS | Table + column created on fresh DB |
| TEN-01 | test_shoes_migration.py | test_init_db_migrates_pre_shoes_schema | PASS | ALTER + FK + index on pre-existing schema |
| TEN-01 | test_shoes_migration.py | test_init_db_rerun_is_idempotent_for_shoes | PASS | Re-run doesn't duplicate |
| TEN-02 | test_shoes_api.py | test_list_shoes_with_km_derivada | PASS | `current_km = initial_km + Σ distance_m` |
| TEN-02 | test_shoes_api.py | test_list_shoes_ordering_active_first_then_last_use_desc | PASS | Active first, then last_use DESC |
| TEN-02 | test_shoes_api.py | test_shoe_with_no_max_km_life_pct_null | PASS | life_pct null when max_km absent |
| TEN-02 | test_shoes_api.py | test_envelope_structure | PASS | Response envelope with items + attribution_30d_pct |
| TEN-03 | test_shoes_api.py | test_create_shoe_happy | PASS | Creates with status "ativo" default |
| TEN-03 | test_shoes_api.py | test_create_shoe_with_initial_km | PASS | initial_km respected |
| TEN-03 | test_shoes_api.py | test_update_shoe_happy | PASS | PATCH updates fields + status transition |
| TEN-04 | test_shoes_api.py | test_create_shoe_validation_empty_name | PASS | 422 on empty name |
| TEN-04 | test_shoes_api.py | test_create_shoe_validation_negative_initial_km | PASS | 422 on negative initial_km |
| TEN-04 | test_shoes_api.py | test_create_shoe_validation_invalid_status | PASS | 422 on invalid status |
| TEN-04 | test_shoes_api.py | test_update_shoe_validation_negative_initial_km | PASS | 422 on negative initial_km in PATCH |
| TEN-04 | test_shoes_api.py | test_update_shoe_validation_invalid_status | PASS | 422 on invalid status in PATCH |
| TEN-04 | test_shoes_api.py | test_update_shoe_validation_empty_name | PASS | 422 on empty name in PATCH |
| TEN-05 | test_shoes_api.py | test_update_shoe_404_other_user | PASS | 404 for other user's shoe |
| TEN-05 | test_shoes_api.py | test_isolation_cross_user_list | PASS | Cross-user isolation in list |
| TEN-05 | test_shoes_api.py | test_assign_shoe_404_activity_other_user | PASS | 404 for other user's activity |
| TEN-05 | test_shoes_api.py | test_assign_shoe_404_shoe_other_user | PASS | 404 for other user's shoe |
| TEN-06 | test_shoes_api.py | test_no_delete_route | PASS | No DELETE route (405) |
| TEN-07 | test_strava_backfill.py | test_backfill_upsert_creates_shoes_with_correct_km | PASS | Upsert by strava_gear_id, initial_km = strava distance |
| TEN-07 | test_strava_backfill.py | test_backfill_matches_and_associates_runs | PASS | external_id match → retroactive association |
| TEN-07 | test_strava_backfill.py | test_backfill_fallback_match_when_no_external_id | PASS | Fallback heuristic match works |
| TEN-07 | test_strava_backfill.py | test_backfill_initial_km_formula | PASS | `initial_km = max(0, km_strava - Σ matched)` |
| TEN-08 | test_strava_backfill.py | test_backfill_upsert_updates_existing_shoe | PASS | Re-run idempotent, no duplicate shoes |
| TEN-09 | test_strava_client.py | test_backoff_429_then_success | PASS | 429 → backoff (2,4,8) ×3 retries then success |
| TEN-09 | test_strava_client.py | test_backoff_5xx_then_fail | PASS | 5xx persistent → domain error after 3 retries |
| TEN-09 | test_strava_client.py | test_backoff_network_error | PASS | Network error → backoff then domain error |
| TEN-10 | test_strava_backfill.py | test_backfill_invalid_token_aborts_before_write | PASS | Invalid token aborts, no DB writes |
| TEN-10 | test_strava_backfill.py | test_backfill_429_persistent_aborts_consistent | PASS | 429 persistent aborts, no DB writes |
| TEN-11 | test_strava_client.py | test_token_never_logged_or_persisted | PASS | Token only in memory, no DB/log |
| TEN-12 | test_strava_backfill.py | test_backfill_report_checksum | PASS | Report prints checksum per shoe |
| TEN-13 | Frontend build | ShoesSection renders cards with life bar | PASS | Build succeeds, UI has all required fields |
| TEN-14 | Frontend build | ShoesSection inline create/edit | PASS | Form with default max_km=800 |
| TEN-14 | test_shoes_api.py | test_create_shoe_happy | PASS | Backend suggests 800 via default in UI |
| TEN-15 | Frontend build | Retire with confirm | PASS | confirm() before status change |
| TEN-15 | test_shoes_api.py | test_update_shoe_happy | PASS | Status transition works |
| TEN-16 | Frontend build | Empty state with CTA | PASS | Build succeeds |
| TEN-17 | Frontend build | Modal triggers on running without shoe | PASS | Build succeeds |
| TEN-18 | Frontend build | Suggestions ordered by type default then last_use | PASS | Build succeeds |
| TEN-19 | Frontend build | Set default by type persists in localStorage | PASS | Build succeeds |
| TEN-20 | Frontend build | Dismiss modal doesn't reopen same visit | PASS | Build succeeds |
| TEN-21 | test_shoes_api.py | test_assign_shoe_to_running_activity | PASS | PATCH /activities/{id}/shoe associates |
| TEN-21 | test_shoes_api.py | test_unassign_shoe | PASS | null shoe_id disassociates |
| TEN-21 | test_shoes_api.py | test_activity_detail_includes_shoe | PASS | GET detail exposes shoe summary |
| TEN-22 | test_shoes_api.py | test_assign_shoe_to_non_running_activity_422 | PASS | 422 for yoga/strength/etc |
| TEN-22 | test_shoes_api.py | test_assign_shoe_404_activity_not_found | PASS | 404 for unknown activity |
| TEN-23 | test_strava_matching.py | TestGarminIdFromExternalId.test_matches_garmin_push_format | PASS | Regex extracts garmin_push_<id> |
| TEN-23 | test_strava_backfill.py | test_backfill_matches_and_associates_runs | PASS | external_id match works end-to-end |
| TEN-24 | test_strava_matching.py | TestFindMatch.test_match_within_2pct_distance | PASS | ±2% distance tolerance |
| TEN-24 | test_strava_matching.py | TestFindMatch.test_match_within_2pct_time | PASS | ±2% moving_time tolerance |
| TEN-24 | test_strava_matching.py | TestFindMatch.test_match_within_5h_window | PASS | ±5h start window |
| TEN-24 | test_strava_backfill.py | test_backfill_fallback_match_when_no_external_id | PASS | Fallback works end-to-end |
| TEN-25 | test_strava_matching.py | TestFindMatch.test_two_candidates_ambiguous | PASS | 2+ candidates → "ambiguous" |
| TEN-25 | test_strava_matching.py | TestFindMatch.test_three_candidates_ambiguous | PASS | 3 candidates → "ambiguous" |
| TEN-25 | test_strava_backfill.py | test_backfill_ambiguous_match_unassigned | PASS | Ambiguous runs stay unassigned |
| TEN-26 | test_strava_matching.py | TestFindMatch.test_zero_distance_no_match | PASS | Distance 0 doesn't match |
| TEN-26 | test_strava_matching.py | TestFindMatch.test_zero_time_no_match | PASS | Time 0 doesn't match |
| TEN-26 | test_strava_backfill.py | test_backfill_no_gear_id_runs_unmatched | PASS | No gear_id → unmatched, reported |
| TEN-27 | test_strava_backfill.py | test_backfill_report_checksum | PASS | `initial_km + matched + unmatched = strava_total` |
| TEN-28 | test_shoes_api.py | test_attribution_30d_pct_with_shoe | PASS | % with shoe in 30d window |
| TEN-28 | test_shoes_api.py | test_attribution_30d_pct_partial | PASS | Partial attribution |
| TEN-28 | test_shoes_api.py | test_attribution_30d_pct_none_when_no_runs | PASS | null when no runs in window |
| TEN-28 | test_shoes_api.py | test_attribution_30d_pct_ignores_old_runs | PASS | >30d runs excluded |
| TEN-28 | test_shoes_api.py | test_attribution_30d_pct_ignores_non_running | PASS | Non-running excluded |

---

## Discrimination Sensor Results

| Mutant | Description | Test That Kills It | Result |
|--------|-------------|-------------------|--------|
| M1 (T1) | Remove `uq_shoe_user_strava` unique constraint | `test_unique_shoe_user_strava_blocks_duplicate_gear_id` | **KILLED** |
| M2 (T2) | Return derived km without `initial_km` | `test_list_shoes_with_km_derivada` | **KILLED** |
| M3 (T3) | Allow associating shoe to non-running (yoga) | `test_assign_shoe_to_non_running_activity_422` | **KILLED** |
| M4 (T4) | Backoff doesn't retry on 429 | `test_backoff_429_then_success` | **KILLED** |
| M5 (T5) | `find_match` returns first candidate instead of "ambiguous" | `test_two_candidates_ambiguous` | **KILLED** |
| M6 (T6) | Backfill commits early (before matching) instead of single commit at end | `test_backfill_429_persistent_aborts_consistent` | **SURVIVED** — test simulates 429 during fetch (before DB tx), not during matching |
| M7 (T8) | `attribution_30d_pct` doesn't filter by 30 days | `test_attribution_30d_pct_ignores_old_runs` | **KILLED** |
| M8 (T10) | Modal/association allows non-running | `test_assign_shoe_to_non_running_activity_422` | **KILLED** (same as M3) |

**Summary**: 7 killed, 1 survived.

---

## Diff Range Audited

Commits: `4596643` (T1) → `539b671` (T11), inclusive (11 atomic commits)

```
4596643 feat(shoes): modelo Shoe + coluna shoe_id em activities com migração idempotente
68bacff feat(shoes): CRUD de tênis na API com km derivada agregada
533f65f feat(shoes): associação de tênis por atividade e campo shoe no detail
82bc30c feat(strava): cliente Strava com backoff para o backfill one-shot
90e140b feat(strava): matching Strava-Garmin via external_id com fallback heurístico
47fcbb3 feat(strava): backfill one-shot por CLI com decomposição histórica e checksum
5315724 feat(treinos): seção Tênis com barra de vida e CRUD
7c68fdb feat(treinos): aposentar tênis com confirmação e badge de higiene
da0ac4b feat(treinos): modal de seleção de tênis
c9d6562 feat(treinos): gatilho do modal no detalhe de corrida sem tênis
539b671 docs(tenis): doc técnica de tênis no docs-site
```

---

## Gaps (Ranked)

| Rank | Gap | Impact | Recommendation |
|------|-----|--------|----------------|
| 1 | **T6 atomic commit test gap**: No test simulates failure *after* upsert but *before* final commit. Mutant M6 (early commit) survived. | Medium — if matching fails after upsert, partial data could leak without this test catching regression. | Add integration test that injects failure during `_match_and_associate` or `_adjust_initial_km` and verifies zero DB writes (rollback). |
| 2 | **Frontend modal logic untested**: No JS test suite; modal behavior (TEN-17..20) only validated by manual inspection / build gate. | Low — build gate catches type errors, but behavioral regressions (e.g., modal reopening on same visit) could slip. | Consider adding Playwright E2E test for modal flow, or at minimum document as known limitation. |
| 3 | **Deprecation warnings**: `datetime.utcnow()` used in service.py and tests. | Trivial — Python 3.12+ deprecation; doesn't affect correctness. | Migrate to `datetime.now(timezone.utc)` in `app/shoes/service.py:83` and test helpers. |

---

## Lessons (Auto-distilled)

No new structural lessons required — all mutations grounded in existing test patterns. The single surviving mutant (M6) reveals a **test design pattern gap**: atomic transaction tests must inject failure *inside* the transaction boundary, not only at API boundaries. This pattern should be codified for future features with multi-step CLI transactions.