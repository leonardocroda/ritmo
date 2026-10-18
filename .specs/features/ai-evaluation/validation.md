# ai-evaluation (Avaliar com IA) — Validation

**Date**: 2026-10-18
**Spec**: `.specs/features/ai-evaluation/spec.md`
**Diff range**: `33a06ac..d1c11d1` (16 commits, incl. spec `4019ad8`, docs `df75158`, gaps `f711034`, fixes `d1c11d1`)
**Verifier**: subagente independente (author ≠ verifier); leitura read-only, mutações só em scratch descartável
**Iteration**: re-verificação 1 de no máximo 3 (fix `d1c11d1` → re-verify)

---

## Validation — veredito: ✅ PASS

### Histórico da iteração anterior (resumo)

- **Iteração 0** (range `33a06ac..df75158`): veredito **FAIL** — gate verde (344 passed) e sensor 3/3, mas **6 gaps de pino de teste/contrato** sobre desfechos que o spec **enumera** (evidence-or-zero): resumo/voltas sem pino de campo (Fix 1), mapa TARGET_ZONES 3/7 (Fix 2), marcadores centrais do prompt + chamada única sem count (Fix 3), aceitação de trail_running (Fix 4), edge usage-zeros sem persistência end-to-end (Fix 5), precedência 503 vs 404/422 indefinida (Fix 6, spec-precision). Nenhum bug de comportamento.
- **Fixes**: commit `d1c11d1` (`test(evaluation): pin verifier gaps in payload service and prompt`) — 6 arquivos: só testes backend + docs do spec/design; **zero mudança de implementação** (diff stat confirma).
- **Esta iteração** (`df75158..d1c11d1`): os 6 fixes foram confirmados com `file:line` + expressão de asserção; cobertura das 20 ACs re-derivada sem regressão; gate **355 passed**; sensor **3/3 mutações novas mortas**; árvore real limpa antes e depois.

**Status**: ✅ Todas as 20 ACs cobertas; 6/6 fixes confirmados; 0 gaps remanescentes.

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 Config NIM/LTHR + httpx runtime | ✅ Done | defaults 120s/177 pinados (`test_evaluation_config.py:28-54`, arquivo intacto nesta iteração); httpx em `dependencies` |
| T2 Schemas | ✅ Done | 16 testes (`test_evaluation_schemas.py:28-139` re-lido nesta iteração) |
| T3 System prompt v1 | ✅ Done | 9 testes; Fix 3 fecha os 3 marcadores que faltavam |
| T4 Payload determinístico | ✅ Done | aritmética exata + **Fix 1 (resumo/voltas por dict inteiro)** + **Fix 2 (mapa 7/7)** |
| T5 Cliente NIM | ✅ Done | MockTransport em 100% dos casos; corpo pinado (`:132-155`) |
| T6 Orquestração/persistência | ✅ Done | happy path + falha-nada-gravado; **Fix 3** (`len(calls) == 1`), **Fix 4**, **Fix 5** nesta camada |
| T7 Endpoint + mapa de erros | ✅ Done | 404/422×3/503/502×2/504/500 pinados; **Fix 6** (precedência 503) aqui |
| T8 Detalhe estendido | ✅ Done | `evaluations` mais-recente-primeiro + `activity_type` (`test_activities_api.py:539-574` re-lido) |
| T9 Contrato frontend | ✅ Done | tipos espelham o backend; build+lint verdes (iteração anterior) |
| T10 EvaluateForm | ✅ Done | pré-preenchimento, busy/"Analisando treino…"; UAT pendente |
| T11 EvaluationCard | ✅ Done | selo ✅/⚠️/❌, listas, rodapé; UAT pendente |
| T12 Composição | ✅ Done | isRunning gate, prepend local, badge; UAT pendente |
| T13 Docs | ✅ Done | README + PLANO §6 Fase 1 |
| **Fix task** (6 gaps do Verifier) | ✅ Done | `d1c11d1` — +11 testes (7 param + 4), 0 implementação |

Todas as 13 tasks [x] em tasks.md + fix task commitada. Contagens: 280 → 344 (iteração 0) → **355** (+11: payload +7 param, prompt +1, service +2, api +1 — confere com os dots por arquivo no gate).

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| EVAL-01: WHEN abre detalhe de corrida THEN formulário de intenção + botão | seletor 7 tipos, pré-preenchido com `inferred_type`; texto ≤500 opcional; botão "Avaliar com IA" | `backend/tests/test_evaluation_schemas.py:98-111` - `EvaluateIn(intent_type=t)` aceita os 7, `intent_text is None`; `:114-119` `len == 500` ok; UI `frontend/src/components/workouts/EvaluateForm.tsx:39-41,20-28,107` (build+leitura, UAT pendente) | ✅ PASS |
| EVAL-02: WHEN intenção válida THEN payload Python com blocos enumerados, só com o que existir | resumo (12 campos spec), voltas (7 campos spec), % por zona, % zona alvo (mapa assumption linha 47), consistência (gate ≥8km/≥4 voltas), contexto, PMC, zonas, LTHR, PRs datados, VDOT, padrões | **Fix 1**: `backend/tests/test_evaluation_payload.py:152-167` - `assert payload["resumo"] == {…14 campos por valor}` (incl. `cadencia_media == 170.0`, `elevacao_gain_m == 55.0`, `te_aerobico == 2.8`, `te_anaerobico == 0.4`, `carga_treino == 120.0`); `:180-189` - `assert voltas[0] == {…8 campos}` (incl. `fc == 142`, `cadencia == 165.0`, `temperatura_c == 22.0`, `elevacao_m == 12.5`); seeds povoam tudo (`:56-81`, `:84-101`). **Fix 2**: `:238-263` - parametrizado sobre as 7 intenções, `assert payload["zona_alvo"]["zonas"] == expected_zones` / `assert "zona_alvo" not in payload`. Aritmética: `:170-175` (easy 84,5 / repetition 15,5, soma 100,0); contexto `:193-197`; PMC `:200`; PRs/VDOT/LTHR `:203-205`; padrões `:207-214`; zonas `:216-219`; consistência gate `:221-222` fora <8km, `:291-306` dentro + longão 100,0; omissões honestas `:278-288`; sem voltas `:266-275` | ✅ PASS (gaps Fix 1-2 fechados) |
| EVAL-03: WHEN payload montado THEN exatamente uma chamada NIM com system prompt vigente (intenção primeiro, contexto nunca decora, elevação), PT-BR, JSON §9.2, números exclusivos do payload | uma chamada; prompt com as regras destiladas; instrução de não recalcular | **Fix 3**: `backend/tests/test_evaluation_service.py:120-121,128` - `calls: list = []` + `assert len(calls) == 1` (duplicar a chamada falha); `:152-155` - `capture["system"] == SYSTEM_PROMPT_V1`, user é o payload JSON; `backend/tests/test_evaluation_prompt.py:81-91` - `assert "A intenção vem antes dos números" in SYSTEM_PROMPT_V1` (`:86`, Regra 1), `"FALHA de execução"` (`:87`), `"Contexto muda o veredito ou o confirma; nunca é decoração"` (`:89`), `"voltas com muito ganho de elevação explicam pace mais lento"` (`:91`) — todos presentes em `backend/app/evaluation/prompt.py:19-22,30,34`; corpo da chamada `backend/tests/test_evaluation_nim.py:132-155` (URL, Bearer, model, temperature 0.2, max_tokens 2000, messages); demais marcadores `:38-78` | ✅ PASS (gap Fix 3 fechado) |
| EVAL-04: WHEN resposta chega THEN validar contra schema e persistir tudo; `evaluated = true` | enum 5 vereditos + confiança; extras ignorados, obrigatórios rejeitam; persiste intent/payload/model/prompt_version/verdict/tokens | `backend/tests/test_evaluation_schemas.py:28-95`; `backend/tests/test_evaluation_service.py:115-147` (todos os campos + `fresh.evaluated is True`); `backend/tests/test_evaluation_api.py:112-137` (200 EvaluationOut completo) | ✅ PASS |
| EVAL-05: WHEN persistida THEN card com headline, selo, % zona alvo, desvios, listas, confiança, modelo, tokens, data | card renderiza todos os campos; selo ✅/⚠️/❌ | `frontend/src/components/workouts/EvaluationCard.tsx:13-19,53-63,65-71,74-78` (build+leitura; UAT pendente; sem mudança frontend nesta iteração — diff stat só .specs + backend/tests) | ✅ PASS |
| EVAL-06: SHALL gravar model, prompt_version, tokens_in/out em toda avaliação | linha persistida sempre com os 4 campos de auditoria | `backend/tests/test_evaluation_service.py:131-134,141-143`; `backend/tests/test_evaluation_api.py:126-129`; **Fix 5** estende o edge de tokens: `test_evaluation_service.py:274-286` | ✅ PASS |
| EVAL-07: SHALL montar payload lendo exclusivamente o banco próprio | zero chamada Garmin na avaliação | `backend/tests/test_evaluation_payload.py:309-315` (fonte nega `app.garmin`/`garminconnect`); suite semeia direto no banco; único I/O externo é `nim.py`, mockado em 100% dos testes | ✅ PASS |
| EVAL-08: WHILE chamada em curso THEN botão desabilitado "Analisando treino…" | sem segundo clique durante a chamada | `frontend/src/components/workouts/EvaluateForm.tsx:43-44,100,107` (build+leitura; UAT pendente) | ✅ PASS |
| EVAL-09: IF id não existe THEN 404 "atividade não encontrada" | status 404 com mensagem exata | `backend/tests/test_evaluation_api.py:140-147` (`status_code == 404`, `detail == "atividade não encontrada"`); `test_evaluation_service.py:229-231` (None) | ✅ PASS |
| EVAL-10: IF não é corrida (running/trail_running) THEN 422 sem chamar NIM; UI omite formulário | 422 antes da NIM; trail_running aceito; UI só renderiza para corrida | Rejeição: `backend/tests/test_evaluation_api.py:150-163` (422 yoga, `calls == []`, `_nothing_saved`); `test_evaluation_service.py:234-247` (ActivityNotRunning, zero chamadas). **Fix 4**: `test_evaluation_service.py:256-271` - `test_trail_running_aceita_avaliacao` semear `activity_type="trail_running"`, avalia, `row.activity_id == trail.id`, `fresh.evaluated is True` (remover trail de `service.py:27` falha). UI `WorkoutDetail.tsx:150,293` | ✅ PASS (gap Fix 4 fechado) |
| EVAL-11: IF intent_type fora dos 7 ou texto >500 THEN 422 antes de payload/NIM | 422 automático na validação | `backend/tests/test_evaluation_api.py:166-171,174-180` (422 "fácil", 422 texto 501); `test_evaluation_schemas.py:122-133` | ✅ PASS |
| EVAL-12: IF NVIDIA_API_KEY vazia THEN 503, sem NIM, nada gravado | 503 citando a var | `backend/tests/test_evaluation_api.py:183-200` (503, "NVIDIA_API_KEY", `calls == []`, `_nothing_saved`) | ✅ PASS |
| EVAL-13: IF NIM erro HTTP ou timeout THEN 502/504 PT-BR, sem gravar | NimError→502; NimTimeout→504 | `backend/tests/test_evaluation_api.py:203-214,231-242` (ambos `_nothing_saved`); `test_evaluation_nim.py:85-93,96-104` | ✅ PASS |
| EVAL-14: IF JSON não valida THEN 502 sem gravar | veredito nunca inventado | `backend/tests/test_evaluation_api.py:217-228`; `test_evaluation_service.py:213-226`; `test_evaluation_nim.py:107-129` | ✅ PASS |
| EVAL-15: IF arquivo de zonas falha THEN 500 "zonas VDOT não configuradas" | 500 com a mensagem do padrão activities | `backend/tests/test_evaluation_api.py:245-255` (500 + detail exato) | ✅ PASS |
| EVAL-16: WHEN sem voltas THEN payload omite bloco e prossegue | blocos omitidos; agregados seguem | `backend/tests/test_evaluation_payload.py:266-275` (`voltas`/`tempo_por_zona_pct`/`zona_alvo`/`consistencia` ausentes; `pace_medio == "5:00/km"`); prompt `:75-78` | ✅ PASS |
| EVAL-17: WHEN detalhe aberto THEN avaliações mais recente primeiro; UI card + anteriores resumidas | lista DESC; UI card + histórico | `backend/tests/test_activities_api.py:539-563` (`["on_target","too_hard"]` + campos completos), `:566-574` (`== []`); `test_evaluation_service.py:193-195` (ordem nova-primeiro); UI `WorkoutDetail.tsx:298-299`, `EvaluationCard.tsx:85-111` | ✅ PASS |
| EVAL-18: WHEN reavalia THEN linha nova como mais recente, anteriores mantidas | linha nova; nenhuma sobrescrita | `backend/tests/test_evaluation_service.py:179-195` (2 linhas, nova-primeiro); UI `WorkoutDetail.tsx:94-108` (prepend local, sem refetch) | ✅ PASS |
| EVAL-19: SHALL nunca sobrescrever nem apagar | re-avaliação só adiciona; primeira intacta | `backend/tests/test_evaluation_service.py:188-191` (`rows[0].intent_text == "primeira"`, `rows[1] == "segunda"`); service só cria `Evaluation` | ✅ PASS |
| EVAL-20: WHEN avaliado THEN badge "Avaliado" na lista | flag `evaluated` alimentada; badge acende | `backend/tests/test_evaluation_service.py:135-137,269-271`; `test_evaluation_api.py:134-137`; UI `WorkoutsList.tsx:47-49` | ✅ PASS |

### Edge Cases (spec §Edge Cases)

| Edge | Evidência | Result |
| ---- | --------- | ------ |
| NIM sem `usage` → persiste com tokens 0 | Cliente: `backend/tests/test_evaluation_nim.py:76-82` (`usage == {"prompt_tokens": 0, "completion_tokens": 0}`). **Fix 5**: persistência end-to-end `backend/tests/test_evaluation_service.py:274-286` (`row.tokens_in == 0 and row.tokens_out == 0`, `scalar_one()` prova linha única persistida) | ✅ (gap Fix 5 fechado) |
| Campos extras ignorados; obrigatórios ausentes rejeitam | `backend/tests/test_evaluation_schemas.py:62-84` | ✅ |
| Padrões vazios / PR sem data → blocos omitidos | `backend/tests/test_evaluation_payload.py:220-230` (agora `:278-288`), `:203` (PR 10K sem data fora; LONGEST_RUN não-canônico fora) | ✅ |
| Dia sem PMC → bloco omitido | `backend/tests/test_evaluation_payload.py:285` | ✅ |
| Usuário sai do detalhe durante avaliação → POST conclui no servidor | comportamento síncrono inerente ao POST; verificação é UAT | ⏭️ UAT |
| Duas abas concorrentes → duas avaliações (sem lock por design) | EVAL-19 (2 linhas, `test_evaluation_service.py:188-191`); guarda é o botão por aba | ✅ |

**Test Integrity**: nenhum teste chama a NIM real — vale também para os 11 novos (trail/usage usam `_mock_nim` monkeypatch; mapa/prompt são asserts de conteúdo; o teste de precedência 503 usa id inexistente, sem NIM). `nim.py` só é exercido via `httpx.MockTransport` ou monkeypatch; `transport` é parâmetro obrigatório nos testes.

---

## Discrimination Sensor

3 mutações **NOVAS** (diferentes da iteração 0, que matou pct/sanitização/504), todas sobre os **pinos novos** desta iteração, no worktree scratch `d1c11d1` com venv próprio (`uv sync`; pacote `ritmo-backend` instala do próprio scratch, então `import app` resolve para o scratch):

| Mutation | File:line (scratch) | Description | Killed? |
| -------- | --------- | ----------- | ------- |
| 4 | `backend/app/evaluation/payload.py:25` | `TARGET_ZONES["tempo"]: ["threshold"]` → `["easy"]` (mapa de zonas alvo — Fix 2) | ✅ Killed — `test_zona_alvo_por_intencao_mapa_completo[tempo]` falha: `AssertionError: assert ['easy'] == ['threshold']` (`test_evaluation_payload.py:263`) |
| 5 | `backend/app/evaluation/prompt.py:19-22` | deletado o bloco da Regra 1 inteiro ("intenção primeiro" — regra central, Fix 3) | ✅ Killed — `test_prompt_pina_regras_centrais_do_spec` falha em `test_evaluation_prompt.py:86` (`assert "A intenção vem antes dos números" in SYSTEM_PROMPT_V1`) |
| 6 | `backend/app/evaluation/service.py:67-69` | chamada NIM duplicada no `evaluate` (2ª chamada idêntica — Fix 3) | ✅ Killed — `test_happy_path_persiste_todos_campos` falha em `test_evaluation_service.py:128`: `AssertionError: assert 2 == 1` |

**Sensor depth**: lightweight (3 mutações; feature não-P0) — cumulativo com a iteração 0: 6 mutações, 6/6 mortas.
**Result**: 3/3 mortas nesta iteração, 0 sobreviventes ✅

Isolamento: baseline do scratch unmutated 17 passed (7 mapa + 9 prompt + 1 happy path). Cada mutação revertida com `git checkout --` no scratch; worktree removido com `git worktree remove --force` (sem resíduo — diretório confirmado inexistente). `git status --porcelain` da árvore real: limpo antes e depois, idêntico ao baseline.

Nota adversarial sobre os demais fixes (leitura, sem mutante — orçamento lightweight 1-3 cumprido): Fix 1 é igualdade `==` de dict literal de 14/8 campos contra seeds que povoam exatamente esses campos (`test_evaluation_payload.py:56-101`) — deletar qualquer campo do `_resumo`/`_voltas` quebra a igualdade mecanicamente, sem caminho de sobrevivência; Fixes 4/5/6 são testes de propósito único cuja asserção espelha direto o desfecho do spec (trail avaliado com NIM; tokens 0 persistidos; 503 antes da consulta com id inexistente 999).

---

## Gate Check

- **Gate command** (tasks.md): `cd backend; uv run pytest` (Quick/Full/Build backend) + `cd frontend; npm run build; npm run lint` (Build frontend)
- **Backend**: **355 passed, 0 failed, 0 skipped** (242,01s; Postgres do compose `ritmo_test`, execução única, nenhuma suite concorrente). 1 warning pré-existente (StarletteDeprecationWarning do `fastapi.testclient`, não é skip). **Exatamente o esperado: 344 + 11 novos.**
- **Frontend**: `npm run build` + `npm run lint` verdes na iteração anterior (em `df75158`); **nenhum arquivo frontend mudou em `df75158..d1c11d1`** (diff stat: só `.specs` + `backend/tests`) — sem novo fato, veredito mantido (regra: não reabrir o já Verified).
- **Test count before feature**: 280 (baseline T1)
- **Test count after feature**: 355
- **Delta**: +75 (64 na iteração 0; **+11 nesta**: T-map 7 param, prompt +1, service +2, api +1 — dots por arquivo no gate conferem: payload 13, prompt 9, service 10, api 11)
- **Skipped**: nenhum
- **Failures**: nenhuma
- **Test Integrity Check**: contagem só subiu; asserções só foram fortalecidas (resumo 7→14 campos por igualdade de dict; volta 3→8; mapa 4→7; prompt 5→8 marcadores; novo count de chamada) — nenhum teste deletido, nenhuma asserção enfraquecida.

---

## Interactive UAT

Não executado (subagente sem acesso interativo; UAT ao vivo com NIM real + key real é do usuário/orquestrador). Pendências inalteradas:

| # | Teste | Result |
| - | ----- | ------ |
| 1 | Avaliar corrida real com key real → card com veredito, listas, tokens e data; recarregar → card persistido; badge "Avaliado" | ⏭️ Pendente |
| 2 | Spot-check do success criteria: treino fácil acima da zona easy nunca sai ✅ | ⏭️ Pendente |
| 3 | Re-avaliar treino avaliado → 2 entradas, nova como card | ⏭️ Pendente |
| 4 | Detalhe de não-corrida (yoga/força) → sem formulário | ⏭️ Pendente |

---

## Code Quality

| Principle | Status |
| ---------- | ------ |
| Minimum code | ✅ fix commit não toca implementação — só testes e docs de spec |
| Surgical changes | ✅ `df75158..d1c11d1` = 9 arquivos, todos no escopo dos 6 fixes + registro de lessons |
| No scope creep | ✅ `calls`/seeds são infra de teste dos próprios pins; nenhum comportamento novo |
| No unnecessary flexibility | ✅ nenhuma abertura nova |
| Matches patterns | ✅ parametrização espelha `test_evaluation_schemas.py:41`; novo teste api segue o padrão monkeypatch get_settings |
| Spec-anchored outcome check | ✅ 20/20 — asserções casam com o desfecho do spec (mapa = assumption linha 47; marcadores = EVAL-03; trail = EVAL-10; tokens 0 = edge; precedência = assumption linha 53) |
| Per-layer Coverage Expectation | ✅ domínio 1:1 com ACs; rota: happy + todos os erros + precedência |
| Every test maps to a spec requirement | ✅ os 11 novos citam EVAL-xx/Fix no docstring; zero testes sem AC |
| Documented guidelines followed: `README.md` §Testes/§Rodando; `frontend/AGENTS.md` | ✅ |

Redundância benigna: `test_progressivo_e_prova_sem_zona_alvo` (`:225-235`) e o novo mapa (`:238-263`) cobrem progressivo/prova — o primeiro também afirma a distribuição (easy 100,0), não é redundância pura; nenhum problema.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| EVAL-01 | ✅ Verified | ✅ Verified |
| EVAL-02 | ❌ Needs Fix (Fixes 1-2) | ✅ Verified |
| EVAL-03 | ❌ Needs Fix (Fix 3) | ✅ Verified |
| EVAL-04 | ✅ Verified | ✅ Verified |
| EVAL-05 | ✅ Verified | ✅ Verified (build + leitura; UAT pendente) |
| EVAL-06 | ✅ Verified | ✅ Verified |
| EVAL-07 | ✅ Verified | ✅ Verified |
| EVAL-08 | ✅ Verified | ✅ Verified (build + leitura; UAT pendente) |
| EVAL-09 | ✅ Verified | ✅ Verified |
| EVAL-10 | ❌ Needs Fix (Fix 4) | ✅ Verified |
| EVAL-11..EVAL-20 | ✅ Verified | ✅ Verified (nenhum reaberto sem novo fato) |

spec.md atualizado nesta validação: EVAL-02/03/10 → ✅ Verified. Assumption nova "Precedência 503 vs 404/422" (spec.md:53) + fluxo do design.md:32 alinhado à implementação.

---

## Fix Plans

Nenhum — 0 gaps remanescentes. Todos os 6 fixes da iteração anterior foram confirmados com evidência e os pinos novos discriminam (sensor 3/3).

---

## Summary

**Overall**: ✅ Ready (backend validado; UAT ao vivo pendente com o usuário)

**Spec-anchored check**: 20/20 ACs com o desfecho verificado por `file:line` | 0 gaps | 0 spec-precision gaps (Fix 6 resolvido por decisão documentada + pino)
**Sensor**: 6/6 mutações mortas no cumulativo (3 na iteração 0 + 3 novas nesta, todas nos pinos novos)
**Gate**: 355 passed, 0 failed, 0 skipped (344 + 11 novos, exatamente o esperado); frontend build+lint verdes (iteração anterior, sem mudança desde então)

**What works**: tudo o que a iteração 0 validou continua de pé (payload determinístico 100% banco com aritmética exata; NIM com corpo pinado e zero chamada real; mapa de erros completo com nada gravado em falha; persistência auditável; sanitização do eco; re-avaliação só adiciona; detalhe DESC + activity_type) **e** os 6 gaps estão fechados: resumo 14/14 e voltas 8/8 por igualdade de dict; mapa TARGET_ZONES 7/7; Regra 1/contexto/elevação pinados no prompt; chamada única pinada por count; trail_running aceito; usage-zeros persistidos; precedência 503 decidida, documentada (spec.md:53, design.md:32) e pinada.

**Issues found**: nenhum nesta iteração.

**Next steps**: UAT ao vivo com o usuário (NIM real + key real — 4 roteiros acima); nenhuma task de correção para rotear.
