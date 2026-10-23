# Home Panel Validation

**Date**: 2026-10-23
**Spec**: `.specs/features/home-panel/spec.md`
**Diff range**: `56ebec3..6709066` (branch `home-panel`, 21 commits, árvore limpa)
**Verifier**: sub-agente independente (autor ≠ verificador); tree real read-only exceto este arquivo

---

## Validation: home-panel - PASS ✅

**Veredito**: PASS. 39/39 ACs P1+P2 com evidência `file:line` re-derivada do zero. Gate: 622 passed, 0 failed (exit 0). Sensor: 5 mutações, 5 mortas, 0 sobreviventes. Zero gaps bloqueantes. HOME-40 é P3 deferido pela própria spec (não conta como falha). Os dois Success Criteria de UAT visual são critérios do usuário: pending-user-UAT.

---

## Commits (range `56ebec3..HEAD`)

| Task | Commit | Task | Commit |
| ---- | ------ | ---- | ------ |
| T1 motor veredito | `3bf8f27` | T9 nav 5 itens | `987018b` |
| T2 recomendações | `93f7daf` | T10 card-veredito | `6798e64` |
| T3 delta+volume | `b264298` | T11 chips+cards | `d23d8a9` |
| T4 app_tz | `8d67c29` | T12 HomePanel raiz | `163d0cc` |
| T5 get_home | `c91740e` | T13 digest P2 backend | `6b066c0` |
| T6 router HomeOut | `66b8229` | T14 mini+digest render | `b8bd1f3` |
| T7 seed meia | `62f6a1c` | T15 docs+greps | `9e9b11d` |
| T8 api.ts HomeToday | `7c96af5` | hash registration | `6709066` (HEAD) |

Docs do ciclo (spec/design/tasks/handoff): `361cabb`, `e6fbe54`, `7de5b43`, `e3b92e7`, `741144c`.

---

## Task Completion

T1–T15: ✅ Done (checkboxes do tasks.md preenchidos; hashes registrados; gate verde). Nenhuma blocked ou partial.

---

## Spec-Anchored Acceptance Criteria (P1+P2 — 39)

Evidence-or-zero: cada linha tem `file:line` + asserção citada. Nome de teste não é evidência; o valor assertado bate com o resultado definido no spec (frases V1–V6 literais, whys, thresholds 0/−10/1.5/14, piso 7h=25200s, cap 3, strip 7 com lacunas 0.0, days_left dinâmico, 401, contrato, None-vazio ≠ "Dia comum").

### P1: Veredito do dia (motor + endpoint)

| AC | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| HOME-01 | `GET /api/home/today` → `HomeOut` com os blocos do painel, payload 1:1, nenhum bloco de outro painel | `backend/tests/test_home_api.py:114` — `assert set(body) == {"date","verdict","signals","strip","last_activity","volume","countdown","recommendations","volume_weeks","predictions"}` + blocos valor a valor `:118-160`; contrato `app/home/router.py:104-116` | ✅ PASS |
| HOME-02 | Veredito por função pura determinística; mesma consulta ⇒ mesmo veredito; zero rede/LLM/aleatoriedade | `backend/tests/test_home_verdict.py:193` — `assert verdict(signals) == verdict(signals)` (2 chamadas idênticas); pureza estrutural: `app/home/calc.py` importa só dataclasses/datetime + `health.calc` (stdlib, zero IO) | ✅ PASS |
| HOME-03 | UNBALANCED + noite < piso (7h) → `"Recuperação em dívida"`, tom `alert` | `backend/tests/test_home_verdict.py:64-68` — `v.phrase == "Recuperação em dívida"`, `v.tone == "alert"`, `v.rule == "V1"` (sono 21600s < 25200s); integração `test_home_service.py:116-120`; HTTP `test_home_api.py:219-220` | ✅ PASS |
| HOME-04 | UNBALANCED sem agravante de sono → `"Corpo pedindo leve"`, `attention` | `backend/tests/test_home_verdict.py:73-77` — phrase/tone/rule exatos (sono 28800s) | ✅ PASS |
| HOME-05 | `acwr > 1.5` → `"Carga alta — segure o volume"`, `attention` | `backend/tests/test_home_verdict.py:82-86` — acwr 1.6, phrase/tone/rule exatos | ✅ PASS |
| HOME-06 | `tsb < -10` → `"Acúmulo de fadiga"`, `attention` | `backend/tests/test_home_verdict.py:91-95` — tsb −10.5, phrase/tone/rule exatos | ✅ PASS |
| HOME-07 | BALANCED + `tsb > 0` + noite NÃO abaixo do piso → `"Pronto pra qualidade"`, `good` | `backend/tests/test_home_verdict.py:101-107` — BALANCED + tsb 5.2 + sono 8h, exatos; negativa `:209-216` (noite 6h bloqueia V5 → V6) | ✅ PASS |
| HOME-08 | Nenhuma regra dispara (incl. `hrv.status == null`) → `"Dia comum, sem urgências"`, `neutral` | `backend/tests/test_home_verdict.py:114-118` — status null → V6 exato; HTTP `test_home_api.py:258` | ✅ PASS |
| HOME-09 | Prioridade fixa V1→V6, primeiro casamento vence, uma frase por dia | `backend/tests/test_home_verdict.py:126-163` — 3 testes de prioridade (V1 vence V3/V4/V5; V2 vence V3/V4; V3 vence V4/V5) | ✅ PASS |
| HOME-10 | Sinal nulo é neutro; chip vazio ("coletando linha de base"/"sem dado") | `backend/tests/test_home_verdict.py:171-179` — sono 6h sem HRV → V6; forma nula não sustenta V5 `:177-179`; sem NENHUM sinal → None `:182-186`; sono ausente não bloqueia V5 `:219-224`; chips vazios `VerdictCard.tsx:103-143` (estrutural) | ✅ PASS |
| HOME-11 | Sessão inválida/ausente → 401 antes de qualquer query | `backend/tests/test_home_api.py:168-169` — `assert response.status_code == 401`, `body == {"detail": "não autenticado"}` (dependency `require_session`, `router.py:121`) | ✅ PASS |
| HOME-12 | `APP_TIMEZONE` inválida → fuso default + `logger.warning`, painel funcional | `backend/tests/test_home_api.py:280-290` — monkeypatch "Mars/Phobos", `status_code == 200`, `date == hoje` no fuso default, `"Mars/Phobos" in caplog.text` (WARNING, logger `app.core.tz`); não-regressão Saúde: `test_health_api.py:663+` (asserções idênticas, patch target movido com o código) | ✅ PASS |

### P1: Card-veredito + strip de 7 dias (frontend — sem framework de teste; instrument gap documentado, verificação estrutural read-only)

| AC | Spec-defined outcome | `file:line` + evidência estrutural | Result |
| --- | --- | --- | --- |
| HOME-13 | Herói `bg-raised`, eyebrow `"Hoje · [dia, data]"`, display 38–40px, chips valor+estado+tom | `frontend/src/components/home/VerdictCard.tsx:92` (`bg-raised`), `:93-95` (eyebrow `Hoje · {eyebrowDate}`), `:96` (`text-[38px]`, dentro da faixa), `:102-144` (chips com dot semântico) | ✅ PASS (estrutural, pending UAT) |
| HOME-14 | Strip = exatamente os últimos 7 dias de `aggregate_daily_loads`, barras neutras, hoje lime, caption `"carga · últimos 7 dias"` | Backend: `backend/tests/test_home_service.py:186-196` — lista exata de 7 pontos terminando hoje; `test_home_api.py:131-137` (datas+loads). Frontend: `VerdictCard.tsx:153-165` (hoje `chart.subject`=lime, demais `chart.context`), caption `:167` literal | ✅ PASS |
| HOME-15 | Dia sem carga → barra altura zero, não omitida | Backend: `test_home_service.py:188-196` (entradas `load 0.0` presentes na strip); `test_home_api.py:137` — `all(p["load"] == 0.0 for p in strip[:6])`. Frontend: `VerdictCard.tsx:160` (altura 0%) | ✅ PASS |
| HOME-16 | Dado anterior a hoje → chip exibe a data do dado, nunca antigo como hoje | Backend: `test_home_api.py:123-130` — `as_of: "2026-10-22"` propagado (≠ hoje). Frontend: `VerdictCard.tsx:121,132,140` — `${hrv.as_of < date ? ` · ${dayMonth(as_of)}` : ""}` | ✅ PASS (backend evidenciado + render estrutural) |
| HOME-17 | Loading = skeletons pulsando, sem spinner (DSN-23) | `frontend/src/components/home/HomePanel.tsx:52-65` — `Skeleton` no lugar do card+chips; grep `"Carregando"` vazio (page.tsx + components/home) | ✅ PASS (estrutural) |
| HOME-18 | Sem botão/ação de sync na Home (AD-023) | grep `SyncButton` em `components/home` vazio; `HomePanel.tsx` sem ação de sync; empty orienta para `/perfil` | ✅ PASS (estrutural) |

### P1: Chips de roteamento + countdown

| AC | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| HOME-19 | Chip último treino: distância + data relativa + `avaliado ✓` quando `evaluated`, rota `/treinos/{id}` | Backend: `test_home_service.py:213-220` — dict exato `{id, date, distance_m: 8000.0, evaluated: True}`; HTTP `test_home_api.py:138-139`. Frontend: `RoutingChips.tsx:84-90` (`href={/treinos/${id}}`, `formatKm`, `relativeDate`, ` · avaliado ✓`) | ✅ PASS |
| HOME-20 | Chip Volume: km da semana corrente vs média das 4 anteriores | Backend: `test_home_service.py:251-255` — `{week_km: 10.0, avg4_km: 35.0, delta_pct: -71.4}`; unit `test_home_volume.py:73-77`; HTTP `test_home_api.py:140` | ✅ PASS |
| HOME-21 | Média de 4 semanas == 0 → delta `—` (nunca divisão por zero) | Backend: `test_home_volume.py:95-98` — `avg4_km == 0.0` ⇒ `delta_pct is None` (guarda em `calc.py:207`). Frontend: `RoutingChips.tsx:95-100` (`"—"`) | ✅ PASS |
| HOME-22 | `days_left == 0` → `é hoje`; prova passada → chip omitido | Backend: `test_home_service.py:314` — `days_left == 0`; `:318-325` — só prova passada ⇒ `countdown is None` (filtro `date >= today`, `service.py:136`); `:299-303` próxima vence; `test_home_seed.py:96-105` — `days_left = (MEIA_DAY - today).days` dinâmico. Frontend: `RoutingChips.tsx:108-112` (`é hoje`), `:103` (null ⇒ chip omitido) | ✅ PASS |
| HOME-23 | `init_db` semeia The Best Açaí (2026-11-08, 21097.5m, goal null); re-executar não duplica | `backend/tests/test_home_seed.py:59-67` — name/date/distance/goal exatos; `:70-74` — 2× init_db ⇒ `count == 1`; `:77-84` — guard por usuário (prova alheia não bloqueia) | ✅ PASS |
| HOME-24 | Sem atividade → chip omitido, não estado vazio | Backend: `test_home_service.py:223-230` — só força ⇒ `last_activity is None`; `test_home_api.py:184` — null. Frontend: `RoutingChips.tsx:83` (`lastActivity !== null &&`) | ✅ PASS |

### P1: Recomendações determinísticas

| AC | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| HOME-25 | 1–3 recomendações, shape fixo, prioridade fixa, nunca >3 | `backend/tests/test_home_recommendations.py:125-131` — `set(r.__dataclass_fields__) == {"text","support","why","tone"}` exato; `:134-140` — `1 <= len(recs) <= 3` para toda combinação regra×countdown; `:96-102` — ordenação R4 > R5 | ✅ PASS (ver Observação 1) |
| HOME-26 | V5 → `"Boa janela pra sessão de qualidade"`, why `HRV · sono · forma` | `backend/tests/test_home_recommendations.py:21-26` — text/why/tone exatos; payload HTTP `test_home_api.py:240-245` (dict completo) | ✅ PASS |
| HOME-27 | V1/V2 → `"Priorize recuperação hoje — leve ou descanso"`, why `HRV · sono` | `backend/tests/test_home_recommendations.py:29-46` — texto exato; tone `alert` (V1) / `attention` (V2) | ✅ PASS |
| HOME-28 | V3/V4 → `"Segure o volume nesta semana"`, why `ACWR · forma` | `backend/tests/test_home_recommendations.py:49-63` — text/why exatos | ✅ PASS |
| HOME-29 | ≤14 dias da prova → `"Semana de prova — redução progressiva (taper)"`, why `prova em N dias`, independente do veredito | `backend/tests/test_home_recommendations.py:83-93` — dispara com V1 + why `prova em 10 dias`; `:96-102` independente e ordenado; `:105-110` boundary 14 e 0; `:113-117` negativa (None/15 ⇒ sem taper) | ✅ PASS |
| HOME-30 | V6 → `"Siga o leve de hoje"` com apoio `"Tudo dentro da faixa"` | `backend/tests/test_home_recommendations.py:66-75` — text/support/why/tone exatos; HTTP `test_home_api.py:259-266` | ✅ PASS |
| HOME-31 | Cards `Recomendação · regra` abaixo da dobra: texto, linha de apoio, tag why | `frontend/src/components/home/RecommendationCards.tsx:35` (`Recomendação · regra`), `:38` texto, `:39-43` apoio, `:44-48` tag `por quê: {why}` | ✅ PASS (estrutural) |

### P1: Home na raiz + navegação + estados

| AC | Spec-defined outcome | `file:line` + evidência | Result |
| --- | --- | --- | --- |
| HOME-32 | `/` renderiza o painel Home; redirect removido; `/hoje` permanece 404 | `frontend/src/app/(app)/page.tsx:8-14` — renderiza `<HomePanel/>`; grep `redirect` vazio; grep `hoje` em `frontend/src` sem rota (só comentários/copy) | ✅ PASS (estrutural) |
| HOME-33 | Nav 5 itens, Home em 1º, tab bar 5 colunas, uma fonte (`PANELS`) | `frontend/src/components/Nav.tsx:114-120` — `{href: "/", label: "Home"}` no índice 0; `:172` `grid grid-cols-5`; grep `grid-cols-4` vazio; special-case raiz `:127-129` (ativo só em `pathname === "/"`) | ✅ PASS (estrutural) |
| HOME-34 | Banco sem dado → estado vazio orientando primeiro sync com link `/perfil`, sem veredito | Backend: `test_home_service.py:341-359` — `verdict is None` + blocos nulos + strip estrutural 7×0.0; `test_home_api.py:172-189` (HTTP). Frontend: `HomePanel.tsx:75-90` — empty com link `/perfil` | ✅ PASS |
| HOME-35 | Fetch falha → estado de erro existente, sem frase de veredito | `frontend/src/components/home/HomePanel.tsx:67-73` — `kind: "error"` com mensagem, nenhum veredito renderizado | ✅ PASS (estrutural) |
| HOME-36 | Zero cor literal fora de chartTheme/globals; alvos ≥44px; `tabular-nums` nos números | grep `#[0-9A-Fa-f]{6}` em `components/home` vazio; `min-h-11` (44px) em `RoutingChips.tsx:58`, `HomePanel.tsx:84`, `PredictionsDigest.tsx:38`; `tabular-nums` em `VerdictCard.tsx:102`, `RoutingChips.tsx:63`, `VolumeMini.tsx:64`, `PredictionsDigest.tsx:35` | ✅ PASS (estrutural) |

### P2: Digest abaixo da dobra

| AC | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| HOME-37 | Mini 10 semanas: barras neutras, corrente lime, sentença `Xkm · ±Y% vs média de 4 semanas · ACWR Z` (valores do payload) | Backend: `backend/tests/test_home_predictions.py:185-191` — exatamente 10 semanas ISO ASC terminando na corrente, semana sem corrida `0.0`; unit `test_home_volume.py:104-110`; HTTP `test_home_api.py:151-156`. Frontend: `VolumeMini.tsx:50-72` (corrente `chart.subject`, sentença com "—" para delta null) | ✅ PASS |
| HOME-38 | Digest: tempos de 10K e meia (`average_s`) + link `ver Performance →` | Backend: `test_home_predictions.py:120-125` — `[{10K, 2448.2}, {HALF_MARATHON, 5421.0}]` exatos (pins da sonda + calibração); `test_home_service.py:265-268`; HTTP `test_home_api.py:157-160`. Frontend: `PredictionsDigest.tsx:25-27` (linha 10K · meia), `:40` (`ver Performance →`) | ✅ PASS |
| HOME-39 | Evento sem predição → omitido do digest (nunca número inventado) | `backend/tests/test_home_predictions.py:133-146` — 10K `average_s: None` ⇒ digest só com HALF_MARATHON: `assert predictions == [{"event": "HALF_MARATHON", "time_s": 5421.0}]` | ✅ PASS |

### P3 (deferido) + Success Criteria do usuário

| Item | Status | Nota |
| --- | --- | --- |
| HOME-40 (RHR no porquê) | ⏸️ P3-deferido | A própria spec marca Pending (rastreabilidade); fora do escopo P1+P2. Não é FAIL. |
| 390px sem scroll acima da dobra | ⏳ pending-user-UAT | Critério visual do usuário; exige `npm run build` + olho no device. Lint+build verdes foram gate das tasks frontend (T8–T15). |
| UAT visual contra o mock v0.3 | ⏳ pending-user-UAT | "O olho dele é o critério final de aceite" (spec). Não automatizável. |

**Status**: ✅ 39/39 ACs P1+P2 cobertos com evidência · 0 gaps · 2 observações (abaixo)

### Payload/conjunction rule (cada campo do `HomeOut` com asserção de valor/estado)

| Campo | Evidência |
| ----- | --------- |
| `date` | `test_home_api.py:200` (`date == hoje.isoformat()`), `test_home_service.py:350` |
| `verdict` | `test_home_api.py:118-122` (dict exato phrase/tone/rule), `:182` (null) |
| `signals.hrv` | `test_home_api.py:123-125` (`{value: 40.0, status: "UNBALANCED", as_of: "2026-10-22"}`) |
| `signals.sleep` | `test_home_api.py:126-127` (duration_s 21600.0, delta_s −7200.0) + as_of `test_home_service.py:129` |
| `signals.fitness` | `test_home_api.py:128-130` (`{tsb: -5.0, acwr: 1.2, as_of}`) |
| `strip` | `test_home_api.py:131-137` (7 pontos, datas, loads) |
| `last_activity` | `test_home_api.py:138-139` (distance_m 5000.0, evaluated true) + dict completo `test_home_service.py:215-220` |
| `volume` | `test_home_api.py:140` (`{week_km: 5.0, avg4_km: 7.5, delta_pct: -33.3}`) |
| `countdown` | `test_home_api.py:141-143` (dict exato name/date/days_left) |
| `recommendations` | `test_home_api.py:144-146` (1..3, 4 campos exatos) + conteúdo `:240-245`, `:259-266` |
| `volume_weeks` | `test_home_api.py:151-156` (10 semanas, km por semana, soma) |
| `predictions` | `test_home_api.py:157-160` (lista exata) |

---

## Discrimination Sensor

Scratch isolado: `git worktree add C:\Users\leona\AppData\Local\Temp\opencode\home-panel-sensor HEAD` (branch à parte; tree real intocado; `git stash` não usado). Baseline `git status --porcelain` do tree real antes do sensor: **vazio**. Sanity run sem mutação: 17 passed. Cada mutação aplicada no scratch, testes relevantes com `-x -q` (suite cheia não roda por mutação), arquivo restaurado via `git checkout`, worktree removido com `--force` ao final.

| # | Mutação (comportamental) | Onde (tree real) | Testes rodados | Resultado |
| - | ------------------------ | ---------------- | -------------- | --------- |
| 1 | Inverter prioridade V1/V2 na cadeia (V2 avaliada antes de V1) | `backend/app/home/calc.py:96-99` | `tests/test_home_verdict.py -x` | ✅ KILLED — `test_v1_unbalanced_and_night_below_floor`: `'Corpo pedindo leve' != 'Recuperação em dívida'` (exit 1) |
| 2 | Boundary `acwr > ACWR_HIGH` → `>=` (1,5 vira V3) | `backend/app/home/calc.py:89` | `tests/test_home_verdict.py -x` | ✅ KILLED — `test_thresholds_are_strict`: `'V3' != 'V6'` em acwr == 1.5 (exit 1) |
| 3 | Suprimir distinção estado-vazio: `return None` → V6 "Dia comum" | `backend/app/home/calc.py:82-83` | `tests/test_home_verdict.py tests/test_home_api.py -x` | ✅ KILLED — `test_no_signals_returns_none`: `Verdict(...V6) != None` (exit 1); `test_empty_bank...` e `test_empty_state...` também o matam |
| 4 | Zero-fill de lacunas do strip → omissão do dia (`loads[day]` + `if day in loads`) | `backend/app/home/service.py:85-88` | `tests/test_home_service.py tests/test_home_api.py -x` | ✅ KILLED — `test_empty_bank_verdict_none_and_null_blocks`: `[] != [7 entradas]` (exit 1). Nuance: o kill veio do banco vazio; ver Observação 2 |
| 5 | Countdown aceita prova passada (remove `Race.date >= today`) | `backend/app/home/service.py:136` | `tests/test_home_service.py -x` | ✅ KILLED — `test_countdown_picks_nearest_upcoming_race`: `{'Passou', days_left: -5} != {'Alvo', 10}` (exit 1); `test_countdown_past_race_only_is_none` idem |

**Sensor depth**: 5 mutações manuais (domínio crítico: motor de veredito + montagem). **Result: 5/5 killed, 0 sobreviventes.**

**Isolamento pós-sensor**: `git worktree remove --force` + `git worktree prune`; diretório scratch confirmado removido; `git status --porcelain` do tree real = vazio (idêntico ao baseline). Frontend: sem framework de teste (gap de instrumento conhecido, documentado em `.specs/features/design-system/validation.md`); sensor cobre backend; frontend validado por greps estruturais re-rodados (abaixo).

---

## Greps estruturais (Success Criteria, re-rodados read-only)

| Grep | Resultado |
| ---- | --------- |
| `redirect` em `frontend/src/app/(app)/page.tsx` | vazio ✅ |
| `#[0-9A-Fa-f]{6}` em `frontend/src/components/home` | vazio ✅ |
| `Carregando` em page.tsx + components/home | vazio ✅ |
| `SyncButton` em components/home | vazio ✅ |
| `grid-cols-4` em Nav.tsx | vazio ✅ |
| `grid-cols-5` em Nav.tsx | presente (`Nav.tsx:172`) ✅ |
| Home em 1º em `PANELS` | presente (`Nav.tsx:115`) ✅ |
| `/hoje` rota | inexistente (AD-016 intacta) ✅ |

---

## Gate Check

- **Gate command**: `uv run pytest` (workdir `backend/`, suite cheia, run único, timeout 1200000ms)
- **Result**: **622 passed, 0 failed** — exit 0, 466.77s
- **Test count before feature**: 550 (baseline tasks.md) · **after**: 622 · **delta**: +72 (test_home_api 8 · test_home_predictions 6 · test_home_recommendations 13 · test_home_seed 5 · test_home_service 13 · test_home_verdict 17 · test_home_volume 10)
- **Skipped**: nenhum
- **Failures**: nenhuma. Flake conhecido (`test_garmin_tokens_store` monotonicidade de relógio, ~2/4 no Windows) **não apareceu** nesta execução; nenhuma re-run necessária.
- **Test integrity**: contagem subiu (nunca caiu); nenhum teste excluído. Única modificação em teste existente: `test_health_api.py:663+` trocou o patch target (`health_router` → `core_tz`) acompanhando a extração T4 — asserções idênticas (200 + warning + data), diff revisado; não é enfraquecimento.

---

## Code Quality

| Princípio | Status |
| --------- | ------ |
| Sem features além do pedido (Out of Scope respeitado: sem habit tracker, sem alertas, sem CRUD de provas, sem LLM no veredito) | ✅ |
| Sem abstrações para código de uso único (`_today` 3-liner local documentado; `get_predictions` extraído só porque 2 consumidores) | ✅ |
| Mudanças cirúrgicas (31 arquivos no diff, todos mapeados a T1–T15; nenhum código adjacente "melhorado") | ✅ |
| Match com padrões existentes (layering AD-003 calc/service/router; PanelState do HealthPanel; seeds idempotentes AD-019; fetchers same-origin AD-020) | ✅ |
| Spec-anchored outcome check (valores literais: frases, whys, thresholds, piso 25200s, pins de sonda) | ✅ |
| Per-layer coverage (domínio 1:1 com ACs; rota happy + 401 + vazio + tz edge; service fixtures de banco) | ✅ |
| Todo teste em escopo mapeia a AC/done-when (docstrings citam HOME-xx; nenhum teste órfão) | ✅ |
| Diretrizes documentadas: `frontend/AGENTS.md` (Next 16), matriz de cobertura do tasks.md (pytest 9 + conftest) | ✅ |

---

## Edge Cases (spec §Edge Cases)

- [x] Sessão ausente → 401 pré-query (HOME-11; `test_home_api.py:163`)
- [x] `APP_TIMEZONE` inválida → default + warning (HOME-12; `test_home_api.py:274`)
- [x] Sinais nulos com histórico → "Dia comum" honesto, nunca alerta sem evidência (`test_home_service.py:154-167`; `test_home_verdict.py:171-186`)
- [x] `days_left == 0` → "é hoje"; passada → omitido (`test_home_service.py:306-325`; `RoutingChips.tsx:103-113`)
- [x] Média 4 semanas 0 → delta `—` (`test_home_volume.py:92-98`; `RoutingChips.tsx:95-100`)
- [x] Evento sem predição → omitido (`test_home_predictions.py:128-146`)
- [x] Semana/dia sem carga → barra zero, não omitida (`test_home_service.py:175-196`; `VerdictCard.tsx:160`)

---

## Observações (não bloqueantes, nenhum fix task exigido)

1. **HOME-25, notação do shape**: o spec escreve `{texto, why[], tom}`; o design aprovado (`design.md` §Contrato) fixa `{text, support, why, tone}` — `support` é exigido pelo próprio HOME-30 ("copy de apoio") e `why` é string como em todos os exemplos do spec ("HRV · sono"). Os testes afirmam o shape do design exato (`test_home_recommendations.py:125-131`). Spec internamente inconsistente, resolvida pelo design; nenhum comportamento fora do especificado.
2. **Sensor mutação 4, nuance do kill**: `test_strip_seven_days_ending_today_with_gaps` semeia atividade hoje, então `aggregate_daily_loads` já cobre a janela com preenchimento contíguo e não discrimina sozinho a omissão de dias. O mutante morreu pelos testes de banco vazio (`test_empty_bank...`, `test_empty_state...`), que exercem a mesma expressão `loads.get(day, 0.0)` com chaves ausentes. Cenário "última atividade < hoje" usa o mesmo caminho de código já pinado; mutante morto, discriminação garantida.

**Ranked gaps**: nenhum. Zero mutantes sobreviventes, zero ACs sem evidência, zero divergências spec↔comportamento.

---

## Requirement Traceability

Statuses no spec.md já estavam `Verified` (HOME-01..39) e `Pending` (HOME-40) e **coincidem com este relatório** — nenhuma atualização necessária. Espec.md não foi alterado (tree read-only para o Verifier).

---

## Summary

**Overall**: ✅ Ready (pending-user-UAT para os 2 critérios visuais)

**Spec-anchored check**: 39/39 ACs P1+P2 com evidência `file:line` · 0 spec-precision gaps · 1 notação de shape resolvida pelo design (Obs. 1)
**Sensor**: 5/5 mutações mortas
**Gate**: 622 passed, 0 failed (+72 vs baseline 550; flake conhecido ausente)

**What works**: motor V1–V6 determinístico com frases/toms literais e prioridade fixa; recomendações R1–R5 com cap 3 e taper independente; strip 7 dias com lacunas zeradas; countdown dinâmico com seed idempotente; 401 pré-query; edge de timezone; contrato HomeOut 1:1 campo a campo; raiz como Home com nav de 5 itens e estados vazio/erro/skeleton.

**Issues found**: nenhum bloqueante. Dois critérios visuais aguardam o UAT do usuário (390px sem scroll; olho contra o mock v0.3).

**Next steps**: UAT visual do usuário contra o mock v0.3; após aceite, o orquestrador decide o commit deste validation.md.

**Lessons**: nenhuma gravada — PASS limpo, sem mutante sobrevivente nem gap (lessons.md: clean PASS → record nothing).
