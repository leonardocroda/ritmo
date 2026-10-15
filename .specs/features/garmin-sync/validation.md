# Sync do Garmin — Validation

**Date**: 2026-10-14
**Spec**: `.specs/features/garmin-sync/spec.md`
**Diff range**: `61729ce^..HEAD` (19 commits: T1–T15 + correções; 32 arquivos, +3903/−115)
**Verifier**: sub-agente independente (author ≠ verifier) — árvore real intacta; mutações só em scratch descartável

---

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 Models + constraints | ✅ Done | `personal_records`/`sync_state`/`uq_split_activity_idx`/índice parcial `uq_syncjobs_user_active` em `backend/app/db/models.py:74,253-259,277,291`; `test_health.py:42-43` estendido |
| T2 Config SYNC_* | ✅ Done | `config.py:38-43` + `.env.example:19-31`; 6 testes em `test_sync_config.py` |
| T3 Compose tokens/TZ/build arg | ✅ Done | `docker-compose.yml:30-33,43-45`; `frontend/Dockerfile:8-10`; `docker compose config -q` exit 0 |
| T4 GarminGateway | ✅ Done | `client.py` (173 linhas); 13 testes em `test_garmin_gateway.py` |
| T5 Mappers puros | ✅ Done | `mappers.py` (208 linhas); 20 testes em `test_garmin_mappers.py`; fixtures reais T15 em `helpers.py:81-93,172-186,219-238` |
| T6 Upserts idempotentes | ✅ Done | `upserts.py` (126 linhas); 13 testes em `test_garmin_upserts.py` (Postgres real) |
| T7 PMC determinística | ✅ Done | `pmc.py` (102 linhas); 8 testes em `test_garmin_pmc.py` vs cálculo manual independente |
| T8 Orquestrador | ✅ Done | `service.py` (369 linhas); 14 testes em `test_garmin_service.py` com FakeGateway |
| T9 Recovery no startup | ✅ Done | `main.py:26` + `service.py:353-369`; 2 testes (`test_garmin_service.py:455,474`) |
| T10 Endpoints de sync | ✅ Done | `router.py` montado em `main.py:45`; 8 testes em `test_sync_api.py` |
| T11 api.ts | ✅ Done | `frontend/src/lib/api.ts:5,61-74`; build/lint exit 0 |
| T12 SyncButton | ✅ Done | `frontend/src/components/SyncButton.tsx` (125 linhas); build/lint exit 0 |
| T13 Header global | ✅ Done | `Header.tsx:7-18` montado em `layout.tsx:36`; build/lint exit 0 |
| T14 CLI login | ✅ Done | `login.py`; 4 testes em `test_garmin_login.py` com lib stubada |
| T15 Sync real + docs | ✅ Done | `README.md:80-134` documenta validação real (14/10/2026): backfill 232 atividades/1563 splits/60–61d saúde/7 recordes, `calls_made` 408 em 606s; incremental 23 chamadas; PMC 3 dias vs manual; token inválido → `error`+`reauth_needed` |

---

## Spec-Anchored Acceptance Criteria

Valores afirmados nos testes conferem com os literais do spec (lição L-001: nenhum teste importa constante da implementação — verificados por leitura integral; o cálculo manual do PMC é reimplementado no próprio teste).

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| SYNC-01: POST cria job `pending`, 201 com id, sync em background | HTTP 201 + `{id, status}` + BackgroundTasks | `backend/tests/test_sync_api.py:58` — `assert response.status_code == 201`; `:60` — `assert body["status"] == "pending"`; `:65` — `job["status"] == "done"` (task de fundo executou); wiring `router.py:80` — `background_tasks.add_task(run_sync, job.id)` | ✅ PASS |
| SYNC-02: 409 se job ativo, com estado do corrente (id, status, started_at) | HTTP 409 + id/status/started_at | `test_sync_api.py:85` — `assert response.status_code == 409`; `:87-89` — `detail["id"] == active_id`, `detail["status"] == "running"`, `detail["started_at"] == "2026-10-14T12:00:00"`; service `test_garmin_service.py:91` — `pytest.raises(JobConflictError)`; índice parcial sem race: `models.py:253-259` | ✅ PASS |
| SYNC-03: chamadas exclusivamente em sequência, pausa `SYNC_CALL_INTERVAL_S` (default 1,0s) | 1 contagem + 1 sleep de 1,0s por chamada | `test_garmin_gateway.py:139-140` — `gateway.calls_made == 1`, `sleeps == [1.0]`; `:150-151` — sequência de 3: `sleeps == [1.0, 1.0, 1.0]`; default literal `test_sync_config.py:44` — `settings.sync_call_interval_s == 1.0` | ✅ PASS |
| SYNC-04: `pending → running` (+started_at) → `done\|error` (+finished_at); fora disso proibido | started_at/finished_at gravados; transição inválida levanta | `test_garmin_service.py:244-246` — snapshot running: `started_at is not None`, `finished_at is None`; `:253-255` — done com `finished_at >= started_at`; `:264` — `pytest.raises(RuntimeError, match="Transição inválida")` + `:267-269` job preservado | ✅ PASS |
| SYNC-05: contadores parciais em `stats_json` via `GET /jobs/{id}` e `/jobs/latest` | stats visíveis durante running | `test_garmin_service.py:450-452` — mid-run: `captured[0]["step"] == "hrv"`, `hrv_days == 4`, `message == "Puxando HRV: 4 dias…"`; `:247-249` — `message == "Puxando 12 atividades…"`, `activities_new == 0`; serialização exata dos GETs: `test_sync_api.py:123-124` — `set(job["stats"].keys()) == STATS_KEYS` (composição: TestClient roda background de forma síncrona — limitação documentada no design) | ✅ PASS |
| SYNC-06: stats finais por tipo + chamadas + duração | 11 contadores do schema do design | `test_garmin_service.py:110-122` — `activities_new == 12`, `activities_updated == 0`, `splits == 20`, `sleep_days == 61`, `hrv_days == 61`, `rhr_days == 61`, `battery_days == 61`, `stress_days == 61`, `records == 2`, `calls_made == 258`, `duration_s >= 0`, `warnings == []`, `reauth_needed is False`; schema exato `test_sync_api.py:23-39,124` | ✅ PASS |
| SYNC-07: 429/transitório → até 3 retries com backoff 2s/4s/8s | backoff exato 2/4/8; sucesso dorme intervalo | `test_garmin_gateway.py:166` — `sleeps == [2, 4, 1.0]` (2 falhas + sucesso); `:175-176` — esgota: `calls_made == 4`, `sleeps == [2, 4, 8]`; `:185-186` — connection error retryable `sleeps == [2, 1.0]`; `:195-196` — auth NÃO retenta (`calls_made == 1`, `sleeps == []`) | ✅ PASS |
| SYNC-08: UI desabilita botão, exibe progresso; resumo/erro ao final | botão disabled durante pending\|running; `stats.message`; resumo dos contadores | `frontend/src/components/SyncButton.tsx:38` — `active = status === "pending" \|\| "running"`; `:86` — `disabled={active}`; `:93` — `stats?.message` no botão; resumo `:20-32` (`summarize`); progresso real T15: `README.md:95-97` ("Puxando 231 atividades…"); gates: `npm run build` exit 0 + `npm run lint` exit 0. **Nota de matriz**: frontend sem asserção automatizada (decisão da Test Coverage Matrix: build+lint+UAT) | ✅ PASS (per matriz) |
| SYNC-09: teto `SYNC_MAX_CALLS` (1500) → error com stats das chamadas feitas | bloqueio ANTES da chamada; job error + stats | `test_garmin_gateway.py:205-208` — `SyncBudgetExceededError` + `fake.calls.get("get_rhr_day") == []` (API nem chamada); service `test_garmin_service.py:394-403` — `status == "error"`, `calls_made == 196`, tipos concluídos antes ficam (`Sleep == 61`), `sync_state` do tipo interrompido é `None`; default 1500: `test_sync_config.py:50` | ✅ PASS |
| SYNC-10: janela `last_sync_activities − SYNC_REPULL_DAYS` (ou backfill) | início = last − 3d literal | `test_garmin_service.py:197` — `fake.calls["activities"] == [(REPULL_START, TODAY)]` com `REPULL_START = date(2026, 10, 11)` (`:41`, TODAY − 3d) | ✅ PASS |
| SYNC-11: upsert por `garmin_id` e splits por `(activity_id, idx)`; 2× sem duplicatas | contagens estáveis; "new"/"updated" | `test_garmin_upserts.py:107` — 2ª retorna `"updated"`, `:110` — `_count == 1`; splits `:140-147` — 2× → 2 linhas, `idxs == [1, 2]`; end-to-end `test_garmin_service.py:171` — `_table_counts(s) == counts_after_first` (todas as 10 tabelas) | ✅ PASS |
| SYNC-12: splits só para corrida (1 chamada/corrida); não-corrida sem chamada | corridas pedem splits; cycling não | `test_garmin_service.py:127` — `len(split_ids) == 11`; `:128` — `CYCLING_ID not in split_ids`; `test_garmin_mappers.py:93-94,98-99` — `is_running(...) is True/False` para running/trail/cycling/yoga | ✅ PASS |
| SYNC-13: `last_sync_activities` atualizado ao concluir tipo | sync_state == fim da janela | `test_garmin_service.py:155-156` — `get_sync_state(s, 1, "activities") == TODAY` (+ 5 tipos); falha não avança: `:298` — `is None`; unidade `test_garmin_upserts.py:311` | ✅ PASS |
| SYNC-14: falha de atividades após retries → job error com mensagem, nada parcial | status error + mensagem + zero gravado | `test_garmin_service.py:285-298` — `status == "error"`, `error == "atividades indisponíveis (retries esgotados)"`, `activities == 0`, `splits == 0`, `sleep == 0` (fases seguintes nem rodaram), `sync_state is None`; API `test_sync_api.py:141-144` | ✅ PASS |
| SYNC-15: sem last_sync → backfill 180d atividades / 60d saúde | janelas literais 180/60 | `test_garmin_service.py:189` — `fake.calls["activities"] == [(date(2026, 4, 17), TODAY)]` (TODAY − 180d); `:190-192` — sleep 61 dias desde `date(2026, 8, 15)` (TODAY − 60d), battery 1 range; defaults `test_sync_config.py:37-38` — `== 180`, `== 60` | ✅ PASS |
| SYNC-16: recordes em todo sync (1 chamada), upsert `(user_id, evento)`, independente de janela | filtro corrida + upsert por evento | `test_garmin_mappers.py:216-222` — só `[FASTEST_5K, LONGEST_RUN]` (typeId 8 cycling filtrado), value/pr_date/raw_json; `test_garmin_upserts.py:277-300` — 2× estável, PR batido atualiza (`value == 1150.0`, 1 linha por evento); fase roda em todo sync (happy path `records == 2` + idempotência 2× estável) | ✅ PASS |
| SYNC-17: `calls_made` em stats_json para auditoria | contagem de chamadas presente e correta | `test_garmin_service.py:119` — `stats["calls_made"] == 258`; `:214-215` — backfill 258 vs incremental 22; schema `test_sync_api.py:35`; real: `README.md:96-97` (408 → 23) | ✅ PASS |
| SYNC-18: re-pull `SYNC_REPULL_DAYS` (3) por dia por tipo + battery 1 range; upsert `(user_id, date)` | 4 dias por tipo incremental; 1 range battery | `test_garmin_service.py:198-202` — `fake.calls["hrv"] == [(REPULL_START + i,) for i in range(4)]`, `len(stress) == 4`, `battery == [(REPULL_START, TODAY)]`; upsert `test_garmin_upserts.py:222-231` — 2 datas 2× → 2 linhas; `:234-246` — mesma data atualiza | ✅ PASS |
| SYNC-19: dia vazio/None → skip sem erro e sem linha | pular silencioso | `test_garmin_service.py:419-427` — `hrv_days == 60`, sem linha em `2026-10-13`, `warnings == []`, `sync_state == TODAY` (tipo conclui); mappers: `test_garmin_mappers.py:156-158,168-170,181-183,192-193,209-210` | ✅ PASS |
| SYNC-20: tipo de saúde falha → demais concluem, `done` + `warnings: [{tipo, erro}]` | warning exato e continuidade | `test_garmin_service.py:314-330` — `status == "done"`, `warnings == [{"tipo": "sleep", "erro": "sleep fora do ar"}]`, demais `== 61`, PMC roda (`DailyLoad == 12`); recordes idem `:348-353` | ✅ PASS |
| SYNC-21: `last_sync_<tipo>` atualizado por tipo concluído | por tipo, só em sucesso | `test_garmin_service.py:155-156` — 6 tipos `== TODAY`; `:328-329` — falha: `sleep is None`, `hrv == TODAY`; unidade `test_garmin_upserts.py:311-313,322-328` | ✅ PASS |
| SYNC-22: CTL = EWMA α=1/42, ATL = EWMA α=1/7, TSB = CTL−ATL, ACWR = soma(7d)/(soma(28d)/4) | fórmulas exatas do spec | `test_garmin_pmc.py:109-114` — comparação com `_manual_pmc` (implementação independente no teste, `:42-58`); âncoras literais `:117-122` — `ctl == 100.0`, `atl == 100.0`, `tsb == 0.0`, `rows[1].ctl == approx(100 - 20/42)`, `atl == approx(100 - 20/7)`, `tsb == approx(100/42)`; ACWR `:138-145` — `rows[26].acwr is None`, `rows[27] == approx(350/(1400/4))`, pico `== approx(500/387.5)` | ✅ PASS |
| SYNC-23: recompute só do dia mais antigo alterado até hoje; histórico preservado | linhas anteriores intocadas; semente da última linha anterior | `test_garmin_pmc.py:167-187` — `recompute(..., date(2024,1,4), ...) == 2`; `:171` — `[(r.id, r.ctl, r.atl, r.tsb) for r in second_run[:3]] == untouched`; semente conferida à mão `:175-184`; valores idênticos à 1ª execução `:186-187` | ✅ PASS |
| SYNC-24: atividade sem `training_load` → carga 0 no dia | dia conta 0, não some o dia | `test_garmin_pmc.py:88` — `aggregate_daily_loads == [(...), (date(2024,1,1), 0.0), (date(2024,1,2), 30.0)]`; no fluxo: esteira sem load no happy path (`test_garmin_service.py:140`, `load == 12` linhas) | ✅ PASS |
| SYNC-25: login/401 → job `error`, mensagem no `error`, `reauth_needed: true` | error + reauth sem retry, banco intacto | gateway `test_garmin_gateway.py:130` — `pytest.raises(GarminAuthExpiredError)`; `:193-196` — em chamada de dados: sem retry, sem sleep; service `test_garmin_service.py:369-378` — `status == "error"`, `reauth_needed is True`, `calls_made == 0`, todas as tabelas 0; API `test_sync_api.py:159-161` — `stats["reauth_needed"] is True`; real: `README.md:98` (tokenstore inválido end-to-end) | ✅ PASS |
| SYNC-26: UI exibe "Reconectar Garmin" + comando CLI no lugar do resumo | estado reauth com instrução | `frontend/src/components/SyncButton.tsx:40` — `reauth = status === "error" && stats?.reauth_needed`; `:101-107` — renderiza `Reconectar Garmin: rode python -m app.garmin.login e clique de novo` no lugar do resumo; build/lint exit 0; UAT real T15 (`README.md:98,103-110`). **Nota de matriz**: sem asserção automatizada (build+UAT per matriz) | ✅ PASS (per matriz) |
| SYNC-27: renovar tokens → retoma incremental, sem backfill | 2º sync usa last−3d, não backfill; sync_state sobrevive à falha | `test_garmin_service.py:197` — 2º sync pede `(REPULL_START, TODAY)`; `:214-215` — `calls_made` 258 → 22 (sem backfill); `:378` — auth falha antes de qualquer fase: `sync_state == 0` linhas (preservado); real: `README.md:96-97,112` (408 → 23 após renovação). Cenário encadeado coberto por composição + UAT real, não por um único teste encadeado | ✅ PASS |

**Status**: ✅ 27/27 ACs com evidência `file:line` + asserção ancorada no literal do spec. 1 spec-precision gap registrado (Success Criteria "≤ ~20 chamadas steady-state" — ver Gaps Ranqueados).

---

## Discrimination Sensor

**Tier**: expandido (pipeline central do MVP) — 14 mutações comportamentais nos 6 pontos de risco (a)–(f).
**Scratch**: cópia de `backend/` em `%TEMP%\opencode\sensor-garmin`, rodando com o venv existente (`backend/.venv`) apontado para a cópia (probe confirmou `app.__file__` no scratch). Controle não-mutado passou antes da 1ª mutação. Nenhuma mutação tocou a árvore real — `git status --porcelain` vazio antes e depois.

| # | Mutante | file:line (scratch) | Descrição | Alvo | Morto? |
| - | ------- | ------------------- | --------- | ----- | ------ |
| M1 | (a) dedup atividade | `upserts.py:43` | `if activity is None:` → `if True:` (sempre insere) | `test_garmin_upserts.py::test_upsert_activity_rerun_is_idempotent` | ✅ Killed (`UniqueViolation` em `garmin_id`) |
| M2 | (a) dedup saúde | `upserts.py:79` | select por `(user_id, date)` removido (`existing = None`) | `::test_upsert_health_rows_sleep_by_user_date` | ✅ Killed (`IntegrityError` `(user_id, date)`) |
| M3 | (a) prune de splits | `upserts.py:58` | `DELETE idx >= len(rows)` removido | `::test_upsert_splits_prunes_rows_beyond_new_length` + `::test_upsert_splits_empty_rows_prune_all` | ✅ Killed (2 testes falham) |
| M4 | (b) α do CTL | `pmc.py:18` | `CTL_ALPHA = 1/42` → `1/7` | `test_garmin_pmc.py` (3 dias vs manual) | ✅ Killed (3 testes falham vs cálculo manual) |
| M5 | (b) janela ACWR | `pmc.py:87` | `offset >= 27` → `>= 26` (off-by-one) | `::test_recompute_acwr_from_complete_28d_window` | ✅ Killed (fronteira exata dos 28d) |
| M6 | (c) backoff | `client.py:31` | `(2, 4, 8)` → `(2, 4, 4)` | `test_garmin_gateway.py::test_retry_exhausted_after_3_retries_raises_last` | ✅ Killed (`sleeps == [2,4,8]` literal) |
| M7 | (c) teto | `client.py:85` | `>= sync_max_calls` → `>` (1 chamada acima passa) | `::test_budget_ceiling_blocks_before_call` | ✅ Killed (DID NOT RAISE) |
| M8 | (c) fatia battery | `client.py:161` | bloco de 28d → 29d | `::test_get_battery_chunks_range_over_28_days` | ✅ Killed (ranges exatos afirmados) |
| M9 | (c) intervalo | `client.py:103` | `sleep(SYNC_CALL_INTERVAL_S)` removido no sucesso | `::test_call_counts_and_sleeps_interval` + `::test_sequential_calls_each_count_and_sleep` | ✅ Killed (2 testes falham) |
| M10 | (d) máquina de estados | `service.py:73` | guarda de transição inválida removida | `test_garmin_service.py::test_invalid_transition_raises` | ✅ Killed (DID NOT RAISE `RuntimeError`) |
| M11 | (e) política de erros | `service.py:226` | warning de tipo de saúde → `raise` (crash) | `::test_health_type_failure_warns_and_continues` | ✅ Killed (deixa de ser `done`+warnings) |
| M12 | (e) reauth_needed | `service.py:342` | `stats["reauth_needed"] = True` removido | `::test_auth_expired_error_reauth_needed` + `test_sync_api.py::test_reauth_error_exposed_via_api` | ✅ Killed (2 níveis falham) |
| M13 | (f) splits p/ tudo | `service.py:172` | `if is_running(raw):` → `if True:` | `::test_run_sync_happy_path_done_with_full_stats` | ✅ Killed (`CYCLING_ID` pede splits; contadores mudam) |
| M14 | (d) recovery startup | `service.py:362` | filtro `("pending","running")` → `("pending",)` | `::test_startup_recovers_orphan_running_job` | ✅ Killed (órfão running não recuperado) |

**Result**: **14/14 killed, 0 sobreviventes** — PASS ✅. Os testes discriminam dedup, EWMA/ACWR, backoff/teto/intervalo/fatia, máquina de estados + recovery, política de erros + reauth e splits-só-corrida.

---

## Edge Cases

- [x] Atividade editada no re-pull → upsert atualiza campos: `test_garmin_upserts.py:121-129` — `distance_m == 5500.0`, `name == "Morning Run (edited)"`, count 1
- [x] Esteira sem GPS → atividade válida sem splits: `test_garmin_mappers.py:130-135` (vazio → `[]` sem warning, `warnings.simplefilter("error")`); `test_garmin_upserts.py:185-190` (prune-all); `test_garmin_service.py:146-151` (treadmill com 0 splits no fluxo)
- [x] Datas de calendário sem conversão: `test_garmin_mappers.py:48` — `start_time == datetime(2024,1,15,7,0)` do literal local; `:149-150` — GMT ms → naive UTC sem conversão
- [x] `get_activity_splits` vazio → sem warning: `test_garmin_mappers.py:130-135` (4 variantes de vazio com warnings como erro)
- [x] API muda endpoint → job error, banco com último estado bom: `test_garmin_service.py:285-298` (nada parcial) + `:394-403` (tipos concluídos antes do teto ficam)
- [x] Dois cliques quase simultâneos → um job, segundo 409: índice parcial `models.py:253-259` (sem janela de corrida check→insert) exercitado em `test_sync_api.py:75-89`

---

## Gate Check

- **Gate command**: `cd backend; uv run pytest` · `docker compose config -q` · `cd frontend; npm run build; npm run lint`
- **Backend**: **97 passed, 0 failed, 0 skipped** (109.91s, exit 0; 1 warning pré-existente `StarletteDeprecationWarning` do TestClient, não relacionado à feature)
- **Compose**: `docker compose config -q` → exit 0
- **Frontend**: `npm run build` exit 0 (Next.js 16.4.0) · `npm run lint` exit 0
- **Test count before feature**: 9 (test_health 3 + test_infra 6)
- **Test count after feature**: 97 (+88 = gateway 13 + mappers 20 + upserts 13 + pmc 8 + service 16 + sync_api 8 + config 6 + login 4)
- **Delta**: +88 novos; nenhum teste deletado (test_health só cresceu a asserção do schema, per T1)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ diff exatamente na superfície planejada; nada além |
| Surgical changes / só arquivos da task | ✅ 32 arquivos, todos mapeados a T1–T15 |
| No scope creep | ✅ out-of-scope do spec respeitado (sem race predictions, sem espelho de exclusão, sem auth web) |
| Matches patterns | ✅ docstrings PT-BR, estilo das camadas existentes, SQLAlchemy 2.x |
| Spec-anchored outcome check | ✅ valores afirmados = literais do spec (L-001); PMC vs cálculo manual independente reimplementado no teste |
| Per-layer Coverage Expectation | ✅ domínio 1:1 com ACs; rotas happy+edge+error (201/409/404/null/reauth); integração no Postgres real |
| Every test maps to a requirement | ✅ cada teste cita SYNC-NN/done-when no docstring; `test_infra.py` (6) é pré-existente (critérios INFRA-xx) |
| Documented guidelines followed | ✅ `README.md` §Testes (uv+postgres), `frontend/AGENTS.md` (Next 16.4.0 — `layout.tsx:29` usa `LayoutProps<"/">` da versão), L-001 aplicada |

---

## Success Criteria

- [x] Tokens válidos terminam `done`, zero chamadas paralelas — provado em teste (M9 do sensor: sem sleep, 2 testes falham) e na execução real (408 chamadas em 606s ≈ 1/s, `README.md:96`)
- [⚠️] Steady-state ≤ ~20 chamadas — **medido 23 (real) / 22 (fake)**: ver Gaps Ranqueados #1
- [x] Sync 2× idempotente — `test_garmin_service.py:171` (todas as 10 tabelas) + real ("contagens idênticas", README)
- [x] Banco vazio → ~180d atividades, 60d saúde, recordes — `test_garmin_service.py:189-192` + real (232 atividades, 60–61d, 7 recordes)
- [x] Token inválido → `error` + `reauth_needed`, UI clara, banco intacto; renovar retoma incremental — testes (`:369-378`, `:197`, `:378`) + real end-to-end (README)
- [x] `user_id` em toda escrita + config 100% env — `test_garmin_upserts.py:93,151,229,286` (`user_id == 1`); `test_sync_config.py:59-73` (overrides)

---

## Fix Plans

Nenhum fix bloqueante. Dois follow-ups não-bloqueantes:

### Follow-up 1: precisão do orçamento de steady-state (spec-precision gap)

- **Root cause**: Success Criteria usa "~15–20 / ≤ ~20" (estimativa com til) enquanto a fórmula real do incremental é determinística: 1 atividades + 4 tipos × 3 dias + 1 battery + 1 recordes + splits das corridas da janela ≈ 18–23. Medido 23. Nenhum SYNC-NN pina contagem de steady-state; o guard rail (`SYNC_MAX_CALLS=1500`) e a sequência estão íntegros e testados.
- **Fix task**: na próxima revisão do spec, trocar o "~" por um teto mensurável (ex.: "≤ 30 chamadas em janela de 3d, auditável via `calls_made`") ou mover a estimativa para nota informativa.
- **Priority**: Minor

### Follow-up 2: nota de cobertura de UI (sem ação imediata)

- A matriz definiu frontend = build + lint + UAT. SYNC-08/SYNC-26 têm implementação verificada por leitura + gates verdes + UAT real documentado, mas nenhuma asserção automatizada. Quando a Fase 1 adicionar infra de teste frontend (ex.: Playwright), cobrir os 5 estados do SyncButton.

---

## Requirement Traceability Update

27/27 SYNC-NN verificados com evidência. O Verifier não altera `spec.md` (restrição de escrita desta validação) — statuses `Implementing → Verified` devem ser atualizados pelo orchestrator ao aceitar este veredito.

---

## Gaps Ranqueados

1. **⚠️ Spec-precision gap (único sinal)**: Success Criteria "steady-state ≤ ~20 chamadas" — real mediu 23 (fake: 22). Nenhuma violação de AC (nenhum SYNC-NN pina esse número; teto 1500 intacto; sequência+intervalo provados por teste e por mutação). A estimativa "~15–20" do Goal nunca foi revisitada quando a fórmula do incremental ficou conhecida. → 1 lição destilada.
2. **Nota, sem ação**: UI (SYNC-08/26) coberta por decisão da matriz (build+lint+UAT), sem teste automatizado — verificado com honestidade, não é gap de implementação.
3. **Nota, sem ação**: SYNC-27 (retomada pós-reauth) coberto por composição (janela incremental + `sync_state` preservado na falha de auth) + UAT real 408→23, sem um único teste encadeado.

---

## Summary

**Overall**: ✅ PASS — Ready

**Spec-anchored check**: 27/27 ACs com `file:line` + asserção conferida ao literal do spec; 6/6 edge cases; 1 spec-precision gap flagado (não bloqueante)
**Sensor**: 14/14 mutações mortas, 0 sobreviventes (tier expandido; scratch isolado; porcelain limpo antes/depois)
**Gate**: 97 passed / 0 failed / 0 skipped · compose config exit 0 · frontend build+lint exit 0
**Test integrity**: 9 → 97 (+88), nenhum teste deletado, nenhuma asserção enfraquecida (test_health só cresceu)

**What works**: pipeline completo end-to-end (job → gateway sequencial → mappers → upserts idempotentes → PMC → stats → API → UI), validado por 97 testes ancorados em literais, 14 mutações mortas e 3 execuções reais documentadas (backfill 408 → incremental 23, zero duplicatas, reauth end-to-end).

**Issues found**: apenas o gap de precisão do spec (Follow-up 1) — nenhuma correção de código exigida.

**Next steps**: orchestrator atualiza statuses do spec.md para Verified; spec ganha teto mensurável de chamadas na próxima revisão; considerar Playwright quando os painéis da Fase 1 entrarem.
