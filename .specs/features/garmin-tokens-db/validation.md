# garmin-tokens-db Validation

**Date**: 2026-10-22 (rodada 2)
**Spec**: `.specs/features/garmin-tokens-db/spec.md`
**Diff range**: `5e74739..HEAD` (13 commits: d49438f, 9e35873, 4a1e2ab, b3901c5, c2dacdd, 7d98f9d, 653cc13, d77902c, 15aa875, f745de1, 82d5348 + fixes 7ab580c, cf64f9d)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Verdict: ✅ PASS (rodada 2 — fix→re-verify, iteração 1 de máx. 3)

Os 2 gaps da rodada 1 foram fechados pelo implementador como testes novos (`7ab580c`, `cf64f9d`), ambos test-only: (1) o mutante M6 agora é KILLED pelo teste de reauth em pleno job com gateway vivo; (2) o sub-caso "ilegível" do GTDB-12 tem evidência `file:line`. Gate 550/0; sensor da rodada 2: 4/4 killed (os 2 gaps re-injetados + 2 mutações adversariais da rodada 1 re-executadas, ainda mortas). Todos os 20 ACs com evidência spec-anchored.

**Histórico**: rodada 1 (2026-10-22, ❌ FAIL — gate 548/0, sensor 5/6, M6 sobreviveu + GTDB-12 "ilegível" sem evidência) → **rodada 2 (2026-10-22, ✅ PASS — gate 550/0, sensor 4/4, 20/20 ACs)**. Fix tasks Fix 1 e Fix 2 executados como `7ab580c` e `cf64f9d`. Nenhuma lição nova registrada — PASS limpo da rodada 2 limpa os sobreviventes (lições L-017/L-018 da rodada 1 permanecem, fundadas).

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1: Modelo GarminToken | ✅ Done | unique + CASCADE + onupdate provados |
| T2: Config chave + cryptography | ✅ Done | campo + dependência; legados removidos depois em T4/T11 |
| T3: Cofre tokens_store | ✅ Done | require_key/get_blob/save_blob/get_meta |
| T4: Gateway from_user | ✅ Done | from_settings morto, blob inline |
| T5: Sync + persist-back | ✅ Done | guard, warning, exclusão reauth — **agora discriminada com gateway vivo (rodada 2)** |
| T6: CLI login | ✅ Done | upsert cifrado; falhas sem gravação |
| T7: CLI import | ✅ Done | branch "ilegível" coberto por `test_import_malformed_json_errors_without_writing` (rodada 2) |
| T8: Fail-fast startup | ✅ Done | lifespan antes do init_db, provado |
| T9: Endpoint de status | ✅ Done | 3 estados + emenda + 401 |
| T10: Seção Conexão | ✅ Done | build gate (frontend, sem testes por matriz) |
| T11: Extinção tokenstore | ✅ Done | compose/env/README limpos; token_utils só resolve_token_path |

---

## Spec-Anchored Acceptance Criteria

| AC | Criterion (re-derived from spec) | Spec-defined outcome | `file:line` + assertion | Result |
| -- | -------------------------------- | -------------------- | ----------------------- | ------ |
| GTDB-01 | Sync hidrata a sessão exclusivamente dos tokens do usuário no banco, decriptados em memória | `garmin.login` recebe o blob DO usuário inline (não path, não arquivo) | `backend/tests/test_garmin_gateway.py:204` — `assert fake.calls["login"] == [(USER_BLOB,)]` + `:206` — `assert gateway.tokens_loaded_at == loaded_at` | ✅ PASS |
| GTDB-02 | Exatamente uma linha por usuário (unique user_id, FK CASCADE) | 2ª linha → IntegrityError; delete do usuário → 0 linhas | `backend/tests/test_garmin_tokens_models.py:42-43` — `with pytest.raises(IntegrityError): db.commit()`; `:57` — `assert db.query(GarminToken).count() == 0` | ✅ PASS |
| GTDB-03 | Sem tokens / blob ilegível / lib rejeita → job `error` com `reauth_needed=true` | `GarminAuthExpiredError` nos 3 gatilhos; stats `reauth_needed is True` | sem linha: `backend/tests/test_garmin_gateway.py:218-220` — `pytest.raises(GarminAuthExpiredError)` + `assert "sem tokens" in str(exc.value)`; blob ilegível: `:234-238` — `pytest.raises(GarminAuthExpiredError)` + fragmentos ausentes; lib rejeita: `:251-252`; ponta a ponta: `backend/tests/test_garmin_service.py:512-515` — `assert finished.status == "error"` + `assert stats["reauth_needed"] is True` (e `:1024`, `:1026` — `select(GarminToken) == []`) | ✅ PASS |
| GTDB-04 AC 1 | Job encerra (done ou error genérico) → linha contém o blob VIGENTE cifrado; caminho reauth NUNCA persiste | decrypt(coluna) == blob da sessão; nunca plaintext; exclusão no reauth mesmo com gateway VIVO (401 em pleno job) | done: `backend/tests/test_garmin_service.py:981-983` — `assert row.token_encrypted != FAKE_SESSION_BLOB` + `assert fernet.decrypt(...).decode() == FAKE_SESSION_BLOB`; error genérico: `:1005`; exclusão (gateway nulo): `:1026` — `select(GarminToken) == []`; **exclusão (gateway VIVO, rodada 2): `:1029-1055` — `test_reauth_mid_job_with_live_gateway_never_persists`: `:1050` `assert finished.status == "error"`, `:1052` `assert finished.stats_json["reauth_needed"] is True`, `:1054` `assert fernet.decrypt(row.token_encrypted.encode()).decode() == SEED_BLOB` (linha intacta), `:1055` `assert row.updated_at == seeded_updated_at` (persist-back ausente — provado empíricamente pelo sensor M6, que falhou exatamente em `:1054`)** | ✅ PASS (rasura da rodada 1 resolvida) |
| GTDB-05 | Tokens mudaram no banco desde o carregamento → persist-back NÃO sobrescreve | guard recusa; linha mais nova (RELOGIN_BLOB) permanece; warning exato | `backend/tests/test_garmin_service.py:1085-1087` — `assert warnings == [{"tipo": "tokens", "erro": "tokens atualizados durante o sync — preservados"}]` + `:1089` — `assert decrypt(row) == RELOGIN_BLOB` + `:1090` — `assert row.updated_at == datetime(2026, 10, 14, 23, 0, 0)` (linhas deslocadas +29 pela inserção do teste novo — spot-check rodada 2 confirmou); cofre: `backend/tests/test_garmin_tokens_store.py:176-181` — `assert refused is False` + `assert decrypt(row) == OUTRO_BLOB` | ✅ PASS |
| GTDB-06 | Persist-back falha → sync conclui normal + warning nos stats | status normal mantido; warning `{"tipo": "tokens", "erro": "persist-back falhou"}`; linha intacta | `backend/tests/test_garmin_service.py:1125` — `assert finished.status == "done"` + `:1127-1129` — `assert warnings == [{"tipo": "tokens", "erro": "persist-back falhou"}]` + `:1130-1131` — `assert decrypt(row) == SEED_BLOB` (deslocado +29 — spot-check rodada 2) | ✅ PASS |
| GTDB-07 | `login --user <email>` válido → upsert cifrado na linha do usuário | decrypt(coluna) == blob da lib; 1:1 (substitui, não duplica) | `backend/tests/test_garmin_login.py:129-133` — `assert len(rows) == 1` + `assert fernet.decrypt(rows[0].token_encrypted.encode()).decode() == BLOB`; MFA + replace: `:149-152` — `assert fake.mfa_code == "654321"` + `assert len(rows) == 1`; via `main()`: `:256-257` — `assert [row.user_id for row in _rows()] == [user_id]` | ✅ PASS |
| GTDB-08 | Email inexistente → erro claro, exit ≠ 0, nada gravado | SystemExit != 0; email no stderr; nenhuma linha; nem lib instanciada | `backend/tests/test_garmin_login.py:181-184` — `assert exc.value.code != 0` + `assert "fantasma@example.com" in capsys.readouterr().err` + `assert created == []` + `assert _rows() == []` | ✅ PASS |
| GTDB-09 | Login falha → erro + tokens existentes inalterados | exceção da lib sobe; ciphertext da linha idêntico ao anterior | `backend/tests/test_garmin_login.py:200-209` — `pytest.raises(GarminConnectAuthenticationError)` + `assert ...scalar_one() == old_ct` | ✅ PASS |
| GTDB-10 | `import_tokens` com tokenstore presente → importa e cifra na linha do usuário 1 | decrypt(coluna do usuário 1) == blob legado; dir E arquivo direto E default `~` | `backend/tests/test_garmin_import.py:55-59` — `assert row.user_id == DEFAULT_USER_ID` + `assert fernet.decrypt(...).decode() == BLOB`; arquivo direto `:70-72`; default `~`: `:161-165` (via `main()`, deslocado +17 — spot-check rodada 2: `main()` sem SystemExit + `assert fernet.decrypt(row...) == BLOB`) | ✅ PASS |
| GTDB-11 | Usuário 1 já tem tokens → recusa com orientação, linha intacta | exit ≠ 0; "login" no stderr; ciphertext preservado | `backend/tests/test_garmin_import.py:87-100` — `assert exc.value.code != 0` + `assert "login" in capsys.readouterr().err` + `assert ...scalar_one() == old_ct` | ✅ PASS |
| GTDB-12 | Arquivo legado ausente OU ILEGÍVEL → erro claro, nada gravado | exit ≠ 0; mensagem no stderr; nenhuma linha | ausente: `backend/tests/test_garmin_import.py:107-112` — `assert exc.value.code != 0` + `assert "não encontrado" in ...err` + `assert _token_row() is None`; sem di_token: `:124-130` — `assert "di_token" in ...err` + `assert _token_row() is None`; **ilegível (rodada 2): `:133-147` — `test_import_malformed_json_errors_without_writing`: grava `garmin_tokens.json` com JSON truncado (`'{"di_token": "di-token-legado"'` sem fechar), `:145` `assert exc.value.code != 0`, `:146` `assert "ilegível" in capsys.readouterr().err`, `:147` `assert _token_row() is None` — provado empíricamente pelo sensor M-alvo-2 (remoção do try/except → `JSONDecodeError` escapa `main()`, teste falha)** | ✅ PASS (gap da rodada 1 resolvido) |
| GTDB-13 | Todo blob exclusivamente cifrado; nenhuma coluna/log com plano | coluna != blob, blob not in coluna, roundtrip Fernet; só tokens_store toca a coluna | `backend/tests/test_garmin_tokens_store.py:110-112` — `assert row.token_encrypted != BLOB` + `assert BLOB not in row.token_encrypted` + `assert fernet.decrypt(...).decode() == BLOB`; `:249-251` — `assert offenders == []` | ✅ PASS |
| GTDB-14 | Chave ausente/inválida → subida interrompida com mensagem clara | `TokenKeyError` com "Fernet.generate_key"; ANTES do init_db (tabela users não existe) | cofre: `backend/tests/test_garmin_tokens_store.py:81-83` e `:88-90` — `pytest.raises(TokenKeyError)` + `assert "Fernet.generate_key" in str(exc.value)`; startup: `backend/tests/test_infra.py:83-90` — `pytest.raises(TokenKeyError)` + `assert "TOKEN_ENCRYPTION_KEY" in str(exc_info.value)` + `assert "Fernet.generate_key()" in str(exc_info.value)` + `assert not inspect(engine).has_table("users")` (spot-check rodada 2: linhas confirmadas) | ✅ PASS |
| GTDB-15 | Nunca registrar conteúdo de token/blob em logs/stats/erros/respostas | zero logging no cofre; mensagens de erro sem fragmentos; payload fechado | `backend/tests/test_garmin_tokens_store.py:233-236` — `assert "import logging" not in source` (+getLogger/logger.); gateway: `backend/tests/test_garmin_gateway.py:237-238` — `assert "di-token-do-usuario" not in message` + `assert USER_BLOB not in message`; login: `backend/tests/test_garmin_login.py:241-242` — `assert "di-token-fake" not in output` + `assert BLOB not in output`; API: `backend/tests/test_profile_connection_api.py:76,89-92,105-108` — igualdade de dicionário fechado | ✅ PASS |
| GTDB-16 AC 1 | /perfil exibe exatamente um de 3 estados; emenda: tokens atualizados após job falho → "Conectado" | `{"state": "not_connected", "tokens_updated_at": None}` / `reauth_needed` (tokens ANTES do fim do job) / `connected` (job sadio) / emenda → `connected` | `backend/tests/test_profile_connection_api.py:76` — `assert _get(client) == {"state": "not_connected", "tokens_updated_at": None}`; `:89-92` — `{"state": "connected", ...TOKEN_ISO}`; `:105-108` — `{"state": "reauth_needed", ...}`; emenda: `:121` — `assert _get(client)["state"] == "connected"` (spot-check rodada 2: linhas confirmadas) | ✅ PASS |
| GTDB-17 | Endpoint só para o usuário da sessão (401 sem sessão); payload só metadados, nunca o blob | 401 sem sessão; shape fechado `{state, tokens_updated_at}` | `backend/tests/test_profile_connection_api.py:132-133` — `assert res.status_code == 401`; metadados-only garantido pelas igualdades fechadas de `:76/:89-92/:105-108` | ✅ PASS |
| GTDB-18 | Compose sem mount `~/.garminconnect`; `.env.example`/README sem GARMINTOKENS(_BASE64) | `docker compose config` sem o mount/env; grep limpo | Verificação definida pelo próprio spec (Independent Test), executada pelo Verifier na rodada 1 em 22/10: `docker compose config` → 0 ocorrências de `garminconnect`/`GARMINTOKENS` (exit 0); `git grep -in GARMINTOKENS` → só `.specs/*` e `backend/app/garmin/login.py:67` (`os.environ.pop` defensivo — não é leitor); `backend/.env.example` com `TOKEN_ENCRYPTION_KEY` documentada; README documenta geração da chave + CLIs. Fix commits da rodada 2 são test-only — nada mudou nesta superfície. Sem asserção pytest (T11 é "none - build gate" na matriz) | ✅ PASS (via verificação spec-defined; anotado) |
| GTDB-19 | Nenhum leitor de tokenstore de arquivo em caminho runtime | `GARMINTOKENS` removida do env antes do login; `login(None)`; blob vai inline do banco | `backend/tests/test_garmin_login.py:166-168` — `assert "GARMINTOKENS" not in os.environ` + `assert fake.login_args == [None]` + `assert len(_rows()) == 1`; from_user inline: `backend/tests/test_garmin_gateway.py:204`; compose/env: ver GTDB-18 | ✅ PASS |
| GTDB-20 | token_utils reter apenas funções em uso; mortas da era MCP removidas | arquivo contém só `resolve_token_path` | Verificação spec-defined executada na rodada 1: `backend/app/garmin/token_utils.py:10-19` — arquivo inteiro contém apenas `resolve_token_path`; suite verde sem os nomes. Fix commits da rodada 2 são test-only — arquivo intacto. Sem asserção pytest dedicada (build gate) | ✅ PASS (via verificação spec-defined; anotado) |

**Status**: ✅ All ACs covered — 20/20 PASS (rodada 1: 18/20 + 2 gaps).

---

## Discrimination Sensor — rodada 2 (re-verificação)

Tier: **EXPANDED** (tokens = caminho crítico de segurança; ≥5 mutações acumuladas entre as rodadas). Método idêntico ao da rodada 1: backup do arquivo alvo em `%TEMP%\opencode\sensor\` (`*.bak-r2`, fora da árvore), mutação aplicada, testes alvo rodados, backup restaurado, `git status --porcelain` conferido IDÊNTICO ao baseline após CADA rodada de mutação (baseline: `M .specs/LESSONS.md`, `M .specs/lessons.json`, `?? .specs/features/garmin-tokens-db/validation.md`); `git diff --stat` final confirma diff zero em `backend/`. Nenhum `git stash`.

| # | Mutação | Arquivo:linha | Descrição | Testes rodados | Resultado |
| - | ------- | ------------- | --------- | -------------- | --------- |
| M6-r2 | Persist-back também no caminho reauth (RE-EXECUÇÃO do gap 1) | `backend/app/garmin/service.py:458-463` | `_persist_tokens(db, job, stats, gateway)` adicionado no `except GarminAuthExpiredError` (dentro do guard `if gateway is not None:`, espelhando o branch de erro genérico) | test_garmin_service.py + test_sync_api.py | ✅ **KILLED** — `test_reauth_mid_job_with_live_gateway_never_persists` (fix `7ab580c`) falhou em `:1054` (`decrypt(row) == SEED_BLOB` — o blob morto FAKE_SESSION_BLOB sobrescreveu a linha e o `updated_at` avançou); 1 failed / 48 passed (239.8s). Sobrevivente da rodada 1 eliminado. |
| M12-r2 | Branch "ilegível" removido (RE-EXECUÇÃO do gap 2) | `backend/app/garmin/import_tokens.py:48-51` | `try/except (OSError, ValueError)` removido — `json.loads` direto → `JSONDecodeError` cru escapa de `main()` | test_garmin_import.py | ✅ **KILLED** — `test_import_malformed_json_errors_without_writing` (fix `cf64f9d`) falhou: `pytest.raises(SystemExit)` não captura o `JSONDecodeError` (traceback em `json/decoder.py`); 1 failed / 6 passed (7.7s). |
| M1-r2 | Guard otimista ignorado (ADVERSARIAL — re-execução de mutante morto) | `backend/app/garmin/tokens_store.py:94-99` | Cláusula `GarminToken.updated_at == expected_updated_at` removida do UPDATE → sempre grava | test_garmin_tokens_store.py + test_garmin_service.py | ✅ KILLED (ainda) — mesmos 2 assassinos da rodada 1: `test_save_blob_guard_refused_preserves_newer_row`, `test_persist_back_guard_refused_preserves_newer_row`; 2 failed / 49 passed (192.6s). |
| M3-r2 | `from_user` sem linha → exceção genérica (ADVERSARIAL) | `backend/app/garmin/client.py:92` | `GarminAuthExpiredError` → `RuntimeError` (fora do canal SYNC-25) | test_garmin_gateway.py | ✅ KILLED (ainda) — `test_from_user_without_tokens_raises_reauth`; 1 failed / 19 passed (18.6s). |

**Sensor depth**: expanded (P0 — 4 mutações manuais nesta rodada; 8 acumuladas entre rodadas 1+2)
**Result**: **4/4 killed — PASS ✅** (acumulado: 8/8 distintos; M6 foi o único sobrevivente histórico e agora morre)

### Por que M6 morre agora (análise)

O teste novo (`7ab580c`) conduz o cenário que faltava: 401 EM PLENO JOB com gateway VIVO — `MidJobReauth(FakeGateway)` levanta `GarminAuthExpiredError` em `get_sleep` com tokens semeados (`SEED_BLOB`) e `tokens_loaded_at` = `updated_at` da linha semeada. Com a mutação, o persist-back roda no `except`, o guard otimista ACEITA (a linha não mudou desde o carregamento) e grava `FAKE_SESSION_BLOB` — `assert fernet.decrypt(...) == SEED_BLOB` (`:1054`) falha imediatamente (e `:1055` também quebraria via `onupdate`). Na rodada 1 todos os testes de reauth passavam com gateway NULO, onde a mutação era vacuamente verdadeira.

---

## Edge Cases (do spec)

- [x] Chave trocada → blob ilegível tratado como tokens ausentes ("Reconectar", nunca crash) — gateway test_garmin_gateway.py:223-238 + cofre test_garmin_tokens_store.py:190-198
- [x] Re-login durante o sync → persist-back preserva tokens novos — test_garmin_service.py:1029-1090 (guard + emenda)
- [x] Blob inline sem credenciais mínimas → reauth_needed — test_garmin_gateway.py:241-252
- [x] Usuário deletado → tokens deletados (CASCADE) — test_garmin_tokens_models.py:47-57
- [x] Dois processos (sync + CLI) → guard de corrida decide; sync_state/lock já cobertos por SYNC-02 — test_garmin_tokens_store.py:156-181
- [x] Job reauth com gateway VIVO (401 em pleno sync) → blob morto não persiste — **test_garmin_service.py:1029-1055 (rodada 2, fix 7ab580c; matado empiricamente pelo sensor M6-r2)**

---

## Gate Check

- **Gate command**: `cd backend && uv run pytest -q` (Full)
- **Result**: **550 passed, 0 failed, 1 warning** (503.26s) — warning pré-existente (`StarletteDeprecationWarning` do TestClient), não introduzido pela feature
- **Test count before feature**: 493 (baseline hr-zones, tasks.md:31)
- **Test count after feature**: 550 (rodada 1: 548 + 2 testes dos fixes)
- **Delta**: +57 novos, zero deletados (548→550: `test_reauth_mid_job_with_live_gateway_never_persists`, `test_import_malformed_json_errors_without_writing` — ambos test-only, zero código de produção alterado pelos fixes)
- **Skipped tests**: nenhum
- **Failures**: nenhum

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ |
| Surgical changes | ✅ (fixes test-only; diff confinado à superfície da feature) |
| No scope creep | ✅ |
| Matches patterns | ✅ (testes novos seguem os helpers/_seed/monkeypatch dos vizinhos) |
| Spec-anchored outcome check | ✅ (20/20 na rodada 2) |
| Per-layer Coverage Expectation | ✅ (branch de erro "ilegível" do import agora coberto) |
| Every test maps to a spec requirement | ✅ (os 2 testes novos citam GTDB-04 AC 1 + SYNC-25 e GTDB-12 nas docstrings) |
| Documented guidelines | none - strong defaults applied |

---

## Fix Plans (da rodada 1 — RESOLVIDOS nesta rodada)

### Fix 1: Mutante sobrevivente — exclusão do persist-back no caminho reauth com gateway vivo (GTDB-04 AC 1) — ✅ RESOLVIDO

- **Prescrição original**: teste com gateway vivo levantando 401 em pleno job, tokens semeados, afirmando status error + `reauth_needed` + linha intacta.
- **Implementado em**: `7ab580c` — `test_reauth_mid_job_with_live_gateway_never_persists`, `backend/tests/test_garmin_service.py:1029-1055` (exatamente a prescrição, com `MidJobReauth(FakeGateway)` em `get_sleep`).
- **Verificado**: mutação M6 re-injetada na rodada 2 → KILLED (falha em `:1054`).

### Fix 2: Sub-caso "ilegível" do GTDB-12 sem evidência — ✅ RESOLVIDO

- **Prescrição original**: teste gravando `garmin_tokens.json` malformado, afirmando `SystemExit` != 0, "ilegível" no stderr e nenhuma linha.
- **Implementado em**: `cf64f9d` — `test_import_malformed_json_errors_without_writing`, `backend/tests/test_garmin_import.py:133-147` (JSON truncado em `tmp_path`, via `main()`).
- **Verificado**: mutação M-alvo-2 re-injetada na rodada 2 → KILLED (`JSONDecodeError` escapa `main()`, teste falha).

---

## Requirement Traceability Update

Não aplicado pelo Verifier (restrição de escrita: somente `validation.md` e lições). Sugestão ao orquestrador para `spec.md`:

| Requirement | Previous | New |
| ----------- | -------- | --- |
| GTDB-01..20 (todos) | Pending | ✅ Verified (20/20) |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 20/20 ACs matched spec outcome
**Sensor**: 4/4 mutations killed nesta rodada (8/8 distintos acumulados; M6 — único sobrevivente histórico — eliminado)
**Gate**: 550 passed, 0 failed (+57 vs baseline 493; +2 vs rodada 1)

**What works**: cofre Fernet com guard otimista (morto nos níveis store e service, re-confirmado na rodada 2); persist-back exclusivo dos finais done|error-genérico — agora PROVADO também com gateway vivo em 401 em pleno job; canal SYNC-25 preservado end-to-end (from_user → reauth, mutação M3 re-mortada); fail-fast da chave no startup antes do init_db; CLIs de login/import com recusa e zero gravação em falha — incluindo o arquivo ilegível; derivação de estado do /perfil com a emenda GTDB-16; extinção completa do tokenstore de arquivo (compose/env/README/code morto).

**Issues found**: nenhum (rodada 2 limpa).

**Next steps**: feature pronta para merge/conclusão. Rodar `validate_state.py` como gate final de Execute; atualizar `spec.md` (GTDB-01..20 → ✅ Verified).
