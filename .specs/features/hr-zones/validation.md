# hr-zones Validation

**Date**: 2026-10-21
**Spec**: `.specs/features/hr-zones/spec.md`
**Diff range**: `3a08443..223e914` (13 task commits: c7a27dd, 2e20377, 60868f7, e49e26f, 008456b, 8c344fd, 24fc4d5, 202ddfa, ffc65c3, 33f5970, 094d84b, 13f87d1, 223e914, on top of planning commit 3a08443)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | `UserHrMetric` + `HrZoneConfig` in `backend/app/db/models.py:346-386` — composite index `(user_id, kind, valid_from)` / `(user_id, valid_from)`, no unique on `valid_from`; `backend/tests/test_hr_zones_models.py:56-104` proves same-day double insert + index/unique shape |
| T2 | ✅ Done | `backend/app/profile/calc.py` — `DEFAULT_BOUNDS` (65/80/89/95/100 lthr Z5 null; 50/60/70/80/90 fcr/fcmax), `validate_bounds`, `zones_bpm`, `classify`; 15 unit tests, all values hand-computed literals |
| T3 | ✅ Done | Seed in `backend/app/db/engine.py:77-97` — only lthr config for user 1, guard-of-existence, zero metrics seeded; `backend/tests/test_hr_zones_models.py:139-156` |
| T4 | ✅ Done | `backend/app/profile/service.py` — `metric_on/metrics_on/config_on/zones_on` (`valid_from ≤ D`, tie-break `(valid_from DESC, id DESC)`), `set_metric` (idempotent + manual-wins), `set_config`, `validate_metrics_set` (merge-aware, PT-BR messages); 13 service tests |
| T5 | ✅ Done | `backend/app/profile/router.py` (GET/PUT/history, shape of GET on PUT response, 422 per field/first invalid point) wired in `backend/app/main.py:64` with `require_session`; 12 API tests incl. 401 + A×B isolation |
| T6 | ✅ Done | `GarminGateway.get_user_settings`/`get_lactate_threshold` (`backend/app/garmin/client.py:189-200`), both via `_call`; FakeGateway extended (`backend/tests/fake_garmin.py:203-211`) incl. `heartRate: None` case; 4 gateway tests incl. read-only source scan |
| T7 | ✅ Done | `update_physio_metrics` (`backend/app/garmin/upserts.py:136-155`) — delegates idempotency/manual-wins to `set_metric`, counts only new rows, None skips; 6 upsert tests |
| T8 | ✅ Done | `_sync_physio` phase (`backend/app/garmin/service.py:318-352`) after predictions: fcmax from `userData.maxHeartRate`, fclthr from `speed_and_heart_rate.heartRate`, fcrest = min-7d of `rhr` (local query), warning `{tipo: "physio"}` + job done on failure; 6 sync tests + API-level test |
| T9 | ✅ Done | `backend/app/evaluation/payload.py:242-284` — `_lthr_bpm` (metric on activity date → env fallback) + `_zonas_fc` (zones of activity date, seconds+pct per zone, denominator = laps with FC); 6 payload tests |
| T10 | ✅ Done | `frontend/src/lib/api.ts` (+101 lines: types + `getHrZones`/`updateHrZones`/`getHrZonesHistory` via `apiFetch`, zero direct `fetch`), `proxy.ts:17` (`/perfil` protected), `UserMenu.tsx` display_name → `/perfil` link; build gate green |
| T11 | ✅ Done | `frontend/src/app/(app)/perfil/page.tsx` + `HrValuesCard.tsx` — 3 value cards with source badge (Garmin/Manual) + vigência, honest empty state, PUT → re-render from response, 422 inline; build gate green |
| T12 | ✅ Done | `HrMethodCard.tsx` (3 methods, defaults prefill, editable percentages), `HrZonesPreview.tsx`, `HrHistoryList.tsx` (DESC, date + source); build gate green |
| T13 | ✅ Done | README §"Zonas de FC no /perfil" (methods, defaults, sync phase +3 calls, manual-wins, nothing seeded, LTHR_BPM fallback, pending-UAT spike note) + `backend/.env.example` documents fallback |

All 13 tasks marked complete in `tasks.md`; commit messages match the plan 1:1.

---

## Spec-Anchored Acceptance Criteria

### P1: Métricas fisiológicas com histórico

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| HRZ-01: WHEN `GET /api/profile/hr-zones` com sessão válida THEN devolve fcmax/fcrest/fclthr vigentes, cada um `{value, source, valid_from}` ou null | Exact GET shape, per-kind value/source/valid_from or null | `backend/tests/test_hr_zones_api.py:100-104` - `assert body["metrics"] == {"fcmax": None, "fcrest": None, "fclthr": {"value": 177, "source": "manual", "valid_from": TODAY_ISO}}` (payload/conjunction rule: whole block asserted on values, not calls); empty state `:131-134` (`metrics` all None, `config is None`, `zones is None`); service-level `backend/tests/test_hr_zones_service.py:99-102` (`metrics["fcmax"].source == "garmin"`, `metrics["fcrest"] is None`) | ✅ PASS |
| HRZ-02: WHEN PUT recebe novo valor THEN linha nova `source=manual`, `valid_from` = hoje, append-only | 1 new manual row dated today; history preserved | `backend/tests/test_hr_zones_api.py:151-161` - response `metrics["fclthr"] == {"value": 185, "source": "manual", "valid_from": TODAY_ISO}` + DB row `== (185, "manual", TODAY)`; append-only proven by history of 3 distinct rows `backend/tests/test_hr_zones_service.py:169-171` | ✅ PASS |
| HRZ-03: IF valor igual ao vigente THEN sucesso sem linha nova (idempotente) | 200 + zero new rows | `backend/tests/test_hr_zones_api.py:163-168` - repeat PUT → 200 + `assert db.query(UserHrMetric)....count() == 1` (`:168`); service `backend/tests/test_hr_zones_service.py:135-139` - `is False` (manual and garmin sources) + `count() == 1` (`:139`); sync-level `backend/tests/test_garmin_upserts.py:508-516` (return 0, count 3) | ✅ PASS |
| HRZ-04: IF valor fora dos limites (fcmax 100–230, fcrest 30–110, fclthr 100–220) ou incoerente (fcrest ≥ fcmax, fclthr ≥ fcmax) THEN 422 apontando campo e motivo | 422 with exact field + PT-BR reason, nothing written | `backend/tests/test_hr_zones_api.py:175-190` - 5 cases with exact details (`"fcmax: deve estar entre 100 e 230 bpm"`, `"fcrest: deve estar entre 30 e 110 bpm"`, `"fclthr: deve estar entre 100 e 220 bpm"`, `"fclthr: limiar acima da FC máxima"`) + `count() == 0` (`:190`); merge incoherence vs vigente `:193-206`; boundary-inclusive + full coherent set `backend/tests/test_hr_zones_service.py:266-279`; both ≥ incoherencies incl. equality `:243-263` | ✅ PASS |
| HRZ-05: WHEN sync executa THEN atualiza as 3 métricas das fontes automáticas (fcmax/fclthr do Garmin, ausente → pula; fcrest = mínimo-7d da série rhr), linha `source=garmin` quando difere | 3 garmin rows after sync; absent value skips; +3 calls | `backend/tests/test_garmin_service.py:649-678` - `by_kind == {"fcmax","fcrest","fclthr"}`, values `190/172/42`, `all(row.source == "garmin")`, `stats["calls_made"] == 502` (`:659`); absent→skip: LTHR None `:681-703` (`set(kinds) == {"fcmax","fcrest"}`, no warning) and maxHR absent `:817-838`; update-if-changed `backend/tests/test_garmin_upserts.py:553-570`; API-level `backend/tests/test_sync_api.py:199-223` | ✅ PASS (⚠️ sub-clause gap — see note below) |
| HRZ-06: IF linha vigente é `source=manual` THEN sync não cria linha nova | Manual never overwritten by Garmin | `backend/tests/test_hr_zones_service.py:144-156` - `set_metric(..., 185, "garmin") is False` + `count() == 1` (`:154`) + row still `(177, "manual")` (`:156`); upsert `backend/tests/test_garmin_upserts.py:519-538` (`len(lthr_rows) == 1`, source manual, return 2 = other kinds only); end-to-end sync `backend/tests/test_garmin_service.py:706-741` (`len(lthr_rows) == 1` after sync `:733`, 2nd sync adds nothing) | ✅ PASS |
| HRZ-07: WHEN banco inicializa THEN semeia APENAS a config lthr do usuário 1 (defaults); nenhuma métrica; idempotente | 1 config row (lthr, defaults, today), 0 metric rows, re-init stable | `backend/tests/test_hr_zones_models.py:139-156` - `len(configs) == 1`, `user_id == 1`, `method == "lthr"`, `bounds == LTHR_BOUNDS` (spec literals), `valid_from == date.today()`, `assert db.query(UserHrMetric).count() == 0` (`:152`), second `init_db()` → still 1 config (`:155`) | ✅ PASS |

**HRZ-05 sub-clause note (honest flag, non-blocking):** the spec pins `fcrest` = "mínimo dos últimos 7 dias da série `rhr`". The code implements exactly that (`backend/app/garmin/service.py:336-341` — `func.min(Rhr.value)` with `Rhr.date >= _today() - timedelta(days=6)`), and the *behavioral* outcomes are tested (value arrives, changes create rows, unchanged syncs don't — `test_garmin_service.py:744-789`). But the fake RHR series is uniform per sync (42 every day, then 40 every day), so **neither the "minimum" nor the "7-day window" is discriminated** — a mutation to `func.max` or to a 30-day window would survive. Test-precision gap on one sub-clause; the AC's main outcomes (auto-update, line creation, manual-wins, skip-if-absent) are all discriminated. Fix-task-eligible if the orchestrator wants 1:1 pinning.

### P1: Config de método e percentuais + zonas derivadas

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| HRZ-08: WHEN método alterado THEN config nova com defaults do método (lthr 65/80/89/95/100; fcr/fcmax 50/60/70/80/90), sem tocar métricas | Exact default tables per method; metrics untouched | `backend/tests/test_hr_zones_calc.py:49-56` - `assert DEFAULT_BOUNDS == {"lthr": [65/80/89/95/100 Z5 null], "fcr": FCR_DEFAULTS, "fcmax": FCR_DEFAULTS}` (spec literals hand-written); API `backend/tests/test_hr_zones_api.py:226-241` - PUT `{"method": "fcr"}` → `config == {"method": "fcr", "bounds": FCR_DEFAULTS, ...}` + `metrics` all None; service `backend/tests/test_hr_zones_service.py:197-213` - `assert db.query(UserHrMetric).count() == 0` (`:213`, métricas intactas) | ✅ PASS |
| HRZ-09: WHEN percentuais editados THEN config nova; IF inválidos (≠5, cadeia não ascendente, zona <1 ponto, z1.low ≤ 0, upper em Z5 do LTHR) THEN 422 com o primeiro ponto inválido | Valid custom bounds create config + recalc; each invalid class rejected pointing at the FIRST invalid zone | `backend/tests/test_hr_zones_calc.py:59-150` - accepts defaults+custom; rejects: count (`:70-73`), z1.low ≤ 0 (`:76-82`), gap AND overlap (`:85-100`, both "zona 2"), <1 point + null high mid-chain (`:103-116`), lthr Z5 high ≠ null (`:119-126`), fcr/fcmax Z5 ≠ 100 incl. null/99/100 (`:129-138`), first-invalid ordering (`:141-150` - "zona 2" asserted, "zona 5" asserted NOT in message); HTTP: `backend/tests/test_hr_zones_api.py:288-304` - 422, `"zona 2" in detail`, `"zona 5" not in detail`, no config row created (`:304`) | ✅ PASS |
| HRZ-10: WHILE métricas exigidas existem THEN zonas em bpm na leitura (lthr `round(pct × fclthr/100)`; fcr Karvonen; fcmax `round(pct × fcmax/100)`), `low ≤ FC < high`, Z5 do LTHR aberta | Exact bpm zones per formula; boundary semantics; open Z5 | `backend/tests/test_hr_zones_calc.py:153-164` - lthr 177 → `[115, 142, 158, 168, 177+]` (formula-literal); custom 64/79/88/94/99 → `[113, 140, 156, 166, 175+]` (`:167-177`); fcr fcrest 50/fcmax 190 → `[120, 134, 148, 162, 176]` Z5 closes at 190 (`:180-191`); fcmax 190 → `[95, 114, 133, 152, 171]` Z5 closes at 190 (`:194-204`); classify boundaries `:218-232` - `classify(115) == 1` (low inclusive), `classify(141) == 1`/`classify(142) == 2` (`:226-227`, high exclusive), `classify(220) == 5` (`:232`, Z5 aberta sem teto); via GET `backend/tests/test_hr_zones_api.py:108-114` | ✅ PASS (⚠️ spec-internal discrepancy — see note below) |
| HRZ-11: IF métrica exigida não existe (ex.: fcr sem fcrest) THEN zonas null (estado vazio honesto, não erro) | `zones: null` per missing required metric, per method | `backend/tests/test_hr_zones_calc.py:207-215` - `zones_bpm("lthr", …, {"fclthr": None}) is None`, fcr missing fcrest **and** missing fcmax both None, fcmax None; service `backend/tests/test_hr_zones_service.py:311-317` - config lthr sem fclthr → `(config, None)`; API empty `backend/tests/test_hr_zones_api.py:131-133` (`zones is None`), fcr sem métricas `:240` | ✅ PASS |
| HRZ-12: WHEN leitura em data D THEN usa métrica e config vigentes em D (treino antigo → zonas da época) | Resolution by `valid_from ≤ D` with same-day tie-break; old activity read with old zones | `backend/tests/test_hr_zones_service.py:63-75` - D9 → None, D15 → `(170, D10)`, D21 → `(180, D20)`; tie-break `:78-88` - two same-day rows, `assert row.value_bpm == 175` (higher id wins, `:88`); config effective-dating `:105-119`; payload `backend/tests/test_evaluation_payload.py:372-381` (`lthr_bpm == 172`, not the later 185) and `:431-445` (zonas da época: `{"n": 1, "low": 112, "high": 138}` from fclthr 172, not 180, plus `lthr_bpm == 172`) | ✅ PASS |

**HRZ-10 spec-internal discrepancy (flag for orchestrator, non-blocking):** the spec's *Independent Test* example says "PUT método=lthr com fclthr 177 → zonas **[115, 141, 156, 168, 177+]**", but the AC's **normative formula** `round(pct × fclthr / 100)` gives 65%→115, 80%×177=141.6→**142**, 89%×177=157.53→**158**, 95%→168, 100%→177. The implementation and every test (`test_hr_zones_calc.py:154-164`, `test_hr_zones_service.py:300-306`, `test_hr_zones_api.py:108-114`) pin the **formula** values `[115, 142, 158, 168, 177+]` — the correct choice per the AC text (formula > illustrative example). The tasks.md T2 done-when has a third variant (`[115, 141, 158, 168, 177+]`), internally inconsistent. Also, AC-10 writes the formula as `round(pct × fclthr)` — literally 65×177 — with the `/100` only explicit in design/tasks (pct in percentage points). Recommendation: amend the Independent Test example and the AC-10 formula notation; no code change.

### P1: Tela de zonas no `/perfil`

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| HRZ-13: WHEN usuário autenticado abre `/perfil` THEN exibe valores com badge de fonte (Garmin/Manual) e vigência, método, percentuais e zonas resultantes (padrão AD-009) | 3 sections with strong headers + "o que é / por que importa" subtitles; badges; zones preview | Frontend has NO test runner (project-decided pattern — tasks.md matrix: "build gate only"). Code evidence: `frontend/src/app/(app)/perfil/page.tsx:96-113` - 3 `PanelSection` with index+title+subtitle ("Quais são os seus números?…", "Como as zonas são calculadas?…", "O que mudou e quando?…"); `frontend/src/components/profile/HrValuesCard.tsx:29-31` - `"garmin" → "Garmin"` badge, vigência + "nunca configurado" empty state (`:124`); `HrMethodCard.tsx` (3 methods, defaults prefill), `HrZonesPreview.tsx`; build gate compiles `/perfil` | ✅ PASS (code + build; runtime rendering pending UAT) |
| HRZ-14: WHEN usuário edita valor/método/percentual THEN client chama PUT e re-renderiza; IF 422 THEN erro inline por campo em PT-BR | PUT on save; response drives re-render ("zonas mudam na hora"); per-field inline PT-BR errors | Code evidence: `frontend/src/lib/api.ts:701-711` - `updateHrZones` via `apiFetch` (PUT); `frontend/src/app/(app)/perfil/page.tsx:41-56` - `handleSaved` puts the **PUT response** into state (re-render) and refetches history; `HrValuesCard.tsx`/`HrMethodCard.tsx` map 422 `detail` per field/zone inline (PT-BR comes from the API contract, exact messages pinned at API level `backend/tests/test_hr_zones_api.py:175-190, 299-301`) | ⚠️ pending runtime UAT (code-verified + build green; interactive behavior — 390px, "zonas mudam na hora" — needs the user's phone; no frontend test runner by project pattern) |
| HRZ-15: WHEN usuário consulta histórico THEN lista mudanças de métricas e configs, mais recente primeiro, com data e fonte | DESC by (valid_from, id) with date + source, both series | `backend/tests/test_hr_zones_api.py:350-383` - exact ordered array `[185 manual 20/10, 177 garmin 20/10, 170 garmin 19/10]` (`:366-373` — same-day tie-break by id DESC visible) + configs `[fcr, lthr]` with today first (`:380-383`); impl `backend/app/profile/router.py:213-224` (`order_by(valid_from.desc(), id.desc())`); frontend `HrHistoryList.tsx` renders badges + dates | ✅ PASS (API exact; frontend rendering pending UAT) |
| HRZ-16: IF sem sessão abre `/perfil` THEN aterrissa em `/login` | Proxy protection + 401 JSON on all 3 endpoints | `backend/tests/test_hr_zones_api.py:391-403` - GET/PUT/history without cookie → `assert response.status_code == 401` + `assert response.json() == {"detail": "não autenticado"}`; impl: `backend/app/main.py:64` (`include_router(profile_router, dependencies=[Depends(require_session)])`); frontend `frontend/src/proxy.ts:17` - `PANEL_PREFIXES = ["/treinos", "/performance", "/saude", "/perfil"]` (no cookie → `/login?next=/perfil`) | ✅ PASS (401 exact; redirect pending UAT) |

### P1: Consumo na avaliação IA

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| HRZ-17: WHEN payload montado THEN `lthr_bpm` da métrica `fclthr` vigente na data do treino; IF não existe THEN fallback env (`LTHR_BPM`) | Both branches pinned with distinct values | `backend/tests/test_evaluation_payload.py:372-381` - fclthr 172 (2024-01-01) + 185 (2024-02-01), activity 2024-01-15 → `assert payload["lthr_bpm"] == 172` (`:381`); fallback `:384-392` - `Settings(_env_file=None, lthr_bpm=181)` sem métrica → `assert payload["lthr_bpm"] == 181` (`:392`); env default 177 also pinned pre-existing `:225`; impl `backend/app/evaluation/payload.py:242-248` | ✅ PASS |
| HRZ-18: WHEN treino tem FC nas voltas THEN payload inclui tempo por zona de FC (segundos e % por zona, só voltas com FC e duração), zonas vigentes na data do treino | Exact zonas + tempo_por_zona arrays; no-FC lap excluded from denominator | `backend/tests/test_evaluation_payload.py:395-428` - 6 splits (5 with FC + 1 `avg_hr=None`), `assert payload["zonas_fc"] == {"zonas": [112/138, 138/153, 153/163, 163/172, 172/null], "tempo_por_zona": [{1, 300.0, 27.8}, {2, 300.0, 27.8}, {3, 300.0, 27.8}, {4, 120.0, 11.1}, {5, 60.0, 5.6}]}` — denominator 1080s (FC laps only; 300/1080=27.8), Z5 aberta catches hr 180; zonas da época `:431-445` | ✅ PASS |
| HRZ-19: IF nenhuma volta tem FC THEN payload omite o bloco (nenhum número inventado) | `zonas_fc` key absent from payload | `backend/tests/test_evaluation_payload.py:448-460` - 2 splits sem FC → `assert "zonas_fc" not in payload` (`:459`, `lthr_bpm` ainda presente `:460`); sem config ou config sem métrica → omitido `:463-479` (`:471`, `:479`); impl `backend/app/evaluation/payload.py:257-259, 272-273` + final `_keep`-style filter `:317` | ✅ PASS |

**Status**: 19/19 ACs have located, spec-outcome-matching evidence; 2 spec-precision gaps flagged (HRZ-05 fcrest min-7d sub-clause; HRZ-10 illustrative example vs normative formula) — both non-blocking, no code change required.

---

## Discrimination Sensor

Method: file-backup (proven on this Windows box; a git worktree would need its own `uv sync`). Baseline `git status --porcelain` = **clean** (recorded before sensor). For each mutation: file copied to `%TEMP%\opencode\hr-zones-sensor\<name>.bak`, edit applied to the real file, targeted test file(s) run **in full (no `-k`)**, file restored from backup, porcelain re-checked. `git stash` was NOT used at any point.

| Mutation | File:line | Description | Killed? |
| -------- | --------- | ----------- | ------- |
| M1 | `backend/app/profile/service.py:49` | Effective-dating boundary: `UserHrMetric.valid_from <= on_date` → `<` | ✅ Killed — `uv run pytest tests/test_hr_zones_service.py tests/test_hr_zones_api.py`: **10 failed, 15 passed**. Primary kill: `test_set_metric_same_value_is_idempotent` at `backend/tests/test_hr_zones_service.py:139` (`assert db.query(UserHrMetric).count() == 1` → 2 — the row created *today* is no longer "vigente today", so the idempotency check reads None); also `test_put_metric_creates_manual_row_and_is_idempotent` (`test_hr_zones_api.py:168`), full-shape GET, isolation and same-valid_from tests |
| M2 | `backend/app/profile/service.py:51` | Same-day tie-break: `UserHrMetric.id.desc()` → `id.asc()` | ✅ Killed — `uv run pytest tests/test_hr_zones_service.py`: **2 failed, 11 passed**. Target `test_metric_on_tie_break_same_day_prefers_higher_id` at `backend/tests/test_hr_zones_service.py:88` (`assert row.value_bpm == 175` → 170); secondary: `test_set_metric_inserts_on_real_change` |
| M3 | `backend/app/profile/service.py:110` | Manual-wins guard flipped: `source == "garmin" and current.source == "manual"` → `source == "manual" and …` | ✅ Killed — `uv run pytest tests/test_hr_zones_service.py tests/test_garmin_upserts.py`: **4 failed, 35 passed**. `test_set_metric_garmin_never_overrides_manual` at `backend/tests/test_hr_zones_service.py:154` (`count() == 1` → 2 — Garmin now overwrites the manual edit); `test_update_physio_metrics_manual_wins_vigente` at `backend/tests/test_garmin_upserts.py:536` (`len(lthr_rows) == 1` → 2) + mixed-outcomes count test |
| M4 | `backend/app/profile/calc.py:143` | Zone semantics: `zone["low"] <= hr < zone["high"]` → `<=` (upper inclusive) | ✅ Killed — `uv run pytest tests/test_hr_zones_calc.py`: **1 failed, 14 passed**. Target `test_classify_boundaries` at `backend/tests/test_hr_zones_calc.py:227` (`assert classify(142, zones) == 2` → 1 — hr 142 must fall in Z2, not stay in Z1) |
| M5 | `backend/app/evaluation/payload.py:258-259` | `zonas_fc` omission guard dropped (`if zones is None: return None` removed) | ✅ Killed — `uv run pytest tests/test_evaluation_payload.py`: **15 failed, 4 passed**. Target `test_zonas_fc_omitido_sem_config_ou_sem_metrica` (`backend/tests/test_evaluation_payload.py:463`; the `"zonas_fc" not in payload` assertions at `:471,479` unreachable — payload build crashes with `TypeError` on None zones); 14 further payload tests crash identically |

**Sensor depth**: lightweight-to-expanded (5 mutations across 4 distinct risk areas: effective-dating resolution ×2, manual-wins guard, zone boundary math, payload omission guard)
**Result**: 5/5 killed — PASS ✅ (no surviving mutants → no fix tasks from the sensor)

**Isolation verification**: `git status --porcelain` returned to the clean baseline after EACH restore (checked after M1, M2, M3, M4, M5); after the final restore `git diff --stat` was also empty (byte-identical to `223e914`). Post-sensor sanity: `uv run pytest tests/test_hr_zones_calc.py tests/test_hr_zones_models.py tests/test_hr_zones_service.py tests/test_hr_zones_api.py` → 43 passed. Temp dir cleaned. Sync-physio risk area was additionally exercised by M3 (the manual-wins rule lives in `set_metric` and is inherited by the sync phase — the upsert tests are the sync path's direct witnesses); the fcrest min-7d sub-clause is not test-discriminated (see HRZ-05 note — a window mutation would survive, flagged there rather than as a sensor survivor, since the tested *behaviors* all hold).

---

## Interactive UAT Results (if performed)

Not performed — the pending items require the user's real Garmin account and phone. Per the tasks.md coverage matrix, frontend behavior is deliberately gated by lint/build only (project-decided pattern), so the following remain **pending user runtime-UAT** (flagged, NOT counted as failures):

1. **First real sync (spike runtime)** — Success Criterion 1: user 1 runs a real sync; `fcmax`/`fclthr` actually arrive from the Garmin account (`userData.maxHeartRate` present, LTHR detected by the watch) and `fcrest` from the min-7d. The lib facts are code-verified (see SPEC_DEVIATION section) but the presence of real values only shows on a real account. README documents this as "Pendente de UAT".
2. **`/perfil` on mobile (390px)** — HRZ-13/14 runtime: values with badges, method switch prefills defaults, saving recalculates zones "na hora", 422 shows inline per-field, history lists the changes (AD-009 clarity pattern).
3. **Manual-wins badge end-to-end** — edit a value manually, run a real sync, confirm the "Manual" badge persists and the history records only real changes.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ — new modules are small and single-purpose (`calc.py` 145 lines pure stdlib, `service.py` 166, `router.py` 239); sync phase reuses the phase/warning pattern; manual-wins and idempotency live in ONE place (`set_metric`) and `update_physio_metrics` delegates instead of duplicating |
| Surgical changes | ✅ — diff touches exactly the mapped files: 9 backend app files + 33-file diff total, of which 13 are new tests + 5 extended tests + 4 new frontend components + page + helpers + proxy/menu + docs; `.specs` files updated with status/traceability only |
| No scope creep | ✅ — no new endpoints beyond the 3 in the spec; VDOT pace zones untouched (`vdot_zones.json` still the only pace source); no retroactive reclassification (vigente-na-data only); `/perfil` born with just the 3 zone sections (rest deferred to `user-profile`, per spec Out of Scope) |
| No speculative tests | ✅ — all 66 new `def test_` reverse-map to HRZ ACs, edge cases, task done-whens or pre-existing gates: calc 15 → HRZ-08/09/10/11 + edge Z5/classify; models 3 → T1/T3 done-whens + HRZ-07; service 13 → HRZ-01/02/03/04/06/08/12; api 12 → HRZ-01/02/03/04/08/09/15/16 + edge same-valid_from + 422-empty (design §Erros); gateway 4 → T6 done-whens (+3 budget, read-only source scan — design risk row); upserts 6 → HRZ-03/05/06; garmin_service 6 → HRZ-05/06 + edge fcrest evolution + SYNC-20 warning; sync_api 1 → HRZ-05 via HTTP; payload 6 → HRZ-12/17/18/19 |
| Matches existing patterns | ✅ — router inline models + `require_session` (health/potential pattern); domain exceptions with exact PT-BR messages (auth/service pattern); pure calc (AD-003); `_call` gateway accounting (AD-002); phase warning + `done` (SYNC-20); seed guard (AD-019); `session_client` for HTTP tests |
| Asserted values match spec (not implementation) | ✅ — defaults, limits (100–230/30–110/100–220), messages ("limiar acima da FC máxima"), formula-derived zone literals, `calls_made == 502` (+3 physio, spec/task-defined) are hand-written literals, not imported constants (L-001/L-002 followed in every new test file) |
| SPEC_DEVIATION marker judged | ✅ **Justified and factually verified** — `backend/app/garmin/client.py:183-192`: design/spec name `get_user_settings`, which does **not** exist in garminconnect 0.3.2; verified in the installed lib: `Garmin.get_lactate_threshold` exists (makes exactly 2 internal `connectapi` requests — power + HR — justifying the honest `self._calls += 1` at `client.py:199`) and the user-settings endpoint (`garmin_connect_user_settings_url`, docstring "Get all users settings", payload `userData`) is exposed as `get_user_profile`. The gateway method keeps the design name and delegates to the real lib function — endpoint, payload key (`userData.maxHeartRate`) and read-only posture are exactly as designed. The spec's assumption row already flagged this as "spike na implementação". No action needed |

---

## Edge Cases

- [x] `fclthr ≥ fcmax` → 422 "limiar acima da FC máxima": Handled — `backend/tests/test_hr_zones_service.py:249-252` (equality included) + API `backend/tests/test_hr_zones_api.py:181-182, 206`
- [x] Sync traz o MESMO valor → nenhuma linha (idempotente): Handled — `backend/tests/test_garmin_upserts.py:508-516` + end-to-end 2nd sync `backend/tests/test_garmin_service.py:736-741`
- [x] Mínimo-7d da fcrest muda entre syncs → linha nova registrando a evolução: Handled — `backend/tests/test_garmin_service.py:744-789` (42 → 40 → nothing); ⚠️ min-ness/window itself not discriminated (flagged at HRZ-05)
- [x] Muda só o método → métricas intactas; muda só percentual → método fica: Handled — `backend/tests/test_hr_zones_service.py:197-213` (`UserHrMetric` count 0) + `backend/tests/test_hr_zones_api.py:306-317` (bounds-only PUT inherits `lthr`)
- [x] Config manual + métrica garmin → séries independentes: Handled structurally — separate tables/series (`backend/tests/test_hr_zones_service.py:211-213` config writes leave metrics untouched; sync tests write only `user_hr_metrics`)
- [x] Zonas mudam → treinos passados NÃO reclassificados: Handled — `backend/tests/test_evaluation_payload.py:372-381, 431-445` (old activity read with old zones/lthr after later changes)
- [x] Método lthr, split com FC > Z4 → Z5 aberta: Handled — `backend/tests/test_hr_zones_calc.py:231-232` (`classify(220) == 5`, sem teto) + payload `:412-413` (hr 180 → Z5)
- [x] PUT altera valor E método na mesma chamada → mesmo `valid_from`: Handled — `backend/tests/test_hr_zones_api.py:320-342` (`metric.valid_from == config.valid_from == TODAY`)

---

## Gate Check

- **Gate command** (Build+Full, final — tasks.md §Gate Check Commands): `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build`
- **Result**: **493 passed, 0 failed, 0 skipped** (backend full suite on compose Postgres, 5:38; 1 pre-existing StarletteDeprecationWarning, no skips). Frontend: `npm run lint` clean (0 errors); `npm run build` compiled successfully — 11 routes including `/perfil`.
- **Test count before feature**: 427
- **Test count after feature**: 493
- **Delta**: +66 — new files `test_hr_zones_calc.py` (15), `test_hr_zones_models.py` (3), `test_hr_zones_service.py` (13), `test_hr_zones_api.py` (12) + extensions: `test_evaluation_payload.py` (+6), `test_garmin_gateway.py` (+4), `test_garmin_service.py` (+6), `test_garmin_upserts.py` (+6), `test_sync_api.py` (+1)
- **Skipped tests**: none
- **Failures**: none
- **Integrity check**: `git grep -c "def test_"` compared at `3a08443` vs `223e914` — every file's count is unchanged or increased (zero deletions); the only expected-value change in pre-existing tests is `calls_made` 499 → 502 (`test_garmin_service.py:135`, `test_sync_api.py:83`), which traces to the spec/task-defined +3 physio calls (1 settings + 2 internal LTHR), not to implementation convenience; assertions were added around those changes (physio rows, warnings, skip branches), never weakened.

---

## Fix Plans (if issues found)

None required. All mutants killed, all 19 ACs have evidence, gates green. Three dispositions for the orchestrator (documentation-level, no code change):

1. **HRZ-10 example values (Spec-internal discrepancy)** — amend the spec's Independent Test example `[115, 141, 156, 168, 177+]` (and the T2 done-when's `[115, 141, 158, 168, 177+]`) to the formula-correct `[115, 142, 158, 168, 177+]`, and optionally clarify AC-10's formula notation to `round(pct × fclthr / 100)` (pct in percentage points). Implementation and tests already follow the formula.
2. **HRZ-05 fcrest sub-clause (Test-precision gap)** — if 1:1 pinning of "mínimo dos últimos 7 dias" is wanted, one test with a non-uniform RHR week (e.g. values [50, 42, 48, 45, 47, 44, 46] → fcrest 42) would discriminate both the minimum and the window; current tests only prove the auto-update behavior.
3. **Runtime UAT** — the 3 items listed in the UAT section (first real sync spike, `/perfil` at 390px, manual-wins badge end-to-end).

---

## Requirement Traceability Update

Update spec.md requirement statuses:

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| HRZ-01 | ✅ Implemented | ✅ Verified |
| HRZ-02 | ✅ Implemented | ✅ Verified |
| HRZ-03 | ✅ Implemented | ✅ Verified |
| HRZ-04 | ✅ Implemented | ✅ Verified |
| HRZ-05 | ✅ Implemented | ✅ Verified (fcrest min-7d sub-clause implemented per spec but not test-discriminated — flagged) |
| HRZ-06 | ✅ Implemented | ✅ Verified |
| HRZ-07 | ✅ Implemented | ✅ Verified |
| HRZ-08 | ✅ Implemented | ✅ Verified |
| HRZ-09 | ✅ Implemented | ✅ Verified |
| HRZ-10 | ✅ Implemented | ✅ Verified (spec's illustrative example contradicts its own formula; implementation/tests follow the formula — flagged for spec amendment) |
| HRZ-11 | ✅ Implemented | ✅ Verified |
| HRZ-12 | ✅ Implemented | ✅ Verified (service + payload + tie-break) |
| HRZ-13 | ✅ Implemented | ✅ Verified (code + build; runtime rendering pending UAT) |
| HRZ-14 | ✅ Implemented | ✅ Verified (code + build; interactive behavior pending runtime UAT — no frontend test runner by project pattern) |
| HRZ-15 | ✅ Implemented | ✅ Verified (API exact; frontend rendering pending UAT) |
| HRZ-16 | ✅ Implemented | ✅ Verified (401 exact at API + proxy prefix; redirect pending UAT) |
| HRZ-17 | ✅ Implemented | ✅ Verified (both branches pinned) |
| HRZ-18 | ✅ Implemented | ✅ Verified (exact arithmetic + denominator + zonas da época) |
| HRZ-19 | ✅ Implemented | ✅ Verified (block omitted in all no-data branches) |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 19/19 ACs matched spec outcome with `file:line` evidence | 2 spec-precision gaps flagged (HRZ-05 fcrest min-7d sub-clause not test-discriminated; HRZ-10 illustrative example contradicts the normative formula — tests correctly follow the formula)
**Sensor**: 5/5 mutations killed (effective-dating boundary, tie-break, manual-wins, zone boundary, payload omission guard)
**Gate**: 493 passed (backend full suite, 0 failed, 0 skipped, +66 vs 427 pre-feature) + frontend lint clean + build OK (`/perfil` included)
**validate_state.py**: exit 0 — "validate_state: 0 error(s) across [hr-zones]" (run after this report was written)

**What works**:
- Effective-dated append-only series for the 3 physio metrics + zone configs, resolved by `(valid_from ≤ D, id DESC)` — old workouts are read with the zones of their date (service, payload lthr and zonas_fc all pinned)
- Manual-wins and idempotency live in one place (`set_metric`) and are inherited by the router PUT, the physio upsert and the sync phase — proven at every layer, and the sensor proves the tests bite
- Sync phase honest by construction: absent value skips silently, +3 counted calls, failure → warning + `done`; nothing is seeded except user 1's lthr config
- Evaluation payload consumes the profile honestly: `lthr_bpm` from the activity-date metric with env fallback, `zonas_fc` block only with real lap data, omitted otherwise
- All 8 spec edge cases have located test evidence; exact PT-BR 422 messages and spec literals asserted throughout (no constants shared with the implementation)

**Issues found**: none blocking. Flagged for the orchestrator: (1) spec's Independent Test example values inconsistent with its own formula (docs amendment); (2) fcrest min-7d sub-clause not discriminated by tests (optional 1-test hardening); (3) 3 runtime-UAT items pending (first real sync spike, 390px `/perfil`, manual-wins badge).

**Next steps**: orchestrator applies the traceability table to `spec.md`, optionally amends the HRZ-10 example + AC-10 notation, and schedules the runtime UAT (first real sync + mobile check). No fix tasks.
