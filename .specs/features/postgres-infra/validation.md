# postgres-infra Validation

**Date**: 2026-10-14 (re-verify iteration 1/3 after Fix 1, commit `90d1363`)
**Spec**: `.specs/features/postgres-infra/spec.md`
**Diff range**: `2d97924^..90d1363` (8 task commits + 1 fix commit, verified: HEAD == 90d1363)
**Verifier**: independent sub-agent (author ≠ verifier), read-only over the real tree; sensor mutations in a disposable worktree only

**Verdict: PASS** — the single gap from iteration 0 (INFRA-06 circular assertion, mutant M2 survived) is closed by `90d1363`: the test now pins the spec-defined literal. Gate 9/9, 9/9 ACs spec-anchored with evidence, 3/3 mutants killed (M2 re-killed independently by this Verifier).

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | psycopg[binary] in `backend/pyproject.toml:21` + `backend/uv.lock:515,845`; default `database_url` is `postgresql+psycopg://` (`backend/app/core/config.py:25`); 2 new tests; gate recorded 5/5 |
| T2 | ✅ Done | sqlite branch (`check_same_thread`, WAL/foreign_keys pragmas, `event` import) removed from `backend/app/db/engine.py`; diff is pure dead-code removal; no sqlite/PRAGMA left (grep: zero in backend code) |
| T3 | ✅ Done | compose postgres:16 + healthcheck + volume + init script; recorded: config OK, healthy, `ritmo`/`ritmo_test` via psql |
| T4 | ✅ Done | conftest → `ritmo_test`, autouse clean-state fixture, fail-fast helper; 4 new tests; recorded gate 9/9 in 9.62s + stopped-postgres demo (RuntimeError with hint, 3s cap) |
| T5 | ✅ Done | backend container; `depends_on: service_healthy`; recorded health 200 `{"status":"ok"}` |
| T6 | ✅ Done | frontend standalone container; recorded `server.js` build evidence, lint OK, HTTP/1.1 200 on :3000 |
| T7 | ✅ Done | `.env.example:8` postgres URL (no sqlite); README covers first up / dev diário / pytest / override de porta |
| T8 | ✅ Done | recorded E2E: `down -v` → `up -d --build` healthy; curls 200; 9/9 tests; volume persistence `SELECT count(*) FROM users` → 1 |

All 8 tasks done; no blocked/partial. Re-verify iteration 1: fix commit `90d1363` ("fix(tests): pin literal postgres startup hint in fail-fast assertion") fecha o gap de INFRA-06 encontrado na iteração 0 — não é um novo task, é a roteação do Fix 1 do ciclo fix→re-verify.

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| INFRA-01: WHEN `docker compose up -d` THEN 3 services up, backend waits for postgres healthcheck (`pg_isready`, `service_healthy`) | postgres+backend+frontend; backend start gated on `service_healthy` | `docker-compose.yml:17-21` - `test: ["CMD-SHELL", "pg_isready -U ritmo -d ritmo"]`; `docker-compose.yml:30-32` - `depends_on: postgres: condition: service_healthy`; live: `docker compose config -q` exit 0, `docker compose ps` → 3 Up, postgres `(healthy)`; recorded T5/T8 gate evidence | ✅ PASS (config + live stack + recorded build gate; layer declared "Tests: none, build gate decides" in the approved matrix) |
| INFRA-02: WHEN stack up THEN `GET /api/health` 200 em :8000 e frontend 200 em :3000 | HTTP 200 both ports | `backend/tests/test_health.py:15-18` - `assert response.status_code == 200` + `body["status"] == "ok"` (runs on Postgres via conftest); live: `curl -fsS localhost:8000/api/health` → 200 `{"status":"ok","app":"Ritmo","env":"dev"}`; `curl -fsSI localhost:3000` → `HTTP/1.1 200 OK` | ✅ PASS |
| INFRA-03: SHALL conectar exclusivamente pela env `DATABASE_URL` (nenhuma URL/credencial no código) | connection driven by env; env override wins; default is postgres, sem `sqlite://` | `backend/tests/test_infra.py:21-22` - `assert settings.database_url.startswith("postgresql+psycopg://")`, `assert "sqlite" not in settings.database_url`; `backend/tests/test_infra.py:30` - `assert settings.database_url == override` (env wins); `backend/app/db/engine.py:17` - `create_engine(settings.database_url)`; `backend/Dockerfile:1-19` has no DB URL; `docker-compose.yml:27` injects it via `environment` | ✅ PASS, nuance below |
| INFRA-04: WHEN backend inicia THEN create_all + seed do usuário default no Postgres | schema criado + usuário default semeado | `backend/app/db/engine.py:36` - `Base.metadata.create_all(bind=engine)`; `backend/app/db/engine.py:38-41` - seed `User(id=DEFAULT_USER_ID)`; `backend/tests/test_health.py:43` - 15 tabelas `assert expected <= table_names`; `backend/tests/test_health.py:50-52` - `assert user.display_name == "Leonardo"`; live: dev DB `SELECT count(*) FROM users` → 1 | ✅ PASS |
| INFRA-05: WHEN pytest roda THEN executa contra `ritmo_test` com estado limpo por teste | banco `ritmo_test`; nenhum teste enxerga dados de outro | `backend/tests/conftest.py:10` - `TEST_DATABASE_URL = "postgresql+psycopg://...localhost:5432/ritmo_test"`; `backend/tests/conftest.py:30` - `Base.metadata.drop_all(bind=engine)` (autouse); par de isolamento: `backend/tests/test_infra.py:46` - `assert ... == [DEFAULT_USER_ID, 42]` (sujou) e `backend/tests/test_infra.py:53` - `assert ... == [DEFAULT_USER_ID]` (limpo) | ✅ PASS (mutante M1 morto exatamente aqui) |
| INFRA-06: IF Postgres inacessível THEN pytest falha imediatamente com mensagem instruindo `docker compose up -d postgres` | RuntimeError imediata citando o comando literal | `backend/tests/test_infra.py:65` - `assert "docker compose up -d postgres" in str(exc_info.value)` (literal pinado pelo spec; fix `90d1363` também removeu o import da constante, `:14`); implementação: `backend/tests/helpers.py:5` - hint correto, `backend/tests/helpers.py:26-29` - RuntimeError com hint, `:9` teto de 3s; `backend/tests/conftest.py:16` - probe no import (fail antes de qualquer teste) | ✅ PASS (mutante M2 morto na re-verificação — ver sensor) |
| INFRA-07: WHEN postgres inicia pela 1ª vez THEN init cria `ritmo_test` além do `ritmo` | `CREATE DATABASE ritmo_test` no init | `docker/postgres/init/01-create-test-db.sql:3` - `CREATE DATABASE ritmo_test;`; montado em `docker-compose.yml:16` (`/docker-entrypoint-initdb.d:ro`); live read-only: `psql` lista `ritmo` e `ritmo_test`; recorded T3 `\l` evidence | ✅ PASS (config + live DB list; build gate decides, per matrix) |
| INFRA-08: SHALL persistir dados em volume nomeado (`down` sem `-v` preserva) | volume nomeado preserva schema + seed | `docker-compose.yml:15` - `postgres-data:/var/lib/postgresql/data`; `docker-compose.yml:43-44` - declaração do volume; live: volume `ritmo_postgres-data` existe, dev DB com 1 usuário; recorded T8: `down && up` → schema + usuário default preservados (`SELECT count(*) FROM users` → 1) | ✅ PASS (evidência de gate registrada + volume vivo; re-execução de down/up proibida a este Verifier — stack não pode ser reiniciada) |
| INFRA-09: SHALL usar psycopg3 (`postgresql+psycopg://`), zero código SQLite no engine | dialeto postgres único caminho | `backend/tests/test_infra.py:37` - `assert engine.url.drivername == "postgresql+psycopg"`; `backend/pyproject.toml:21` - `psycopg[binary]>=3.3.6` (`uv.lock:515,829,845`); engine sem sqlite/PRAGMA/`check_same_thread` (diff = remoção; grep: zero `sqlite://` no repo); `backend/app/core/config.py:25` default postgres | ✅ PASS (mutante M3 morto) |

**INFRA-03 nuance** (documented, not a gap): `config.py:25`'s default contains the dev URL `ritmo:ritmo@localhost:5432/ritmo` in code. The spec's own assumptions table declares `ritmo:ritmo` dev-only, not a secret; approved T1 and the Test Coverage Matrix explicitly require this exact default; the success criterion bans only `sqlite://` (repo-wide grep: zero). Env override governs the connection (`test_infra.py:30`). Judged PASS per the approved interpretation.

**Status**: ✅ All ACs covered — o gap de INFRA-06 da iteração 0 foi fechado por `90d1363`: a asserção agora mira o literal do spec e o mutante M2 morre.

---

## Discrimination Sensor

Iteration 0 (at `44b9848`): scratch `git worktree add %TEMP%\opencode\pginfra-sensor HEAD`, mutated there, `uv run pytest` from the scratch backend, removed with `git worktree remove --force`. Real-tree porcelain before AND after: empty (identical). No `git stash` used.

Re-verify iteration 1 (at `90d1363`): same discipline, scratch `%TEMP%\opencode\pginfra-reverify`; porcelain before/after: apenas os 3 artefatos deste Verifier (`.specs/LESSONS.md`, `.specs/lessons.json`, `validation.md`) — idêntico.

| Mutation | File:line | Description | Killed? |
| -------- | --------- | ----------- | ------- |
| M1 | `backend/tests/conftest.py:30` | Removed required side effect `Base.metadata.drop_all(bind=engine)` from the autouse clean-state fixture | ✅ Killed — `test_clean_state_sees_only_seed` fails: `assert [1, 42] == [1]` (`test_infra.py:53`) |
| M2 | `backend/tests/helpers.py:5` | `POSTGRES_UP_HINT` flipado para instrução errada (viola INFRA-06: mensagem deixa de instruir `docker compose up -d postgres`) | ✅ Killed na re-verify (iteração 0: ❌ Survived em `44b9848` com a asserção circular `POSTGRES_UP_HINT in str(...)`; fix `90d1363` pinou o literal) |
| M3 | `backend/app/core/config.py:25` | Default `database_url` → `"sqlite:///./ritmo.db"` (regressão ao default SQLite) | ✅ Killed — `test_default_database_url_is_postgres` falha em `test_infra.py:21` (`startswith("postgresql+psycopg://")`) |

**M2 re-kill evidence (dupla, independente)**:
- Orchestrator (scratch em `90d1363`): hint → `"sudo reboot now"` → teste falha; porcelain limpo antes/depois.
- Este Verifier (scratch próprio em `90d1363`, hint → `"sudo reboot now"`): `uv run pytest -q tests/test_infra.py::test_fail_fast_message_when_postgres_down` → 1 failed (`test_infra.py:65` — a mensagem termina em "sudo reboot now", sem o literal); suite inteira no scratch → 1 failed, 8 passed. Mutante morto.

**Sensor depth**: lightweight (3 mutations; infra feature, not a P0 path, per tier table).
**Result**: 3/3 killed — **PASS** (M1 e M3 mortos na iteração 0; M2 morto na re-verify após o fix `90d1363`).

Note: a 4th candidate (removing `connect_args={"connect_timeout": 3}` em `helpers.py:20`) was considered and not run — with the compose Postgres up, the dead-URL probe gets instant connection-refused, so it would survive for environmental reasons; the 3s cap is hardening for the WSL-hang case, demonstrated in the recorded T4 gate evidence (postgres parado → RuntimeError imediato, teto de 3s). The sharp spec-anchored mutation is M2, and it was run.

---

## Interactive UAT Results

Not performed — backend/infra feature; per validate.md, automated checks are sufficient for infrastructure work.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (no features beyond asked) | ✅ each diff is the minimum for its task: `config.py` 2 lines, `engine.py` pura remoção de código morto, `next.config.ts` 1 linha (`output: "standalone"`), Dockerfiles mínimos |
| Surgical changes (no adjacent "improvements") | ✅ revisados diff a diff; nenhum toque fora do escopo |
| No scope creep | ✅ README também removeu menções a SQLite que a feature invalidou (justificado no status de T7); limpeza do `_remove_test_db` do conftest é código que a mudança órfã |
| No abstractions / unnecessary flexibility | ✅ `helpers.py` tem 1 função, 1 propósito |
| Matches existing patterns/style | ✅ docstrings pt-BR, padrão conftest (env antes dos imports da app) preservado |
| Spec-anchored outcome check | ✅ 9/9 ancoradas (INFRA-06 corrigido por `90d1363`: `test_infra.py:65` mira o literal do spec) |
| Per-layer Coverage Expectation (matrix: config/engine/fail-fast = integration; Docker/compose/docs = build gate) | ✅ 6 testes novos de integração cobrem config (2), engine/dialeto (1), estado limpo (2), fail-fast (1); camadas infra/docs cobertas pelo build gate registrado |
| Every test maps to a spec AC/edge/Done-when — no unclaimed tests | ✅ os 6 novos mapeiam para INFRA-03 (×2), INFRA-09, INFRA-05 (×2), INFRA-06; os 3 pré-existentes (`test_health.py`) servem de evidência INFRA-02/INFRA-04 no Postgres |
| Would senior engineer approve | ✅ |
| Documented guidelines followed: `backend/pyproject.toml` (pytest>=9, sem thresholds), `frontend/AGENTS.md` (Next.js 16 — `output: "standalone"` é a opção documentada; T6 registra conferência e build standalone) | ✅ |

---

## Edge Cases

- [x] Host ocupa 5432 → override de porta documentado sem esconder o erro: `README.md:66-77` (`docker-compose.override.yml` com `5433:5432`, explica que dentro do compose nada muda)
- [x] Backend sobe antes do postgres aceitar conexões → `depends_on: condition: service_healthy` retém o start: `docker-compose.yml:30-32`; live: postgres `(healthy)` e backend Up; registrado em T5/T8
- [x] pytest em paralelo com dev backend → bancos distintos: `conftest.py:10` força `ritmo_test`; dev usa `ritmo` (`docker-compose.yml:27`, `config.py:25`); live: ambos os bancos existem, dev DB com 1 usuário
- [x] Imagem postgres:16 ausente → primeiro `up` faz pull, documentado: `README.md:37-38`

---

## Gate Check

- **Gate command** (tasks.md): quick/full = `uv run pytest` (em `backend/`); build = `docker compose config -q && docker compose up -d --build && curl -fsS :8000/api/health && curl -fsSI :3000 && uv run pytest && npm run build && npm run lint`
- **Result**: **9 passed, 0 failed, 0 skipped** (iteração 0: 9.92s; re-verify em `90d1363`: 10.43s; Python 3.12.15, pytest 9.1.1, contra o Postgres do compose). 1 warning pré-existente (StarletteDeprecationWarning do TestClient, nível de dependência, não relacionado à feature)
- **Read-only build-gate pieces re-executados por este Verifier** (idênticos nas duas iterações, em `44b9848` e `90d1363`): `docker compose config -q` → exit 0; `docker compose ps` → 3 serviços Up, postgres healthy; `curl -fsS localhost:8000/api/health` → 200 `{"status":"ok",...}`; `curl -fsSI localhost:3000` → `HTTP/1.1 200 OK`; `psql` read-only → bancos `ritmo` + `ritmo_test` existem, dev DB `users` = 1; volume `ritmo_postgres-data` presente
- **NOT re-executed** (proibido reiniciar/rebuildar o stack em execução): `up -d --build`, `down -v`, ciclo down/up de persistência, `npm run build`, `npm run lint` — cobertos pela evidência de gate registrada em T3/T5/T6/T8 (especificamente: standalone `server.js` confirmado, lint OK, `down && up` preservou schema + usuário, `SELECT count(*) FROM users` → 1)
- **Test count before feature**: 3 (`backend/tests/test_health.py`, intocado pela feature — diff vazio confirmado)
- **Test count after feature**: 9
- **Delta**: +6 (todos em `backend/tests/test_infra.py`: 2 de T1, 4 de T4) — bate com a matriz e com o delta declarado
- **Skipped tests**: nenhum
- **Failures**: nenhuma
- **Test integrity**: nenhum teste deletado; `test_health.py` idêntico (asserções não enfraquecidas); conftest reescrito sem remover asserção alguma (o `_remove_test_db` removido era scaffolding de arquivo, não teste)

---

## Fix Plans

### Fix 1: INFRA-06 — asserção circular não ancora a mensagem do spec — ✅ APPLIED (`90d1363`)

- **Root cause** (iteração 0): `backend/tests/test_infra.py:61` afirmava `POSTGRES_UP_HINT in str(exc_info.value)`, mas `POSTGRES_UP_HINT` (`backend/tests/helpers.py:5`) era a mesma constante usada para construir a mensagem (`helpers.py:28`). A asserção comparava a constante consigo mesma: qualquer hint passava. Mutante M2 sobreviveu com 9/9 verdes.
- **Fix aplicado** (commit `90d1363`, "fix(tests): pin literal postgres startup hint in fail-fast assertion"): a asserção passou a ser o literal do spec — `backend/tests/test_infra.py:65` - `assert "docker compose up -d postgres" in str(exc_info.value)`; o import da constante foi removido (`:14`); docstring registra a lição L-001. Sem mudança de implementação (`helpers.py` já estava correto).
- **Verify (executado)**: (1) `uv run pytest` na árvore real → 9/9 (10.43s); (2) mutante M2 re-injetado por este Verifier em scratch próprio → teste falha em `test_infra.py:65`, suite do scratch 1 failed/8 passed — mutante morto. Corroborado pelo scratch do orchestrator.
- **Status**: ✅ Resolvido — gap fechado, nenhuma ação pendente.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| INFRA-01 | Verified (autor, no diff da feature) | ✅ Verified (confirmado) |
| INFRA-02 | Verified | ✅ Verified (confirmado) |
| INFRA-03 | Verified | ✅ Verified (confirmado, nuance documentada) |
| INFRA-04 | Verified | ✅ Verified (confirmado) |
| INFRA-05 | Verified | ✅ Verified (confirmado, mutante M1 morto) |
| INFRA-06 | Needs Fix (iteração 0: implementação correta; teste não ancora o valor do spec — M2 sobreviveu) | ✅ Verified (fix `90d1363` aplicado; literal pinado em `test_infra.py:65`; M2 re-morto; re-verificado) |
| INFRA-07 | Verified | ✅ Verified (confirmado) |
| INFRA-08 | Verified | ✅ Verified (confirmado via evidência de gate registrada + volume vivo) |
| INFRA-09 | Verified | ✅ Verified (confirmado, mutante M3 morto) |

Nota: o autor já havia marcado os 9 como Verified dentro do diff da feature, antes da validação independente. A iteração 0 reverteu INFRA-06 para Needs Fix (mutante M2 sobrevivente); a re-verify confirma os 9 como Verified após o fix `90d1363`.

---

## Summary

**Overall**: ✅ Ready — **PASS** (re-verify iteração 1/3: o único gap da iteração 0 foi fechado pelo fix `90d1363` e re-derivado do zero por este Verifier)

**Spec-anchored check**: 9/9 ACs ancorados com evidência file:line + asserção (INFRA-06 agora com o literal do spec em `test_infra.py:65`)
**Sensor**: 3/3 mutantes mortos (M1 drop_all → morto; M3 default sqlite → morto; M2 hint flipado → sobreviveu na iteração 0, morto na re-verify após o fix — re-kill confirmado independentemente por este Verifier em scratch próprio)
**Gate**: 9 passed, 0 failed, 0 skipped contra o Postgres do compose (re-run em `90d1363`: 10.43s); compose config OK; stack vivo com curls 200/200

**What works**: stack completo sobe por compose com healthcheck e ordering (INFRA-01/02); config 100% env com default postgres (INFRA-03, mutante M3 morto); create_all + seed no Postgres (INFRA-04); suite contra `ritmo_test` com estado limpo real — o par polui/verifica mata mutantes (INFRA-05, M1); fail-fast com a mensagem do spec agora pinada por asserção literal e guardada contra mutantes (INFRA-06, M2 morto); init cria `ritmo_test` (INFRA-07, confirmado vivo); volume nomeado presente e persistência registrada (INFRA-08); psycopg3 único caminho, zero `sqlite://` no repo (INFRA-09).

**Issues found**: nenhum remanescente. (Iteração 0: INFRA-06 com asserção circular, mutante M2 sobrevivente — resolvido pelo fix `90d1363`, ver Fix Plans.)

**Next steps**: nenhum — feature pronta. Lição L-001 (candidate) registrada a partir do mutante sobrevivente; promoção acontece no próximo load de Specify/Design se corroborada em outra feature.
