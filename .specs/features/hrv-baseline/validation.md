# HRV Baseline Científico (hrv-baseline) — Validation

**Date**: 2026-10-17
**Spec**: `.specs/features/hrv-baseline/spec.md` (15 ACs, HRV-01..HRV-15; HRV-14 P3 deferred/Pending por design — não é gap)
**Diff range**: `1ace5a1..8b7aaed` — 6 commits (`a04fe92` calc, `1ca1af7` service+router+testes [T2+T3 fundidas, documentado em `tasks.md:119,148-150` — não é desvio], `0318b5d` backfill, `d805cec` HrvChart+api.ts, `9e7fbab` HrvTable, `8b7aaed` docs); 17 arquivos, +777/−148
**Verifier**: sub-agente independente (author ≠ verifier) — spec rederivada do zero, asserções abertas e conferidas ao valor exato; árvore real intacta (`git status --porcelain` vazio antes e depois do sensor); mutações só em worktree descartável fora do repo (`C:\Users\leona\AppData\Local\Temp\opencode\hrv-vrf-scratch`, detached `8b7aaed`, removido com `--force`; `git worktree list` = só `main`)

---

## Validation — Veredito: PASS ✅

**14/14 ACs implementados (HRV-01..HRV-13 + HRV-15) com evidência `file:line`** e resultado conforme o desfecho definido pela spec (0 spec-precision gaps); HRV-14 (P3) Pending por design — não avaliado, não é gap; 4/4 edge cases verificados; gates verdes (backend **280 passed** = 268 base + 12 novos, 0 failed, 0 skipped; frontend build+lint exit 0); sensor **3/3 mutações mortas**. ACs de UI verificados por inspeção de código com citação `file:line` + asserção comportamental (o que renderiza), conforme a matriz da feature (sem runner de teste no frontend — precedente `.specs/features/panel-clarity/validation.md:39`); UAT real 390px fica após este Verifier (Handoff `STATE.md`).

---

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 `hrv_model` no calc | ✅ Done | `backend/app/health/calc.py:29-32` (réguas `HRV_AVG_DAYS=7`, `HRV_BASELINE_DAYS=60`, `HRV_BASELINE_MIN_VALUES=14`, `HRV_BASELINE_SD_FACTOR=0.75`), `calc.py:61-117` (`hrv_model`: janela de exibição `L−(days−1)` :84-85; `avg7` média dos disponíveis em `[d−6, d]` :88-99; banda `[d−59, d]` ≥14 :89-94; `current`+status sem arredondar :108-116); 8 testes unitários (`test_health_calc.py:388-537`) |
| T2 `_hrv_history`+`_hrv_block` + isolamento | ✅ Done | `backend/app/health/service.py:117-135` (`max(date)` do usuário :121-123; `start = latest − (days−1+59)` :126; filtro `Hrv.user_id == DEFAULT_USER_ID` :122,130), `service.py:138-170` (`_hrv_block`: `[]` → `None` :144-145; arredondamento 1 casa só no payload via `_one` :148-149,156-158; status cru da Garmin ausente do payload :151-170), mount :268; teste de isolamento (`test_health_api.py:322-398`); `_series` segue para dose-resposta :250,260 |
| T3 contrato router + pins (fundida na T2) | ✅ Done | `backend/app/health/router.py:68-96` (`HrvPoint`/`HrvCurrent`/`HrvBlock` — sem campo de status Garmin), :168-175 (`HealthSummaryOut.hrv`), :191-200 (`days` [7,365] intocado); pins novos (`test_health_api.py:190-209, 605-612`) + cenários 119d/UNBALANCED/days=7 (`:406-475`) |
| T4 backfill 120d | ✅ Done | `backend/app/core/config.py:48` (`sync_backfill_health_days: int = 120` + comentário HRV-15); `test_sync_config.py:34-38` (default 120), :59-73 (env override 90); `test_garmin_service.py:41,116,540-555` (sync full persiste 121 dias [TODAY−120, TODAY] ≥ 119); teto conferido: 120×4+extras = 499 < 1500 (`test_garmin_service.py:117-118`) |
| T5 api.ts + HrvChart rewrite | ✅ Done | `frontend/src/lib/api.ts:338-359` (espelho do contrato: `HrvPoint`/`HrvCurrent`/`HrvBlock`, sem status Garmin); `HrvChart.tsx:118-215` (banda 2 Areas empilhadas :176-194, linha `avg7` `connectNulls={false}` :198-206, noites Scatter :208, card status local :139-141, contexto :144-152, noites fora em âmbar :80-92) |
| T6 HrvTable + mount | ✅ Done | `frontend/src/components/health/HrvTable.tsx:1-93` (7 linhas/página :13,29-30; desc sobre `value ≠ null` :24-28; `atual/total` só >7 :68,78-80); mount no card do HRV abaixo do gráfico (`HealthPanel.tsx:153-158`, import :18); janela fixa 60d (`HealthPanel.tsx:47` chama `getHealthSummary()` default `days=60` — `api.ts:423`) |
| T7 docs + memory + traceability | ✅ Done | `docs/PLANO_PLATAFORMA.md:109` (§4.5 modelo científico, sem resquício do modelo antigo); `.specs/STATE.md:77-84` (AD-010: decision/reason/trade-off/scope/date/status active) + Handoff com ops-note do re-sync (`STATE.md` Handoff); traceability spec :155-169 (HRV-01..13+15 ✅ Verified, HRV-14 Pending); checkboxes de tasks.md todos `[x]` |

Todas as 7 tasks `[x]` em `tasks.md`; nenhuma blocked ou parcial. T2+T3 num único commit coeso, documentado na própria task (`tasks.md:119, 148-150`) — o corte intermediário deixaria a suite vermelha.

---

## Spec-Anchored Acceptance Criteria

**Convenção da matriz** (`tasks.md:22-28` + precedente `panel-clarity/validation.md:39`): ACs de contrato/matémática por pytest com pins literais; ACs de UI por inspeção do código do componente com citação `file:line` + a asserção comportamental da spec (o que renderiza). Evidence-or-zero aplicado: todos os 14 têm citação. Valores canônicos conferidos à mão: banda 15 valores 60..88 → 74 ± 0,75√80 = (67,291796, 80,708204) ✓; supressão → 60 ± 0,75√840 = (38,262935, 81,737065) ✓; primeiro dia 119d → 70,1667 ± 0,75√(5/3) → (69,2, 71,1) com 1 casa ✓.

### P1: Gráfico no modelo científico (HRV-01..HRV-05)

| Criterion | Spec-defined outcome | `file:line` + asserção/inspeção | Result |
| --------- | -------------------- | -------------------------------- | ------ |
| HRV-01: painel carrega com ≥1 dia de HRV → gráfico exibe um ponto discreto para cada noite individual da janela de 60 dias corridos | ponto por noite com dado; dias corridos terminando na última data com dado `L` (janela = `L−59..L`, não "hoje") | Contrato: `calc.py:84-85,95-103` (`day = latest − timedelta(days=days−1)`; `"value": by_date.get(day)`); pins: `test_health_calc.py:521-537` — `len(model["points"]) == 10`, `points[0]["date"] == 2026-10-06`, `points[-1]["date"] == 2026-10-15`, `[p["value"] for p in points if value is not None] == [70.0]` (dado de 08-20 fora da exibição); API: `test_health_api.py:194-195` (`len(hrv["points"]) == 60`, `points[0]["date"] == 2026-08-17` terminando em 15/10); UI: `HrvChart.tsx:208` `<Scatter dataKey="value" shape={NightDot} />` + `HrvChart.tsx:75-93` (círculo `r=2` renderizado só quando `point.value != null` — noite individual como ponto discreto) | ✅ PASS |
| HRV-02: linha com um ponto por dia corrido cuja janela móvel de 7 dias contenha ≥1 valor, valor = média dos valores **disponíveis** na janela de 7 dias corridos terminando naquele dia | média sobre o disponível (lacuna não quebra a linha); janela `[d−6, d]` | Contrato: `calc.py:88` (`w7 = window(day - timedelta(days=HRV_AVG_DAYS - 1), day)`) + :99 (`"avg7": sum(w7)/len(w7) if w7 else None`); pins: `test_health_calc.py:397-418` — dia 10-03 sem captura: `value is None` + `avg7 == 65.0` (média (60+70)/2); truncada: 10-01 `== 60.0` (só ela), 10-04 `== 70.0` ((60+70+80)/3); API: `test_health_api.py:201-204` (`avg7 == 82.0`, `== 75.0` (82+68)/2, `== 75.0` (82+68+75)/3); UI: `HrvChart.tsx:198-206` `<Line dataKey="avg7" connectNulls={false}>` (ponto por dia com valor; null sem ponto) | ✅ PASS |
| HRV-03: janela móvel de 7 dias de um dia corrido sem nenhum valor → dia exibido sem ponto na linha | `avg7` None; nenhum valor inventado | Pin: `test_health_calc.py:421-436` — histórico 09-01 e 10-10: `by_day[2026-10-04]["avg7"] is None`, `by_day[2026-10-09]["avg7"] is None`, `by_day[2026-10-10]["avg7"] == 60.0` (só ela na janela); :413 (`by_day[2026-09-28]["avg7"] is None`); UI: `HrvChart.tsx:205` `connectNulls={false}` — null quebra a linha (dia sem ponto) | ✅ PASS |
| HRV-04: janela móvel de 60 dias de um dia exibido com ≥14 valores → banda para esse dia = média ± 0,75 × DP **amostral** (n−1) da janela daquele dia, atrás da série | banda por dia (móvel, desliza); DP amostral `statistics.stdev`; atrás da série | Contrato: `calc.py:89-94` (`w60 = window(day − 59d, day)`; `len(w60) >= HRV_BASELINE_MIN_VALUES` → `mean ± HRV_BASELINE_SD_FACTOR * stdev(w60)`); pin à mão: `test_health_calc.py:439-458` — `round(band_low, 6) == 67.291796`, `round(band_high, 6) == 80.708204` (15 valores 60..88: média 74, var 1120/14=80); banda DESLIZA dia a dia: `test_health_api.py:406-430` — 119 dias semeados: `all(p["band_low"] is not None)` nos 60 exibidos, primeiro dia `band_low == 69.2`/`band_high == 71.1` (59×70+1×80) ≠ último `80.0/80.0`; UI: `HrvChart.tsx:176-194` — 2 `<Area stackId="band">` (base transparente + span `fillOpacity 0.12`) declaradas **antes** de Line/Scatter no ComposedChart → renderizadas atrás da série | ✅ PASS |
| HRV-05: janela móvel de 60 dias com <14 valores → dia exibido sem banda | banda null sob threshold, por dia | Contrato: `calc.py:90-91` (`band_low = band_high = None` fora do threshold); pins de fronteira: `test_health_calc.py:452-453` — 13 valores → `band_low is None`; 14 valores → `band_low is not None`; :496-518 — 3 noites: `all(p["band_low"] is None)` + `current` banda null; API: `test_health_api.py:205` (3 noites → todos sem banda), :449-450 (119d-parcial: primeiro dia exibido com janela vazia → `band_low is None`); UI: `HrvChart.tsx:126-127` (`bandSpan = null` quando banda falta) + :185-194 (null quebra a Area — dia sem banda não desenha) | ✅ PASS |

### P1: Status local explicável no card (HRV-06..HRV-09)

| Criterion | Spec-defined outcome | `file:line` + asserção/inspeção | Result |
| --------- | -------------------- | -------------------------------- | ------ |
| HRV-06: janela de 60d do último dia com dado com ≥14 valores → card exibe status local: BALANCED dentro da banda (limites **inclusos**), UNBALANCED fora | comparação SEM arredondar; limites inclusos | Contrato: `calc.py:110-115` (`if current["band_low"] is not None: status = "BALANCED" if low <= avg7 <= high else "UNBALANCED"` — valores crus, sem `round`); pins: `test_health_calc.py:461-474` — borda inclusiva: 15 valores iguais → banda (70, 70), média 70 → `status == "BALANCED"`; :477-493 — queda: média 7d 20 fora de (38,262935, 81,737065) → `"UNBALANCED"`; API: `test_health_api.py:427-430` (`current.status == "BALANCED"` com banda completa), :451-454 (`"status": "UNBALANCED"`); UI: `HrvChart.tsx:139-141` — badge renderiza `current.status` (o status local do payload) | ✅ PASS |
| HRV-07: status exibido → card exibe junto a média 7d e os limites da banda do último dia com dado, com 1 casa decimal | média 7d + limites visíveis; 1 casa (arredondamento só na exibição) | Contrato: `service.py:148-149` (`_one` = `round(value, 1)`) aplicado a `avg7/band_low/band_high` :156-158,165-167 (status já decidido sem arredondar no calc); pins: `test_health_api.py:424-426` (`avg7 == 71.4`, `band_low == 69.2`, `band_high == 71.1` — 1 casa), :451-454 (`38.3/81.7`); UI: `HrvChart.tsx:144-152` — `média 7d {formatVdot(current.avg7)} ms · banda {formatVdot(current.band_low)}–{formatVdot(current.band_high)} ms`, `formatVdot` = `toFixed(1)` PT-BR (`frontend/src/lib/format.ts:33-35`) | ✅ PASS |
| HRV-08: janela de 60d do último dia com dado com <14 valores → card mantém o valor da última noite e exibe "coletando linha de base" no lugar do status | value/avg7 preservados; status null → texto explícito | Contrato: `calc.py:106-116` (`current` = último dia com dado — `value`/`avg7` garantidos; `status = None` sem banda); pins: `test_health_calc.py:510-517` — `current == {date 10-15, value 75.0, avg7 75.0, band_low None, band_high None, status None}`; API: `test_health_api.py:206-209` (idem via service), HTTP: `test_health_api.py:609-612` (`"status": None` no JSON); UI: `HrvChart.tsx:134-141` — valor da última noite em destaque (`formatVdot(current.value)} ms`) + `{current.status ?? "coletando linha de base…"}` (fallback textual no lugar do badge) | ✅ PASS |
| HRV-09 (ubiquitous): UI do bloco HRV exibe APENAS o status local, omitindo o status cru da Garmin em todas as superfícies do bloco | status Garmin fora do payload e do render do bloco (persistido na tabela) | Contrato: `router.py:68-96` (`HrvPoint`/`HrvCurrent`/`HrvBlock` sem nenhum campo de status Garmin — `status: str \| null` :91 é o LOCAL) + `service.py:151-170` (payload sem status cru; dict-equality pins flagrariam chave extra: `test_health_api.py:196-199, 206-209, 381-384, 605-612`); cliente: `api.ts:338-359` (espelho sem status Garmin); UI: inspeção — os únicos usos de `status` no bloco são `current.status` local (`HrvChart.tsx:140`); `HrvTable.tsx` não tem coluna status (design §Decisões.4); o chip "Contexto do dia" do treino mantém o status Garmin (`WorkoutDetail.tsx:205`, tipo `api.ts:191`) — explicitamente out of scope (spec §Out of Scope: "superfície fora do painel Saúde") | ✅ PASS |

### P1: Histórico que sustenta a banda (HRV-15)

| Criterion | Spec-defined outcome | `file:line` + asserção | Result |
| --------- | -------------------- | ----------------------- | ------ |
| HRV-15: backfill inicial de saúde busca ≥119 dias corridos por tipo de dado (60 exibição + 59 lookback) | default 120; env override; ≥119 persistidos em base nova | Config: `backend/app/core/config.py:48` (`sync_backfill_health_days: int = 120` + comentário citando HRV-15); pins: `test_sync_config.py:34-38` — `settings.sync_backfill_health_days == 120`; :59-73 — `SYNC_BACKFILL_HEALTH_DAYS=90` → `== 90` (100% env var); sync full em base sem `sync_state`: `test_garmin_service.py:540-555` (`test_health_backfill_covers_hrv_band_lookback`) — `oldest == BACKFILL_HEALTH_START` (2026-06-16 = TODAY−120, :41), `newest == TODAY`, `_count(s, Hrv) == 121  # >= 119 do AC`; happy path: `test_garmin_service.py:116` (`hrv_days == 121`); janela servida: `fake.calls["sleep"][0] == (BACKFILL_HEALTH_START,)` (:194); efeito de leitura: `test_health_api.py:457-475` — `days=7` exibe 7 pontos mas o primeiro tem `band_low == 80.0` com janela de 60d (lookback `days+58` :`service.py:126`); teto: 499 chamadas < `sync_max_calls=1500` (`test_garmin_service.py:117-118`) | ✅ PASS |

### P1: Tabela diária com paginação (HRV-10..HRV-12)

| Criterion | Spec-defined outcome | `file:line` + inspeção | Result |
| --------- | -------------------- | ---------------------- | ------ |
| HRV-10: bloco renderiza com ≥1 dia com dado → tabela exibe os até 7 dias com dado mais recentes em ordem decrescente, colunas Data (PT-BR), HRV e média 7d, valores com 1 casa | só dias com dado; desc; Data "20/04/2026"; 1 casa; tabular-nums | UI: `HrvTable.tsx:24-28` — `hrv.points.filter((p) => p.value !== null).slice().reverse()` (dias com dado, mais recente primeiro — sem linhas "—", spec assumption); :29-30 (`nights.slice(page*7, page+1*7)` = até 7); :36-45 (cabeçalhos `Data`/`HRV`/`Média 7d`); :55 (`fullDay` → `dd/mm/yyyy` PT-BR wall clock); :57-62 (`formatVdot` 1 casa + `tabular-nums`); dados vêm do contrato de dias corridos pinado (`test_health_api.py:605-608` — `points[59]` com `value: 75.0`); mount no card: `HealthPanel.tsx:153-158` | ✅ PASS |
| HRV-11: >7 dias com dado → controles que avançam de 7 em 7 + indicador "atual/total" sobre a janela de 60 dias | paginação 7 em 7 client-side; indicador `atual/total` | UI: `HrvTable.tsx:13` (`PAGE_SIZE = 7`), :29 (`totalPages = Math.ceil(nights.length / PAGE_SIZE)`), :30 (`rows` avançam 7 em 7), :68-90 — botões `Anterior`/`Próxima` (`setPage(p => Math.max(0, p−1))` / `Math.min(totalPages−1, p+1)`) + `:78-80` `{page + 1}/{totalPages}` (formato atual/total); janela de 60 dias fixa: `HealthPanel.tsx:47` → `getHealthSummary()` default `days=60` (`api.ts:423`) | ✅ PASS |
| HRV-12: ≤7 dias com dado → linhas disponíveis SEM controles de paginação | controles ausentes com ≤7 | UI: `HrvTable.tsx:68` — `{totalPages > 1 && (…)}`: com ≤7 noites `totalPages == 1` → bloco de controles não renderiza; a tabela em si (:34-66) renderiza as linhas disponíveis independentemente | ✅ PASS |

### P2: Noites fora da faixa destacadas (HRV-13)

| Criterion | Spec-defined outcome | `file:line` + inspeção | Result |
| --------- | -------------------- | ---------------------- | ------ |
| HRV-13: faixa normal presente → pontos das noites fora da faixa (abaixo OU acima) usam cor diferenciada das noites dentro | cor diferenciada só quando banda existe; fora = `< low` ou `> high` | UI: `HrvChart.tsx:80-83` — `const out = point.band_low != null && point.band_high != null && (point.value < point.band_low || point.value > point.band_high)` (abaixo ou acima; noites sem banda nunca marcadas); :84-92 — `<circle fill={out ? OUT_COLOR : HRV_COLOR}>` com `OUT_COLOR = "#fbbf24"` âmbar (:31), dentro da banda `#38bdf8` (:29); legenda com a entrada "noite fora da banda" (:96-101); contrato alimenta os dois campos (banda por ponto — `test_health_api.py:425-426`) | ✅ PASS |

**HRV-14** (P3: paginar além de 60 dias até 365): **deferred por design** — traceability Pending (spec.md:169), out of scope declarado (spec.md:25). `HrvTable` pagina client-side apenas a janela carregada de 60 dias; o endpoint suporta `days` até 365 (router.py:193). Não é gap.

**Status**: ✅ 14/14 ACs implementados com evidência `file:line` + asserção/inspeção conferida ao desfecho EXATO da spec (janela `[d−6,d]`, banda `[d−59,d]` ≥14, ±0,75 DP amostral n−1, limites inclusos sem arredondar, janela de exibição `days` dias corridos em `L`, backfill ≥119, "coletando linha de base"). 0 spec-precision gaps.

---

## Edge Cases (spec.md:142-147)

- [x] **Nenhum dado de HRV → bloco exibe o estado vazio existente (sem gráfico e sem tabela)** — `service.py:144-145` (`_hrv_block([])` → `None`); pin: `test_health_api.py:251` (`payload["hrv"] is None`) e via HTTP `:645` (`body["hrv"] is None`); UI: `HealthPanel.tsx:153-163` (`hrv !== null ? <HrvChart>+<HrvTable> : <BlockEmpty>`) — sem gráfico, sem tabela
- [x] **Histórico começa dentro da janela → médias 7d dos primeiros dias usam os valores disponíveis (janela móvel truncada)** — pins: `test_health_calc.py:414-415` (10-01 `avg7 == 60.0` — só ela na janela), `:436` (09-05 `avg7 == 50.0` — 09-01 alcançada pela janela 7d); API: `test_health_api.py:201-202` (`avg7 == 82.0` primeira noite, `== 75.0` (82+68)/2)
- [x] **Histórico total menor que o lookback (primeiro sync) → dias com <14 valores ficam sem banda até o threshold completar** — pins: `test_health_calc.py:518` (`all(p["band_low"] is None)`), `test_health_api.py:205` (3 noites → 60 pontos todos sem banda), `:449-450` (primeiro dia exibido com janela 60d vazia → `band_low is None`); UI quebra a Area nesses dias (`HrvChart.tsx:126-127`)
- [x] **Média 7d exatamente igual a um limite da faixa → BALANCED (limites inclusos)** — pin: `test_health_calc.py:461-474` — 15 valores iguais → DP 0 → banda (70, 70), `avg7 == 70.0`, `status == "BALANCED"` (comparação `<=`/`>=` em `calc.py:113`)

**Independent Tests da spec** (spec.md:67,84,98,114): 119 dias → banda deslizando pinada (`test_health_api.py:406-430`); <threshold → sem banda (`test_health_calc.py:439-458, 496-518`); queda fora da banda → UNBALANCED (`test_health_calc.py:477-493`, `test_health_api.py:433-454`); 8 dias → status null/"coletando" (contrato pinado `test_health_api.py:206-209` + UI fallback `HrvChart.tsx:140`); backfill 120 → ≥119 persistidos (`test_garmin_service.py:540-555`); tabela 30 dias/5 dias → inspeção (`HrvTable.tsx:13,29-30,68` — mesmo código-path, sem runner no frontend).

---

## Discrimination Sensor

**Tier**: lightweight (3 mutações comportamentais no código novo de maior risco — 2 no modelo puro `calc.py`, 1 no isolamento de `service.py`).
**Scratch**: `git worktree add C:\Users\leona\AppData\Local\Temp\opencode\hrv-vrf-scratch HEAD` (detached `8b7aaed`, venv próprio via `uv run`); alvo por mutação: `uv run pytest tests/test_health_calc.py tests/test_health_api.py -q` (conftest aponta o `ritmo_test` do compose — suite real da árvore NÃO rodou em paralelo). M1 e M2 no mesmo arquivo, uma por vez com revert entre elas. Nenhuma mutação tocou a árvore real — `git status --porcelain` vazio antes e depois (baseline idêntico); worktree removido com `--force`; `git worktree list` mostra só `main`.

| # | Mutante | file:line (scratch) | Descrição | Morto? |
| - | ------- | ------------------- | --------- | ------ |
| M1 | janela da média móvel | `backend/app/health/calc.py:88` | `w7 = window(day - timedelta(days=HRV_AVG_DAYS - 1), day)` → `window(day - timedelta(days=HRV_AVG_DAYS), day)` (off-by-one: janela `[d−7, d]` de 8 dias) | ✅ **Killed** — 4 failed / 47 passed: `test_hrv_model_band_pin_and_threshold` (`avg7 == 82.0` virou 81.0 — janela pegou 74 a mais), `test_hrv_model_status_unbalanced_after_suppression` (`avg7 == 20.0` virou 27.5 — janela pegou um 80), `test_hrv_band_slides_day_by_day_with_full_history` (`avg7 == 71.4` virou 71.2 — 7×70+80/8), `test_hrv_status_unbalanced_after_recent_suppression` (`avg7: 27.5 != 20.0` no current) — morto nas duas camadas (puro + integração) |
| M2 | threshold da banda | `backend/app/health/calc.py:91` | `if len(w60) >= HRV_BASELINE_MIN_VALUES:` → `if len(w60) > HRV_BASELINE_MIN_VALUES:` (banda sumiria com exatamente 14 valores) | ✅ **Killed** — 1 failed / 50 passed: `test_hrv_model_band_pin_and_threshold:453` — `assert by_day[2026-09-29]["band_low"] is not None  # 14 valores` → `assert None is not None` (o pino de fronteira 13/14 mata a mutação `>`) |
| M3 | vazamento entre usuários | `backend/app/health/service.py:130` | `.where(Hrv.user_id == DEFAULT_USER_ID, Hrv.date >= start)` → `.where(Hrv.date >= start)` (filtro `user_id` removido da query principal; `max` mantido) | ✅ **Killed** — 1 failed / 50 passed: `test_other_users_rows_never_leak_into_panel:381-384` — `assert by_day[2026-10-12] == {value: None, avg7: None, ...}` falhou com `{'value': 40.0} != {'value': None}` e `{'avg7': 40.0} != {'avg7': None}` (a HRV alheia de 12/10 entrou no modelo do usuário 1) |

**Result**: **3/3 killed — PASS ✅**. Os testes discriminam a semântica exata da janela de 7 dias (off-by-one morto em 4 asserções distintas, puro e integração), a fronteira inclusiva ≥14 do threshold e o isolamento por `user_id` (lição L-005 aplicada preventivamente vira cobertura real: o leak-check pina o dia alheio com dict completo). **0 sobreviventes.**

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ 17 arquivos no diff, todos mapeados a T1–T7 (+ artefatos `.specs` + `STATE.md` AD-010); out-of-scope respeitado: dose-resposta intocado (`_series` segue :250,260; testes `test_dose_response_*` verdes sem edição de comportamento), chip do treino intocado (`WorkoutDetail.tsx:205` segue com status Garmin — spec §Out of Scope), tabela `hrv` e coluna `status` cru persistidas (`models.py` fora do diff; `_seed_hrv` continua semeando status), `_series`/janela das outras séries sem mudança, sem seletor de janela na UI, sem status LOW/POOR, sem alertas, sem coluna status na tabela (design §Decisões.4) |
| No abstractions for single-use code | ✅ `hrv_model` é a única função nova no calc; `_hrv_history`/`_hrv_block` seguem o padrão dos blocks existentes; helpers reusados (`_one` local de 3 linhas, `formatVdot`, `SeriesLegend` local); zero indireção nova |
| No unnecessary flexibility | ✅ nenhuma config/prop nova: réguas são constantes do backend (`calc.py:29-32`), `PAGE_SIZE` local, `HrvChart`/`HrvTable` recebem só `HrvBlock` |
| Surgical changes / só arquivos da task | ✅ `calc.py` +69 linhas (função nova + réguas + docstring); `service.py` +60 (2 funções + import); `router.py` +22 (3 models); `config.py` 1 linha; `HrvChart.tsx` rewrite de 135 sobre o padrão RemChart/PmcChart; `HrvTable.tsx` 93 no estilo PredictionsTable/DecayTable; `HealthPanel.tsx` +3 (import, comentário, mount); `api.ts` tipos espelho; testes co-localizados por camada |
| Didn't "improve" unrelated code | ✅ dose-response, sono/RHR/estresse/PMC/lifestyle, sync (além do default), páginas e `format.ts` fora do diff; o suite inteiro pré-feature segue verde sem edição (268 base preservados — 0 testes removidos: diff de `backend/tests/` não tem nenhum `-def test_`) |
| Matches patterns | ✅ AD-003 (matemática em função pura pinável — `hrv_model` sem DB/IO, pins literais à mão); AD-009 (payload espelha render: `points` dias corridos servem gráfico e tabela, `current` = o que o card mostra; router↔api.ts espelho 1:1); AD-008 (Recharts ComposedChart padrão PmcChart); AD-001 (filtro `user_id` em max e select); réguas no padrão `SLEEP_FLOOR_S`/`REM_BAND`; pins literais nunca compartilhados com a implementação (L-001/L-002 citadas nos headers); PT-BR na UI/ASCII na API; `uv run pytest` no Postgres do compose (README §Testes); Next 16: nenhum API novo do framework (`frontend/AGENTS.md`) — client components no padrão existente |
| Spec-anchored outcome check | ✅ asserções de VALOR/ESTADO: bandas pinadas com 6 decimais (`round(..., 6) == 67.291796`), dicts completos de `current` (status/banda null inclusive), `is None`/`is not None` de threshold por dia, `all(...)` sobre a janela, `len(points) == days` — não só chamadas; aritmética rederivada à mão pelo Verificador (√80, √840, √(5/3), médias truncadas) |
| Tests non-shallow (spot-check) | ✅ HRV-04: banda deslizando com janela completa em 119 dias + lookback da média 7d usando noites FORA da janela de exibição (`avg7 == 71.4` — sem lookback seria 80.0 — `test_health_api.py:424`); HRV-15: contagem persistida + datas extremas + `days=7` mantendo banda 60d; fronteira 13/14 no mesmo teste; leak-check com dict completo do dia alheio |
| Per-layer Coverage Expectation (tasks.md:22-29) | ✅ calc: unit 1:1 (8 testes cobrindo HRV-01..06/08 + truncamento + borda inclusiva + janela de exibição); service: integration com db fixture (janela de datas + lookback, filtro user_id, arredondamento só no payload); router: contrato pinado via TestClient (points/current/status null); sync: backfill ≥119 em base sem sync_state + pins de janela adaptados; frontend: none + build/lint verdes (sem runner — matriz) |
| Every test maps to a spec requirement | ✅ cada teste novo cita HRV/done-when/edge no docstring (ex.: `test_health_calc.py:389-391, 398-401, 440-444, 462-463, 478-480, 497-500, 522-524`; `test_health_api.py:407-412, 434-436, 458-460`; `test_garmin_service.py:541-545`); nenhum teste órfão |
| Senior engineer approve? | ✅ sim, com 2 notas cosméticas não-bloqueantes: (1) docstring de `test_sync_config.py:35` ficou desatualizada ("60d de saúde" — o pin à frente afirma 120); (2) typo "vazaSEM" em `test_health_api.py:342`. Ambas comentário/copy, zero efeito comportamental — registradas aqui, sem correção (escopo do Verifier é read-only) |

---

## Gate Check

- **Gate commands** (tasks.md:33-39): Postgres do compose no ar → `cd backend; uv run pytest -q` · `cd frontend; npm run build; npm run lint`
- **Backend**: **280 passed, 0 failed, 0 skipped** (217.98s, exit 0; 1 warning pré-existente `StarletteDeprecationWarning` do TestClient, não relacionado à feature)
- **Frontend**: `npm run build` exit 0 (Next 16.4.0/Turbopack; TypeScript ok; 9 rotas geradas) · `npm run lint` exit 0 (zero reportes)
- **Test count before feature**: 268 (baseline pós panel-clarity, tasks.md:20)
- **Test count after feature**: 280
- **Delta**: **+12 novos, 0 removidos** — `test_health_calc.py` +8 (`test_hrv_model_constants_match_spec`, `test_hrv_model_rolling_avg_fills_capture_gaps`, `test_hrv_model_day_with_empty_window_has_no_avg`, `test_hrv_model_band_pin_and_threshold`, `test_hrv_model_status_balanced_on_inclusive_edge`, `test_hrv_model_status_unbalanced_after_suppression`, `test_hrv_model_without_band_status_is_none`, `test_hrv_model_window_is_calendar_days_ending_at_latest_data`) · `test_health_api.py` +3 (`test_hrv_band_slides_day_by_day_with_full_history`, `test_hrv_status_unbalanced_after_recent_suppression`, `test_hrv_short_window_keeps_sixty_day_band_lookback`) · `test_garmin_service.py` +1 (`test_health_backfill_covers_hrv_band_lookback`); pins existentes adaptados, não removidos (`test_garmin_service.py` 61→121, `test_sync_api.py:73` 259→499, `test_sync_config.py:38` 60→120, happy-path/leak em `test_health_api.py`)
- **Skipped**: nenhum · **Failures**: nenhuma
- **Árvore real**: `git status --porcelain` vazio antes e depois de TODO o sensor; `git worktree list` = só `main`

---

## Success Criteria (spec.md:179-184)

- [x] **Exemplo real (69/76/70–98): card BALANCED com média 7d e banda do dia visíveis; linha dentro da banda, que desliza dia a dia** — mecânica pinada nos dois lados: status do card (`test_health_api.py:427-430` BALANCED com banda completa; `:451-454` UNBALANCED 38,3/81,7), banda deslizando (`:419-426` 69,2/71,1 → 80,0/80,0), card com números (`HrvChart.tsx:139-152`); confirmação no exemplo real do usuário é UAT/ops (depende do re-sync 120d — Handoff `STATE.md`)
- [x] **Após re-sync com backfill 120, todos os dias da janela têm banda com janela completa** — pinado com 119 dias semeados: `all(p["band_low"] is not None for p in hrv["points"])` (`test_health_api.py:423`); backfill ≥119 persistidos (`test_garmin_service.py:540-555`); ops-note do re-sync documentada no Handoff (`STATE.md`)
- [x] **Status deriva sempre da regra visível (média 7d vs faixa local) — zero dependência do `status` Garmin na UI do Saúde** — contrato sem status Garmin (`router.py:68-96`, pins dict-completos), UI usa só `current.status` (`HrvChart.tsx:140`), tabela sem status (`HrvTable.tsx`); chip do treino out of scope (spec.md:22)
- [~] **Tabela pagina pelos 60 dias no mobile 390px sem quebra** — per matriz (sem runner): inspeção sem larguras fixas (`HrvTable.tsx` `w-full text-xs`, sem `min-w`, botões flex); confirmação visual no UAT real 390px (após o Verifier, per Handoff)
- [x] **Suite existente (268) + novos passando no Postgres do compose** — 280 passed / 0 failed / 0 skipped

---

## Requirement Traceability

14/14 ACs implementados verificados com evidência `file:line`; a tabela de traceability do `spec.md:155-169` (T7) está correta: HRV-01..HRV-13 + HRV-15 ✅ Verified, HRV-14 Pending (P3 deferred por design — spec.md:25,169). Este Verificador não precisou alterá-la.

| Requirement | Status |
| ----------- | ------ |
| HRV-01..HRV-13, HRV-15 | ✅ Verified (14/14, evidência acima) |
| HRV-14 | Pending (P3 deferred — não é gap) |

---

## Gaps Ranqueados

Nenhum. 14/14 ACs implementados verificados (HRV-01..13 + HRV-15); HRV-14 P3 deferred por design; 4/4 edge cases; 3/3 mutantes mortos (0 sobreviventes); gates verdes (268 → 280, +12, 0 removidos); build+lint exit 0. Duas notas cosméticas não-gaps registradas em Code Quality (docstring de `test_sync_config.py:35`, typo em `test_health_api.py:342`).

---

## Summary

**Overall**: ✅ PASS — Ready

**Spec-anchored check**: 14/14 ACs implementados com `file:line` + asserção/inspeção conferida ao desfecho exato da spec (contrato por pytest com pins literais — banda 74 ± 0,75√80 = 67,291796/80,708204, supressão 38,262935/81,737065, banda deslizando 69,2/71,1 → 80,0/80,0, fronteira 13/14 valores, borda inclusiva BALANCED, janela de exibição `days` dias corridos terminando em `L`; UI por inspeção comportamental — Scatter por noite, `connectNulls={false}`, Areas empilhadas atrás da série, `current.status ?? "coletando linha de base…"`, âmbar fora da banda, 7/página com `atual/total` só >7); 0 spec-precision gaps; 4/4 edge cases
**Sensor**: 3/3 mutações mortas (M1 off-by-one da janela 7d — 4 asserções nas duas camadas; M2 threshold `>=` → `>` — fronteira 14; M3 vazamento `user_id` — leak-check pina o dia alheio) — worktree descartável, porcelain idêntico antes/depois
**Gate**: backend 280 passed / 0 failed / 0 skipped (268 → 280, +12 novos, 0 removidos, 217.98s) · frontend build+lint exit 0

**What works**: o modelo científico atravessou ponta a ponta — `hrv_model` puro e pinável (AD-003) calcula média 7d sobre os valores disponíveis e banda móvel por dia (60d ± 0,75 DP amostral, threshold 14); o service traz exibição + lookback de 59d com filtro `user_id` e arredonda só no payload (status decide sem arredondar); o contrato novo (points dias corridos + current com status local, zero status Garmin) é espelhado no `api.ts` e renderizado pelo `HrvChart` (banda atrás da série, linha 7d, noites discretas, âmbar fora da banda, card com os números que decidem) e pela `HrvTable` (7/página, `atual/total`); backfill 120d persiste 121 ≥ 119 dias; docs e memória honestos (PLANO §4.5, AD-010, ops-note do re-sync).

**Issues found**: nenhum bloqueante. Notas não-gaps: (1) duas cosméticas em testes (docstring `test_sync_config.py:35` desatualizada, typo `test_health_api.py:342`); (2) UAT real 390px e o exemplo-real do usuário seguem após este Verifier (per Handoff — dependem do re-sync 120d para a banda completa nos 60 dias).

**Next steps**: UAT no celular 390px + re-sync completo (limpar `sync_state` dos tipos de saúde) para colher os 60 dias extras de backfill. Lições: nenhum sinal (PASS limpo, 0 mutantes sobreviventes, 0 gaps, 0 ACs falhos) — nada a registrar.

---

## Addendum — Interactive UAT (pós-Verifier, 2026-10-17)

UAT real no celular 390px, dados do usuário, stack local recriada para o teste (`docker compose up -d --build backend frontend` — o código é queimado na imagem, containers antigos serviam a versão anterior; após o rebuild o modelo novo renderizou). Dados no momento do teste: **última noite 69,0 · média 7d 76,5 · banda 66,9–85,2 → BALANCED** — o exemplo canônico da spec (69/76/~70–98) confirmado ao vivo.

| # | Test | Result | Details |
| - | ---- | ------ | ------- |
| 1 | Bloco HRV completo com dados reais (banda por dia, linha 7d, noites discretas, card com status local + banda, tabela 7/página) | ✅ Pass | Usuário: "deu certo! sucesso demais!" |
| 2 | Fix de UAT — hierarquia do card: média 7d no destaque (ela decide o status), última noite na linha de contexto | ✅ Pass (pós-fix) | `fb3dc9b` (`fix(ui): make 7d average the hrv card headline`); decisão registrada em `context.md` §"Hierarquia do card"; usuário: "aprovado!" |

Notas: (1) UAT realizado **sem** o re-sync 120d — a banda cobriu a porção recente da janela e o threshold por dia comunicou a ausência no início (comportamento da spec, HRV-05); o re-sync completo (`DELETE FROM sync_state WHERE data_type IN ('sleep','hrv','rhr','stress','body_battery')` + "Puxar do Garmin") segue como ops opcional para banda de janela cheia nos 60 dias; (2) Success Criterion 4 (tabela 7/página sem quebra em 390px) confirmado pela aprovação; (3) as 2 notas cosméticas do Verifier foram corrigidas em `f973808`.

**UAT**: ✅ **Aprovado pelo usuário (17/10/2026). Feature encerrada.**
