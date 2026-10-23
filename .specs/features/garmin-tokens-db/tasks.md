# garmin-tokens-db Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/garmin-tokens-db/design.md`
**Spec**: `.specs/features/garmin-tokens-db/spec.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: none at repo root - strong defaults applied. Commands extraídos do próprio repo: `uv run pytest` (README:60, backend/), `npm run lint` + `npm run build` (frontend/package.json). Padrão de teste amostrado: unit com lib stubada via monkeypatch (`tests/test_garmin_login.py`, `tests/fake_garmin.py`), API via TestClient com sessão real (`tests/conftest.py:60`), Postgres do compose (`ritmo_test`).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domínio backend (tokens_store, gateway, service, CLIs) | unit | 1:1 com os ACs do spec; todos os edge cases listados; lib sempre stubada (nenhum teste toca a API real) | `backend/tests/test_garmin_*.py` | `uv run pytest` (quick: arquivo alvo) |
| API (endpoint de status, startup) | integration (TestClient) | Todos os endpoints no escopo: happy + 3 estados + 401 + fail-fast de startup | `backend/tests/test_*_api.py`, `backend/tests/test_infra.py` | `uv run pytest` |
| Modelo / entidade | unit | Constraints: unique por usuário + FK CASCADE | `backend/tests/test_garmin_tokens_models.py` | `uv run pytest` |
| Frontend | none - build gate | lint + build verdes | `frontend/src/**` | `npm run lint` + `npm run build` |
| Config / docs / compose | none - build gate | suite inteira verde | `docker-compose.yml`, `backend/.env.example`, `README.md` | `uv run pytest` (full) |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Baseline atual: 493 testes verdes (handoff hr-zones).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks com testes unitários de arquivo(s) alvo | `cd backend && uv run pytest tests/test_<arquivo>.py -q` |
| Full | Após tasks que tocam service/API compartilhada | `cd backend && uv run pytest -q` |
| Build | Ao fim de cada fase (e tasks config/docs/frontend) | `cd backend && uv run pytest -q` **e** `cd frontend && npm run lint && npm run build` (quando frontend/config mudar) |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação (banco + config)

Tabela e chave — pré-requisito de tudo.

```
T1 → T2
```

### Phase 2: Cofre e leitura por usuário

O cofre Fernet e o novo gateway; o sync passa a ler do banco com persist-back.

```
T1 → T3
T2 → T3
T3 → T4 → T5
```

### Phase 3: CLIs de escrita

Login de convidado e importação do legado.

```
T3 → T6 → T7
```

### Phase 4: Startup e status

Fail-fast da chave e endpoint de exibição.

```
T1 → T9
T2 → T8 → T9
T3 → T8 → T9
T3 → T9
```

### Phase 5: Frontend e desligamento

Seção no /perfil e extinção do tokenstore de arquivo.

```
T9 → T10 → T11
T4 → T11
T6 → T11
```

> Toda seta acima corresponde a um `Depends on` real; a ordem dentro da fase é
> a ordem de execução (o predecessor da fase sempre aparece como dependência).

---

## Task Breakdown

### T1: Modelo GarminToken

**What**: Criar a tabela `garmin_tokens` — 1:1 com usuário (`user_id` UNIQUE, FK CASCADE), `token_encrypted` (Text), `created_at`, `updated_at` (onupdate) — seguindo o padrão `UserSession`/`UserHrMetric` de `models.py`.
**Where**: `backend/app/db/models.py`
**Depends on**: None
**Reuses**: padrão FK CASCADE de `app/db/models.py:61`; `_utcnow` do mesmo módulo
**Requirement**: GTDB-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `GarminToken` definido com unique `user_id` + CASCADE + `updated_at` com `onupdate`
- [x] `Base.metadata.create_all` cobre a tabela nova (sem ALTER — AD-019)
- [x] Testes: unique violada → IntegrityError; deletar o usuário apaga a linha (CASCADE)
- [x] Gate check passes: `cd backend && uv run pytest tests/test_garmin_tokens_models.py -q`
- [x] Test count: ~2-3 testes novos (baseline 493)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(db): tabela garmin_tokens por usuário`

---

### T2: Config da chave + dependência cryptography

**What**: Adicionar `token_encryption_key: str = ""` ao `Settings` (env `TOKEN_ENCRYPTION_KEY`) e `cryptography>=43` às dependências de produção do pyproject (com `uv lock`).
**Where**: `backend/app/core/config.py`
**Depends on**: T1
> Dependência de ordem da fase — nenhum acoplamento técnico.
**Reuses**: padrão dos demais campos de env comentados de `config.py`
**Requirement**: GTDB-13, GTDB-14 (infraestrutura)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Campo presente com default vazio e comentário de contexto (geração da chave)
- [x] `cryptography` instalada e importável (`from cryptography.fernet import Fernet`)
- [x] Os campos `garmintokens`/`garmintokens_base64` permanecem (remoção é da T4/T11 — o leitor morre junto)
- [x] Gate check passes: `cd backend && uv run pytest -q` (suite inteira verde, 493)

**Tests**: none
**Gate**: full

**Commit**: `feat(core): token_encryption_key e dependência cryptography`

---

### T3: Cofre tokens_store (Fernet + banco)

**What**: Criar `app/garmin/tokens_store.py` com `TokenKeyError`, `require_key(settings) -> Fernet`, `get_blob(db, user_id, fernet) -> tuple[str, datetime] | None`, `save_blob(db, user_id, blob, fernet, expected_updated_at=None) -> bool` (upsert com guard otimista `WHERE updated_at = :expected`) e `get_meta(db, user_id) -> tuple[bool, datetime | None]` — o ÚNICO módulo que toca a coluna cifrada.
**Where**: `backend/app/garmin/tokens_store.py`
**Depends on**: T1, T2
**Reuses**: `GarminToken` (T1); padrão de módulo de domínio puro do projeto (`app/profile/calc.py`)
**Requirement**: GTDB-13, GTDB-14, GTDB-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `require_key` aceita chave Fernet válida; ausente e inválida → `TokenKeyError` com mensagem apontando o comando de geração
- [x] `save_blob` grava ciphertext (nunca plano); sem linha cria, com linha atualiza (`updated_at` avança); guard recusa (`False`) quando a linha mudou desde o carregamento
- [x] `get_blob` devolve `(blob, updated_at)` ou `None` sem linha; ciphertext de outra chave → exceção de decript (tratada pelos chamadores como "sem tokens")
- [x] `get_meta` devolve existência + `updated_at` sem decriptar
- [x] Nenhuma chamada de log no módulo (GTDB-15)
- [x] Gate check passes: `cd backend && uv run pytest tests/test_garmin_tokens_store.py -q`
- [x] Test count: ~8 testes novos

**Tests**: unit
**Gate**: quick

**Commit**: `feat(garmin): cofre Fernet para tokens (tokens_store)`

---

### T4: Gateway from_user (leitura do banco)

**What**: Substituir `GarminGateway.from_settings` por `from_user(db, user_id, settings=None)` (sem linha / blob ilegível / lib rejeita → `GarminAuthExpiredError` sem conteúdo do blob), adicionar `session_blob()` e `tokens_loaded_at`; remover `from_settings` e os campos `garmintokens`/`garmintokens_base64` do `Settings`; migrar os testes de `from_settings`. **Ajuste de fronteira (orquestador, 22/10): T4 troca também o call site de `run_sync` (`service.py:397`) e renomeia `from_settings`→`from_user` nos fakes de teste (`tests/fake_garmin.py`, `tests/test_sync_api.py`), mantendo a suite verde neste commit — sem isso o T4 deixaria a suite quebrada até o T5.**
**Where**: `backend/app/garmin/client.py`
**Depends on**: T3
**Reuses**: canal `GarminAuthExpiredError` (`client.py:42`); `make_settings` de `tests/test_garmin_gateway.py`
**Requirement**: GTDB-01, GTDB-03, GTDB-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `from_user` hidrata via `garmin.login(blob)` inline; `GarminConnectAuthenticationError` → `GarminAuthExpiredError`
- [x] Sem tokens / `InvalidToken` → `GarminAuthExpiredError` com mensagem sem fragmento de blob
- [x] `session_blob()` devolve `self._garmin.client.dumps()`; `tokens_loaded_at` devolve o `updated_at` visto no carregamento
- [x] `from_settings` deletado; nenhum import de `resolve_token_path`/`secure_token_dir` resta em `client.py`
- [x] `Settings` sem os campos legados; testes de gateway migrados (login ok, sem tokens, blob ilegível, lib rejeita)
- [x] Gate check passes: `cd backend && uv run pytest tests/test_garmin_gateway.py -q`
- [x] Test count: suite de gateway verde com ~4-5 testes de from_user (os 2 de from_settings migrados)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(garmin): gateway from_user lê tokens do banco`

---

### T5: Sync por usuário + persist-back

**What**: `run_sync` garante o persist-back (`_persist_tokens`) no fim do job — done e error genérico, NUNCA no caminho `reauth_needed` — com guard recusado/exceção virando warning nos stats; o call site `from_user` e a renomeação dos fakes já entraram no T4 — aqui o `FakeGateway` ganha `session_blob()`/`tokens_loaded_at` para os testes do persist-back.
**Where**: `backend/app/garmin/service.py`
**Depends on**: T4
**Reuses**: padrão de warnings dos stats (`service.py:364`); FakeGateway (`tests/fake_garmin.py:130`)
**Requirement**: GTDB-01, GTDB-03, GTDB-04, GTDB-05, GTDB-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Job de usuário SEM tokens → `error` com `reauth_needed=true` (canal SYNC-25 intacto)
- [x] Job done → linha do banco contém o blob vigente do gateway (cifrado); job error genérico idem
- [x] Guard recusado (tokens mudaram no meio do job) → warning nos stats e linha mais nova PRESERVADA
- [x] Persist-back com exceção → warning nos stats, job segue para o status normal
- [x] Caminho reauth NÃO persiste (blob morto)
- [x] `FakeGateway` espelha a assinatura nova; suite inteira verde (nenhum site de teste quebrado)
- [x] Gate check passes: `cd backend && uv run pytest -q`
- [x] Test count: ~6 testes novos em test_garmin_service.py; 493 baseline + novos, zero deletados

**Tests**: unit
**Gate**: full

**Commit**: `feat(garmin): persist-back do refresh no fim do sync`

---

### T6: CLI de login por usuário

**What**: Reescrever `app/garmin/login.py` como `python -m app.garmin.login --user <email>`: resolve usuário por email (lowercase, padrão auth), login de credenciais com MFA interativo, `os.environ.pop("GARMINTOKENS")` antes do login, valida `di_token` não-nulo e grava UPSERT cifrado; email inexistente ou falha → erro e nenhuma gravação.
**Where**: `backend/app/garmin/login.py`
**Depends on**: T3
**Reuses**: fluxo da lib (5 estratégias + `prompt_mfa`) do login atual; padrão CLI com sessão própria ao banco de `app/auth/set_password.py`; `save_blob` (T3)
**Requirement**: GTDB-07, GTDB-08, GTDB-09, GTDB-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Login válido (com e sem MFA) → linha do usuário criada/substituída com ciphertext
- [x] Email inexistente → mensagem clara, exit != 0, nenhuma gravação
- [x] Falha de credenciais/MFA/rate limit → erro, tokens existentes inalterados
- [x] Sessão sem `di_token` → erro "sem token DI", nada gravado
- [x] `GARMINTOKENS` removida do env do processo antes do login (fake registra `login(None)`)
- [x] Nenhum fragmento de token em mensagens de erro (GTDB-15)
- [x] Gate check passes: `cd backend && uv run pytest tests/test_garmin_login.py -q`
- [x] Test count: ~6 testes (reescrita completa do arquivo)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(garmin): CLI de login por usuário grava no banco`

---

### T7: CLI de importação do legado

**What**: Criar `app/garmin/import_tokens.py` — `python -m app.garmin.import_tokens [--path <p>]`: lê `<path>/garmin_tokens.json` (ou arquivo direto), valida JSON com `di_token`, RECUSA se o usuário 1 já tem tokens (orienta o login CLI, exit != 0, nada gravado) e grava cifrado na linha do usuário 1.
**Where**: `backend/app/garmin/import_tokens.py`
**Depends on**: T6
> Dependência de ordem da fase — T7 é tecnicamente independente de T6 (ambos dependem de T3).
**Reuses**: `token_utils.resolve_token_path` (expansão de `~`); `DEFAULT_USER_ID` de `models.py`; `save_blob` (T3)
**Requirement**: GTDB-10, GTDB-11, GTDB-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Import válido (dir com `garmin_tokens.json` e arquivo direto) → linha do usuário 1 cifrada
- [x] Linha existente → recusa com orientação para `login --user`, exit != 0, linha intacta
- [x] Arquivo ausente/ilegível/JSON sem `di_token` → erro claro, nenhuma gravação
- [x] `--path` com default `~/.garminconnect` (seam de teste, sem `--user` — spec trava o usuário 1)
- [x] Gate check passes: `cd backend && uv run pytest tests/test_garmin_import.py -q`
- [x] Test count: ~5 testes novos

**Tests**: unit
**Gate**: quick

**Commit**: `feat(garmin): CLI de importação do tokenstore legado`

---

### T8: Fail-fast da chave no startup

**What**: Chamar `tokens_store.require_key(get_settings())` como primeira linha do lifespan (`main.py`) e setar `TOKEN_ENCRYPTION_KEY` fixa de teste no conftest ANTES do import da app (como `DATABASE_URL`); teste de integração prova que sem a chave a subida interrompe com `TokenKeyError`.
**Where**: `backend/app/main.py`
**Depends on**: T2, T3
**Reuses**: padrão do conftest (`tests/conftest.py:12` — env antes do import)
**Requirement**: GTDB-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Lifespan valida a chave ANTES do `init_db()`; ausente/inválida → `TokenKeyError` com o comando de geração
- [x] conftest seta chave de teste fixa antes de qualquer import da app; suite inteira segue verde
- [x] Teste de integração: env sem a chave + `get_settings.cache_clear()` + entrar no TestClient → `TokenKeyError` (higiene de cache no próprio teste)
- [x] Gate check passes: `cd backend && uv run pytest -q`
- [x] Test count: +1 teste de startup; 493+ baseline, zero deletados

**Tests**: integration
**Gate**: full

**Commit**: `feat(core): fail-fast de TOKEN_ENCRYPTION_KEY no startup`

---

### T9: Endpoint de status da conexão

**What**: Criar `GET /api/profile/garmin-connection` — derivação pura em `profile/service.py` (`garmin_connection(db, user_id)` com normalização UTC naive) + rota em `profile/router.py` com `ConnectionOut(state, tokens_updated_at)`; só metadados, nunca o blob.
**Where**: `backend/app/profile/router.py`
**Depends on**: T1, T3, T8
**Reuses**: padrão dos routers/schemas de `app/profile/`; `require_session` via include do `main.py`; `GarminToken` (T1) e `SyncJob` (leitura)
**Requirement**: GTDB-16, GTDB-17

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Sem linha → `not_connected`; linha + último job reauth (tokens não atualizados após o fim do job) → `reauth_needed`; caso contrário → `connected`
- [x] Tokens atualizados APÓS o job falho → `connected` (emenda GTDB-16)
- [x] Resposta contém apenas `state` + `tokens_updated_at` (nenhum fragmento de blob)
- [x] Sem sessão → 401 (padrão do include)
- [x] Gate check passes: `cd backend && uv run pytest tests/test_profile_connection_api.py -q`
- [x] Test count: ~4 testes novos (3 estados + 401)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(profile): endpoint de status da conexão Garmin`

---

### T10: Seção Conexão Garmin no /perfil

**What**: Adicionar `GarminConnectionOut` + `getGarminConnection()` em `api.ts`, criar `components/profile/ConnectionCard.tsx` (pill por estado + "tokens atualizados em …") e inserir a seção no topo do `/perfil` com `PanelSection` SEM índice (título "Conexão Garmin", subtítulo "o que é / por que importa" — AD-009).
**Where**: `frontend/src/components/profile/ConnectionCard.tsx`
**Depends on**: T9
**Reuses**: `PanelSection` (índice opcional, `PanelSection.tsx:11`); padrão de fetch dos componentes `components/profile/*`; pills `bg-accent/15`
**Requirement**: GTDB-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Três estados renderizam com pill distinta (Conectado / Reautenticação necessária / Não conectado)
- [x] Seção no topo da página, sem índice, subtítulo sempre visível (mobile-first 390px)
- [x] `npm run lint` e `npm run build` verdes (Next 16 — seguir o guia em `node_modules/next/dist/docs/` se API nova for usada)
- [x] Gate check passes: `cd frontend && npm run lint && npm run build`

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): seção Conexão Garmin no /perfil`

---

### T11: Extinção do tokenstore de arquivo

**What**: Remover o mount `~/.garminconnect` e `GARMINTOKENS` do compose, as duas linhas de `GARMINTOKENS(_BASE64)` do `.env.example`, documentar no README (geração da chave, `import_tokens` run-once, `login --user` por convidado) e limpar `token_utils.py` para reter apenas `resolve_token_path`.
**Where**: `backend/app/garmin/token_utils.py`
**Depends on**: T4, T6, T10
> As dependências T4/T6 são técnicas (cleanup exige from_settings morto e login.py reescrito); T10 é ordem da fase.
**Reuses**: nada — é a remoção; README ganha a seção de operação dos CLIs
**Requirement**: GTDB-18, GTDB-19, GTDB-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `docker-compose.yml` sem mount e sem `GARMINTOKENS`; `docker compose config` confirma
- [x] `.env.example` sem as linhas legadas e com `TOKEN_ENCRYPTION_KEY` documentada (comando de geração)
- [x] README com a seção "Conexão Garmin por usuário" (import run-once + login por convidado)
- [x] `token_utils.py` retém só `resolve_token_path`; `secure_token_dir`/`get_token_path`/`get_token_base64_path`/`token_exists`/`validate_tokens`/`remove_tokens`/`get_token_info` removidas sem referência restante
- [x] `grep -ri GARMINTOKENS` no repo só encontra o CLI de importação (e nenhum leitor runtime)
- [x] Gate check passes: `cd backend && uv run pytest -q` (493+ baseline, zero deletados)

**Tests**: none
**Gate**: full

**Commit**: `chore(garmin): remove tokenstore filesystem e code morto`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Phase 1:  T1 ------→ T2
Phase 2:  T3 ------→ T4 ------→ T5
Phase 3:  T6 ------→ T7
Phase 4:  T8 ------→ T9
Phase 5:  T10 -----→ T11
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Batching**: 11 tasks → 2 batches (Batch 1 = Phases 1-3, T1-T7; Batch 2 = Phases 4-5, T8-T11). A Verifier roda automaticamente após o Batch 2.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Modelo GarminToken | 1 componente (+1 arquivo de teste) | ✅ Granular |
| T2: Config chave + cryptography | 1 campo de config + 1 dependência (coesos) | ✅ Granular |
| T3: Cofre tokens_store | 1 módulo | ✅ Granular |
| T4: Gateway from_user | 1 classe-método + morte do leitor legado (coeso) | ✅ Granular |
| T5: Sync por usuário + persist-back | 1 função + espelho no fake de teste | ✅ Granular |
| T6: CLI de login | 1 comando | ✅ Granular |
| T7: CLI de importação | 1 comando | ✅ Granular |
| T8: Fail-fast no startup | 1 ponto de costura + env de teste | ✅ Granular |
| T9: Endpoint de status | 1 endpoint | ✅ Granular |
| T10: Seção no /perfil | 1 componente + wiring (coeso) | ✅ Granular |
| T11: Extinção do tokenstore | 1 cleanup coeso (compose/env/docs/mortas) | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | início da Fase 1 (sem seta de entrada) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T3 | T3 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T2, T3 | T2 → T8, T3 → T8 | ✅ Match |
| T9 | T1, T3, T8 | T1 → T9, T3 → T9, T8 → T9 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | T4, T6, T10 | T10 → T11, T4 → T11, T6 → T11 | ✅ Match |

Nenhuma dependência aponta para fase posterior (validado pelo script).

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Modelo/entidade | unit | unit | ✅ OK |
| T2 | Config | none - build gate | none | ✅ OK |
| T3 | Domínio backend | unit | unit | ✅ OK |
| T4 | Domínio backend | unit | unit | ✅ OK |
| T5 | Domínio backend | unit | unit | ✅ OK |
| T6 | Domínio backend (CLI) | unit | unit | ✅ OK |
| T7 | Domínio backend (CLI) | unit | unit | ✅ OK |
| T8 | API (startup) | integration | integration | ✅ OK |
| T9 | API (endpoint) | integration | integration | ✅ OK |
| T10 | Frontend | none - build gate | none | ✅ OK |
| T11 | Config/docs/compose | none - build gate | none | ✅ OK |

---

## Requirement Traceability (tasks)

| Requirement | Tasks |
| ----------- | ----- |
| GTDB-01 | T4, T5 |
| GTDB-02 | T1, T4 |
| GTDB-03 | T4, T5 |
| GTDB-04 | T5 |
| GTDB-05 | T5 |
| GTDB-06 | T5 |
| GTDB-07 | T6 |
| GTDB-08 | T6 |
| GTDB-09 | T6 |
| GTDB-10 | T7 |
| GTDB-11 | T7 |
| GTDB-12 | T7 |
| GTDB-13 | T2, T3 |
| GTDB-14 | T2, T3, T8 |
| GTDB-15 | T3, T6 |
| GTDB-16 | T9, T10 |
| GTDB-17 | T9 |
| GTDB-18 | T11 |
| GTDB-19 | T4, T11 |
| GTDB-20 | T11 |

**Coverage:** 20 total, 20 mapped to tasks, 0 unmapped ✅
