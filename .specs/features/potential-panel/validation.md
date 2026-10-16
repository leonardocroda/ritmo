# Painel Potencial — Validation

**Date**: 2026-10-16
**Spec**: `.specs/features/potential-panel/spec.md`
**Diff range**: `941c734..HEAD` (17 commits: 2 docs de planejamento + 15 de código/docs; 36 arquivos, +2828/−166)
**Verifier**: sub-agente independente (author ≠ verifier) — árvore real intacta; mutações só em worktree descartável

---

## Veredito

**PASS ✅** — 29/29 ACs com evidência `file:line` e resultado conforme a spec; 10 edge cases verificados (8 com teste, 2 notas); sensor 4/4 mutações mortas; gates verdes (228 passed; build+lint exit 0). Dois pontos flagados como **⚠️ spec-precision gap** (nenhum bloqueia — detalhes em Gaps Ranqueados).

---

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 daniels.py (move + CLI fino) | ✅ Done | `vdot/daniels.py` (6 funções puras); `calibrate_vdot.py` consome o módulo; 6 testes com pins literais (`test_vdot_daniels.py:19-62`) + `gerar_zonas(50.2)` reproduz o JSON gravado (`:57-62`) |
| T2 calibration.py | ✅ Done | `vdot/calibration.py` (`Calibration` + `load_calibration`, `ZoneConfigError` herdada de `zones.py`); 5 testes (`test_vdot_calibration.py:21-69`), arquivo real pinado campo a campo |
| T3 data dos PRs | ✅ Done | `mappers.py:219-227` (`activityStartDateTimeLocal` → fallback `prStartTimeGmt` → NULL); fixture real em `helpers.py:277-296`; self-heal testado (`test_garmin_upserts.py:368-391`) |
| T4 predições model+mapper+upsert | ✅ Done | `RacePrediction` (UNIQUE user_id+event), `map_race_predictions` (`mappers.py:234-250`), `upsert_race_predictions` (`upserts.py:115-132`); payload da sonda 15/10 em `helpers.py:303+` |
| T5 etapa de sync | ✅ Done | `client.py:175-177` (1 `_call`), `service.py:287-313` (`_sync_predictions` tolerante), ordem records→predictions→pmc (`service.py:368-370`); `_initial_stats` com `predictions: 0` (`service.py:98`) |
| T6 calc timeline | ✅ Done | `potential/calc.py:21-128` (CANONICAL, riegel_time, timeline_points com dedup/validade, demonstrated); 10 testes em `test_potential_calc.py:68-178` |
| T7 calc predictions/decay | ✅ Done | `calc.py:141-203` (média só das presentes, âncora guardada, decay com sinal); 8 testes em `test_potential_calc.py:186-301` |
| T8 service de leitura | ✅ Done | `potential/service.py:126-169` (5 blocos do banco próprio; filtro de corridas em Python — AD-001); 6 testes service em `test_potential_api.py:103-296` |
| T9 router + mount | ✅ Done | `potential/router.py:99-117` (`Query(180, ge=1, le=365)`, 500 "zonas VDOT não configuradas"); montado em `main.py:20,49`; 6 testes HTTP (`test_potential_api.py:316-409`) |
| T10 lib api+format | ✅ Done | `api.ts:290-305` (`PotentialOut` espelhando os modelos, `getPotential(days=180)`, `no-store`); `formatVdot` em `format.ts`; build/lint exit 0 |
| T11 VdotTimeline | ✅ Done | `VdotTimeline.tsx` (ScatterChart + ReferenceArea da faixa + ReferenceLine corrente + tooltip); build/lint exit 0 |
| T12 PredictionsTable + DecayTable | ✅ Done | `PredictionsTable.tsx` ("—" para NULL, nota da média honesta), `DecayTable.tsx` (Δ% com sinal, maior gap destacado); build/lint exit 0 |
| T13 PmcChart | ✅ Done | `PmcChart.tsx` (Bar TSB + Line CTL/ATL, zero marcado, cards do último dia, ACWR "—" quando null); build/lint exit 0 |
| T14 Vo2maxTrend | ✅ Done | `Vo2maxTrend.tsx` (selo "estimativa do relógio" + nota de hierarquia AD-005); build/lint exit 0 |
| T15 PotentialPanel + rota | ✅ Done | `PotentialPanel.tsx` (GapCard com narrativa §9.5, estados loading/error/empty, seções condicionais); `app/potencial/page.tsx` renderiza o painel; build/lint exit 0 |
| T16 validação real + fechamento | ✅ Done | UAT real aprovado pelo usuário (sync com `predictions: 4`, `pr_date` auto-curado nas 7 PRs, painel com dados reais); STATE handoff em `45fd9ca`/`f930868` |

---

## Spec-Anchored Acceptance Criteria

Pins matemáticos **re-derivados de forma independente** pelo Verifier (execução direta das funções, não leitura dos testes): `calculate_vdot(5000, 1163.8299560546875) = 51.6193` → `round(...,2) = 51.62`; `gap_pct = 50.2/51.6193×100 = 97.2504 → 97.3`; `equivalent_time(50.2, 5/10/21.0975/42.195) = 1191.9/2471.1/5472.3/11401.4`; Riegel `2426.5/5353.8/11162.4`; decay 5K `232.8/238.4` e maratona `330.0/270.2 → −22.1`. Todos conferem com as asserções dos testes.

**Convenção da matriz**: frontend sem infra de testes (decisão da Test Coverage Matrix: build + lint + UAT). Para ACs de UI (POT-17..POT-29), a evidência é implementação (`file:line`) + gates + UAT real de 15/10/2026 (aprovado pelo usuário; task T16).

| Criterion | Spec-defined outcome | `file:line` + asserção | Result |
| --------- | -------------------- | ----------------------- | ------ |
| POT-01: passo de predições após records, exatamente 1 chamada do orçamento | 1 chamada, dentro do teto | `test_garmin_service.py:372` — `fake.calls["race_predictions"] == [()]`; `:384` — `stats_json["calls_made"] == 259` (258 + 1); ordem `:443` — `observed_steps == ["records", "predictions"]` (espionando o step gravado no banco na hora da chamada) | ✅ PASS |
| POT-02: upsert por (user_id, event) com time_s e raw_json; evento ausente → linha intocada (sem delete) | idempotente 2×; ausente preserva | `test_garmin_upserts.py:398-410` — 2× upsert → `_count == 4`, `time_s == 11989.0`, `raw_json == RACE_PREDICTIONS_PAYLOAD`; `:429-451` — payload sem `timeMarathon` → `marathon_after.id == marathon_before.id` e `time_s == 11989.0` (linha intocada), 5K atualizado | ✅ PASS |
| POT-03: falha no passo → warning `{tipo: "predictions"}` e sync continua | job done + warning literal | `test_garmin_service.py:404` — `stats["warnings"] == [{"tipo": "predictions", "erro": "predições fora do ar"}]`; `:401` — `status == "done"`; `:407` — `stats["step"] == "pmc"` (pmc rodou depois); `:410` — `_count(DailyLoad) == 12` | ✅ PASS |
| POT-04: `stats_json` inclui contador `predictions` | contador presente (0 inicial, 4 no happy path) | `test_garmin_service.py:121` — `stats["predictions"] == 4`; `:405` — `== 0` na falha; `service.py:98` — `"predictions": 0` no `_initial_stats` | ✅ PASS |
| POT-05: `pr_date` = data local de `activityStartDateTimeLocal`; fallback `prStartTimeGmt`; nenhum → NULL | wall clock local; NULL sem timestamp | `test_garmin_mappers.py:278` — esforço 22:30 local (= 01:30 UTC do dia seguinte) → `pr_date == date(2026, 4, 26)` (falharia sob a leitura GMT do bug); `:285` — fallback `prStartTimeGmt` → `date(2024, 1, 14)`; `:292` — nenhum timestamp → `pr_date is None` | ✅ PASS |
| POT-06: re-upsert atualiza `pr_date` (self-heal) | linha existente curada sem duplicar | `test_garmin_upserts.py:381,386-391` — linha legacy com `pr_date` NULL → re-upsert → `healed.id == stored.id` (não duplicou, `_count == 2`) e `pr_date == date(2026, 4, 26)` | ✅ PASS |
| POT-07: bloco `vdot` com corrente/demonstrado/gap_pct/timeline | corrente da calibração; demonstrado = maior VDOT entre PRs canônicos **datados** + provas + teste; gap = corrente/demonstrado | `test_potential_api.py:129-133` — `current == {"vdot": 50.2, "source": "10K em 41:15", "test_date": date(2026,10,3)}`; `:135-137` — `demonstrated == 51.62/FASTEST_5K/2026-04-26`; `:138` — `gap_pct == 97.3` (= 50.2/51.6193×100, re-derivado); `:268-271` — sem PRs, demonstrado = o próprio teste e `gap_pct == 100.0` | ✅ PASS |
| POT-08: pontos `{date, vdot, source, label, distance_m, time_s}` derivados com `calculate_vdot`, nunca coluna pronta | VDOT recalculado por ponto | `test_potential_calc.py:97-113` — 6 pontos com (date, source, label) e `[round(p["vdot"],2)] == [51.32, 49.52, 51.62, 50.88, 39.48, 50.18]` + (distance_m, time_s) literais; `calc.py:85,103,114` — sempre `calculate_vdot(...)`; serviço nunca lê coluna de VDOT (não existe) | ✅ PASS |
| POT-09: prova com PR canônico na mesma data → ponto da prova excluído | PR certificado prevalece | `test_potential_calc.py:122-124` — `(2026-07-05, "prova") not in` pontos, `(2026-07-05, "pr") in`, prova em data livre presente; via API `test_potential_api.py:141-148` (Londrina deduplicada, timeline com 6 entradas) | ✅ PASS |
| POT-10: bloco `predictions` — 4 distâncias × garmin_s/riegel_s (âncora 5K, NULL sem ela)/vdot_s/average_s (média das presentes)/pr_s+pr_date | fórmula de Riegel T2=T1×(D2/5000)^1.06; média honesta | `test_potential_calc.py:191-216` — chaves `["5K","10K","HALF_MARATHON","MARATHON"]`, riegel `1163.8/2426.5/5353.8/11162.4`, vdot_s `1191.9/2471.1/5472.3/11401.4`, garmin da sonda, médias `1173.6/2448.2/5421.0/11517.6`, pr_s+pr_date; via API `test_potential_api.py:151-166` (dict completo) | ✅ PASS |
| POT-11: `days` em [1,365] → `pmc` com `points[{date,ctl,atl,tsb,acwr}]` das últimas `days` linhas (default 180) + `current`; fora → 422 sem query | janela pedida + current do último dia; 422 | `test_potential_api.py:193-201` — days=2 → 2 pontos (mais antiga primeiro) e `current` = dia 15; `:362-366` — days 0/366/−1 → `422`; `:369-379` — bordas 1 e 365 → 200; `router.py:101` — `Query(default=180, ge=1, le=365)` (validação FastAPI precede o handler — mesma nota estrutural do TRN-09) | ✅ PASS |
| POT-12: sem linhas em `load` → `pmc=null` (não erro) | null, resto do painel intacto | `test_potential_api.py:214` — `payload["pmc"] is None`; via HTTP `:400-401` — `body["pmc"] is None` com timeline presente | ✅ PASS |
| POT-13: `vo2max` de `raw_json.vO2MaxValue` das corridas por `start_time` ASC; nenhuma → `null` | filtro running/trail_running; null | `test_potential_api.py:237-244` — cycling 60.0 e corrida sem campo ficam fora; empate de start_time → ordem id ASC (55.5 antes de 56.0); `:253` — `vo2max is None`; `service.py:81-84` — `key=(start_time, id)`; `:88` — guarda `isinstance` | ✅ PASS |
| POT-14: `decay` por distância canônica COM PR: real_pace_s/ideal_pace_s/delta_pct; sem PR fica fora | distâncias sem PR de fora; sinal | `test_potential_calc.py:265-276` — ordem canônica, `by_event["MARATHON"] == {real 330.0, ideal 270.2, delta −22.1}` (real mais lento → negativo = gap), `min(delta_pct) == MARATHON`; `:283` — só 10K quando só ele tem PR; `:288-289` — vazio sem canônicos | ✅ PASS |
| POT-15: endpoint sem nenhuma chamada à API do Garmin | zero imports do gateway no domínio | `test_potential_api.py:286-296` — varre todos os `*.py` de `potential/` afirmando `"from app.garmin"` e `"import app.garmin"` ausentes; `service.py:13-21` — imports só de db/potential/vdot | ✅ PASS |
| POT-16: `vdot_zones.json` ausente/inválido → 500 "zonas VDOT não configuradas" | 500 com mensagem exata | `test_potential_api.py:390-391` — `status_code == 500` e `detail == "zonas VDOT não configuradas"`; `router.py:111-116` — `ZoneConfigError` → HTTPException; calibração inválida → `ZoneConfigError` em `test_vdot_calibration.py:31-69` (4 formas) | ✅ PASS |
| POT-17: gráfico com ponto por entrada, linha no corrente e faixa até o demonstrado | pontos + ReferenceLine + ReferenceArea | `VdotTimeline.tsx:101-109` — `ReferenceArea y1=current y2=demonstrated` (só se demonstrated ≠ null); `:110-121` — `ReferenceLine` tracejada rotulada `corrente 50,2`; `:122` — `Scatter` por ponto; tooltip `:49-68`; UAT real | ✅ PASS (per matriz) |
| POT-18: `gap_pct` exibido com narrativa honesta de §9.5 | "você já demonstrou X; o teste atual valida Y — o meio é o alvo honesto" | `PotentialPanel.tsx:31-50` — GapCard com `gap_pct` (ou "—") e o texto literal "Você já demonstrou … o teste atual valida … — o meio é o alvo honesto."; UAT real | ✅ PASS (per matriz) |
| POT-19: falha da API → mensagem de erro sem quebrar a navegação | erro inline | `PotentialPanel.tsx:86-92` — mensagem inline "Não foi possível carregar o potencial: …" (nav vive fora do `<main>` em `app/potencial/page.tsx`); UAT real | ✅ PASS (per matriz) |
| POT-20: painel legível em 390px sem scroll horizontal | padrão workouts-list | `PotentialPanel.tsx` (`max-w-3xl px-4` na page; tabelas `w-full text-xs`, gráficos `ResponsiveContainer width="100%"`); UAT real 15/10 (aprovado) | ✅ PASS (per matriz) |
| POT-21: tabela de previsões — linhas por distância, colunas Garmin/Riegel/VDOT/Média/PR com data | 4×4 + PR datado | `PredictionsTable.tsx:39-93` — thead com as 6 colunas, `EVENTS.map` nas 4 linhas, PR com `formatDay(row.pr_date)` `:80-84`; UAT real (4 estimativas × 4 distâncias com PR datado) | ✅ PASS (per matriz) |
| POT-22: NULL → "—"; média honesta só com as presentes | nenhum número inventado | `PredictionsTable.tsx:26-28` — `secondsOrDash` ("—" quando null) aplicado às 4 colunas de estimativa e ao PR `:86-88`; nota da média `:96-99`; backend: média das presentes pinada em `test_potential_calc.py:227-228,243-245` | ✅ PASS |
| POT-23: CTL e ATL como linhas, TSB como série distinta, eixos rotulados | 3 séries distintas | `PmcChart.tsx:133` — `Bar dataKey="tsb"` (semitransparente, atrás), `:134-149` — `Line ctl` + `Line atl` em cores próprias; legenda rotulada `:77-97`; eixos com formatters de data/valor `:117-130`; UAT real (curva com 182 dias) | ✅ PASS (per matriz) |
| POT-24: valores do último dia como destaques; ACWR null → "—" | cards CTL/ATL/TSB/ACWR | `PmcChart.tsx:104-110` — 4 `StatCard` do `pmc.current`; `:51-53` — `statOrDash` ("—" quando null), aplicado ao ACWR `:109-110` com o comentário SYNC-24; UAT real | ✅ PASS (per matriz) |
| POT-25: `pmc=null` → estado vazio orientando o sync | sem erro, sem tela branca | `PotentialPanel.tsx:132-139` — seção com "Sem curva de carga ainda — ela nasce no primeiro sync…"; empty state geral `:98-110` apontando "Puxar do Garmin"; UAT real | ✅ PASS (per matriz) |
| POT-26: linha VO2max com selo "estimativa do relógio" + nota de hierarquia (AD-005) | selo visual + nota | `Vo2maxTrend.tsx:56-59` — badge "estimativa do relógio"; `:94-97` — "Provas e testes de campo medem; o relógio estima… hierarquia de métricas"; UAT real (54–56 com selo) | ✅ PASS (per matriz) |
| POT-27: `vo2max=null` → omitir o bloco inteiro | seção ausente, não vazia | `PotentialPanel.tsx:141-147` — `{vo2max !== null && <Section…>}`; UAT real | ✅ PASS (per matriz) |
| POT-28: decay — real, ideal e delta percentual com sinal | sinal rotulado | `DecayTable.tsx:67-78` — real/ideal com `formatPace` + Δ% ; `:18-21` — `formatDelta` ("−22,1%" / "+2,3%"); nota do sinal `:85-88` ("Negativo = pace real mais lento que o ideal"); UAT real | ✅ PASS (per matriz) |
| POT-29: maior gap destacado, sem interpretação inventada | só destacar o número | `DecayTable.tsx:27-29` — `worstGap = reduce(delta mais negativo)`; `:53-59` — linha com `bg-accent/10` e Δ% em destaque; UAT real (maratona destacada) | ✅ PASS (per matriz) |

**Status**: ✅ 29/29 ACs com evidência `file:line` + asserção conferida ao resultado definido pela spec (pins re-derivados). 2 ⚠️ spec-precision gaps não-bloqueantes (ver Gaps Ranqueados).

---

## Desvios documentados — julgamento do Verifier

1. **`gap_pct` 97.3 (código/testes) vs 97.2 (ilustração do design)**: a spec define `gap_pct = corrente/demonstrado` (AC POT-07) **sem pinar número**; o design marca o payload como "ilustrativos". Re-derivado: 50.2/51.6193×100 = 97.2504 → **97.3** é o valor exato da fórmula da spec; 97.2 derivaria do pré-arredondado 51.62. **Spec satisfeita** — o teste pina o valor correto da fórmula (`test_potential_api.py:138`), e o Success Criteria ("lacuna ~97%") cobre ambos.
2. **Label do ponto "teste" = `calibration.source` verbatim ("10K em 41:15") vs "10K 41:15" ilustrativo**: a spec não define o formato do label do ponto de calibração (POT-08 lista `label` sem conteúdo; o design é ilustrativo). A implementação usa o campo `source` do arquivo (`calc.py:116`), documentada no docstring e nos testes. **⚠️ Spec-precision gap** — inofensivo (dado verbatim é mais honesto que o formatado), mas o formato exibido não está ancorado num AC.

---

## Edge Cases (spec.md)

- [x] PR canônico sem data → fora da timeline: `test_potential_calc.py:127-137` (`[p["source"]] == ["teste"]`). **⚠️ 2ª cláusula** ("permanece elegível ao demonstrado") não implementada nem testada — ver Gaps #1.
- [x] Predições vazias → Garmin "—" e média usa Riegel+VDOT: `test_potential_calc.py:234-245` (10K `garmin_s is None`, `average_s == 2448.8` = (2426.5+2471.1)/2) + sem-sync nenhum em `test_potential_api.py:273-280` (média = única estimativa presente)
- [x] Sem PR de 5K → `riegel_s` NULL em todas + média só das presentes: `test_potential_calc.py:225-228` (`all(riegel_s is None)`, `average_s == 2459.1`)
- [x] `days` > histórico → todas as linhas disponíveis: `test_potential_api.py:203-207` (days=365 com 3 linhas → as 3, sem inventar)
- [x] Empate de `start_time` → ordem estável por `id` ASC: `test_potential_api.py:229-243` (ids 14/15 no mesmo horário → 55.5 antes de 56.0) — mutação M3 confirma que o teste discrimina
- [x] Teste de calibração → o corrente permanece o `vdot` do arquivo, independente dos pontos: `test_potential_api.py:129-133` (corrente 50.2 com demonstrado 51.62). **⚠️ cláusula "ambos viram pontos" (teste com data igual/futura a um PR) correta por construção** (`calc.py:111-120` — append incondicional, dedup só contra datas de PR) **mas sem teste direto com datas colididas** — ver Gaps #2
- [x] `distance_m`/`time_s` 0/negativo → fora da timeline e do demonstrado, sem crash: `test_potential_calc.py:140-151` (0/negativo/None de fora; só maratona vira ponto); provas inválidas idem `:154-163`; demonstrado é função pura dos pontos (`:166-171`), então excluído do ponto = excluído do demonstrado
- [x] Maratona com atividade E PR na mesma data → só o PR vira ponto: `test_potential_calc.py:116-124` + API `test_potential_api.py:108-148` (Londrina)
- [x] `training_load` NULL em tudo → `load` sem linhas → `pmc=null`: `test_potential_api.py:210-214` (mecanismo de sincronização é do PMC SYNC-24, pré-existente)
- [x] Duas entradas na mesma data são plotáveis lado a lado (provas distintas): races só deduplicam contra datas de PR (`calc.py:98`), nunca entre si; coberto indireto pelos fixtures (prova em data livre + PRs). Mesma nota do Gaps #2 para a colisão teste×PR

---

## Discrimination Sensor

**Tier**: lightweight (4 mutações comportamentais nos pontos de maior risco do domínio novo — 1 por camada: calc-timeline, calc-predictions, service-vo2max, sync).
**Scratch**: `git worktree add C:\Users\leona\AppData\Local\Temp\opencode\potential-verifier-wt HEAD` (detached em `f930868`), `uv sync` no worktree (cache), probe confirmou `app.__file__` resolvendo para a cópia do worktree. Controle não-mutado: 18 testes de calc verdes antes da 1ª mutação. Nenhuma mutação tocou a árvore real — `git status --porcelain` vazio antes e depois; worktree removido com `--force`.

| # | Mutante | file:line (scratch) | Descrição | Morto? |
| - | ------- | ------------------- | --------- | ------ |
| M1 | dedup da timeline | `potential/calc.py:98` | `if race_date in pr_dates: continue` → `if False:` (prova na data do PR vira ponto duplicado) | ✅ Killed — 3 failed, incl. `test_timeline_points_dedup_race_on_pr_date`, `test_timeline_points_real_fixture_chronological` e `test_get_potential_full_payload_from_seeds` (API) |
| M2 | guarda da âncora Riegel | `potential/calc.py:160` | `if pr_5k_s and pr_5k_s > 0` → `if pr_5k_s is not None` (âncora 0/negativa passa a projetar) | ✅ Killed — `test_predictions_invalid_anchor_time_does_not_project` (riegel_s deixa de ser None) |
| M3 | ordenação do VO2max | `potential/service.py:83` | `key=(a.start_time, a.id)` → `key=(a.id,)` (determinismo por data quebrado) | ✅ Killed — `test_vo2max_points_filtered_and_ordered_from_raw_json` (54.0 do dia 22 viraria 1º ponto) |
| M4 | side effect do sync | `garmin/service.py:301` | `upsert_race_predictions(db, user_id, rows)` removido (linhas nunca persistidas) | ✅ Killed — 3 failed, incl. `test_predictions_synced_after_records_exactly_one_call` (0 eventos no banco), `test_run_sync_happy_path_done_with_full_stats` e `test_predictions_resync_updates_without_duplicates` |

**Result**: **4/4 killed, 0 sobreviventes** — PASS ✅. Os testes discriminam a dedup prova×PR, a validade da âncora Riegel, o determinismo de leitura do VO2max e a persistência das predições no sync.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ diff na superfície planejada (T1–T16); out-of-scope respeitado (sem CRUD de races, sem popular `vdot_tests`, sem gráfico de decay, sem histórico de predições, sem média ponderada v2 — `riegel_time` isolada como função pura para viabilizar a troca) |
| Surgical changes / só arquivos da task | ✅ 36 arquivos, todos mapeados a T1–T16 (+spec/design/tasks da própria feature); `calibrate_vdot.py` vira consumidor fino sem mudança de comportamento (pinado por `test_vdot_daniels.py:57-62`) |
| No scope creep | ✅ |
| Matches patterns | ✅ docstrings PT-BR, padrão router/service do activities, upsert espelhando `upsert_records`, client components no padrão WorkoutDetail/WorkoutsList, PT-BR na exibição com ASCII na API |
| Spec-anchored outcome check | ✅ pins literais conferidos por re-derivação independente (51.62/97.3/11401.4/2426.5/−22.1…); asserções de VALOR/ESTADO em todos os campos de payload (predictions/vdot/pmc/vo2max/decay como dicts completos, não só chamadas) |
| Per-layer Coverage Expectation | ✅ domínio 1:1 com ACs (daniels/calibration/calc); rotas happy+edge+error (200/422/500, pmc null, vo2max null, janelas e bordas); integração no Postgres real do compose; sync com happy+failure+ordem |
| Every test maps to a spec requirement | ✅ cada teste cita POT-NN/T#/edge no docstring; nenhum teste órfão |
| Documented guidelines followed | ✅ README §Testes (uv + Postgres do compose), `frontend/AGENTS.md` (Next 16), L-001/L-002 aplicadas (valores literais, nunca constantes compartilhadas) |

---

## Gate Check

- **Gate commands**: `cd backend; uv run pytest` · `cd frontend; npm run build; npm run lint`
- **Backend**: **228 passed, 0 failed, 0 skipped** (142.01s, exit 0; 1 warning pré-existente `StarletteDeprecationWarning` do TestClient, não relacionado)
- **Frontend**: `npm run build` exit 0 (rotas /_not-found, /hoje, /potencial, /saude, /treinos, /treinos/[id]) · `npm run lint` exit 0
- **Test count before feature**: 170 (fim do workouts-list)
- **Test count after feature**: 228 (+58 = daniels 6 + calibration 5 + mappers 9 + upserts 3 + service/sync 6 + calc 18 + api 12 — contagens por arquivo conferidas)
- **Delta**: +58 novos; nenhum teste deletado; nenhuma asserção enfraquecida
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Success Criteria

- [x] `/potencial` mostra timeline com pontos reais, linha em 50,2, faixa até 51,6 e lacuna 97,3% com narrativa honesta — UAT real aprovado (T16); 97,3 confirmado por re-derivação da fórmula da spec
- [x] Tabela de previsões com as 4 estimativas + PR por distância, "—" onde não há dado, PRs datados (self-heal confirmado no banco pelo sync real) — UAT + `test_garmin_upserts.py:368-391`
- [x] Curva PMC com o histórico real e destaques do último dia — UAT + `test_potential_api.py:184-207`
- [x] VO2max com selo "estimativa" e decaimento destacando a maratona — UAT + `test_potential_calc.py:260-276`
- [x] Zero chamadas Garmin na leitura — `test_potential_api.py:286-296` (varredura de imports)
- [x] Suite verde no Postgres do compose pinando valores exatos — 228 passed

---

## Requirement Traceability Update

29/29 POT-NN verificados com evidência. O Verifier não altera `spec.md` (restrição de escrita desta validação) — statuses `Implemented → Verified` devem ser atualizados pelo orchestrator ao aceitar este veredito.

---

## Gaps Ranqueados

1. **⚠️ Spec-precision gap (não-bloqueante) — contradição interna da spec no edge case "PR sem data"**: o edge case (spec.md:201) diz que o PR canônico sem data "permanece elegível ao demonstrado", mas o AC POT-07 (spec.md:106) define demonstrado sobre "PRs canônicos **datados**" — e o design/tasks formalizaram `demonstrated(points)` (pontos = entradas datadas). A implementação segue o AC: PR sem data fica fora do demonstrado também (`service.py:145-151` — demonstrado derivado de `timeline_points`, que filtra sem data em `calc.py:80`). Nenhum teste pina qualquer um dos comportamentos para o demonstrado. **Recomendação**: reconciliar a spec (ou o edge case cede ao AC "datados" — postura atual, coerente com §9.5 "melhor VDOT de prova máxima"; ou o demonstrado passa a incluir PRs sem data — 1 linha em `service.py` + teste). Decisão do usuário/orchestrator; se mudar, vira fix task pequena.
2. **⚠️ Spec-precision gap (não-bloqueante) — formato do label do ponto "teste"**: a spec não define o texto do label do ponto de calibração; a implementação usa `calibration.source` verbatim ("10K em 41:15" — `calc.py:116`, pinado em `test_potential_calc.py:103,137`) e o design ilustrava "10K 41:15". Postura verbatim é defensável (dado real do arquivo), mas o formato exibido não está ancorado num AC. **Recomendação**: registrar o formato no design como contrato ou aceitar o verbatim (sem mudança de código exigida).
3. **Nota de cobertura (sem ação exigida)**: a cláusula "teste de calibração com data igual/futura a um PR → ambos viram pontos" (spec.md:207) está correta por construção (`calc.py:111-120` — append incondicional do teste; dedup só contra datas de PR) mas **não tem teste direto com datas colididas**. Quando a feature receber manutenção, adicionar 1 teste em `test_potential_calc.py` com `test_date == pr_date`.
4. **Nota, sem ação**: POT-11 "422 sem executar query" é garantia estrutural do FastAPI (`Query(ge=1, le=365)` no signature, `router.py:101` precede o handler) — o teste cobre o outcome observável (422), mesma postura aceita no TRN-09.
5. **Nota, sem ação**: UI (POT-17..20, 23..27, 29) coberta por decisão da matriz (build+lint+UAT) sem asserção automatizada — quando houver infra de teste frontend, cobrir os estados do painel.

---

## Summary

**Overall**: ✅ PASS — Ready

**Spec-anchored check**: 29/29 ACs com `file:line` + asserção conferida ao resultado da spec (pins re-derivados de forma independente); 10/10 edge cases verificados (8 testados, 2 notas); 2 ⚠️ spec-precision gaps não-bloqueantes
**Sensor**: 4/4 mutações mortas, 0 sobreviventes (worktree descartável; porcelain idêntico ao baseline antes/depois)
**Gate**: 228 passed / 0 failed / 0 skipped · frontend build+lint exit 0
**Test integrity**: 170 → 228 (+58), nenhum teste deletado, nenhuma asserção enfraquecida

**What works**: pipeline completo end-to-end (equações de Daniels em módulo único → calibração vigente do JSON → data dos PRs corrigida com self-heal → snapshot de predições sincronizado com 1 chamada tolerante → calc puro de timeline/demonstrado/gap/Riegel/média honesta/decay com dedup e validade → payload único de leitura 100% do banco próprio → UI com faixa honesta, narrativa §9.5, tabelas sem número inventado, PMC e VO2max condicionais), validado por 228 testes ancorados em literais re-derivados, 4 mutações mortas e UAT real de 15/10/2026.

**Issues found**: 2 spec-precision gaps (contradição interna do edge case "PR sem data" vs AC POT-07; formato do label "teste") — nenhum exige correção de código imediata; 1 edge case correto por construção sem teste direto.

**Next steps**: orchestrator atualiza statuses POT-01..POT-29 para `Verified` no spec.md; decidir o Gap #1 (reconciliar spec ou abrir fix task de 1 linha + teste se o usuário quiser PRs sem data elegíveis ao demonstrado); registrar as lições; subir a próxima feature.
