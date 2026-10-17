# Painel Clareza (panel-clarity) — Validation

**Date**: 2026-10-16
**Spec**: `.specs/features/panel-clarity/spec.md` (27 ACs, CLR-01..27)
**Diff range**: `42b2fa8..HEAD` — 13 commits (`1fbb055..2892734` + docs `1a10b7c`); 19 arquivos, +1558/−283
**Verifier**: sub-agente independente (author ≠ verifier) — árvore real intacta (`git status --porcelain` vazio antes e depois do sensor); mutações só em worktree descartável fora do repo

---

## Validation — Veredito: PASS ✅

**27/27 ACs (CLR-01..27) com evidência `file:line`** e resultado conforme o desfecho definido pela spec (0 spec-precision gaps); 6/6 edge cases verificados; gates verdes (backend **268 passed** = 262 base + 6 novos, 0 failed, 0 skipped; frontend build+lint exit 0); sensor **3/3 mutações mortas**. UAT interativo 390px **realizado e aprovado pelo usuário (17/10/2026)** — ACs de UI verificados por inspeção de código na rodada do Verifier (conforme a matriz da própria spec, assumption "Verificação de UI sem runner": sem runner de teste no projeto) e confirmados visualmente no aparelho.

---

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 `_pmc_block` no health service | ✅ Done | `backend/app/health/service.py:149-170` (`_pmc_block(rows, days)`: sem linhas → `None` :154-155; `entry` lê as colunas cruas :157-164; `current` = última linha :169); montagem entre `stress` e `dose_response` :223; janela via `_series(db, DailyLoad, days)` :205; 4 testes service (`test_health_api.py:406-457`) |
| T2 router expõe `pmc` | ✅ Done | `backend/app/health/router.py:99-116` (`PmcPoint`/`PmcBlock` migrados), :148-155 (`HealthSummaryOut.pmc: PmcBlock \| None` :153, entre `stress` :152 e `dose_response` :154); 2 testes HTTP (`test_health_api.py:600-635`); 422 bounds seguem verdes (`test_health_api.py:521-534`) |
| T3 `api.ts` aditivo | ✅ Done | `frontend/src/lib/api.ts:346-363` (`PmcPoint`/`PmcBlock` na seção Saúde), :396 (`HealthSummaryOut.pmc`); `getPotential` intocado nesta task (commit `2733973` — sem quebra intermediária) |
| T4 `PanelSection` | ✅ Done | `frontend/src/components/PanelSection.tsx:11-46` — props `{index?, title, subtitle, badge?, children}`; índice :32-34; título h2 :35; badge pill :36-40; subtítulo sempre visível :42; `mt-8` externo :30 vs `mt-3` interno :43 |
| T5 `PmcChart` move | ✅ Done | `git diff -M` — rename `potential/PmcChart.tsx` → `health/PmcChart.tsx`, similarity 91%: só o header comment muda (POT-23/24 → CLR-07/08/10); nenhum pixel muda; `components/potential/` sem o arquivo antigo; `PotentialPanel` importou o novo caminho no commit `d5a1848` |
| T6 `HealthPanel` recomposto | ✅ Done | 5 `PanelSection` numerados 1–5 (`HealthPanel.tsx:102-194`), linha-guia :96-100, Carga posição 2 :129-144, empty geral inclui `pmc` :79-92, `Section` local antigo removido |
| T7 legenda por método | ✅ Done | `frontend/src/components/potential/PredictionsTable.tsx:97-114` — 4 entradas (Garmin/Riegel/VDOT/média honesta), sempre visíveis sob a tabela |
| T8 `DecayTable` explainer | ✅ Done | `frontend/src/components/potential/DecayTable.tsx:86-90` — o que compara + sinal, sempre visível; destaque do maior gap intocado :27-30 |
| T9 `PotentialPanel` recomposto | ✅ Done | 3 `PanelSection` sem índice (`PotentialPanel.tsx:117-148`), linha-guia :111-115, empty recalculado sem pmc :96-107, `Section` local e `PmcChart` import removidos |
| T10 potencial sem `pmc`/`days` | ✅ Done | `backend/app/potential/service.py:90-133` (assinatura sem `days`; payload 4 chaves :119-132), `backend/app/potential/router.py:78-86` (`PotentialOut` sem `pmc`; handler sem `Query`); 500 de calibração preservado (`test_potential_api.py:389-398`); migração 1:1 executada (ver Gate Check) |
| T11 `api.ts` fecha contrato | ✅ Done | `frontend/src/lib/api.ts:275-283` (`PotentialOut` sem `pmc`, comentário CLR-03/04), :285-294 (`getPotential()` sem param e sem query na URL :289-291); nenhum `pmc` no domínio potencial (grep: só comentário de empty check :93) |
| T12 README | ✅ Done | `README.md:165-213` (Potencial 3 blocos, sem PMC/days :202-206), :215-247 (Saúde 5 seções, Carga :227-231, AD-009 :243-247); status :8 (ver Code Quality — julgado aceitável) |

Todas as 12 tasks `[x]` em `tasks.md`; nenhuma blocked ou parcial.

---

## Spec-Anchored Acceptance Criteria

**Convenção da matriz** (tasks.md:22-25): frontend sem runner de teste — ACs de contrato por pytest pinando fixtures; ACs de UI por inspeção do código do componente com citação `file:line` (assumption da spec: "Verificação de UI sem runner"). Evidence-or-zero aplicado: todos os 27 têm citação.

### P1: Contrato — PMC muda para `/api/health/summary` (CLR-01..06)

| Criterion | Spec-defined outcome | `file:line` + asserção | Result |
| --------- | -------------------- | ----------------------- | ------ |
| CLR-01: `GET /api/health/summary` com `days` em [7,365] → bloco `pmc` `{days, points[{date,ctl,atl,tsb,acwr}], current}` das últimas `days` linhas de `load`, mesma forma do bloco antigo do potencial | janela pedida refletida em `days`; `points` ASC com os valores das linhas; `current` = última linha; mesma shape | `backend/tests/test_health_api.py:406-423` — `pmc["days"] == 2` (:416), `points == [{14/10: 21.0/27.0/−6.0/1.40}, {15/10: 22.0/28.0/−6.0/1.42}]` ASC (:417-420), `current == {15/10, 22.0, 28.0, −6.0, 1.42}` (:421-423); janela > histórico devolve o que existe com `days == 365` (:426-438); posição entre `stress` e `dose_response` — `list(payload.keys())` pinada (:447-457); via HTTP com bloco inteiro pinado + ordem de chaves JSON (:600-624); shape idêntica ao antigo `_pmc_block` (`git show 42b2fa8:backend/app/potential/service.py:39-71` — mesmo `entry` de 5 campos) | ✅ PASS |
| CLR-02: sem linhas em `load` → `pmc=null` (estado vazio, não erro) | `pmc is None`; 200 via HTTP | `backend/tests/test_health_api.py:441-444` — `assert service.get_health(db, 60, SAO_PAULO)["pmc"] is None`; via HTTP `test_health_api.py:627-635` — 200 + `assert body["pmc"] is None` (:634) | ✅ PASS |
| CLR-03: `GET /api/potential` → 200 com payload apenas `{vdot, predictions, vo2max, decay}` — sem `pmc` | exatamente 4 chaves; exclusão é do contrato (não do dado vazio) | `backend/tests/test_potential_api.py:274-285` — com 3 linhas de `load` semeadas, `assert list(payload.keys()) == ["vdot", "predictions", "vo2max", "decay"]` (:285); via HTTP `test_potential_api.py:347-359` — `list(response.json().keys()) == ["vdot", "predictions", "vo2max", "decay"]` (:357-359); código: `backend/app/potential/service.py:119-132`, `backend/app/potential/router.py:78-83` | ✅ PASS |
| CLR-04: `GET /api/potential?days=90` (param morto) → 200 normalmente, param removido da assinatura, nenhum efeito no payload | 200; payload idêntico; sem validação nova no espaço do param | `backend/tests/test_potential_api.py:362-374` — painel cheio semeado (incl. `load`): `with_days.json() == plain.json()` (:374), ambos 200 (:372-373); `test_potential_api.py:377-386` — days 0/−1/366 → 200 com payload == baseline (:383-386; valores que eram 422 no contrato antigo agora são query ignorada); assinatura sem param: `backend/app/potential/router.py:85-86` | ✅ PASS |
| CLR-05: bloco `pmc` computado exclusivamente do banco próprio, zero chamadas Garmin (AD-002) | nenhum import do gateway no domínio health | `backend/tests/test_health_api.py:460-470` — varre todos os `*.py` de `health/` afirmando `"from app.garmin"` e `"import app.garmin"` ausentes (:468-469); `backend/app/health/service.py:18-36` importa só `app.db.models` + `app.health.calc` | ✅ PASS |
| CLR-06: ctl/atl/tsb/acwr idênticos às linhas de `load` — zero recálculo | valores exatamente como as linhas; nenhuma aritmética sobre eles | `backend/app/health/service.py:157-164` — `entry` lê `row.ctl/atl/tsb/acwr` crus (nenhuma operação); pin de igualdade: `test_health_api.py:410-412` semeia 20.0/25.0/−5.0/1.40 etc. via `_seed_load` e `:417-423` afirma os mesmos literais no payload (recálculo qualquer quebraria o pin); janela DESC+limit+reverse idêntica à antiga (`_series`, `service.py:50-64`) | ✅ PASS |

### P1: Seção "Carga de treino" na Saúde (CLR-07..11)

| Criterion | Spec-defined outcome | `file:line` + asserção/inspeção | Result |
| --------- | -------------------- | ------------------------------ | ------ |
| CLR-07: `/saude` com `pmc != null` → seção "Carga de treino" na posição 2 (entre Sono e Recuperação) com gráfico CTL/ATL/TSB + destaques do último dia (CTL, ATL, TSB, ACWR), reutilizando o componente existente | posição 2; curva + 4 destaques; componente reusado (move puro) | `frontend/src/components/health/HealthPanel.tsx:129-144` — `PanelSection index={2} title="Carga de treino"` (:130-131), `pmc !== null → <PmcChart pmc={pmc} />` (:134-137), entre Sono (:102-127) e Recuperação (:146); `frontend/src/components/health/PmcChart.tsx:135` (`Bar dataKey="tsb"`), :136-143 (`Line ctl`), :144-151 (`Line atl`), :106-113 (4 `StatCard` de `current`); reuso: rename git 91% similarity — nenhum pixel muda | ✅ PASS |
| CLR-08: seção Carga exibe subtítulo sempre visível explicando fitness (CTL), fadiga (ATL) e forma (TSB) e por que importa | subtítulo com os 3 conceitos + consequência | `frontend/src/components/health/HealthPanel.tsx:132` — "Quanta carga estou impondo ao corpo? A curva de 60 dias traz fitness (CTL), fadiga (ATL) e forma (TSB) — carga acima da que o corpo absorve compromete recuperação e adaptação."; sempre visível via `PanelSection.tsx:42` (`<p className="mt-1 text-sm text-muted">{subtitle}</p>` — sem estado/interação) | ✅ PASS |
| CLR-09: `pmc=null` → seção Carga com estado vazio orientando o primeiro sync (sem gráfico quebrado, HLT-19) | estado vazio orientando sync dentro da seção | `frontend/src/components/health/HealthPanel.tsx:138-143` — `<BlockEmpty> Sem curva de carga ainda — ela nasce no primeiro sync, que acumula o treino dos últimos dias.</BlockEmpty>` | ✅ PASS |
| CLR-10: `acwr` do último dia NULL → destaque exibe "—" | "—" (janela 28d incompleta, SYNC-24) | `frontend/src/components/health/PmcChart.tsx:53-55` — `statOrDash`: `value !== null ? formatVdot(value) : "—"`; aplicado ao ACWR em :112 (`<StatCard label="ACWR" value={statOrDash(current.acwr)} />`); contrato atravessa null (`router.py:107` `acwr: float \| None`) | ✅ PASS |
| CLR-11: empty geral inclui `pmc` — painel "vazio" somente com sono, HRV, RHR, estresse E PMC ausentes; com PMC presente renderiza | check de 5 blocos; `pmc != null` → painel renderiza | `frontend/src/components/health/HealthPanel.tsx:79-92` — `sleep === null && hrv === null && rhr === null && stress === null && pmc === null` (:80-84) → empty; com só `load` no banco o check falha e a seção 2 renderiza `<PmcChart pmc={pmc} />` (:134-137) com dados | ✅ PASS |

### P1: Cabeçalhos fortes na Saúde (CLR-12..16)

| Criterion | Spec-defined outcome | `file:line` + inspeção | Result |
| --------- | -------------------- | ---------------------- | ------ |
| CLR-12: cada uma das 5 seções com cabeçalho: índice numerado (1–5), título e subtítulo sempre visível | 5 seções numeradas com título + subtítulo | `frontend/src/components/health/HealthPanel.tsx:102-194` — `PanelSection` com `index={1}` Sono (:102-103), `index={2}` Carga (:129-130), `index={3}` Recuperação (:146-147), `index={4}` Dose-resposta (:175-176), `index={5}` Equilíbrio (:183-184); `PanelSection.tsx:32-35` renderiza `{index}.` + `<h2>` título, :42 subtítulo sempre visível | ✅ PASS |
| CLR-13: subtítulo de cada seção indica a pergunta que responde (Sono: durmo o suficiente?; Carga: quanta carga imponho?; Recuperação: como o corpo responde?; Dose: o que dormir mal custa?; Equilíbrio: a base sustenta o treino?) | as 5 perguntas presentes | `HealthPanel.tsx:105` "Durmo o suficiente pra absorver o treino?" · :132 "Quanta carga estou impondo ao corpo?" · :149 "Como o corpo está respondendo?" · :178 "O que dormir mal me custa?" · :186 "A base fora da corrida sustenta o treino?" — as 5 abrem os subtítulos | ✅ PASS |
| CLR-14: espaçamento entre seções claramente maior que entre gráficos internos (sem container aninhado) | externo >> interno; sem card wrapper | `frontend/src/components/PanelSection.tsx:30` — `<section className="mt-8">` (32px) vs interno `space-y-3` entre gráficos (`HealthPanel.tsx:108,151,188` — 12px) e `mt-3` header→conteúdo (`PanelSection.tsx:43`); `PanelSection` não envolve `children` em card (context.md D); fixo, não proporcional ao conteúdo | ✅ PASS |
| CLR-15: 390px legível sem scroll horizontal | sem overflow horizontal | Inspeção: nenhum elemento novo de largura fixa — `PanelSection` é texto que flui (:30-43); grids `grid-cols-4 gap-2` (`PmcChart.tsx:107`), gráficos `w-full` + `ResponsiveContainer width="100%"` (`PmcChart.tsx:115-117`), tabelas em wrapper `overflow-hidden` + `w-full` (`PredictionsTable.tsx:38-39`, `DecayTable.tsx:34-35`), page `max-w-3xl px-4` (`app/saude/page.tsx:7`); componentes movidos/herdados já validados a 390px nas features anteriores. Confirmação visual: UAT do orquestrador | ✅ PASS (per matriz; visual no UAT) |
| CLR-16: falha da API → mensagem de erro inline sem quebrar navegação (comportamento existente preservado) | erro inline; navegação de pé | `frontend/src/components/health/HealthPanel.tsx:50-56` (catch → estado error), :66-72 — "Não foi possível carregar a saúde: {message}" inline; a nav vive fora do `<main>` (`app/saude/page.tsx:7-10`); idem `PotentialPanel.tsx:67-77,83-89` | ✅ PASS |

### P1: Potencial narrativo com selo de fonte (CLR-17..25)

| Criterion | Spec-defined outcome | `file:line` + inspeção | Result |
| --------- | -------------------- | ---------------------- | ------ |
| CLR-17: `/potencial` em 3 blocos nesta ordem: "Onde estou" (lacuna + timeline VDOT), "O que isso prevê" (previsões + decaimento), "O que o relógio estima" (VO2max, quando existir) | 3 blocos na ordem, com os sub-conteúdos certos | `frontend/src/components/potential/PotentialPanel.tsx:117-148` — "Onde estou" (:117-127: `GapCard` :122 + `VdotTimeline` :124), "O que isso prevê" (:129-137: `PredictionsTable` :134 + `DecayTable` :135), "O que o relógio estima" (:139-148: `Vo2maxTrend` :145, condicional) | ✅ PASS |
| CLR-18: bloco "Onde estou" com subtítulo sempre visível explicando VDOT (régua de Daniels — tempo → capacidade aeróbica), corrente (último teste calibrado), demonstrado (melhor prova máxima) e a lacuna % | 4 conceitos cobertos | `frontend/src/components/potential/PotentialPanel.tsx:119` — "VDOT é a régua de equivalência de Daniels — um tempo numa distância vira capacidade aeróbica. O corrente vem do último teste calibrado, o demonstrado da melhor prova máxima; a lacuna % é quanto do demonstrado o teste atual valida." | ✅ PASS |
| CLR-19: tabela identifica cada método de forma distinguível com fonte: Garmin (preditor do Garmin Connect), Riegel (extrapolação ancorada no PR de 5K), VDOT (equivalência de Daniels do teste corrente), média honesta (média das presentes) — legenda por método, além do nome da coluna | 4 métodos com fonte, sempre visível | `frontend/src/components/potential/PredictionsTable.tsx:97-114` — legenda `<ul>` sob a tabela: Garmin "preditor do Garmin Connect, sincronizado no sync" (:98-101), Riegel "extrapolação T2 = T1 × (D2/D1)^1,06 ancorada no PR de 5K" (:102-105), VDOT "equivalência de Daniels do teste corrente" (:106-109), Média honesta "média só das estimativas presentes na distância, nenhuma célula inventada" (:110-113) — sem interação | ✅ PASS |
| CLR-20: decaimento com explicação sempre visível do que compara (pace real dos PRs vs pace ideal da equivalência VDOT corrente) e por que importa (gap de execução/especificidade, não de motor) | comparação + interpretação do sinal | `frontend/src/components/potential/DecayTable.tsx:86-90` — "Compara o pace real dos seus PRs com o pace ideal da equivalência VDOT do teste corrente. Negativo = pace real mais lento que o ideal — gap de execução/especificidade, não de motor." | ✅ PASS |
| CLR-21: bloco "O que o relógio estima" mantém selo "estimativa do relógio" e nota de hierarquia (provas/testes > algoritmo — AD-005) sempre visíveis | selo + nota de hierarquia | `frontend/src/components/potential/Vo2maxTrend.tsx:56-60` — badge pill "estimativa do relógio" (sempre renderizado); :94-97 — "Provas e testes de campo medem; o relógio estima... o algoritmo fica abaixo deles na hierarquia de métricas"; bloco renderizado em `PotentialPanel.tsx:144-146` | ✅ PASS |
| CLR-22: `/potencial` exibe apenas os 3 blocos — nenhuma seção de carga/PMC (ubiquitous) | render tree sem PMC | `frontend/src/components/potential/PotentialPanel.tsx:109-150` — só os 3 `PanelSection`; imports :13-21 sem `PmcChart`; grep de `pmc\|Pmc` em `components/potential/` → único hit é comentário de empty check (`PotentialPanel.tsx:93`); backend: `test_potential_api.py:285,357-359` | ✅ PASS |
| CLR-23: `vo2max=null` → bloco 3 inteiro ausente; `decay=[]` → sub-bloco decaimento fora | condicionais corretas | `frontend/src/components/potential/PotentialPanel.tsx:139` — `{vo2max !== null && (<PanelSection title="O que o relógio estima">...)}` (bloco inteiro, incluindo header, ausente); :135 — `{decay.length > 0 && <DecayTable rows={decay} />}` | ✅ PASS |
| CLR-24: timeline ≤1 ponto, `vo2max=null` e `decay` vazio → estado vazio orientando sync (check recalculado sem pmc) | empty check sem `pmc`, apontando sync | `frontend/src/components/potential/PotentialPanel.tsx:96-107` — `vdot.timeline.length <= 1 && vo2max === null && decay.length === 0` (:97-99, sem pmc — saiu do contrato em T10/T11) → "Nada por aqui ainda. Use o botão "Puxar do Garmin"..." | ✅ PASS |
| CLR-25: `/potencial` a 390px legível sem scroll horizontal | sem overflow horizontal | Inspeção idem CLR-15: novos elementos são texto fluente (`PotentialPanel.tsx:111-115` linha-guia, legendas `<ul>`/`<p>`); tabelas pré-existentes em `overflow-hidden` + `w-full` (`PredictionsTable.tsx:38-39`, `DecayTable.tsx:34-35`); page `max-w-3xl px-4` (`app/potencial/page.tsx:7`); nenhum `min-w`/largura fixa no diff. Confirmação visual: UAT do orquestrador | ✅ PASS (per matriz; visual no UAT) |

### P2: Linha-guia de leitura (CLR-26..27)

| Criterion | Spec-defined outcome | `file:line` + inspeção | Result |
| --------- | -------------------- | ---------------------- | ------ |
| CLR-26: `/saude` com linha-guia sempre visível no topo conectando as 5 seções em uma frase (o fio) | 1 frase no topo, acima da 1ª seção, sempre visível, conectando as 5 | `frontend/src/components/health/HealthPanel.tsx:96-100` — "O fio: o sono recupera, o treino impõe carga, o corpo responde, dormir mal custa — e a vida fora da corrida sustenta tudo." — cobre Sono→Carga→Recuperação→Dose→Equilíbrio na ordem das seções, `<p>` sempre visível acima da seção 1 (:102); redação é discretion do design (context.md "Redação exata dos subtítulos e da linha-guia") | ✅ PASS |
| CLR-27: `/potencial` com linha-guia sempre visível no topo com a pergunta do painel (qual meu máximo e a que distância dele estou?) e a régua de leitura (provas/testes > estimativas — AD-005) | pergunta + régua, sempre visíveis | `frontend/src/components/potential/PotentialPanel.tsx:111-115` — "Qual é o meu máximo e a que distância dele estou? A régua: provas e testes de campo medem, estimativas do relógio só aproximam." — `<p>` sempre visível acima do bloco 1 (:117) | ✅ PASS |

**Status**: ✅ 27/27 ACs com evidência `file:line` + asserção/inspeção conferida ao desfecho definido pela spec. 0 spec-precision gaps — todos os ACs definem outcome observável (valor, estado, chave de contrato, elemento de UI).

---

## Edge Cases (spec.md:153-160)

- [x] **`?days=90` no potencial → 200, query não declarada ignorada; nenhuma validação nova herda o espaço** — `backend/tests/test_potential_api.py:362-374` (payload idêntico com painel cheio semeado) + `:377-386` (0/−1/366, que eram 422, agora 200 idêntico); handler sem `Query` (`backend/app/potential/router.py:85-86`)
- [x] **`pmc` existe mas sono/HRV/RHR/estresse não → `/saude` renderiza apenas a seção Carga com dados (painel não-vazio)** — empty geral exige os 5 ausentes (`HealthPanel.tsx:79-92`, `pmc === null` :84); com só `load`, Carga renderiza `<PmcChart>` (:134-137) e as demais seções mostram `BlockEmpty` (:107-126 sono, :152-171 hrv/rhr; estresse tem card "—" interno pré-existente — `StressChart.tsx:54-60`)
- [x] **estimativa NULL na tabela → célula "—"; média honesta usa só as presentes (POT-22 preservado)** — `PredictionsTable.tsx:27-29` (`secondsOrDash` → "—") aplicado a todas as colunas de estimativa (:73-76); a legenda nova (:97-114) não toca células nem contrato de dado — média honesta continua no backend (`app/potential/calc.py`, fora do diff)
- [x] **bloco interno null → estado vazio do bloco dentro da seção (HLT-19), cabeçalho forte não substitui** — sono: `HealthPanel.tsx:107-126`; HRV/RHR: :152-171; estresse: card "—" interno pré-existente (`StressChart.tsx:54-60`, HLT-26)
- [x] **copy cita régua → valor é o do payload; UI não hardcoda régua nova** — Sono cita "piso de 7h" + "banda de 21–31%" (`HealthPanel.tsx:105`) == `floor_s` 25200s (`app/health/calc.py:19`; pin `test_health_api.py:157`) e `rem_band` [21.0, 31.0] (`calc.py:20`; pin :158); Dose cita "<6h"/"≥6h45" (`HealthPanel.tsx:178`) == `SHORT_MAX_S` 21600 / `ADEQUATE_MIN_S` 24300 (`calc.py:21-22`); nenhum número novo inventado
- [x] **seções adjacentes com quantidades diferentes de gráficos → fronteira continua legível (espaçamento fixo, não proporcional)** — `PanelSection.tsx:30` `mt-8` fixo por seção, independente do conteúdo interno (Sono tem 4 cards, Dose-resposta 1 — mesma fronteira)

---

## Discrimination Sensor

**Tier**: lightweight (3 mutações comportamentais nos pontos de maior risco do código novo — 1 por camada: montagem do bloco, contrato do router, contrato do service do potencial).
**Scratch**: `git worktree add C:\Users\leona\AppData\Local\Temp\opencode\pc-sensor HEAD` (detached `2892734`), venv próprio via `uv run`; suite completa `uv run pytest -q` por mutação (aponta o `ritmo_test` do compose via conftest). Nenhuma mutação tocou a árvore real — `git status --porcelain` vazio antes e depois (baseline idêntico); worktree removido com `--force`; `git worktree list` mostra só `main`.

| # | Mutante | file:line (scratch) | Descrição | Morto? |
| - | ------- | ------------------- | --------- | ------ |
| M1 | `current` do bloco PMC | `backend/app/health/service.py:169` | `"current": entry(rows[-1])` → `entry(rows[0])` (primeira linha em vez da última) | ✅ **Killed** — 2 failed / 266 passed: `test_pmc_window_asc_and_current_from_load` (`test_health_api.py:421` — current virou 14/10 21.0/27.0/1.40 ≠ 15/10 22.0/28.0/1.42) + `test_api_pmc_traverses_http_between_stress_and_dose` (`test_health_api.py:615` — mesmo desvio via HTTP) |
| M2 | campo do contrato | `backend/app/health/router.py:153` | `pmc: PmcBlock \| None` removido de `HealthSummaryOut` | ✅ **Killed** — 2 failed / 266 passed: `test_api_pmc_traverses_http_between_stress_and_dose` (`test_health_api.py:612` — ordem das chaves sem `pmc`) + `test_api_pmc_null_traverses_http_without_load` (`test_health_api.py:634` — `KeyError: 'pmc'`) |
| M3 | chave proibida no potencial | `backend/app/potential/service.py:133` | `"pmc": None` reintroduzido no payload de `get_potential` (viola CLR-03) | ✅ **Killed** — 1 failed / 267 passed: `test_service_payload_omits_pmc_even_with_load_rows` (`test_potential_api.py:285` — `list(payload.keys())` ganhou 'pmc') |

**Result**: **3/3 killed — PASS ✅**. Os testes discriminam a semântica do `current` (última linha) nas duas camadas, a presença/posição do campo `pmc` no contrato da Saúde e a exclusão do `pmc` no payload do Potencial.

**Nota de camada (não é gap)**: na M3, o `response_model` `PotentialOut` teria mascarado a chave extra no JSON (pydantic `extra='ignore'` na validação do FastAPI) — por isso o kill veio do pin de chaves no service (`test_potential_api.py:285`). A variante router da mesma mutação (campo `pmc` em `PotentialOut`) é morta pelo pin de chaves do JSON em `test_potential_api.py:357-359` — ambas as camadas do contrato têm pino independente.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ 19 arquivos no diff, todos mapeados a T1–T12 (+ artefatos `.specs` da feature + `STATE.md` AD-009); out-of-scope respeitado: Treinos e Hoje intocados (`app/treinos/**`, `app/hoje` fora do diff), zero cálculo novo (`calc.py` de ambos os domínios fora do diff), sem seletor de janela (UI fixa 60), sem alertas, sem i18n/glossário, sem recolhível |
| No abstractions for single-use code | ✅ único componente novo é `PanelSection` — reuso trans-painel (5× Saúde, 3× Potencial) é a entrega da feature; helpers existentes reusados (`_series`, `BlockEmpty`, `formatVdot`) |
| No unnecessary flexibility | ✅ props exatamente as 4 da spec/design (`index?` opcional conforme decisão "Só na Saúde"); nenhum knob novo |
| Surgical changes / só arquivos da task | ✅ `PmcChart` move puro (rename 91% similarity — só header comment); `Section` locais antigos removidos dos 2 painéis (substituídos pelo `PanelSection`); `potential/service.py`/`router.py` só remoção; `api.ts` só tipos/assinatura/comentários; README só as 2 seções de painel + linha de status |
| Didn't "improve" unrelated code | ✅ gráficos de sono/HRV/RHR/dose/lifestyle, `StressChart`, `Vo2maxTrend`, `VdotTimeline`, `GapCard` (corpo), `format.ts` e as páginas `/saude`/`/potencial` intocados — só a composição mudou; `docker-compose.yml` fora do diff |
| Matches patterns | ✅ espelho 1:1 router↔`api.ts` (AD-009); docstrings citando CLR; seeds ORM + TestClient; PT-BR na UI/ASCII na API; `cache: "no-store"`; pins literais nunca compartilhados com a implementação (L-001/L-002 citadas nos cabeçalhos dos testes) |
| Spec-anchored outcome check | ✅ asserções de VALOR/ESTADO: dicts completos pinados (`pmc == {days: 60, points: [...], current: {...}}`), listas de chaves pinadas nos dois endpoints, `is None`, `==` de payload idêntico — não só chamadas |
| Tests non-shallow (spot-check) | ✅ CLR-01: bloco inteiro pinado em 2 camadas (service :406-423, HTTP :600-624) com janela, ASC, valores e posição; exclusão do `pmc` no potencial é pinada COM linhas de `load` semeadas (exclusão do contrato, não do dado vazio — :274-285) |
| Per-layer Coverage Expectation | ✅ domínio 1:1 com CLR-01..06 (janela pedida, ASC, current, null, posição, sem-pmc, dead-days, zero recálculo, zero Garmin); rotas happy+edge+error (200 default/bordas 7–365, 422 no health, dead-days 200 no potencial, 500 de calibração preservado, blocos null via HTTP) |
| Every test maps to a spec requirement | ✅ cada teste novo cita CLR/done-when/edge no docstring (ex.: `test_health_api.py:402-404,595-598`; `test_potential_api.py:269-271`); nenhum teste órfão |
| Documented guidelines followed | ✅ README §Testes (`uv run pytest` no Postgres do compose, suite no host); `frontend/AGENTS.md` Next 16 (nenhum API novo do Next usado — só client components existentes; build exit 0); AD-008/AD-009 (`.specs/STATE.md:69-76`) seguidas |
| Senior engineer approve? | ✅ — incluindo a nota da T12: a linha de status `README.md:8` ganhou "painel Saúde ✅". **Julgado aceitável**: o README pré-feature (`42b2fa8`) dizia "próximos: Saúde, Avaliar com IA, Hoje" embora o painel Saúde já existisse (feature health-panel, baseline 262) — a adição conserta uma mentira pré-existente sobre a seção que o próprio README documenta na íntegra (README.md:215-247); mudança de 1 palavra, mínima e necessária à honestidade do doc |

---

## Gate Check

- **Gate commands** (tasks.md:27-36): `docker compose up -d postgres` → `cd backend; uv run pytest -q` · `cd frontend; npm run build; npm run lint`
- **Backend**: **268 passed, 0 failed, 0 skipped** (171.22s, exit 0; 1 warning pré-existente `StarletteDeprecationWarning` do TestClient, não relacionado)
- **Frontend**: `npm run build` exit 0 (Next 16.4.0/Turbopack; rotas /, /hoje, /potencial, /saude, /treinos, /treinos/[id]) · `npm run lint` exit 0 (zero reportes)
- **Test count before feature**: 262 (baseline pós health-panel, tasks.md:18)
- **Test count after feature**: 268
- **Delta**: **+6 novos** — `test_health_api.py` 15→21 (+4 service T1: `test_pmc_window_asc_and_current_from_load`, `test_pmc_window_larger_than_history_returns_what_exists`, `test_pmc_null_without_load_rows`, `test_pmc_sits_between_stress_and_dose_response` · +2 HTTP T2: `test_api_pmc_traverses_http_between_stress_and_dose`, `test_api_pmc_null_traverses_http_without_load`); `test_potential_api.py` 13→13 (−5 +5)
- **Migração 1:1 (checklist T10)** — nenhum assert de PMC removido sem contrapartida viva:
  - `test_pmc_block_respects_days_window_and_current` → `test_pmc_window_asc_and_current_from_load` + `test_pmc_window_larger_than_history_returns_what_exists` (a edge de janela>histórico, que no antigo era asserção interna do mesmo teste, virou teste próprio)
  - `test_pmc_null_without_load_rows` → `test_pmc_null_without_load_rows` (health, service)
  - `test_api_pmc_null_traverses_http_as_json_null` → `test_api_pmc_null_traverses_http_without_load` (health, HTTP)
  - `test_api_days_out_of_range_responds_422` / `test_api_days_boundaries_respond_200` (potencial) → contrapartes vivas no domínio onde o `days` existe: `test_health_api.py:521-525` (422) e `:528-534` (bordas 7/365); a inversão intencional no potencial (param morto → 200) está pinada por `test_api_dead_days_param_space_has_no_validation` (`test_potential_api.py:377-386`)
  - 5 novos do potencial: `test_service_payload_omits_pmc_even_with_load_rows`, `test_api_payload_omits_pmc_even_with_load_rows`, `test_api_dead_days_param_returns_identical_payload`, `test_api_dead_days_param_space_has_no_validation`, `test_api_empty_bank_keeps_empty_states_without_pmc`
- **Skipped**: nenhum · **Failures**: nenhuma

---

## Success Criteria (spec.md:200-209)

- [x] **`/potencial` 3 blocos na ordem, sem PMC; métodos distinguíveis** — `PotentialPanel.tsx:109-150` + legenda `PredictionsTable.tsx:97-114`; backend `test_potential_api.py:347-359`
- [x] **`/saude` 5 seções numeradas, subtítulos visíveis, fio no topo, PMC posição 2 com os mesmos valores** — `HealthPanel.tsx:94-195`; "mesmos valores" = zero recálculo pinado (CLR-06) + shape idêntica ao bloco antigo
- [x] **Contrato: health traz `pmc` (ou null) na janela; potencial sem `pmc` e sem `days`; pytest verde; migração 1:1** — gate 268; tabela de contrapartidas no Gate Check
- [x] **Zero chamadas à API do Garmin nos endpoints de leitura** — `test_health_api.py:460-470` + `test_potential_api.py:256-266` (POT-15 vivo)
- [x] **Estados vazios honestos**: seção Carga com `pmc=null` (CLR-09), painel vazio geral só com tudo ausente (CLR-11), Potencial vazio recalculado sem pmc (CLR-24)
- [x] **390px sem scroll horizontal nos dois painéis** — UAT aprovado pelo usuário (17/10/2026, celular 390px via LAN `http://192.168.15.16:3000`): 5 seções numeradas e 3 blocos distinguíveis de relance, sem scroll horizontal; valores reais conferidos (Carga de treino com CTL 132,2 · ATL 141,3 · TSB −9,2 · ACWR 1,1 de 16/10)

---

## Interactive UAT Results

Realizado pelo usuário (Leonardo) em 17/10/2026, celular 390px via LAN (`http://192.168.15.16:3000`), com a stack do compose rebuildada (`NEXT_PUBLIC_API_URL` apontando para o IP da LAN — o Next assa a URL no build).

| #   | Test                                             | Result   | Details                                                                                                      |
| --- | ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | `/potencial`: 3 blocos narrativos, sem PMC, legenda por métodos, linha-guia | ✅ Pass  | "Ficou ok" (resposta do usuário) — veredito sobre o checklist completo do UAT apresentado                      |
| 2   | `/saude`: 5 seções numeradas com Carga de treino na posição 2 (valores reais do dia), linha-guia | ✅ Pass  | idem — checklist apresentado em uma passada; resposta única cobrindo os dois painéis                          |
| 3   | 390px sem scroll horizontal nos dois painéis     | ✅ Pass  | idem — nenhum relato de overflow                                                                              |

Resposta literal do usuário ao checklist completo: **"Ficou ok"** — aprovado sem ressalvas. Severity: n/a (nenhum issue relatado).

---

## Requirement Traceability Update

27/27 CLR-01..CLR-27 verificados com evidência `file:line` e sem gaps. Este Verifier atualizou a tabela de traceability do `spec.md` (CLR-01..27: `Implementing` → `✅ Verified`), conforme instrução do orquestrador.

| Requirement | Previous Status | New Status |
| ----------- | --------------- | ---------- |
| CLR-01..CLR-27 | Implementing | ✅ Verified (27/27) |

---

## Gaps Ranqueados

Nenhum. 27/27 ACs verificados; 3/3 mutantes mortos; 6/6 edge cases; gates verdes; contagem de testes subiu (262 → 268, nenhum teste perdido — migração 1:1 documentada).

---

## Summary

**Overall**: ✅ PASS — Ready

**Spec-anchored check**: 27/27 ACs com `file:line` + asserção/inspeção conferida ao desfecho da spec (CLR-01..06 contrato por pytest com valores pinados; CLR-07..27 UI por inspeção de código, conforme a matriz da spec); 0 spec-precision gaps; 6/6 edge cases
**Sensor**: 3/3 mutações mortas (M1 `current` do PMC, M2 campo `pmc` do `HealthSummaryOut`, M3 chave `pmc` no payload do potencial — worktree descartável, porcelain idêntico ao baseline antes/depois)
**Gate**: backend 268 passed / 0 failed / 0 skipped (262 → 268, +6, migração 1:1 sem perda de assert) · frontend build+lint exit 0

**What works**: o contrato migrou ponta a ponta — `pmc` (mesma shape, zero recálculo, janela única da Saúde) entra em `/api/health/summary` entre `stress` e `dose_response` e sai de `/api/potential` junto com o `days` morto (`?days=90` → 200 sem efeito); a Saúde narra em 5 seções numeradas com subtítulos sempre visíveis, linha-guia no topo e a Carga de treino na posição 2 reusando o `PmcChart` (move puro); o Potencial conta a história em 3 blocos com legenda por método, explainer do decaimento, selo/hierarquia do relógio e empty state recalculado; cliente `api.ts` espelha os dois contratos; README honesto sobre a nova composição (incluindo o conserto do status pré-existente desatualizado).

**Issues found**: nenhum bloqueante. Duas notas não-gaps: (1) UAT interativo 390px **aprovado pelo usuário (17/10/2026)** — ver Interactive UAT Results; (2) a mutação M3 é mascarada no HTTP pelo `response_model` (pydantic `extra='ignore'`), mas o pin duplo (service `test_potential_api.py:285` + HTTP `:357-359`) cobre as duas camadas do contrato.

**Next steps**: nenhum — feature fechada (Verifier PASS + UAT aprovado). Lições: nenhum sinal (PASS limpo, 0 mutantes sobreviventes, 0 gaps) — nada a registrar.
