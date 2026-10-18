# ai-evaluation (Avaliar com IA) — Validation

**Date**: 2026-10-18
**Spec**: `.specs/features/ai-evaluation/spec.md` (emenda job 18/10 — ACs EVAL-21..25 + 04/05/08/13/14 reescritas)
**Diff range da emenda**: `44dea48..d6fa4bd` (10 commits — ver composição abaixo)
**Verifier**: subagente independente (author ≠ verifier); leitura read-only, mutações só em scratch descartável
**Iteration**: verificação da emenda (Phase 4, T14-T20) — 3ª passagem do verificador sobre a feature

---

## Validation — veredito da EMENDA: ✅ PASS

### Histórico das iterações

| Iteração | Range | Veredito | Resumo |
| -------- | ----- | -------- | ------ |
| 0 (feature original) | `33a06ac..df75158` | ❌ FAIL | gate 344 verde, sensor 3/3, mas 6 gaps de pino (Fixes 1-6) |
| 1 (fixes) | `df75158..d1c11d1` | ✅ PASS | 20/20 ACs, gate 355, sensor 3/3 novos (6/6 cumulativo) |
| UAT do usuário | — | — | "tomar um erro e perder tudo é um problema" → **emenda job** (POST pending + worker BackgroundTasks + polling) |
| **2 (esta — emenda)** | `44dea48..d6fa4bd` | **✅ PASS** | **25/25 ACs, gate 362, sensor 3/3 novos (9/9 cumulativo)** |

**Status**: ✅ Todas as 25 ACs cobertas (20 originais sem regressão + 5 novas); 0 gaps remanescentes.

### Composição do range `44dea48..d6fa4bd` (10 commits, não 9)

| Commit | Conteúdo | Escopo |
| ------ | -------- | ------ |
| `caa1f09` | compose: env file opcional do backend | infra (fora das tasks) |
| `150b653` | NIM: `content: null` (raciocinador esgota max_tokens) → `NimInvalidJSON` com `finish_reason`; `MAX_TOKENS` 2000→16000; timeout default 120s→**420s** | fix de UAT pré-emenda, documentado no design (risks + Tech Decisions) |
| `874c9a6` | docs(specs): emenda do spec/design/tasks | docs amenda |
| `7cad5a7` | T14: colunas `status`/`error` em `Evaluation` | emenda |
| `f15ad04` | T15: status/error em `EvaluationOut` | emenda |
| `59ad92e` | T16: service vira job (create + worker + recovery) | emenda |
| `e59e56d` | T17: POST 201 + GET de status + recovery no lifespan | emenda |
| `dc4faf3` | T18: contrato frontend do job | emenda |
| `549d1f5` | T19: UI pending + polling + erro preservado | emenda |
| `d6fa4bd` | T20: docs do fluxo assíncrono | emenda |

Os 2 commits fora das tasks são coerentes com a emenda (o `content: null` do UAT é exatamente o caso "NIM não devolve veredito" que a emenda transforma em linha `error` em vez de perder a tentativa).

---

## Task Completion (Phase 4)

| Task | Status | Notes |
| ---- | ------ |-------|
| T14 colunas status/error | ✅ Done | `models.py:218-220` (`status` default "pending", `error` nullable, docstring cita EVAL-21..23); suite recria schema por teste |
| T15 status no contrato | ✅ Done | `schemas.py:97-98`; espelho + pending válido (`test_evaluation_schemas.py:136-184`) |
| T16 service job | ✅ Done | `create_evaluation` (`service.py:63-110`), `run_evaluation` (`:124-167`), `recover_stale_evaluations` (`:170-186`); `evaluate()` síncrono removido |
| T17 endpoint 201 + GET + lifespan | ✅ Done | `router.py:23-59` (201 + `background_tasks.add_task` :58), `:62-72` (GET); `main.py:19,32` |
| T18 contrato frontend | ✅ Done | `api.ts:116-133` (status/error), `:279-291` (201/pending), `:295-304` (`getEvaluation`, no-store) |
| T19 UI do job | ⚠️ Done com ressalva de bookkeeping | polling/card/erro implementados e build+lint **verdes (re-run por mim nesta validação)** — mas o checkbox "npm run build + npm run lint verdes" ficou **desmarcado** em tasks.md (T19, último Done when). Conteúdo done; orquestrador pode marcar |
| T20 docs job | ✅ Done | README:264-265 (201 pending + worker background), :278 (recovery "interrompida") |

Tasks T1-T13: ✅ (validação anterior, nenhuma regressão — arquivos de payload/prompt/activities intocados no range).

---

## Spec-Anchored Acceptance Criteria (25/25)

### P1 — fluxo job (emenda)

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| **EVAL-21** (nova): WHEN pede avaliação válida THEN cria `status=pending` com `payload_json` montado e responde 201 — zero NIM no request path; validações rápidas síncronas nada criam quando falham | 201 com registro pending; payload já persistido; `calls == []` no POST; 404/422/503/500 sem linha | `backend/tests/test_evaluation_service.py:112-143` — `created["status"] == "pending"` (:125), `assert calls == []` (:131, pino por count), `row.payload_json["intencao"] == {"tipo": "facil", "texto": …}` (:135-138), `payload_json["zona_alvo"]["pct_zona_alvo"] == 84.5` (:139), `fresh.evaluated is False` (:143); HTTP: `backend/tests/test_evaluation_api.py:107-134` — `response.status_code == 201` (:119), `body["status"] == "pending"` (:121), `body["verdict_json"] is None` (:123); falhas síncronas nada criam: `:218-232` (422, zero rows), `:252-270` (503, zero rows); contrato: `backend/tests/test_evaluation_schemas.py:164-184` (pending sem veredito é válido) | ✅ PASS |
| **EVAL-22** (nova): WHEN worker recebe resposta THEN valida JSON e conclui `status=done` com veredito, `verdict_json` sanitizado, tokens do usage e `evaluated=true` | done; pct do Python (não eco); tokens 1234/56; evaluated true; linha não-pending é no-op | `backend/tests/test_evaluation_service.py:146-179` — `row.status == "done"` (:170), `row.verdict == "on_target"` (:171), `row.tokens_in == 1234 and row.tokens_out == 56` (:172), `verdict_json["execucao_vs_intencao"]["pct_zona_alvo"] == 84.5` com eco mockado 61.0 (:152-155,174 — sanitização), `fresh.evaluated is True` (:179); no-op: `:253-266` (`len(calls) == 1` após re-run, :263); end-to-end HTTP: `test_evaluation_api.py:107-134` (`row.status == "done"` :129, `evaluated is True` :134) | ✅ PASS |
| **EVAL-23** (nova): IF NIM erro HTTP/timeout THEN worker marca `status=error` com o motivo NA LINHA — a tentativa sobrevive; nenhum veredito inventado | linha error com motivo ("NIM HTTP 503"); intent_text preservado; evaluated false; worker não levanta | `backend/tests/test_evaluation_service.py:199-218` — `row.status == "error"` (:212), `"NIM HTTP 503" in row.error` (:213), `row.intent_text == "tento 1"` (:215, a tentativa sobrevive), `fresh.evaluated is False` (:218); veredito inválido → error: `:221-235` (`"fora do schema" in row.error` :234); exceção inesperada → error sem crash: `:238-250` (`"erro inesperado" in row.error` :250); HTTP end-to-end: `test_evaluation_api.py:137-157` (201 pending na resposta :148, `row.status == "error"` + motivo :153-154); finish_reason visível: `test_evaluation_nim.py:85-98` (`"finish_reason=length" in str(exc)` :97) | ✅ PASS |
| **EVAL-24** (nova): WHEN backend inicia com pending órfãs THEN startup marca `status=error` "interrompida" | pending pré-startup vira error com "interrompida" | `backend/tests/test_evaluation_service.py:269-281` — `row.status == "error"` (:280), `"interrompida" in row.error` (:281); via lifespan: `backend/tests/test_evaluation_api.py:187-205` — `with TestClient(app)` (:199, lifespan roda recovery), `row.status == "error"` (:204), `"interrompida" in row.error` (:205); wire: `backend/app/main.py:32` (`recover_stale_evaluations()` no lifespan); implementação: `backend/app/evaluation/service.py:170-186` | ✅ PASS |
| **EVAL-25** (nova): SHALL expor status por id (endpoint leve) para o polling | GET 200 com EvaluationOut; 404 id inexistente/de outro treino; polling ~2s na UI | `backend/tests/test_evaluation_api.py:160-184` — `status.status_code == 200` (:173), `body["status"] == "done"` (:175), `body["verdict_json"]["headline"]` (:177), 404 id (:180), 404 outro treino (:183); rota: `backend/app/evaluation/router.py:62-72`; frontend: `frontend/src/lib/api.ts:295-304` (`getEvaluation`, no-store) + polling `frontend/src/components/workouts/WorkoutDetail.tsx:81-114` (setInterval 2000ms :86,112, merge por id :96-98) | ✅ PASS |

### P1 — ACs originais reescritas pela emenda

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| **EVAL-04** (reescrita): WHEN resposta da NIM chega THEN validar contra schema e concluir done com veredito/verdict_json sanitizado/tokens/evaluated | enum 5 vereditos + confiança; extras ignorados, obrigatórios rejeitam; persistido no done (não mais na resposta HTTP) | Validação: `backend/tests/test_evaluation_schemas.py:28-95` (enum :41-45, obrigatório ausente :62-75, extras :78-84); conclusão: `test_evaluation_service.py:146-179` (todos os campos + `evaluated is True` — tabela EVAL-22 acima); exatamente uma chamada com prompt vigente: `:163-164` (`len(calls) == 1`, `capture["system"] == SYSTEM_PROMPT_V1`) | ✅ PASS |
| **EVAL-05** (reescrita): WHEN fica `done` THEN card com headline, selo ✅/⚠️/❌, % zona alvo, desvios, listas, confiança, modelo, tokens, data | card completo do §9.2; pending e error têm estados próprios | `frontend/src/components/workouts/EvaluationCard.tsx:79-117` — headline (:89), selo por veredito (:13-19,:90-92), pct (:95-99), desvios + 3 listas (:101-107), rodapé confiança·modelo·tokens·data (:110-114); estados da emenda: pending "Analisando treino…" (:48-63), error com motivo (:64-77); histórico ⏳/⚠️ (:122-126) | ✅ PASS (build+leitura; UAT pendente) |
| **EVAL-08** (reescrita): WHILE existe pending THEN botão desabilitado "Analisando treino…" e poll ~2s — nenhum clique duplo gera segunda avaliação | guarda = prop pending (fila), não a chamada; intervalo 2000ms | `frontend/src/components/workouts/EvaluateForm.tsx:67` (`const blocked = busy || pending`), disabled select/textarea/botão (:80,:100,:107), rótulo (:114), docstring "o guarda real contra fila dupla é a prop pending" (:54); prop vem de `WorkoutDetail.tsx:342` (`evaluations.some((e) => e.status === "pending")`); polling 2s: `WorkoutDetail.tsx:81-114` | ✅ PASS (build+leitura; UAT pendente) |
| **EVAL-13** (reescrita): IF NIM erro HTTP/timeout THEN worker marca error com motivo na linha — tentativa sobrevive, UI exibe o motivo | (mesma evidência da EVAL-23) | `test_evaluation_service.py:199-218`, `test_evaluation_api.py:137-157`, `test_evaluation_nim.py:85-98,120-128` (timeout NimTimeout), UI `EvaluationCard.tsx:64-77` (motivo inline :70) | ✅ PASS |
| **EVAL-14** (reescrita): IF JSON não valida THEN worker marca error com motivo — veredito nunca inventado | (mesma evidência da EVAL-23, ramo ValueError) | `test_evaluation_service.py:221-235`; cliente: `test_evaluation_nim.py:107-153` (HTTP 500 / não-JSON / envelope malformado / não-objeto) | ✅ PASS |

### P1/P2 — ACs originais inalteradas (re-derivadas; sem regressão)

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | -------------------- | ----------------------- | ------ |
| EVAL-01: form 7 tipos pré-preenchido + botão | select 7 opções, inferred_type default, botão | `test_evaluation_schemas.py:98-111` (7 aceitos); `EvaluateForm.tsx:20-28` (opções), `:42-44` (pré-preenchido), `:104-115` (botão) | ✅ PASS |
| EVAL-02: payload determinístico com blocos, só o que existir | resumo/voltas pinados por igualdade; % zona alvo exato | `backend/tests/test_evaluation_payload.py:152-189,238-263` (arquivo **intocado no range** — evidência da iteração 1 segue válida, re-lida) | ✅ PASS |
| EVAL-03: exatamente uma chamada NIM com prompt vigente | 1 chamada; system = SYSTEM_PROMPT_V1; user = payload | agora no worker: `test_evaluation_service.py:163-166` (`len(calls) == 1`, system, `sent["intencao"]["tipo"]`); marcadores do prompt `test_evaluation_prompt.py:81-91` (intocado); corpo `test_evaluation_nim.py:156-179` (max_tokens 16000, :175) | ✅ PASS |
| EVAL-06: model/prompt_version/tokens_in/out em toda avaliação | auditoria persistida (create grava model/version; worker grava tokens) | `backend/app/evaluation/service.py:101-102` (create), `:156-157` (worker); `test_evaluation_service.py:128-129,172`; `test_evaluation_schemas.py:154-157` | ✅ PASS |
| EVAL-07: payload 100% banco próprio | zero Garmin na avaliação | `test_evaluation_payload.py:309-315` (intocado — fonte nega `app.garmin`); único I/O externo é `nim.py`, mockado em 100% dos testes | ✅ PASS |
| EVAL-09: id inexistente → 404 "atividade não encontrada" | 404 + mensagem exata | `test_evaluation_api.py:208-215` (`detail == "atividade não encontrada"` :215); service None: `test_evaluation_service.py:284-286` | ✅ PASS |
| EVAL-10: não-corrida → 422 sem NIM, nada criado; UI omite form; trail aceito | 422; `calls == []`; zero rows | `test_evaluation_api.py:218-232` (422, zero rows :232); `test_evaluation_service.py:289-302` (yoga), `:305-318` (trail done + evaluated); UI `WorkoutDetail.tsx:194-195,338` | ✅ PASS |
| EVAL-11: intent inválido → 422 antes de payload/NIM | 422 tipo fora dos 7 e texto 501 | `test_evaluation_api.py:235-249`; pydantic `test_evaluation_schemas.py:122-133` | ✅ PASS |
| EVAL-12: key vazia → 503 sem NIM, nada gravado (+ precedência) | 503 citando NVIDIA_API_KEY; 503 antes da consulta | `test_evaluation_api.py:252-270` (503, `calls == []`, zero rows), `:273-282` (precedência com id 999) | ✅ PASS |
| EVAL-15: zonas falham → 500 "zonas VDOT não configuradas" | 500 + mensagem do padrão activities | `test_evaluation_api.py:285-295` (`detail == "zonas VDOT não configuradas"` :295) | ✅ PASS |
| EVAL-16: sem voltas → blocos omitidos, agregados seguem | voltas/zona omitidos; pace presente | `test_evaluation_payload.py:266-275` (intocado) | ✅ PASS |
| EVAL-17: detalhe lista DESC; UI card + histórico | mais recente primeiro; status no contrato | `test_evaluation_service.py:337-352` (`[second["id"], first["id"]]` :348, `status == "done"` :350); activities `test_activities_api.py:539-574` (intocado); UI `WorkoutDetail.tsx:345-350`, `EvaluationCard.tsx:129-158` | ✅ PASS |
| EVAL-18: re-avaliação → linha nova como mais recente | prepend; badge acende em done | `test_evaluation_service.py:344-352`; UI `WorkoutDetail.tsx:141-153` (prepend local) | ✅ PASS |
| EVAL-19: nunca sobrescrever/apagar | 2 linhas, primeira intacta | `test_evaluation_service.py:352` (`len(...) == 2`); worker nunca reprocessa não-pending (:253-266) | ✅ PASS |
| EVAL-20: badge "Avaliado" alimentado pelo motor; honesto na emenda | `evaluated` só em done; badge acende no done do polling | `backend/app/evaluation/service.py:159-161` (só no done); UI `WorkoutDetail.tsx:99-103` (badge acende quando `fresh.status === "done"`), `:215-219`; lista `WorkoutsList.tsx:47-49` (intocado) | ✅ PASS |

**Status**: ✅ 25/25 ACs cobertas — 0 gaps, 0 spec-precision gaps.

### Edge Cases (spec §Edge Cases)

| Edge | Evidência | Result |
| ---- | --------- | ------ |
| NIM sem `usage` → tokens 0, avaliação persiste | `test_evaluation_nim.py:76-82` (zeros); persistência: `test_evaluation_service.py:321-334` (`row.status == "done"`, `tokens_in == 0 and tokens_out == 0`) | ✅ |
| **NIM sem conteúdo (novo no range, `150b653`)**: content null/vazio (raciocinador esgota max_tokens) → `NimInvalidJSON` com finish_reason — na emenda vira linha error, não crash 500 | `test_evaluation_nim.py:85-107` (`"finish_reason=length"` :97); `backend/app/evaluation/nim.py:94-98` | ✅ |
| Campos extras ignorados; obrigatórios ausentes rejeitam | `test_evaluation_schemas.py:62-84` | ✅ |
| Padrões vazios / PR sem data → blocos omitidos | `test_evaluation_payload.py:278-288,203` (intocado) | ✅ |
| Dia sem PMC → bloco omitido | `test_evaluation_payload.py:285` | ✅ |
| Usuário sai do detalhe durante a avaliação → POST conclui no servidor | na emenda o POST nem espera: worker em background conclui; detalhe recarregado reflete o banco (avaliação done/error persistida) — verificação é UAT | ⏭️ UAT |
| Duas abas concorrentes → duas avaliações (sem lock) | EVAL-19 (`:352`); guarda é o botão por aba (`EvaluateForm.tsx:67`) | ✅ |

**Test Integrity**: nenhum teste chama a NIM real — vale para os novos (nim via MockTransport; service/api via monkeypatch de `nim.chat_completion`). `transport` segue sendo seam obrigatória nos testes do cliente.

---

## Discrimination Sensor

3 mutações **NOVAS** (as 6 das iterações anteriores não repetidas — alvos distintos: pct/sanitização/504, mapa TARGET_ZONES, Regra 1 do prompt, chamada dupla), todas sobre o código novo da emenda, no worktree scratch `C:\Users\leona\AppData\Local\Temp\opencode\ritmo-sensor` @ `d6fa4bd` com venv próprio (`uv sync` — pacote instala do próprio scratch, `import app` resolve para o scratch). Suite rodou contra o Postgres do compose (`ritmo_test`), uma suite por vez, sem concorrência.

**Baseline do scratch (unmutated)**: 3 passed (os 3 testes-alvo, 3,69s).

| Mutation | File:line (scratch) | Description | Killed? |
| -------- | -------------------- | ----------- | ------- |
| M7 | `backend/app/evaluation/service.py:100` | `payload_json=payload` → `payload_json=None` (create NÃO grava o payload — alvo a, EVAL-21) | ✅ Killed — 2 failed: `test_create_evaluation_pending_sem_chamar_nim` (`row.payload_json["intencao"]` quebra) e `test_worker_conclui_done_com_veredito_sanitizado` (`KeyError: 'intencao'` no capture da NIM em `test_evaluation_service.py:166` — worker chamaria a NIM com payload vazio) |
| M8 | `backend/app/evaluation/service.py:159-161` | `activity.evaluated = True` → `pass` (worker done ignora evaluated — alvo b, EVAL-22) | ✅ Killed — 2 failed: `test_worker_conclui_done_com_veredito_sanitizado` (`fresh.evaluated is True`, :179) e `test_post_201_pending_e_worker_conclui` (pós-condição HTTP, `test_evaluation_api.py:134`) |
| M9 | `backend/app/evaluation/service.py:178` | filtro do recovery `STATUS_PENDING` → `STATUS_DONE` (órfãs nunca marcadas — alvo c, EVAL-24) | ✅ Killed — 2 failed: `test_recover_stale_pending_vira_interrompida` (`row.status == "error"`, :280) e `test_lifespan_recupera_pending_orfa` (lifespan, :204) |

**Sensor depth**: lightweight (3 mutações; feature não-P0) — cumulativo da feature: **9 mutações, 9/9 mortas** (3 iteração 0 + 3 iteração 1 + 3 nesta).
**Result**: 3/3 mortas nesta iteração, 0 sobreviventes ✅

**Nota adversarial sobre o alvo (d) — router não despachar BackgroundTask** (leitura, sem mutante — teto de 3 do tier lightweight): a dispatch é `backend/app/evaluation/router.py:58` (`background_tasks.add_task(service.run_evaluation, result["id"])`). Três testes de API afirmam a PÓS-CONDIÇÃO do worker após `post()` retornar (o TestClient executa background tasks no ciclo do request): `test_post_201_pending_e_worker_conclui` (`row.status == "done"`, :129), `test_post_erro_nim_vira_linha_error` (`row.status == "error"`, :153) e `test_get_status_do_polling` (`body["status"] == "done"`, :175). Sem a dispatch, a linha ficaria `pending` e as três asserções falham mecanicamente — sem caminho de sobrevivência.

**Isolamento**: worktree removido com `git worktree remove --force` (diretório confirmado inexistente); `git worktree list` mostra só o principal; `git status --porcelain` da árvore real **limpo antes e depois**, idêntico ao baseline. Nenhum `git stash` usado.

---

## Gate Check

- **Gate command** (tasks.md): `cd backend; uv run pytest` + `cd frontend; npm run build; npm run lint`
- **Backend**: **362 passed, 0 failed, 0 skipped** (237,98s ≈ 4 min; Postgres do compose `ritmo_test`, execução única — nenhuma suite concorrente; sem órfãos pytest antes de rodar). 1 warning pré-existente (StarletteDeprecationWarning do `fastapi.testclient`, não é skip). **Exatamente o esperado (362).**
- **Frontend**: `npm run build` ✅ (rotas geradas, incluindo `/treinos/[id]` PPR) e `npm run lint` ✅ (zero achados) — **executados por mim nesta validação**, o que fecha o checkbox de T19 que ficou desmarcado em tasks.md.
- **Test count before emenda**: 355 (validação 1)
- **Test count after emenda**: 362
- **Delta**: **+7**, conferido por arquivo (dots do gate): `test_evaluation_nim.py` 9→11 (+2, content null — commit `150b653`), `test_evaluation_schemas.py` 16→17 (+1, pending no contrato — T15), `test_evaluation_service.py` 10→14 (+4, fluxo job — T16/T17), `test_evaluation_api.py` 11→11 (reescrito para 201+worker, mesmo count). 355 + 7 = 362 ✓
- **Skipped**: nenhum
- **Failures**: nenhuma
- **Test Integrity Check**: contagem só subiu; testes de API/service foram REESCRITOS para o fluxo job (502/504 HTTP deixaram de existir para NIM — agora viram linha `error`, mais forte que antes porque afirma persistência + pós-condição do worker, não só status HTTP); nenhuma asserção enfraquecida; nenhum teste deletado sem substituto (cada caso de erro antigo tem correspondente novo afirmando a linha error).

---

## Interactive UAT

Não executado (subagente sem acesso interativo; UAT ao vivo com NIM real é do usuário, que está UAT-ando em paralelo — não é gap deste verificador). Roteiros atualizados para a emenda:

| # | Teste | Result |
| - | ----- | ------ |
| 1 | Avaliar corrida real → card pending na hora ("Analisando treino…", botão travado) → polling troca para veredito sem recarregar; tokens/modelo/data no rodapé | ⏭️ Pendente (usuário) |
| 2 | Simular falha (key inválida/NIM fora) → card de erro com o motivo; tentativa preservada no histórico; botão volta | ⏭️ Pendente (usuário) |
| 3 | Restart do backend com avaliação em curso → linha vira error "interrompida" (recovery visível) | ⏭️ Pendente (usuário) |
| 4 | Spot-check: treino fácil acima da zona easy nunca sai ✅ | ⏭️ Pendente (usuário) |

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ emenda segue o padrão SyncJob existente (`garmin/service.py`) sem abstrações novas |
| Surgical changes | ✅ range = emenda + 2 fixes de UAT coerentes (nim null-content, compose env); zero escopo além disso |
| No scope creep | ✅ migração mínima (2 colunas, sem Alembic — padrão do repo: suite recria schema; ALTER no banco vivo documentado em design.md) |
| No unnecessary flexibility | ✅ `get_evaluation` filtra por activity+id+user (sem endpoint genérico) |
| Matches patterns | ✅ `_mark_error`/no-op/guard `except Exception` espelham o worker do sync; 201+BackgroundTasks espelha `garmin/router.py` |
| Spec-anchored outcome check | ✅ 25/25 — asserções casam com os desfechos da emenda (201+pending por count; error-row com motivo; recovery "interrompida"; GET 404 de outro treino) |
| Per-layer Coverage Expectation | ✅ service 1:1 com EVAL-21..24; rotas: happy (201+worker) + GET 200/404 + todos os erros síncronos; frontend sem runner (padrão do repo — build+lint+leitura) |
| Every test maps to a spec requirement | ✅ testes novos citam EVAL-21..25 no docstring; zero testes sem AC |
| Documented guidelines followed: `README.md` §Testes/§Rodando; `frontend/AGENTS.md` | ✅ |

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| EVAL-01..03, 06..12, 15..20 | ✅ Verified | ✅ Verified (sem regressão; arquivos de teste correspondentes intocados ou re-pinados) |
| EVAL-04 | ✅ Verified (fluxo síncrono) | ✅ Verified (fluxo job — worker done) |
| EVAL-05 | ✅ Verified | ✅ Verified (card + estados pending/error) |
| EVAL-08 | ✅ Verified | ✅ Verified (guard pending + polling 2s) |
| EVAL-13 | ✅ Verified (502/504 HTTP) | ✅ Verified (linha error com motivo) |
| EVAL-14 | ✅ Verified (502 HTTP) | ✅ Verified (linha error com motivo) |
| EVAL-21 | Implementing | ✅ Verified |
| EVAL-22 | Implementing | ✅ Verified |
| EVAL-23 | Implementing | ✅ Verified |
| EVAL-24 | Implementing | ✅ Verified |
| EVAL-25 | Implementing | ✅ Verified |

`spec.md` atualizado nesta validação: EVAL-21..25 → ✅ Verified. Assumption "Síncrono vs job" já marcada `y` na emenda (spec.md:48).

---

## Fix Plans

Nenhum gap remanescente. 0 mutantes sobreviventes, 0 spec-precision gaps.

Ressalva de bookkeeping (não é gap de código): o último checkbox "Done when" de **T19** (build+lint) está desmarcado em tasks.md — os gates passam (re-run por mim); orquestrador pode marcar.

---

## Summary

**Overall**: ✅ Ready (backend + frontend validados; UAT ao vivo pendente com o usuário)

**Spec-anchored check**: 25/25 ACs com o desfecho verificado por `file:line` | 0 gaps | 0 spec-precision gaps
**Sensor**: 3/3 mutações novas mortas (9/9 cumulativo na feature)
**Gate**: backend 362 passed, 0 failed, 0 skipped (exatamente o esperado: 355 + 7); frontend build+lint verdes

**What works (emenda)**: POST responde 201 com o pending e **nunca** toca a NIM no request path (pino por count); worker conclui done com veredito sanitizado + tokens + `evaluated=true`; falha da NIM/veredito/exceção inesperada vira linha `error` com o motivo — **a tentativa sobrevive** (a queixa do UAT, resolvida); startup recupera órfãs como "interrompida"; GET de status alimenta o polling de ~2s; UI trava o botão enquanto há pending e renderiza os três estados; `content: null` do raciocinador vira erro de contrato com `finish_reason` (nada de crash 500); timeout default 420s cobre modelos raciocinadores. O que a iteração 1 validou continua de pé (payload determinístico, mapa de erros síncrono, sanitização, append-only, detalhe DESC).

**Issues found**: nenhum nesta iteração.

**Next steps**: UAT ao vivo com o usuário (4 roteiros acima); nenhuma task de correção para rotear.
