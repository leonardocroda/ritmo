# Painel Potencial — Especificação

> Feature 3 da Fase 1 · Painel "Potencial" (§4.4): timeline VDOT com faixa honesta, previsões vs PRs (4 estimativas), curva PMC, decaimento por distância e tendência VO2max do relógio

## Problem Statement

O produto tem treinos (workouts-list) mas não responde à pergunta central do corredor: "qual meu máximo e a que distância dele estou?" (§4.4). Os dados já existem no banco (PMC com 182 dias em `load`, 7 PRs em `personal_records`, calibração 50,2 no `vdot_zones.json`, VO2max do relógio no `raw_json` das atividades) — falta calcular, expor e renderizar. Faltam também duas bases: a estimativa do Garmin (preditor de prova, não sincronizada) e a data dos PRs (bug de key-case no mapper deixa `pr_date` NULL).

## Goals

- [ ] Endpoint `GET /api/potential` montando o painel inteiro a partir do banco próprio (zero chamadas Garmin — AD-002)
- [ ] Timeline VDOT: cada teste/prova máxima datada vira um ponto; linha no VDOT corrente (50,2) e faixa honesta até o demonstrado (5K 19:23 → 51,6 pela forma fechada de Daniels) com a lacuna narrada (§9.5, AD-004)
- [ ] Previsões vs PRs: 4 estimativas (Garmin, Riegel, equivalência VDOT, média honesta) para 5K/10K/meia/maratona + PR histórico
- [ ] Curva PMC (CTL/ATL/TSB) da tabela `load` + ACWR do dia
- [ ] Decaimento por distância: pace real (PR) vs ideal (equivalência VDOT corrente) — números, sem gráfico dedicado (§9.1)
- [ ] Tendência VO2max do relógio com selo "estimativa" (hierarquia de métricas AD-005)
- [ ] Sync do preditor de prova do Garmin (`get_race_predictions`, +1 chamada sequencial) + correção da data dos PRs

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| -------- | ------ |
| Cadastro de prova-alvo (`races`) e alvo plotado no gráfico | Decisão do usuário: CRUD de prova pertence à feature do painel Hoje (countdown também o precisa); aqui o painel só plotaria quando existir cadastro |
| Popular a tabela `vdot_tests` | Decisão do usuário: timeline derivada em tempo de leitura dos PRs/provas — mesmo padrão do tipo inferido (workouts-list), zero escrita duplicada |
| Gráfico dedicado de decaimento por distância | §9.1: "v1 mostra o número, sem gráfico dedicado" |
| Card de avaliação IA alimentando o painel | Feature própria da Fase 1 ("Avaliar com IA"); o painel Potencial só consumirá vereditos quando ela existir |
| Calibração de zonas no app / edição do `vdot_zones.json` pela UI | Fase 2 (§6); v1 lê o arquivo como fonte de verdade |
| Histórico de predições do Garmin (evolução do preditor ao longo do tempo) | O painel consome o snapshot "latest" por evento; guardar histórico é feature futura |
| PRs de 1K/milha/LONGEST_RUN na timeline e no "demonstrado" | 1K/milha são marcadores de velocidade, não aeróbicos — VDOT de Daniels não os valida como potencial; LONGEST_RUN é distância, não tempo |
| Seleção de janela da PMC na UI | A API aceita `days` (1–365); a UI v1 fixa 180 dias — seletor é polimento futuro |
| Alertas de carga (ACWR alto, TSB muito negativo) | Painel mostra os números com narrativa honesta; alertas proativos são Fase 2 (§9.1) |
| Previsão por média ponderada dos PRs (algoritmo v2) | Decisão do usuário (15/10/2026): v1 ancora o Riegel no PR de 5K; combinar os PRs das 4 distâncias com pesos (ex.: proximidade à distância-alvo, recência) para gerar a previsão é evolução futura — o painel já isola o cálculo em função pura para viabilizar a troca |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Estimativa "Garmin" | Nova etapa de sync após records: `get_race_predictions()` (snapshot latest) upsertado por `(user_id, event)` | Decisão do usuário (15/10/2026): manter as 4 estimativas do plano; +1 chamada sequencial por sync, dentro do teto `SYNC_MAX_CALLS` (15) | y |
| Fonte dos pontos da timeline | Derivada em tempo de leitura: PRs canônicos datados + provas (`eventType=race`) + teste de calibração do `vdot_zones.json`; nada persistido em `vdot_tests` | Decisão do usuário (15/10/2026); recalibração/testes futuros re-derivar automaticamente; mesmo padrão do tipo inferido | y |
| Alvo da próxima prova plotado | Cortado da v1 (sem CRUD de `races`) | Decisão do usuário (15/10/2026); vai com o painel Hoje | y |
| Referência do Riegel (âncora) | Fixa no PR de 5K: T2 = T1 × (D2/5000)^1.06 com T1 = tempo do PR de 5K; NULL quando não houver PR de 5K (nenhuma âncora inventada) | Decisão do usuário (15/10/2026): mais recente mistura flutuação de forma com escala de distância; maior distância extrapola para baixo (direção mais frágil); menor (1K/milha) não é marcador aeróbico — 5K é a âncora intermediária padrão da literatura, e as projeções vão só para cima (10K→meia→maratona, a direção confiável) | y |
| Correção da data dos PRs | Mapper lê `activityStartDateTimeLocal` (data local wall clock — mesma convenção de `start_time` das atividades), fallback `prStartTimeGmt`; bug atual: key-case `prStartTimeGmt` ≠ `prStartTimeGMT` | Sonda real no banco: payload usa `Gmt` (o mapper lê `GMT`); `prStartTimeLocal` vem NULL; `activityStartDateTimeLocalFormatted` presente em todos os 7 PRs | n |
| Chaves do payload de predições | Eventos mapeados de `time5K`/`time10K`/`timeHalfMarathon`/`timeMarathon` (s) + `calendarDate` para os eventos canônicos | **Sonda real 15/10/2026** (login via tokenstore, 1 chamada sequencial): payload plano `{"calendarDate": "2026-10-15", "time5K": 1165, "time10K": 2447, "timeHalfMarathon": 5437, "timeMarathon": 11989}` — fixture espelha o payload gravado | y |
| VDOT das estimativas por equivalência | Recomputado do `vdot` numérico via `equivalent_time(vdot, d)` — nunca parse das strings de pace do JSON | Strings são exibição; número é fonte. `calculate_vdot`/`equivalent_time` já existem como funções puras em `calibrate_vdot.py` | n |
| Decaimento "ideal" | Pace da equivalência VDOT corrente (50,2) por distância | Régua única e recalculável; mostra exatamente a distância entre o executado e o que o teste atual valida | n |
| Média honesta | Média aritmética das estimativas presentes naquela distância (das 3: Garmin, Riegel, VDOT) | Plano §4.4 "a média honesta"; sem estimativa ausente → média das restantes | n |
| "Demonstrado" | Maior VDOT entre PRs canônicos datados + provas + teste de calibração (hoje: 5K 19:23 → 51,62 pela forma fechada) | §9.5: "melhor VDOT de prova máxima"; o "~53" do plano vem da tabela tabulada de Daniels — a forma fechada de `calibrate_vdot.py` é a fonte da verdade do app e é a mesma que gerou o 50,2 do teste de 10K; só distâncias canônicas (ver Out of Scope) | y |
| Lacuna ("quanto já está liberado") | `gap_pct = vdot_corrente / vdot_demonstrado` exibido com narrativa honesta (§9.5: "o meio é o alvo honesto") | AD-004: faixa honesta, nunca número único mágico | n |
| Dedup prova × PR na mesma data | Prova (`eventType=race`) não vira ponto quando existe PR canônico na mesma data | Sonda real: maratona de Londrina tem PR (3:52:05, distância certificada) E atividade (3:54:43, GPS continuou após a chegada) — o PR é o resultado certificado; dois pontos iguais na mesma data são ruído | n |
| Janela da PMC | `days` default 180 (1–365; fora → 422); UI fixa em 180 | 182 dias reais de `load`; 180 cobre o histórico sem paginação | n |
| Tendência VO2max | `raw_json.vO2MaxValue` de corridas (running/trail_running) em tempo de leitura — sem nova etapa de sync | Sonda real: 138 corridas com valor (54–56); dado já sincronizado; §4.4 pede a ressalva visual, não fonte nova | n |
| Sem `vdot_zones.json` | HTTP 500 "zonas VDOT não configuradas" (mesma exceção do workouts-list) | O VDOT corrente move previsões, faixa e decaimento — sem ele o painel não existe | n |

**Open questions:** none — todas resolvidas com o usuário ou registradas como premissa acima.

---

## User Stories

### P1: Sync das predições de prova do Garmin ⭐ MVP

**User Story**: Como corredor, quero a estimativa do preditor do Garmin Connect (5K/10K/meia/maratona) sincronizada a cada sync, para compará-la com minhas outras estimativas no painel.

**Why P1**: É 1 das 4 estimativas do plano §4.4; sem ela a tabela de previsões nasce capenga.

**Acceptance Criteria**:

1. WHEN o sync executa THEN o sistema SHALL rodar o passo de predições após o passo de records consumindo exatamente 1 chamada sequencial do orçamento (`get_race_predictions()` snapshot latest), dentro do teto `SYNC_MAX_CALLS`. <!-- event-driven -->
2. WHEN o payload traz um evento válido THEN o upsert SHALL gravar ou atualizar a linha por `(user_id, event)` com `time_s` e `raw_json` preservado; IF um evento não vem no payload THEN a linha existente SHALL permanecer intocada (sem delete — mesma semântica do `upsert_records`). <!-- complex -->
3. IF o passo de predições falha THEN o sync SHALL registrar warning `{tipo: "predictions"}` e continuar os passos seguintes (tolerância herdada do records). <!-- unwanted-behavior -->
4. WHEN o sync conclui THEN o `stats_json` SHALL incluir o contador `predictions`. <!-- event-driven -->

**Independent Test**: Rodar sync com payload falso de predições → linhas upsertadas por evento; reexecutar → mesmas linhas atualizadas sem duplicar; payload sem um evento → linha do evento permanece.

---

### P1: Data dos recordes pessoais (correção do mapper) ⭐ MVP

**User Story**: Como corredor, quero minhas PRs com a data em que aconteceram, para a timeline VDOT e a coluna de PR histórico fazerem sentido.

**Why P1**: O mapper lê `prStartTimeGMT` mas o payload real usa `prStartTimeGmt` — hoje TODAS as PRs têm `pr_date` NULL (sonda real no banco); timeline e coluna PR dependem da data.

**Acceptance Criteria**:

1. WHEN o sync processa um recorde com `activityStartDateTimeLocal` no payload THEN o mapper SHALL gravar `pr_date` como a data local (wall clock) desse timestamp; IF o campo não existe THEN o mapper SHALL usar a data do `prStartTimeGmt`; IF nenhum existe THEN `pr_date` SHALL ficar NULL. <!-- complex -->
2. WHEN um recorde existente é re-upsertado THEN o upsert SHALL atualizar `pr_date` (self-heal: o próximo sync após a correção preenche as datas das PRs atuais). <!-- event-driven -->

**Independent Test**: Fixture espelhando o payload real (com `prStartTimeGmt` e `activityStartDateTimeLocalFormatted`) → `pr_date` preenchido com a data local; payload sem os campos → NULL.

---

### P1: Endpoint `GET /api/potential` ⭐ MVP

**User Story**: Como corredor, quero um endpoint que monte o painel Potencial inteiro a partir do banco, para a UI consumir um payload só.

**Why P1**: Único ponto de leitura do painel; todo cálculo é determinístico em Python (AD-003) e zero Garmin (AD-002).

**Acceptance Criteria**:

1. The system SHALL montar o bloco `vdot` com: corrente (`vdot`, `source`, `test_date` do `vdot_zones.json`), demonstrado (maior VDOT entre PRs canônicos datados, provas e teste de calibração), `gap_pct = corrente/demonstrado` e a timeline de pontos. <!-- ubiquitous -->
2. The system SHALL derivar cada ponto da timeline como `{date, vdot, source, label, distance_m, time_s}` a partir de: PRs canônicos (5K/10K/meia/maratona) com data, provas (`eventType=race`), e o teste de calibração do `vdot_zones.json` — recalculando o VDOT com `calculate_vdot`, nunca lendo coluna pronta. <!-- ubiquitous -->
3. WHEN uma prova (`eventType=race`) tem PR canônico na mesma data THEN o endpoint SHALL excluir o ponto da prova (o PR certificado prevalece — premissa de dedup). <!-- event-driven -->
4. The system SHALL montar o bloco `predictions` com as 4 distâncias canônicas, cada uma com: `garmin_s` (da tabela de predições, NULL quando ausente), `riegel_s` (T2 = T1 × (D2/5000)^1.06 ancorado no PR de 5K, NULL quando não houver PR de 5K), `vdot_s` (`equivalent_time(vdot_corrente, d)`), `average_s` (média das presentes) e `pr_s` com `pr_date` (do `personal_records`, NULL quando ausente). <!-- ubiquitous -->
5. WHILE o parâmetro `days` está em [1, 365] THEN o endpoint SHALL devolver o bloco `pmc` com `points[{date, ctl, atl, tsb, acwr}]` das últimas `days` linhas de `load` (default 180) e os valores do último dia em `current`; IF `days` fora do intervalo THEN o sistema SHALL responder HTTP 422 sem executar query. <!-- complex -->
6. IF não existem linhas em `load` THEN o endpoint SHALL devolver `pmc=null` (estado vazio, não erro). <!-- unwanted-behavior -->
7. The system SHALL montar o bloco `vo2max` com `points[{date, value}]` do `raw_json.vO2MaxValue` das corridas por `start_time` ASC; IF nenhuma corrida tem o campo THEN o bloco SHALL ser `null`. <!-- ubiquitous -->
8. The system SHALL montar o bloco `decay` com, por distância canônica que tenha PR: `real_pace_s` (PR), `ideal_pace_s` (equivalência VDOT corrente) e `delta_pct` — distâncias sem PR ficam de fora (nenhum número inventado). <!-- ubiquitous -->
9. The system SHALL executar este endpoint sem nenhuma chamada à API do Garmin — toda leitura vem do banco próprio (AD-002). <!-- ubiquitous -->
10. IF o `vdot_zones.json` não existe ou está inválido THEN o endpoint SHALL responder HTTP 500 com "zonas VDOT não configuradas" (premissa: sem VDOT corrente não há painel). <!-- unwanted-behavior -->

**Independent Test**: Com fixtures de PRs/predições/load/corridas no banco → payload com todos os bloces e valores pináveis; sem `load` → `pmc=null`; `days=0` → 422; sem `vdot_zones.json` → 500.

---

### P1: Timeline VDOT com faixa honesta ⭐ MVP

**User Story**: Como corredor, quero ver a linha do tempo do meu VDOT com a linha do corrente e a faixa até o demonstrado, para responder "a que distância do meu máximo estou?".

**Why P1**: É o retrato central do painel (§4.4) e a materialização da AD-004 (faixa honesta, nunca número único).

**Acceptance Criteria**:

1. WHEN a UI pede `/potencial` com pontos na timeline THEN ela SHALL renderizar o gráfico: um ponto por entrada (rotulado pelo evento/prova), linha horizontal no VDOT corrente e faixa sombreada entre corrente e demonstrado. <!-- event-driven -->
2. WHEN a timeline renderiza THEN a UI SHALL exibir o valor da lacuna (`gap_pct`) com a narrativa honesta de §9.5 ("você já demonstrou X; o teste atual valida Y — o meio é o alvo honesto"). <!-- event-driven -->
3. IF a chamada à API falha THEN a UI SHALL exibir mensagem de erro na página sem quebrar a navegação. <!-- unwanted-behavior -->
4. WHEN o painel renderiza em 390px THEN todos os blocos SHALL permanecer legíveis sem scroll horizontal (padrão do workouts-list). <!-- event-driven -->

**Independent Test**: Abrir `/potencial` com dados reais: pontos de out/2024 a out/2026, linha em 50,2, faixa até ~53, lacuna ~95%; recarregar → mesmos valores (determinístico).

---

### P1: Previsões vs PRs (tabela das 4 estimativas) ⭐ MVP

**User Story**: Como corredor, quero Garmin, Riegel, equivalência VDOT, média honesta e meu PR lado a lado por distância, para calibrar a expectativa da próxima prova sem acreditar em número único.

**Why P1**: §4.4 "previsões vs PRs" — é o coração anti-"precision theater" do painel (AD-004).

**Acceptance Criteria**:

1. WHEN a UI renderiza o bloco `predictions` THEN ela SHALL exibir a tabela com linhas por distância (5K/10K/Meia/Maratona) e colunas Garmin, Riegel, VDOT, Média honesta e PR (com data). <!-- event-driven -->
2. IF uma estimativa ou o PR é NULL naquela distância THEN a célula SHALL exibir "—" (nenhum número inventado), e a média honesta SHALL considerar só as estimativas presentes. <!-- unwanted-behavior -->

**Independent Test**: Com dados reais: 4 colunas numéricas onde existem, PR 5K 19:23,8 com data; bloquear/derrubar a tabela de predições → coluna Garmin toda "—" e média recalculada.

---

### P1: Curva PMC (CTL/ATL/TSB) ⭐ MVP

**User Story**: Como corredor, quero a curva fitness/fadiga (CTL, ATL, TSB) e o ACWR do dia, para ver o efeito acumulado do treinamento.

**Why P1**: §4.4 "o clássico, porque funciona"; os 182 dias já estão calculados pelo sync (SYNC-22..24) — só expor e renderizar.

**Acceptance Criteria**:

1. WHEN a UI renderiza o bloco `pmc` THEN ela SHALL desenhar CTL e ATL como linhas e TSB como série distinta ao longo da janela, com os eixos rotulados (padrão a803911). <!-- event-driven -->
2. WHEN a UI renderiza o bloco `pmc` THEN ela SHALL exibir os valores do último dia (CTL, ATL, TSB, ACWR) como destaques numéricos; IF `acwr` do último dia é NULL THEN a UI SHALL exibi-lo como "—" (janela de 28d incompleta — honestidade do SYNC-24). <!-- complex -->
3. IF `pmc=null` THEN a UI SHALL exibir estado vazio orientando fazer o primeiro sync (sem erro, sem tela branca). <!-- unwanted-behavior -->

**Independent Test**: Abrir `/potencial` → curva com 182 dias, CTL subindo ao longo do bloco de treino, TSB oscilando; conta nova sem `load` → estado vazio orientando ao sync.

---

### P2: Tendência VO2max do relógio (com ressalva)

**User Story**: Como corredor, quero a linha do VO2max estimado pelo relógio ao longo do tempo, com o selo "estimativa", para comparar tendência sem confundir com teste de campo.

**Why P2**: §4.4 item 5 pede com a ressalva; o dado já está no banco, mas é hierarquicamente inferior a prova/teste (AD-005) — não é o retrato central.

**Acceptance Criteria**:

1. WHEN a UI renderiza o bloco `vo2max` THEN ela SHALL desenhar a linha dos pontos com o selo visual "estimativa do relógio" e a nota de hierarquia (provas/testes > algoritmo — AD-005). <!-- event-driven -->
2. IF `vo2max=null` THEN a UI SHALL omitir o bloco inteiro (não exibe seção vazia). <!-- unwanted-behavior -->

**Independent Test**: Com dados reais: linha 54–56 ao longo de ~138 corridas com selo "estimativa"; conta sem corridas com vO2MaxValue → bloco ausente.

---

### P2: Decaimento de ritmo por distância (números)

**User Story**: Como corredor, quero comparar meu pace real por distância (dos PRs) com o ideal da equivalência VDOT, para ver onde o gap é de execução/especificidade e não de motor.

**Why P2**: §4.4 item 4 / §9.1: entra na v1 como número (tabela), sem gráfico dedicado; alimenta a narrativa "sou 5K–meia, maratona é gap de execução".

**Acceptance Criteria**:

1. WHEN a UI renderiza o bloco `decay` THEN ela SHALL exibir por distância: pace real (PR), pace ideal (equivalência VDOT corrente) e o delta percentual, com sinal e rotulado (ideal mais rápido que real = gap negativo). <!-- event-driven -->
2. IF o delta de uma distância é menor (mais negativo) que o das demais THEN a UI SHALL destacar qual distância tem o maior gap — sem inventar interpretação, só destacar o número. <!-- state-driven -->

**Independent Test**: Com dados reais: maratona com o maior gap negativo (execução), 5K/meia próximos do ideal — números batem com o cálculo manual de `equivalent_time(50.2, d)`.

---

## Edge Cases

- IF um PR canônico está sem data (payload sem nenhum dos timestamps) THEN ele não vira ponto da timeline (não há como plotar) mas permanece elegível ao "demonstrado".
- IF duas entradas da timeline caem na mesma data (ex.: teste de calibração e PR) THEN ambas são pontos (eventos distintos plotáveis lado a lado).
- IF a tabela de predições está vazia (sync antigo ao bugfix, predição nunca sincronizada) THEN a coluna Garmin é "—" e a média honesta usa Riegel + VDOT.
- IF não existe PR de 5K THEN `riegel_s` é NULL em todas as distâncias (âncora ausente, não substituída por outra distância) e a média honesta usa só as estimativas presentes.
- IF `days` maior que o histórico existente THEN o bloco pmc devolve todas as linhas disponíveis (janela pedida, não inventada).
- IF `start_time` de duas corridas empata THEN a ordem dos pontos de VO2max é estável por `id ASC` (determinismo de leitura).
- IF o teste de calibração do `vdot_zones.json` tem data no futuro ou igual a um PR THEN ambos viram pontos; o corrente permanece o `vdot` do arquivo (linha), independente dos pontos.
- IF `distance_m` ou `time_s` de um PR é 0 ou negativo THEN o PR fica fora da timeline e do demonstrado (VDOT indefinido), sem crash.
- WHEN a maratona real tem atividade E PR na mesma data THEN só o PR vira ponto (dedup da premissa) — a atividade segue visível em /treinos.
- IF `training_load` é NULL em todas as atividades THEN `load` não tem linhas e `pmc=null` (estado vazio, não zero).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| POT-01 | P1: Sync predições | Design | Implemented |
| POT-02 | P1: Sync predições | Design | Implemented |
| POT-03 | P1: Sync predições | Design | Implemented |
| POT-04 | P1: Sync predições | Design | Implemented |
| POT-05 | P1: Data dos PRs | Design | Implemented |
| POT-06 | P1: Data dos PRs | Design | Implemented |
| POT-07 | P1: Endpoint /api/potential | Design | Implemented |
| POT-08 | P1: Endpoint /api/potential | Design | Implemented |
| POT-09 | P1: Endpoint /api/potential | Design | Implemented |
| POT-10 | P1: Endpoint /api/potential | Design | Implemented |
| POT-11 | P1: Endpoint /api/potential | Design | Implemented |
| POT-12 | P1: Endpoint /api/potential | Design | Implemented |
| POT-13 | P1: Endpoint /api/potential | Design | Implemented |
| POT-14 | P1: Endpoint /api/potential | Design | Implemented |
| POT-15 | P1: Endpoint /api/potential | Design | Implemented |
| POT-16 | P1: Endpoint /api/potential | Design | Pending |
| POT-17 | P1: Timeline VDOT | Design | Pending |
| POT-18 | P1: Timeline VDOT | Design | Pending |
| POT-19 | P1: Timeline VDOT | Design | Pending |
| POT-20 | P1: Timeline VDOT | Design | Pending |
| POT-21 | P1: Previsões vs PRs | Design | Pending |
| POT-22 | P1: Previsões vs PRs | Design | Pending |
| POT-23 | P1: Curva PMC | Design | Pending |
| POT-24 | P1: Curva PMC | Design | Pending |
| POT-25 | P1: Curva PMC | Design | Pending |
| POT-26 | P2: VO2max | Design | Pending |
| POT-27 | P2: VO2max | Design | Pending |
| POT-28 | P2: Decaimento | Design | Pending |
| POT-29 | P2: Decaimento | Design | Pending |

**Coverage:** 29 total, 29 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] Após sync real, `/potencial` mostra a timeline com os pontos reais (10K out/2024, 5K/meia/maratona 2026, teste out/2026), a linha em 50,2, a faixa até ~51,6 e a lacuna (~97%) com narrativa honesta
- [ ] Tabela de previsões com as 4 estimativas + PR por distância; nenhuma célula inventada ("—" onde não há dado); PRs exibem data (bugfix auto-curado pelo sync)
- [ ] Curva PMC com o histórico real (182 dias) e destaques CTL/ATL/TSB/ACWR do último dia
- [ ] VO2max com selo "estimativa" e decaimento por distância destacando o maior gap (maratona)
- [ ] Zero chamadas à API do Garmin a partir do endpoint de leitura (verificável por código: nenhum import/uso do gateway no domínio `potential/`)
- [ ] Suite de testes do backend verde no Postgres do compose, pinando valores exatos de VDOT/Riegel/equivalência com fixtures
