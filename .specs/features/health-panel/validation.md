# Painel Saúde — Validation

**Date**: 2026-10-16 (validação) · 2026-10-16 (re-verificação, iteração 2 de 3)
**Spec**: `.specs/features/health-panel/spec.md`
**Diff range**: `cf7431c..HEAD` (18 commits; código em `3db133d..c3df7e5`; 26 arquivos, +3821/−2)
**Verifier**: sub-agente independente (author ≠ verifier) — árvore real intacta (`git status --porcelain` idêntico ao baseline antes e depois de cada sensor: só os artefatos sancionados — validation.md e lessons store); mutações só em worktree descartável fora do repo

---

## Veredito

**PASS ✅ (re-verificação, iteração 2 de 3)** — 30/30 ACs com evidência `file:line` e resultado conforme a spec (0 spec-precision gaps); 10/10 edge cases verificados; gates verdes (backend **262 passed** = 228 base + 34 novos, 0 skipped; frontend build+lint exit 0 da iteração 1 seguem válidos — a fix não tocou frontend). Sensor final: **3/3 mutações mortas**.

Histórico do ciclo fix→re-verify: a iteração 1 achou **1 mutante sobrevivente** (M3 — remoção do filtro `user_id` em `service.py:56` indetectável pela suite; veredito FAIL com 1 gap Minor) e registrou a lição L-005. A **Fix 1** (commit `c3df7e5` — teste `test_other_users_rows_never_leak_into_panel`) foi aplicada pelo orquestrador e verificada aqui: mutante re-injetado de forma idêntica no scratch **morre** na primeira asserção do teste novo (noite alheia de 4h vazando nos pontos), e a suite passou a 262. Gap fechado; nada mais mudou (a fix toca só `backend/tests/test_health_api.py` + 1 linha de nota no context.md).

---

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 env `APP_TIMEZONE` | ✅ Done | `config.py:25-26` (`app_timezone: str = "America/Sao_Paulo"`); `.env.example:35-36` comentada; `docker-compose.yml` intocado (não aparece no diff — done-when satisfeito) |
| T2 `health/calc.py` | ✅ Done | Réguas `calc.py:19-22` (25200/21–31/21600/24300); `dose_response` :51-92, `weekday_pattern` :95-109, `regularity` :120-136, `local_minute` :28-35, `strength_weeks` :139-190, `below_floor` :112-117; 19 testes (`test_health_calc.py:48-374`) |
| T3 `health/service.py` | ✅ Done | `get_health` :169-199 (4 séries + activities, blocos null, cruzamento por data, fuso injetado); testes service-level `test_health_api.py:141-334` |
| T4 router + mount | ✅ Done | `router.py:150-159` (`GET /summary`, `Query(60, ge=7, le=365)` :152, fallback de tz :137-147); `main.py:20,51` (`include_router`; `/api/health` de infra intocado — `main.py:54`); testes HTTP `test_health_api.py:342-456` |
| T5 `api.ts` | ✅ Done | Tipos `api.ts:312-391` (null atravessa o contrato); `getHealthSummary` :394-400 (`cache: "no-store"` :396, `parseError` :398) |
| T6 `format.ts` | ✅ Done | `formatHours` :70-72 (vírgula, 1 casa), `formatClock` :76-81 (1336 → "22:16"), `formatWeekday` :87-88 (seg..dom) |
| T7 `SleepChart` | ✅ Done | Barras h + `ReferenceLine` do piso :133-138 (`extendDomain`), resumo pct :104-109, tooltip score/REM :62-69 |
| T8 `SleepStagesChart` | ✅ Done | 3 `Bar` `stackId="fases"` :121-123, domínio 0–100 :111-117, despertares no tooltip :67-69 (omitido quando null), sem normalização |
| T9 `RemChart` | ✅ Done | `ReferenceArea` da banda do payload :110-115, domínio Y fixo 0–40 :102-108, tooltip :48-54 |
| T10 `WeekdayPattern` | ✅ Done | Cards deitar/acordar via `formatClock` :73-83, barras por weekday :87-107, `regularity` null → "—" :75-82 |
| T11 `HrvChart` | ✅ Done | Valor atual + badge textual do `current.status` cru :66-75, `Line` :97-104, tooltip valor+status :52-57 |
| T12 `RhrChart` | ✅ Done | `ReferenceLine` no `baseline` rotulada :80-90, `Line` :91-98, tooltip :47-51 |
| T13 `StressChart` | ✅ Done | Card média da janela :57-60 ("—" quando null :59), linha condicional :62-93 |
| T14 `DoseResponse` | ✅ Done | Cards lado a lado :47-50, nota neutra :51-53, média null → "—" :16-18 |
| T15 `Lifestyle` | ✅ Done | Força streak/janela/corrente :26-38, yoga :39-45, zeros como estão |
| T16 `HealthPanel` + rota | ✅ Done | Estados loading :67-69 / error inline :71-77 / painel vazio :83-90; seções condicionais por bloco :92-153; `app/saude/page.tsx:10` renderiza `<HealthPanel />` |

---

## Spec-Anchored Acceptance Criteria

Pins **re-derivados de forma independente** pelo Verifier (cálculo manual a partir das fixtures, não leitura dos testes): dose short (68+70+69,5+70+70)/5 = **69,5** / score 302/5 = **60,2**; adequate (81+81,5+81+81,5+81+81,5+82+81+81,7+81)/10 = **81,3** / score 802/10 = **80,2**; below_floor 2/3×100 = **66,7**; regularity das NIGHTS — deitar GMT 01:16/01:27/01:16 → local 1336/1347/1336, média circular **1339,7**; acordar 302/272/302 → **292,0**; weekday 2026-10-13/14/15 = ter/qua/qui (1/2/3); lifestyle — janela 17/08..16/10 = 9 semanas ISO, força 14/09+21/09+28/09+05/10 batidas → streak **4**, weeks_hit **4**, corrente (12/10) **1**, yoga 3 na janela → 3/9 = **0,3**; RHR (45+44+43)/3 = **44,0**; estresse (25+23)/2 = **24,0**. Todos conferem com as asserções.

**Convenção da matriz**: frontend sem infra de testes (matriz em tasks.md:25 — build + lint + UAT). Para ACs de UI (HLT-13..30), a evidência é implementação (`file:line`) + gates; o UAT real é do orquestrador.

| Criterion | Spec-defined outcome | `file:line` + asserção | Result |
| --------- | -------------------- | ----------------------- | ------ |
| HLT-01: payload exclusivamente do banco próprio, zero Garmin | nenhum uso do gateway no domínio | `test_health_api.py:324-334` — varre todos os `*.py` de `health/` afirmando `"from app.garmin"` e `"import app.garmin"` ausentes; `service.py:18-35` importa só db/calc | ✅ PASS |
| HLT-02: `days` em [7,365] → 200 com os 6 blocos na janela (default 60) | 200; blocos `sleep/hrv/rhr/stress/dose_response/lifestyle`; janela corta | `test_health_api.py:350-382` — 200 com os 6 blocos pinados e `days == 60` sem param (:354); bordas 7/365 → 200 (:392-398); janela corta as mais antigas — 8 noites, days=7 → 7 recentes ASC (:420-434); lifestyle limitado à janela — yoga 3/4 semeadas (:130-133 → :207-211 `sessions == 3`), streak `weeks_hit` limitado (:305-321) | ✅ PASS |
| HLT-03: `days` fora de [7,365] → 422 sem query | 422 | `test_health_api.py:385-389` — days 6/366/0/−1 → `status_code == 422`; `router.py:152` (`Query(ge=7, le=365)` precede o handler — garantia estrutural FastAPI, mesma nota aceita no POT-11) | ✅ PASS |
| HLT-04: bloco `sleep` completo | `points[{date,duration_s,score,rem_pct,deep_pct,light_pct,awakenings,bed_local,wake_local}]` ASC, `floor_s` 25200, `below_floor{nights,pct}`, `rem_band` [21,31], `weekday_pattern` 7 entradas, `regularity{avg_bed_min,avg_wake_min}` | `test_health_api.py:150-177` — floor_s `== 25200` (:152), rem_band `== [21.0, 31.0]` (:153), below_floor `== {"nights": 2, "pct": 66.7}` (:154), regularity (:156), 7 entradas weekday (:157-160), 3 pontos com todos os campos (:161-177); ASC pinado em :214-225 (2 noites → 14/10, 15/10); réguas também em `test_health_calc.py:48-53` | ✅ PASS |
| HLT-05: `bed_time`/`wake_time` convertidos para `APP_TIMEZONE`; GMT nunca exposto como local | 01:16 GMT → 22:16 local; fallback em fuso inválido | `test_health_calc.py:252-256` — `local_minute(datetime(2026,10,16,1,16), São Paulo) == 1336`; :259-264 — 02:59 GMT → 1439 e UTC → 76 (sem hardcode); `test_health_api.py:437-456` — APP_TIMEZONE "Mars/Phobos" → 200 + warning + `bed_local == "22:16"` (nunca "01:16"); conversão no service (`service.py:79-80`, `_hhmm` :66-69) | ✅ PASS |
| HLT-06: bloco `hrv` com `points[{date,value,status}]` ASC + `current` | ASC; current = último dia com dado | `test_health_api.py:185-192` — pontos 13→14→15 ASC com status, `current == {"date": 15/10, "value": 75.0, "status": "BALANCED"}` (última linha); via HTTP :373-375 | ✅ PASS |
| HLT-07: bloco `rhr` com `points[{date,value}]` ASC + `baseline` (média, 1 casa) | baseline 1 casa | `test_health_api.py:193-200` — 3 pontos ASC, `baseline == 44.0` (re-derivado (45+44+43)/3); via HTTP :376 | ✅ PASS |
| HLT-08: bloco `stress` com `points[{date,avg}]` ASC + `avg_window` (1 casa) | média 1 casa; dia sem avg fora | `test_health_api.py:202-205` — dia 14/10 (avg NULL) fora da série, `avg_window == 24.0`; série só com NULLs → bloco null :272-278 | ✅ PASS |
| HLT-09: `dose_response` — buckets `short` (<21600) e `adequate` (≥24300) com `{nights,avg_hrv,avg_score}` cruzados na mesma data + `neutral_nights`; bucket vazio → médias NULL | <6h vs ≥6h45; neutra 6h–6h45; NULL sem noites | `test_health_calc.py:61-88` — pins short **{5, 69.5, 60.2}** / adequate **{10, 81.3, 80.2}** (re-derivados); :91-105 — 6h exata neutra, 6h45 exata adequate, 21599 short; :108-122 — noite sem HRV fora, neutra só na faixa; :125-138 — tudo neutro/[] → `{0, None, None}`; :141-153 — score NULL conta noite, não entra na média; cruzamento por mesma data: `test_health_api.py:289-302` — HRV só na véspera/dia seguinte → buckets 0; service cruza via `hrv_by_date` (`service.py:186-187`) | ✅ PASS |
| HLT-10: `lifestyle` — `strength{streak_weeks,weeks_hit,weeks_total,current_week_sessions}` + `yoga{sessions,per_week_avg}` das activities por typeKey em leitura | typeKey exato; nada persistido | `test_health_api.py:207-211` — `{streak 4, hit 4/9, corrente 1}` + yoga `{3, 0.3}` (re-derivado); :305-321 — streak 5 excede janela de 19d com weeks_hit 2/3; `service.py:39-40` (`strength_training`/`yoga`), :152-159 (filtro por typeKey em Python, AD-001) | ✅ PASS |
| HLT-11: domínio vazio → bloco null; dose_response mantém buckets nights=0/médias null | estado vazio, não erro | `test_health_api.py:228-246` — sleep/hrv/rhr/stress `is None`, dose com zeros, lifestyle com zeros; via HTTP :401-417 | ✅ PASS |
| HLT-12: streak = semanas ISO completas consecutivas (≥2) terminando na última completa (pode exceder janela); weeks_hit/total na janela; corrente separada (parcial não quebra) | sem julgar a corrente; janela separada | `test_health_calc.py:290-313` — streak 4 com corrente 1 separada; :316-334 — última completa <2 → streak 0 (não herda) com `current_week_sessions == 0`; :337-350 — streak 5 > janela 3; :353-374 — virada de ano ISO (30/12/25 e 02/01/26 = mesma semana 2026-W01) streak 3; loop da streak começa em `week_of(today) − 7d` (`calc.py:164-167`, corrente nunca julgada) | ✅ PASS |
| HLT-13: UI — gráfico de duração por noite com linha do piso visível + tooltip score/REM% | barra por noite; `floor_s` como referência | `SleepChart.tsx:139` (`Bar` horas), :133-138 (`ReferenceLine y=floorHours` tracejada, `extendDomain` — visível mesmo com todas as noites abaixo), :62-69 (tooltip `Score {score} · REM {rem}`) | ✅ PASS (per matriz) |
| HLT-14: UI — resumo "X% das noites abaixo do piso" | `below_floor.pct` exibido | `SleepChart.tsx:104-109` — `{pct}% das noites abaixo do piso` (1 casa, vírgula) | ✅ PASS (per matriz) |
| HLT-15: UI — REM% por noite com banda ideal 21–31% visível | banda do payload no gráfico | `RemChart.tsx:110-115` — `ReferenceArea y1/y2` de `rem_band` do payload (UI não inventa régua), domínio Y 0–40 fixo :102-108, `Line rem_pct` :116-123, legenda "banda ideal (21,0–31,0%)" :58-80 | ✅ PASS (per matriz) |
| HLT-16: UI — regularidade (deitar/acordar médios locais) + padrão por dia da semana | minutos → HH:MM; média por weekday | `WeekdayPattern.tsx:73-83` — cards "Deitar médio"/"Acordar médio" via `formatClock` (minutos locais do backend); :87-107 — barras das 7 entradas com `formatWeekday` (seg..dom), domínio começando em 0; regularity null → "—" :75-82 | ✅ PASS (per matriz) |
| HLT-17: UI — linha de HRV + status do último dia como destaque textual | `current.status` (BALANCED/UNBALANCED/LOW) textual | `HrvChart.tsx:66-75` — valor atual em destaque + badge com o status cru (sem tradução), :97-104 `Line value`; tooltip com valor+status :52-57 | ✅ PASS (per matriz) |
| HLT-18: UI — linha de RHR com linha de referência do baseline visível | `baseline` visível | `RhrChart.tsx:80-90` — `ReferenceLine y=baseline` rotulada `baseline {valor}`; `Line value` :91-98; tooltip :47-51 | ✅ PASS (per matriz) |
| HLT-19: UI — `hrv`/`rhr` null → estado vazio orientando o primeiro sync | sem erro, sem tela branca | `HealthPanel.tsx:119-137` — `BlockEmpty` "Sem dados de HRV noturna ainda — eles chegam no primeiro sync do Garmin" (HRV) e equivalente para RHR | ✅ PASS (per matriz) |
| HLT-20: UI — dois buckets lado a lado com `{nights, avg_hrv, avg_score}` | short vs adequate juntos | `DoseResponse.tsx:47-50` — `grid-cols-2` com "Noites <6h" e "Noites ≥6h45", cada card com noites/HRV média/score médio :25-42 | ✅ PASS (per matriz) |
| HLT-21: UI — nota da faixa neutra | `neutral_nights` fora da comparação | `DoseResponse.tsx:51-53` — "{N noites} fora da comparação (6h–6h45)" com plural PT-BR :21-23 | ✅ PASS (per matriz) |
| HLT-22: UI — média de bucket null → "—" | nenhum número inventado | `DoseResponse.tsx:16-18` — `avgOrDash` ("—" quando null) aplicado a `avg_hrv` e `avg_score` :33,37 | ✅ PASS (per matriz) |
| HLT-23: UI — força: streak em semanas, weeks_hit/weeks_total, sessões da corrente em andamento | 3 números da força | `Lifestyle.tsx:26-38` — "{N semanas} de streak", "{hit}/{total} semanas na janela", "Semana corrente (em andamento): {N sessões}" | ✅ PASS (per matriz) |
| HLT-24: UI — yoga: sessões na janela + média por semana | sessões + per_week_avg | `Lifestyle.tsx:39-45` — "{N sessões}" + "{média}/semana" (1 casa, vírgula :16-19) | ✅ PASS (per matriz) |
| HLT-25: UI — estresse: linha da média diária + média da janela no bloco de equilíbrio de vida | dentro do bloco lifestyle | `StressChart.tsx:56-93` (card média :57-60, linha :82-89) renderizado na seção "Equilíbrio de vida" — `HealthPanel.tsx:146-152` | ✅ PASS (per matriz) |
| HLT-26: UI — `stress` null → omitir a linha, média como "—" | bloco não quebra | `StressChart.tsx:59` — média "—" quando null; :62 — linha condicional (`stress !== null &&`), card permanece | ✅ PASS (per matriz) |
| HLT-27: UI — falha da API → mensagem de erro na página sem quebrar navegação | erro inline | `HealthPanel.tsx:71-77` — "Não foi possível carregar a saúde: {message}" inline; a nav vive fora do `<main>` (`app/saude/page.tsx:10-12`) | ✅ PASS (per matriz) |
| HLT-28: UI — painel inteiro vazio → estado vazio orientando o primeiro sync | apontar o sync | `HealthPanel.tsx:83-90` — sleep/hrv/rhr/stress todos null → "Nada por aqui ainda. Use o botão "Puxar do Garmin" no topo para sincronizar seus dados." | ✅ PASS (per matriz) |
| HLT-29: UI — 390px legível, sem scroll horizontal | padrão dos painéis anteriores | Estrutura sem larguras fixas: todos os gráficos `ResponsiveContainer width="100%"` (SleepChart.tsx:112, SleepStagesChart.tsx:100, RemChart.tsx:90, WeekdayPattern.tsx:86, HrvChart.tsx:78, RhrChart.tsx:61, StressChart.tsx:64); grids `grid-cols-2 gap-2` (DoseResponse.tsx:47, Lifestyle.tsx:24, WeekdayPattern.tsx:73); page `max-w-3xl px-4` (`app/saude/page.tsx:11`). Nenhum `min-w`/largura fixa no diff. Confirmação visual: UAT do orquestrador | ✅ PASS (per matriz; visual no UAT) |
| HLT-30: UI — fases empilhadas por noite (leve/profundo/REM, fechando ~100%) + despertares no tooltip | stack das 3 fases; despertares visíveis | `SleepStagesChart.tsx:121-123` — 3 `Bar` com `stackId="fases"` (light base, deep, rem), domínio 0–100 :111-117; tooltip :62-69 com as 3 fases + "{N} despertar(es)" (:46-48), omitido quando null :67 | ✅ PASS (per matriz) |

**Status**: ✅ 30/30 ACs com evidência `file:line` + asserção conferida ao resultado definido pela spec (pins re-derivados de forma independente). 0 spec-precision gaps — todos os ACs definem outcome observável (valor, código, estado, elemento de UI).

---

## Edge Cases (spec.md:169-180)

- [x] **Fases fora de 100% (±0,5) → exibidas como vieram, sem normalização**: `SleepStagesChart.tsx:119-123` — pcts entram como gravados (nenhuma aritmética sobre eles); comentário explícito "sem normalização"
- [x] **Noite sem HRV na mesma data → fora do dose-resposta; neutra só se 6h–6h45**: `test_health_calc.py:108-122` (curta e adequada sem HRV saem; neutra sem HRV conta :122) + `test_health_api.py:289-302` (HRV de datas vizinhas não vira par)
- [x] **Todas as noites na faixa neutra → buckets nights=0, médias null, nota com total**: `test_health_calc.py:125-138` (`neutral_nights == 2` com buckets zerados); UI: "—" via `DoseResponse.tsx:16-18`
- [x] **bed/wake NULL → noite nos gráficos, fora de regularity**: `test_health_api.py:249-269` (ponto presente com `bed_local is None`, regularity só das noites com horário; nenhuma elegível → `regularity is None`, bloco de pé) + `test_health_calc.py:233-244`
- [x] **Semana corrente com 0 sessões → `current_week_sessions=0`, streak não quebrada por ela**: `test_health_calc.py:316-334` (`current_week_sessions == 0`); streak nunca julga a corrente (`calc.py:164-167` — começa em `week_of(today) − 7d`); corrente com 1 sessão também não quebra (:290-313)
- [x] **Última semana completa <2 sessões → streak 0 (não herda) + weeks_hit real**: `test_health_calc.py:316-334` (`streak_weeks == 0` com histórico batido antes)
- [x] **`APP_TIMEZONE` inválida → default America/Sao_Paulo + warning, sem crash**: `test_health_api.py:437-456` (200 + `"Mars/Phobos" in caplog.text` + `bed_local == "22:16"`); `router.py:137-147`
- [x] **Atividade força/yoga com `duration_s` nula → ainda conta**: impossível no schema (`models.py:56` — `duration_s` NOT NULL) e o lifestyle conta por presença (só `start_time` + `activity_type`, `service.py:152-157` — duração nunca consultada). Seguro por construção
- [x] **Duas noites na mesma data — n/a**: unique constraint `(user_id, date)` (premissa da spec; spec.md:179 marca n/a)
- [x] **`days` > histórico → devolve tudo que existe**: `_series` com `limit(days)` devolve as linhas disponíveis (`service.py:49-63`); happy path days=60 com 3 noites → as 3 (`test_health_api.py:141-177`); borda 365 → 200 (:392-398)

---

## Discrimination Sensor

**Tier**: lightweight (3 mutações comportamentais nos pontos de maior risco do domínio novo — 1 por camada: calc-bucket, calc-fuso, service-query).
**Scratch**: `git worktree add C:\Users\leona\projects\ritmo-verifier-scratch HEAD` — iteração 1 detached em `14af2c5`, iteração 2 em `c3df7e5` (com a Fix 1), venv próprio via `uv run`. M1 rodou a **suite completa** como controle (261 coletados — cópia fiel). M2/M3 nos módulos mutados: os módulos de `health/` só são exercitados pelos testes de saúde, logo o subconjunto equivale à suite total para o kill. Nenhuma mutação tocou a árvore real — `git status --porcelain` idêntico ao baseline antes e depois de cada iteração; worktree removido com `--force`; `git worktree list` mostra só `main`.

| # | Mutante | file:line (scratch) | Descrição | Morto? |
| - | ------- | ------------------- | --------- | ------ |
| M1 | limiar do bucket short | `health/calc.py:72` | `if duration < SHORT_MAX_S:` → `<=` (noite de exatamente 6h migra de neutra para short) | ✅ Killed (it. 1) — suite completa: 1 failed / 260 passed; `test_dose_response_band_boundaries` (`test_health_calc.py:103`) falha com `{'nights': 2, 'avg_hrv': 55.0, 'avg_score': 62.5}` |
| M2 | conversão de fuso | `health/calc.py:34` | `naive_utc.replace(tzinfo=utc).astimezone(tz)` → `naive_utc` (GMT tratado como local: 01:16 exibido como 01:16) | ✅ Killed (it. 1) — 6 failed / 27 passed: `test_local_minute_gmt_to_local_pin` (76 ≠ 1336), `test_local_minute_crosses_midnight_and_other_zones`, `test_get_health_full_payload_from_seeds` (regularity 79,7 ≠ 1339,7), `test_regularity_null_without_bed_wake_times`, `test_api_happy_path_200_full_payload`, `test_api_invalid_app_timezone_falls_back_with_warning` (`'01:16' != '22:16'`) |
| M3 | filtro de usuário | `health/service.py:56` | `.where(model.user_id == DEFAULT_USER_ID)` removido da query `_series` | It. 1: ❌ Survived (33/33 verdes — a suite nunca semeava um segundo usuário) → **Fix 1** (`c3df7e5`) → ✅ **Killed (it. 2)**: 1 failed / 14 passed — `test_other_users_rows_never_leak_into_panel` (`test_health_api.py:349`) falha na primeira asserção: a noite alheia de 12/10 (4h, HRV 40) vaza para os pontos do usuário 1 |

**Result**: **3/3 killed** — PASS ✅. Os testes discriminam os buckets do dose-resposta (inclusive o boundary de 6h), a conversão de fuso nas duas camadas e, após a Fix 1, o isolamento de usuário em todos os blocos (o teste novo também mataria a remoção do filtro da query de activities — as 3 forças + yoga alheias mudariam lifestyle).

**Quirks reais expostas pela fix, ambas documentadas** (não são gaps): (1) `init_db` insere o usuário default com `id` explícito sem avançar a sequência do Postgres — pendência Fase 2.5 anotada no `context.md`; (2) flush explícito necessário no seed porque, sem `relationship()` entre mappers, o SQLAlchemy não ordena users antes das FKs (comentários do próprio teste, `test_health_api.py:311-316`).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ 26 arquivos, todos mapeados a T1–T16 (+artefatos .specs da feature); out-of-scope respeitado (sem passos/NEAT, sem body battery, sem seletor de janela na UI — fixa 60, sem alertas, sem input manual) |
| No abstractions for single-use code | ✅ helpers pequenos e todos usados (`_series`, `_hhmm`, `_night`, blocos por série); sem parâmetros de flexibilidade além do `days` da spec |
| Surgical changes / só arquivos da task | ✅ `main.py` +2 linhas (import + include_router); `config.py` +4; `api.ts`/`format.ts` só extensão; `page.tsx` swap do placeholder; `docker-compose.yml` intocado (done-when T1) |
| Didn't "improve" unrelated code | ✅ nenhum arquivo fora da superfície da feature no diff |
| Matches patterns | ✅ espelho do `potential/` (router/service/calc, seeds ORM, TestClient), padrão `PmcChart` nos componentes, PT-BR na exibição/ASCII na API, docstrings PT-BR |
| Spec-anchored outcome check | ✅ asserções de VALOR/ESTADO em todos os campos de payload (dicts completos, não só chamadas); pins literais re-derivados de forma independente (69,5/81,3/66,7/1339,7/44,0/24,0/0,3) |
| Tests non-shallow (spot-check) | ✅ dose-resposta: fixture com 15 noites pinando buckets completos + boundaries + ausência de HRV; `dose_response` é coverage 1:1 com HLT-09 |
| Per-layer Coverage Expectation | ✅ domínio 1:1 com ACs (calc: HLT-04/09/10/11/12); rotas happy+edge+error (200 default, bordas 7/365, 422 em 6/366/0/−1, blocos null, fallback de tz, corte de janela); integração no Postgres real do compose |
| Every test maps to a spec requirement | ✅ cada um dos 33 testes cita HLT-NN/T-done-when/edge no docstring; nenhum teste órfão |
| Documented guidelines followed | ✅ README §Testes (`uv run pytest` no Postgres do compose, suite no host); `frontend/AGENTS.md` (Next 16 — build exit 0); L-001 aplicada (literais, nunca constantes compartilhadas — cabeçalhos dos testes citam) |

---

## Gate Check

- **Gate commands**: `cd backend; uv run pytest` · `cd frontend; npm run build; npm run lint`
- **Backend (it. 2, pós-Fix 1)**: **262 passed, 0 failed, 0 skipped** (136.07s, exit 0; 1 warning pré-existente `StarletteDeprecationWarning` do TestClient, não relacionado)
- **Frontend (it. 1)**: `npm run build` exit 0 (Next 16.4.0/Turbopack; rotas /, /hoje, /potencial, **/saude**, /treinos, /treinos/[id]) · `npm run lint` exit 0 (zero reportes) — a fix não tocou frontend, gates seguem válidos
- **Test count before feature**: 228 (fim do potential-panel; registrado na matriz de tasks.md:18)
- **Test count after feature**: 262
- **Delta**: **+34 novos** (calc 19 + api 15, incluindo `test_other_users_rows_never_leak_into_panel`); nenhum teste deletado; nenhuma asserção enfraquecida (arquivos pré-existentes intactos no diff)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Success Criteria (spec.md:225-234)

- [x] **Zero chamadas Garmin na leitura** — `test_health_api.py:324-334` (varredura de imports do domínio)
- [x] **Suite verde pinando os valores** — 262 passed; pins re-derivados conferem (§ Spec-Anchored)
- [x] **Réguas do backend** (piso 25200, REM 21–31, buckets) — pinadas no calc + service + HTTP (floor_s/rem_band/dose nos 3 níveis)
- [x] **Regularidade em horário local, nunca GMT** — `01:16 GMT → 22:16` pinado (`test_health_calc.py:252-256`, `test_health_api.py:454`)
- [x] **Composição de fases com despertares no tooltip, stack fecha ~100%** — pontos carregam `deep_pct`/`light_pct`/`rem_pct`/`awakenings` pinados (`test_health_api.py:161-177`); UI empilha sem normalizar (`SleepStagesChart.tsx:121-123`)
- [x] **Força honesta (streak baixa real, corrente separada) + yoga ~/semana** — semântica pinada (`test_health_calc.py:290-374`, `test_health_api.py:207-211`); zeros exibidos como são (`Lifestyle.tsx`)
- [ ] **Valores do banco real** (60 noites renderizadas, ~84% abaixo, REM ~14%, deitar ~22:20, sexta 5,74h, HRV 52–103, RHR ~44, estresse ~24, dose 17 vs 27, yoga ~2,4/sem) — **UAT do orquestrador**: os testes pinam o shape com fixtures (design §Riscos: "testes usam fixtures curtas; os valores reais são conferidos no UAT")

---

## Requirement Traceability Update

30/30 HLT-01..30 verificados com evidência `file:line`. O Verifier não altera `spec.md` (restrição de escrita desta validação) — a tabela de traceability já os lista como `Verified` (autor); este veredito independente confirma os 30. O gap do sensor não é AC falho: é discriminação de teste sobre a convenção AD-001.

---

## Gaps Ranqueados

1. **✅ RESOLVIDO (Fix 1, it. 2) — Mutante sobrevivente M3 (severidade Minor)**: a remoção de `.where(model.user_id == DEFAULT_USER_ID)` (`backend/app/health/service.py:56`) deixava a suite 100% verde na iteração 1 — nenhum teste semeava um segundo usuário (single-user Fase 1; convenção AD-001 "user_id em toda query" era código morto para a suite). **Fix aplicada pelo orquestrador** (`c3df7e5`): `test_other_users_rows_never_leak_into_panel` (`backend/tests/test_health_api.py:305-374`) semeia o usuário 2 com uma linha em cada fonte (sono 4h + HRV 40 + RHR 99 + estresse 90 + 3 forças + yoga) e afirma que nenhum bloco do usuário 1 muda (points/below_floor/dose/HRV current/RHR null/stress null/lifestyle zeros). **Verificado nesta re-verificação**: mutante re-injetado idêntico no scratch morre na primeira asserção (`test_health_api.py:349` — a noite alheia vaza); suite 262 verde. Nenhum gap remanescente.

---

## Fix Plans

### Fix 1: Teste de isolamento de usuário no painel Saúde — ✅ aplicada e verificada

- **Root cause**: a suite de saúde (e todo o backend) só semeava dados do usuário default; o filtro `user_id` das queries de leitura nunca tinha chance de falhar num teste — remoção era invisível.
- **Fix task (executada)**: `test_other_users_rows_never_leak_into_panel` em `backend/tests/test_health_api.py:305-374` — usuário 2 semeados em todas as 5 fontes; payload do usuário 1 afirmado intacto em todos os blocos.
- **Verify (executada, it. 2)**: sensor M3 re-injetado no scratch → **killed** (1 failed / 14 passed); suite completa verde a 262.
- **Priority**: Minor · **Status**: fechado

---

## Summary

**Overall**: ✅ PASS — Ready (re-verificação, iteração 2 de 3)

**Spec-anchored check**: 30/30 ACs com `file:line` + asserção conferida ao resultado da spec (pins re-derivados de forma independente); 0 spec-precision gaps; 10/10 edge cases verificados
**Sensor**: 3/3 mutações mortas (M1/M2 na it. 1; M3 morto pela Fix 1 na it. 2 — re-injeção idêntica no scratch; worktree descartável; porcelain idêntico ao baseline antes/depois)
**Gate**: backend 262 passed / 0 failed / 0 skipped (228 → 262, +34, nenhum deletado) · frontend build+lint exit 0

**What works**: domínio `health/` completo end-to-end — calc puro (buckets <6h/≥6h45 com boundary exato, weekday 7 entradas, truque ±12h, semanas ISO com virada de ano), service de leitura 100% do banco próprio (zero Garmin, verificado por varredura), router com 422 estrutural e fallback de fuso com warning, payload de 6 blocos pinado nos 3 níveis (calc/service/HTTP) com literais re-derivados, e a UI inteira (`/saude`) com estados honestos, réguas do backend (nunca inventadas na UI) e formatação PT-BR. Os testes discriminam fortemente os três pontos de maior risco (M1/M2 mortos nas duas camadas; M3 morto pelo teste de isolamento após a fix).

**Issues found**: 1 mutante sobrevivente na it. 1 (filtro `user_id` indetectável — postura de todo o backend, não só desta feature) — **resolvido e verificado**: Fix 1 (`c3df7e5`, `test_other_users_rows_never_leak_into_panel`) mata o mutante na re-injeção; suite 262 verde. Nenhum AC falhou; nenhum spec-precision gap; nenhuma pendência aberta.

**Next steps**: UAT interativo com o usuário (valores reais: ~84% abaixo do piso, deitar ~22:20 local, sexta 5,74h, dose 69,5 vs 81,3, 390px) — a cargo do orquestrador. Lição L-005 (candidate) registrada na it. 1; promoção é do script ao reincidir em outra feature.
