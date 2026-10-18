# ai-evaluation (Avaliar com IA) — Validation

**Date**: 2026-10-18
**Spec**: `.specs/features/ai-evaluation/spec.md`
**Diff range**: `33a06ac..df75158` (14 commits, incl. o commit de spec `4019ad8`)
**Verifier**: subagente independente (author ≠ verifier); leitura read-only, mutações só em scratch descartável

---

## Validation — veredito: ❌ FAIL

O gate está verde (344 passed) e o sensor matou 3/3 mutantes. O motor funciona conforme o spec por leitura: payload determinístico 100% do banco, NIM mockada em todos os testes, mapa de erros HTTP completo, nada gravado em falha, sanitização do eco AD-003. Nenhum bug de comportamento foi encontrado.

O veredito é FAIL porque 5 desfechos que o spec **enumera** estão sem pino de asserção: deletar qualquer um deles da implementação deixaria a suite verde. Evidence-or-zero: critério enumerado sem `file:line` = não coberto. São gaps de teste (strengthening), não de comportamento. Um deles atinge a regra central da feature (intenção primeiro, EVAL-03). Há ainda 1 spec-precision gap (precedência 503 vs 404/422, indefinida no spec).

**Status**: ❌ Gaps presentes (5 pinos de teste ausentes + 1 spec-precision gap)

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 Config NIM/LTHR + httpx runtime | ✅ Done | defaults 120s/177 pinados (`test_evaluation_config.py:28-54`); httpx em `dependencies` |
| T2 Schemas | ✅ Done | 16 testes coletados confirmam a contagem da task |
| T3 System prompt v1 | ✅ Done | 8 testes de marcadores; 3 marcadores do spec ficaram de fora (Fix 3) |
| T4 Payload determinístico | ✅ Done | aritmética exata pinada; campos de resumo/voltas e 3/7 mapeamentos sem pino (Fixes 1-2) |
| T5 Cliente NIM | ✅ Done | MockTransport em 100% dos casos; corpo da chamada pinado |
| T6 Orquestração/persistência | ✅ Done | happy path + falha-nada-gravado pinados |
| T7 Endpoint + mapa de erros | ✅ Done | 404/422×3/503/502×2/504/500 todos pinados por status exato |
| T8 Detalhe estendido | ✅ Done | `evaluations` mais-recente-primeiro + `activity_type` pinados |
| T9 Contrato frontend | ✅ Done | tipos espelham o backend; build+lint verdes |
| T10 EvaluateForm | ✅ Done | pré-preenchimento, busy/"Analisando treino…" no código; UAT pendente |
| T11 EvaluationCard | ✅ Done | selo ✅/⚠️/❌, listas, rodapé de método; UAT pendente |
| T12 Composição | ✅ Done | isRunning gate, prepend local, badge; UAT pendente |
| T13 Docs | ✅ Done | README documenta fluxo/config/falhas; PLANO §6 Fase 1 marcado |

Todas as 13 tasks marcadas [x] em tasks.md; nenhuma bloqueada ou parcial. Contagens declaradas por task (284/300/308/314/323/331/341/344) conferem com os arquivos de teste: 4+16+8+6+9+8+10+3 = 64 novos, 280 → 344.

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| EVAL-01: WHEN abre detalhe de corrida THEN formulário de intenção + botão | seletor 7 tipos, pré-preenchido com `inferred_type` quando existir; texto livre opcional; botão "Avaliar com IA" | `backend/tests/test_evaluation_schemas.py:98-111` - `EvaluateIn(intent_type=t)` aceita os 7, `intent_text is None`; `:114-119` texto ≤500. UI: `frontend/src/components/workouts/EvaluateForm.tsx:39-41` (`inferred_type ?? "facil"`), `:20-28` (7 opções), `:107` ("Avaliar com IA") | ✅ PASS (backend pinned; UI por build gate + UAT pendente) |
| EVAL-02: WHEN intenção válida THEN payload em Python com blocos enumerados, cada bloco só com o que existir | resumo (dist, duração, pace, FC méd/máx, cadência, elevação, TE aer/anaer, carga, feel, RPE), voltas (km, pace, FC, cadência, temp, elevação, zona), % por zona, % zona alvo (mapa facil→easy, tempo/limiar→threshold, intervalado→interval, longao→easy∪marathon, progressivo/prova→None), consistência (gate ≥8km/≥4 voltas), contexto, PMC, zonas, LTHR, PRs datados, VDOT, padrões | `backend/tests/test_evaluation_payload.py:130-192` blocos + aritmética exata (easy 84,5 / repetition 15,5, soma 100,0), `:139-145` resumo (7/12 campos), `:156-161` voltas (km/zona/pace), `:164-167` contexto, `:170` PMC, `:173-175` PRs/VDOT/LTHR 177, `:178-184` padrões, `:192` consistência omitida <8km, `:220-230` omissões honestas, `:233-248` longão 100,0, `:195-205` progressivo/prova sem `zona_alvo` | ⚠️ GAP parcial: cadência/elevação/TEs/carga do resumo e FC/cadência/temperatura/elevação por volta sem asserção (seeds não povoam); TARGET_ZONES tempo/limiar/intervalado (3/7) sem pino |
| EVAL-03: WHEN payload montado THEN exatamente uma chamada NIM com system prompt vigente (intenção primeiro, contexto nunca decora, hierarquia pace>FC, calor, elevação), PT-BR, JSON §9.2, números exclusivos do payload | uma chamada; prompt com as regras destiladas; instrução de não recalcular | `backend/tests/test_evaluation_nim.py:132-155` corpo pinado (URL, Bearer, model, temperature 0.2, max_tokens 2000, messages); `backend/tests/test_evaluation_service.py:142` `capture["system"] == SYSTEM_PROMPT_V1`; `:143-145` user é o payload JSON; `backend/tests/test_evaluation_prompt.py:38-77` 5 vereditos, 9 chaves §9.2, "nunca recalcular", "Pace e zona decidem"/"nunca decide sozinha", 25°C, LTHR, PT-BR, sem voltas | ⚠️ GAP parcial: marcadores "intenção primeiro" (Regra 1), "contexto... nunca decora" e "elevação" sem asserção (presentes em `backend/app/evaluation/prompt.py:19-22,30-38` por leitura); "exatamente uma chamada" sem count (2ª chamada passaria) |
| EVAL-04: WHEN resposta chega THEN validar contra schema e persistir tudo; `evaluated = true` | enum 5 vereditos + confianca; extras ignorados, obrigatórios rejeitam; persiste intent_type/intent_text/payload_json/model/prompt_version/verdict/verdict_json/tokens | `backend/tests/test_evaluation_schemas.py:28-95` (5 vereditos, enum fora rejeita, obrigatório ausente rejeita, extras ignorados, pct null); `backend/tests/test_evaluation_service.py:110-145` (linha com todos os campos + `fresh.evaluated is True`); `backend/tests/test_evaluation_api.py:112-137` (200 EvaluationOut completo) | ✅ PASS |
| EVAL-05: WHEN persistida THEN card no detalhe com headline, selo, % zona alvo quando existir, desvios, listas, confiança, modelo, tokens, data | card renderiza todos os campos; selo ✅/⚠️/❌ | `frontend/src/components/workouts/EvaluationCard.tsx:13-19` (selo por veredito), `:53-63` (headline, selo, pct `!== null`), `:65-71` (4 listas), `:74-78` (confiança · modelo · tokens · data) | ✅ PASS pela estratégia declarada (matrix: none; build+lint verdes); UAT pendente |
| EVAL-06: SHALL gravar model, prompt_version, tokens_in/out em toda avaliação | linha persistida sempre com os 4 campos de auditoria | `backend/tests/test_evaluation_service.py:131-133` (`row.model`, `row.prompt_version == "v1"`, tokens 1234/56); `backend/tests/test_evaluation_api.py:126-129` | ✅ PASS |
| EVAL-07: SHALL montar payload lendo exclusivamente o banco próprio | zero chamada Garmin na avaliação | `backend/tests/test_evaluation_payload.py:251-257` (fonte lida: nega `app.garmin`/`garminconnect`); suite toda semeia direto no banco; único I/O externo é `nim.py`, mockado em 100% dos testes | ✅ PASS |
| EVAL-08: WHILE chamada em curso THEN botão desabilitado com "Analisando treino…" | sem segundo clique durante a chamada | `frontend/src/components/workouts/EvaluateForm.tsx:43-44` (busy), `:100` (`disabled={busy}`), `:107` (label "Analisando treino…") | ✅ PASS pela estratégia declarada; UAT pendente |
| EVAL-09: IF id não existe THEN 404 "atividade não encontrada" | status 404 com mensagem exata | `backend/tests/test_evaluation_api.py:140-147` (`status_code == 404`, `detail == "atividade não encontrada"`) | ✅ PASS |
| EVAL-10: IF não é corrida (running/trail_running) THEN 422 sem chamar NIM; UI omite formulário | 422 antes da NIM; UI só renderiza form para corrida | `backend/tests/test_evaluation_api.py:150-163` (422 yoga, `calls == []`, `_nothing_saved`); `backend/tests/test_evaluation_service.py:224-237` (ActivityNotRunning, zero chamadas); UI `frontend/src/components/workouts/WorkoutDetail.tsx:150,293` | ⚠️ GAP parcial: aceitação de `trail_running` sem teste (só a rejeição yoga→422 está pinada; `backend/app/evaluation/service.py:27`) |
| EVAL-11: IF intent_type fora dos 7 ou texto >500 THEN 422 antes de payload/NIM | 422 automático na validação, antes do handler | `backend/tests/test_evaluation_api.py:166-171` (422 "fácil"), `:174-180` (422 texto 501); `backend/tests/test_evaluation_schemas.py:122-133` (pydantic rejeita) | ✅ PASS |
| EVAL-12: IF NVIDIA_API_KEY vazia THEN 503, sem NIM, nada gravado | 503 com mensagem clara citando a var | `backend/tests/test_evaluation_api.py:183-200` (503, "NVIDIA_API_KEY" no detail, `calls == []`, `_nothing_saved`) | ✅ PASS |
| EVAL-13: IF NIM erro HTTP ou timeout THEN 502/504 PT-BR, sem gravar, evaluated inalterado | NimError→502; NimTimeout→504; nada gravado | `backend/tests/test_evaluation_api.py:203-214` (502 "Falha na IA"), `:231-242` (504 "demorou demais"), ambos `_nothing_saved`; `backend/tests/test_evaluation_nim.py:85-93` (HTTP 500→NimError), `:96-104` (timeout→NimTimeout) | ✅ PASS |
| EVAL-14: IF JSON não valida THEN 502 sem gravar | veredito nunca inventado | `backend/tests/test_evaluation_api.py:217-228` (502 "fora do contrato", `_nothing_saved`); `backend/tests/test_evaluation_service.py:203-216` (ValueError → 0 linhas, evaluated False); `backend/tests/test_evaluation_nim.py:107-129` (lixo/envelope/não-objeto → NimInvalidJSON) | ✅ PASS |
| EVAL-15: IF arquivo de zonas falha THEN 500 "zonas VDOT não configuradas" | 500 com a mensagem do padrão activities | `backend/tests/test_evaluation_api.py:245-255` (500 + detail exato) | ✅ PASS |
| EVAL-16: WHEN corrida sem voltas THEN payload omite bloco de voltas e prossegue | blocos de voltas/zona omitidos; resumo/contexto seguem | `backend/tests/test_evaluation_payload.py:208-217` (`voltas`/`tempo_por_zona_pct`/`zona_alvo`/`consistencia` ausentes; `pace_medio == "5:00/km"`); prompt cobre o caso `backend/tests/test_evaluation_prompt.py:75-77` | ✅ PASS (composição end-to-end sem voltas sem teste dedicado; cada etapa pinada separadamente) |
| EVAL-17: WHEN detalhe aberto THEN lista de avaliações mais recente primeiro; UI mais recente como card + anteriores resumidas | lista DESC; UI: card + entradas resumidas | `backend/tests/test_activities_api.py:539-563` (ordem `["on_target","too_hard"]` + campos completos), `:566-574` (vazia `== []`); `backend/tests/test_evaluation_service.py:183-185,240-243`; UI `frontend/src/components/workouts/WorkoutDetail.tsx:298-299`, `frontend/src/components/workouts/EvaluationCard.tsx:85-111` | ✅ PASS |
| EVAL-18: WHEN reavalia THEN linha nova como mais recente, anteriores mantidas | linha nova; nenhuma sobrescrita | `backend/tests/test_evaluation_service.py:169-185` (2 linhas, ordem nova-primeiro); UI `frontend/src/components/workouts/WorkoutDetail.tsx:94-108` (prepend local + `evaluated: true`, sem refetch) | ✅ PASS |
| EVAL-19: SHALL nunca sobrescrever nem apagar avaliações | re-avaliação só adiciona; primeira linha intacta | `backend/tests/test_evaluation_service.py:178-181` (`rows[0].intent_text == "primeira"`, `rows[1] == "segunda"`); o service só cria `Evaluation` (sem update/delete no diff) | ✅ PASS |
| EVAL-20: WHEN treino avaliado THEN badge "Avaliado" na lista | flag `evaluated` alimentada pelo motor; badge pré-existente acende | `backend/tests/test_evaluation_service.py:135-137` + `backend/tests/test_evaluation_api.py:134-137` (`fresh.evaluated is True`); `frontend/src/components/workouts/WorkoutsList.tsx:47-49` (`item.evaluated` → "Avaliado") | ✅ PASS |

### Edge Cases (spec §Edge Cases)

| Edge | Evidência | Result |
| ---- | --------- | ------ |
| NIM sem `usage` → persiste com tokens 0 | `backend/tests/test_evaluation_nim.py:76-82` pinza o contrato do cliente (`{prompt_tokens: 0, completion_tokens: 0}`); persistência end-to-end com zeros sem teste | ⚠️ GAP menor (Fix 5) |
| Campos extras ignorados; obrigatórios ausentes rejeitam | `backend/tests/test_evaluation_schemas.py:62-84` | ✅ |
| Padrões vazios / PR sem data → blocos omitidos | `backend/tests/test_evaluation_payload.py:220-230` (blocos), `:173` (PR 10K sem data fora; LONGEST_RUN não-canônico fora) | ✅ |
| Dia sem PMC → bloco omitido | `backend/tests/test_evaluation_payload.py:227` | ✅ |
| Usuário sai do detalhe durante avaliação → POST conclui no servidor | comportamento síncrono inerente ao POST; verificação é UAT | ⏭️ UAT |
| Duas abas concorrentes → duas avaliações (sem lock por design) | coberto por EVAL-19 (2 linhas, `backend/tests/test_evaluation_service.py:178-181`); guarda é o botão por aba | ✅ |

**Test Integrity**: nenhum teste chama a NIM real. `nim.py` só é exercido via `httpx.MockTransport` (`test_evaluation_nim.py`) ou monkeypatch do módulo (`test_evaluation_service.py:94-107`, `test_evaluation_api.py:92-101`); o `transport` é parâmetro obrigatório nos testes. O teste de URL (`test_evaluation_nim.py:145`) afirma a string, não faz chamada.

---

## Discrimination Sensor

| Mutation | File:line | Description | Killed? |
| -------- | --------- | ----------- | ------- |
| 1 | `backend/app/evaluation/payload.py:150` | inversão numerador/denominador no cálculo de `pct_zona_alvo` (`in_target / total` → `total / in_target`) | ✅ Killed — 4 falhas: `test_payload_completo_blocos_e_matematica_exata` (84,5 → 118,3), `test_happy_path_persiste_todos_campos`, `test_sanitiza_eco_pct_zona_alvo`, `test_200_happy_path_devolve_avaliacao` |
| 2 | `backend/app/evaluation/service.py:76` | sanitização do eco removida (`sanitize_echo(verdict, python_pct)` → `verdict.model_dump()`; eco do LLM persistido) | ✅ Killed — `test_sanitiza_eco_pct_zona_alvo` (esperado 84,5 do Python, eco 61,0; progressivo esperado None) |
| 3 | `backend/app/evaluation/router.py:52-56` | mapa de status HTTP: `NimTimeout` 504 → 502 | ✅ Killed — `test_504_timeout_da_nim` (`assert 502 == 504`) |

**Sensor depth**: lightweight (3 mutações; feature não-P0)
**Result**: 3/3 mortos, 0 sobreviventes ✅

Isolamento: worktree `git worktree add %TEMP%\opencode\ritmo-sensor df75158` com venv próprio (`uv sync`; `import app` resolve para o scratch, confirmado por `__file__`). Teste-alvo rodado unmutado antes da 1ª mutação (6 passed). Cada mutação revertida com `git checkout --` no scratch. Scratch descartado (`git worktree remove --force` + limpeza de resíduo bloqueado por lock). `git status --porcelain` da árvore real: limpo antes e depois, idêntico ao baseline.

---

## Gate Check

- **Gate command** (tasks.md): `cd backend; uv run pytest` (Quick/Full/Build backend) + `cd frontend; npm run build; npm run lint` (Build frontend)
- **Result**: backend **344 passed, 0 failed, 0 skipped** (236,9s; Postgres do compose, banco `ritmo_test`, execução única). Frontend build ✅ + lint ✅. 1 warning pré-existente (StarletteDeprecationWarning do `fastapi.testclient`, não é skip).
- **Test count before feature**: 280 (baseline verificada na T1; o "268" do README estava defasado)
- **Test count after feature**: 344
- **Delta**: +64 (T1 +4, T2 +16, T3 +8, T4 +6, T5 +9, T6 +8, T7 +10, T8 +3; contagens confirmadas contra os arquivos)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Interactive UAT

Não executado (subagente sem acesso interativo; feature user-facing). Pendente com o usuário, já registrada no README ("UAT ao vivo na sequência"):

| # | Teste | Result |
| - | ----- | ------ |
| 1 | Avaliar corrida real com key real → card com veredito, listas, tokens e data; recarregar → card persistido; badge "Avaliado" na lista | ⏭️ Pendente |
| 2 | Spot-check do success criteria: treino fácil acima da zona easy nunca sai ✅ | ⏭️ Pendente |
| 3 | Re-avaliar treino avaliado → 2 entradas, nova como card | ⏭️ Pendente |
| 4 | Detalhe de não-corrida (yoga/força) → sem formulário | ⏭️ Pendente |

---

## Code Quality

| Principle | Status |
| ---------- | ------ |
| Minimum code | ✅ domínio evaluation enxuto; sem abstrações além das 6 peças do design |
| Surgical changes | ✅ diff = exatamente os arquivos planejados (33 arquivos); nada fora do escopo |
| No scope creep | ✅ out-of-scope respeitado: sem seletor de modelo, sem retry, sem feed no Potencial, non-running 422 |
| No unnecessary flexibility | ✅ `transport` é o único seam, justificado pelo requisito de zero chamada real |
| Matches patterns | ✅ espelha activities/health/potential; import em nível de função documentado (evita ciclo) |
| Spec-anchored outcome check | ⚠️ 5 desfechos enumerados sem pino (Fixes 1-5) |
| Per-layer Coverage Expectation | ⚠️ rotas: happy + todos os erros ✅; domínio: 1:1 exceto sub-campos de EVAL-02/03 e trail_running |
| Every test maps to a spec requirement | ✅ cada teste cita EVAL-xx no docstring; zero testes sem AC |
| Documented guidelines followed: `README.md` §Testes/§Rodando (compose + `uv run pytest`); `frontend/AGENTS.md` (docs do Next lidas nas tasks T9-T12) | ✅ |

---

## Fix Plans

### Fix 1 (Major): pinos de campo do resumo e das voltas (EVAL-02)

- **Root cause**: os seeds de `backend/tests/test_evaluation_payload.py` não povoam cadência, elevação, TEs e carga de treino (resumo), nem FC/cadência/temperatura/elevação por volta; as asserções cobrem 7/12 campos do resumo e 3/7 por volta. Deletar `"te_aerobico": source["aerobic_te"]` (etc.) de `payload.py` deixa a suite verde.
- **Fix task**: estender `_seed_activity`/`_seed_split` com `avg_cadence`, `elevation_m`, `aerobic_te`, `anaerobic_te`, `training_load` e afirmar os 12 campos do resumo e os 7 por volta (incl. `temperatura_c`) no `test_payload_completo_blocos_e_matematica_exata`, por valor literal.
- **Verify**: suite verde com as novas asserções; remoção de qualquer campo do `_resumo`/`_voltas` falha.
- **Done when**: 12/12 campos do resumo e 7/7 por volta afirmados por valor.

### Fix 2 (Major): mapa TARGET_ZONES completo (EVAL-02)

- **Root cause**: só facil/longão/progressivo/prova estão pinados; tempo→threshold, limiar→threshold e intervalado→interval (assumption do spec, linha 47) não têm asserção. Trocar `"tempo": ["threshold"]` por `["easy"]` passa na suite.
- **Fix task**: parametrizar `test_evaluation_payload.py` sobre as 7 intenções: 4 com alvo (facil/tempo/limiar/intervalado/longão) afirmam `zona_alvo["zonas"]`; progressivo/prova afirmam ausência.
- **Verify**: suite verde; mutação de qualquer entrada de `TARGET_ZONES` falha.
- **Done when**: 7/7 entradas do mapa cobertas.

### Fix 3 (Major): marcadores centrais do prompt + count de chamada única (EVAL-03)

- **Root cause**: `test_evaluation_prompt.py` não pina "intenção primeiro" (Regra 1, regra central da feature), "contexto... nunca decora" nem "elevação por volta" (todos presentes em `backend/app/evaluation/prompt.py:19-22,30-38`); nenhum teste afirma que o happy path faz exatamente 1 chamada à NIM (o `capture` do service é sobrescrito, uma 2ª chamada passaria).
- **Fix task**: 3 asserts de marcadores em `test_evaluation_prompt.py` + `calls` em lista no happy path do service com `assert len(calls) == 1`.
- **Verify**: suite verde; deletar a Regra 1 do prompt falha; duplicar a chamada no service falha.
- **Done when**: regras de intenção/contexto/elevação pinadas; chamada única pinada por count.

### Fix 4 (Minor): aceitação de trail_running (EVAL-10)

- **Root cause**: `RUNNING_TYPES = ("running", "trail_running")` (`backend/app/evaluation/service.py:27`), mas só a rejeição yoga→422 é testada. Remover `"trail_running"` passa na suite.
- **Fix task**: teste de service (ou api) semeando `activity_type="trail_running"` → avalia com 200 e NIM mockada.
- **Verify**: suite verde; remoção de trail_running de RUNNING_TYPES falha.

### Fix 5 (Minor): edge "usage ausente" end-to-end

- **Root cause**: o edge do spec (tokens 0, avaliação persiste) está pinado só no cliente NIM (`backend/tests/test_evaluation_nim.py:76-82`); nenhum teste persiste com usage zeros.
- **Fix task**: teste de service com mock devolvendo `(verdict, {"prompt_tokens": 0, "completion_tokens": 0})` → linha persistida com `tokens_in == 0 and tokens_out == 0`.
- **Verify**: suite verde; mapear tokens para outro valor falha.

### Fix 6 (Minor, spec-precision): precedência 503 vs 404/422

- **Root cause**: o spec não define a ordem de validação entre key ausente (503) e id inexistente/não-corrida (404/422). O design declara "404 → 422 → 503"; a implementação checa 503 antes (`backend/app/evaluation/router.py:33` antes do service). Com key vazia e id inexistente, o usuário vê 503. Nenhum AC é violado; a divergência design↔implementação está sem pino em ambos os lados.
- **Fix task**: decidir a ordem (503 primeiro é razoável: config antes de query), alinhar o texto do design e pinar a precedência com um teste (ex.: id inexistente + key vazia → status decidido).
- **Verify**: suite verde; inversão da ordem falha.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| EVAL-01 | Implementing | ✅ Verified |
| EVAL-02 | Implementing | ❌ Needs Fix (Fixes 1-2: pinos de campo e mapa) |
| EVAL-03 | Implementing | ❌ Needs Fix (Fix 3: marcadores + chamada única) |
| EVAL-04 | Implementing | ✅ Verified |
| EVAL-05 | Implementing | ✅ Verified (build + leitura; UAT pendente) |
| EVAL-06 | Implementing | ✅ Verified |
| EVAL-07 | Implementing | ✅ Verified |
| EVAL-08 | Implementing | ✅ Verified (build + leitura; UAT pendente) |
| EVAL-09 | Implementing | ✅ Verified |
| EVAL-10 | Implementing | ❌ Needs Fix (Fix 4: trail_running) |
| EVAL-11 | Implementing | ✅ Verified |
| EVAL-12 | Implementing | ✅ Verified |
| EVAL-13 | Implementing | ✅ Verified |
| EVAL-14 | Implementing | ✅ Verified |
| EVAL-15 | Implementing | ✅ Verified |
| EVAL-16 | Implementing | ✅ Verified |
| EVAL-17 | Implementing | ✅ Verified |
| EVAL-18 | Implementing | ✅ Verified |
| EVAL-19 | Implementing | ✅ Verified |
| EVAL-20 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready (gaps de pino de teste; comportamento conforme o spec por leitura, gate verde, sensor 3/3)

**Spec-anchored check**: 20/20 ACs com o desfecho principal verificado por `file:line` | 5 gaps de pino em sub-critérios enumerados (EVAL-02 ×2, EVAL-03, EVAL-10, edge usage) + 1 spec-precision gap (precedência)
**Sensor**: 3/3 mutações mortas (payload `pct_zona_alvo`, sanitização do eco, mapa 504)
**Gate**: 344 passed, 0 failed, 0 skipped; `npm run build` + `npm run lint` verdes

**What works**: payload determinístico 100% banco com aritmética exata; cliente NIM com corpo pinado e zero chamada real em teste; mapa de erros 404/422×3/503/502×2/504/500 com mensagens PT-BR e nada gravado em falha; persistência auditável (model/prompt_version/tokens/payload/veredito); sanitização do eco AD-003; re-avaliação só adiciona; detalhe expõe avaliações mais-recente-primeiro + `activity_type`; docs honestas.

**Issues found**: 6 (Fixes 1-6 acima). Todos de strengthening de teste ou decisão de contrato; nenhum bug de comportamento detectado.

**Next steps**: orquestrador roteia Fixes 1-6 como tasks de correção (uma task única de testes resolve 1-5); re-verificação após os fixes (máx. 3 iterações); UAT ao vivo pendente (treino real + key real).
