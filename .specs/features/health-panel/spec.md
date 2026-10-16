# Painel Saúde — Especificação

> Feature 4 da Fase 1 · Painel "Saúde" (§4.5): sono vs piso 7h com REM% e regularidade, linhas HRV/RHR, dose-resposta sono→HRV/score e equilíbrio de vida (força 2×, yoga, estresse)

## Problem Statement

O produto mostra treinos e potencial, mas não responde "meu corpo está absorvendo o treino?" (§4.5). Os dados já estão no banco — 62 noites de sono (todas com score, REM%, deitar/acordar), 62 dias de HRV com status, 63 de RHR e estresse, 233 atividades incluindo 62 yoga e 14 força — mas nenhuma tela os expõe. O padrão é visível e medível: 84% das noites abaixo do piso de 7h, REM médio 14,2% (ideal 21–31%), sexta é o buraco semanal (5,74h) e noites <6h cobram HRV média 69,5 vs 81,3 das ≥6h45.

## Goals

- [ ] Endpoint `GET /api/health/summary` montando o painel inteiro a partir do banco próprio (zero chamadas Garmin — AD-002)
- [ ] Sono: duração vs piso 7h, % de noites abaixo do piso, score, REM% com banda ideal 21–31%, regularidade (deitar/acordar em horário local) e padrão por dia da semana
- [ ] HRV (linha da janela + status do último dia) e RHR (linha + baseline da janela)
- [ ] Dose-resposta pessoal: noites <6h vs ≥6h45 → médias de HRV e score da mesma noite (o "juros" que convence a dormir — §4.5)
- [ ] Equilíbrio de vida: força 2×/semana (streak ISO), yoga, estresse médio
- [ ] Página `/saude` com os blocos renderizados, estados honestos e mobile-first 390px

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| -------- | ------ |
| Passos/NEAT (sync de passos + checklist) | Decisão do usuário (16/10/2026): cortado da v1 por custo de infra (não existe tabela nem etapa de sync) — **dado importantíssimo para avaliar a saúde geral**, vira feature própria futura (sync de passos) que o painel Hoje também consumirá; ver Deferred Ideas do context.md |
| Sleep debt acumulado no mês | §9.1 não o inclui na composição v1; o % de noites <7h e o padrão semanal carregam o recado |
| Body Battery | Insumo do card de readiness do painel Hoje (§4.2); no Saúde só na Fase 2 |
| Correlações avançadas (sono × HRV do dia seguinte × FC do treino) | §9.1 corta da v1; o dose-resposta (mesma noite) é o recado que entra |
| Alertas proativos (HRV 2+ dias, sono véspera de treino forte, força em falta) | Fase 2 (§9.1); a v1 mostra números com narrativa honesta, sem disparar alertas |
| Edição manual de sono/metras de vida (input de dados pela UI) | O banco só recebe do sync; input manual é feature futura |
| Seleção de janela na UI | A API aceita `days` (7–365); a UI v1 fixa 60 dias — seletor é polimento futuro |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Estresse médio no painel | Linha + média da janela no bloco de equilíbrio de vida | Decisão do usuário (16/10/2026): dado já sincronizado (63 dias), fecha o §4.5 sem correlações | y |
| NEAT/passos | Cortado da v1; feature futura própria (sync de passos) | Decisão do usuário (16/10/2026); custo de infra hoje (tabela + sync + mapper) vs número sem regra consumindo; importância registrada | y |
| Dose-resposta | 2 buckets `<6h` vs `≥6h45` + faixa neutra (6h–6h45) exibida como nota com N noites | Decisão do usuário (16/10/2026): fiel ao §4.5, contraste máximo; com 62 noites a faixa do meio diluiria o recado | y |
| HRV do dose-resposta | HRV/score da **mesma noite** (mesma data da linha de sono) | A HRV do Garmin é medida durante o sono (última noite, mesma `calendarDate`); a correlação "dia seguinte" está cortada em §9.1 — destacado ao usuário sem objeção | y |
| Streak de força | Semana ISO com ≥2 sessões de `strength_training`; streak de semanas completas + x/y na janela + semana corrente parcial separada | Decisão do usuário (16/10/2026): a regra do plano é "2×/semana" e o alerta da Fase 2 é semanal | y |
| Janela do painel | Único param `days` (default 60, limites 7–365, 422 fora) para todas as séries + derivados; UI fixa 60 | Plano pede "HRV 60d"; sono tem 62 noites — uma janela única simplifica API e UI | n |
| Fuso dos horários de sono | `bed_time`/`wake_time` convertidos para `APP_TIMEZONE` (env nova, default `America/Sao_Paulo`) no backend | O sync grava GMT wall clock naive (01:16–01:27 GMT ≈ 22:20 local) — exibir GMT seria errado; 100% env vars (Fase 1) | n |
| Caminho do endpoint | `GET /api/health/summary` (não `/api/health`) | `/api/health` já é o health check de infra (main.py:52), contrato validado pelo postgres-infra (INFRA-02, `validation.md` + README) — renomear quebraria spec verificada; descoberta no design (16/10/2026) | n |
| Weekday do padrão semanal | Weekday da data da linha de sono (data de acordar) | Convenção já existente no sync (calendarDate); "minha sexta é o buraco" refere-se à noite que virou sexta | n |
| Baseline do RHR | Média da janela exibida como linha de referência | §4.5 "RHR: linha vs baseline" sem baseline persistido no banco; média da janela é régua honesta e recalculável | n |
| Piso de sono e banda REM | Constantes no payload: `floor_s` 25200 (7h) e `rem_band` [21, 31] | Fonte única no backend (§4.5: piso 7h, ideal 21–31%); a UI não inventa régua | n |
| Yoga no checklist | Sessões na janela + média por semana ("mantém como está", §4.5) | Yoga já está no alvo (62 sessões); não precisa de streak agressiva | n |
| Fases do sono | Composição empilhada leve/profundo/REM + despertares no tooltip; **% acordado fora da v1** | Decisão do usuário (16/10/2026): dado 100% presente no banco (`deep_pct`/`light_pct`/`rem_pct`/`awakenings`; a stack soma 100% em todas as 62 noites — `sleepTimeSeconds` do Garmin cobre só as 3 fases); % de tempo acordado exigiria sonda + coluna nova (`awake_pct` + ALTER TABLE) sem garantia de que o payload traga o campo | y |
| Detecção de força/yoga | typeKey exato das `activities` (`strength_training`, `yoga`) em tempo de leitura — nada persistido | Mesmo padrão do tipo inferido (workouts-list): derivação em leitura, zero escrita duplicada | n |

**Open questions:** none — todas resolvidas com o usuário ou registradas como premissa acima.

---

## User Stories

### P1: Endpoint `GET /api/health/summary` ⭐ MVP

**User Story**: Como corredor, quero um endpoint que monte o painel Saúde inteiro a partir do banco, para a UI consumir um payload só.

**Why P1**: Único ponto de leitura do painel; todo número é determinístico em Python (AD-003) e zero Garmin (AD-002).

**Acceptance Criteria**:

1. The system SHALL montar o payload do painel exclusivamente a partir do banco próprio, sem nenhuma chamada à API do Garmin. <!-- ubiquitous -->
2. WHEN uma requisição chega com `days` em [7, 365] THEN o endpoint SHALL responder 200 com os blocos `sleep`, `hrv`, `rhr`, `stress`, `dose_response` e `lifestyle` limitados à janela de `days` dias (default 60 quando ausente). <!-- event-driven -->
3. IF `days` está fora de [7, 365] THEN o endpoint SHALL responder HTTP 422 sem executar query. <!-- unwanted-behavior -->
4. WHEN o painel é montado THEN o bloco `sleep` SHALL conter: `points[{date, duration_s, score, rem_pct, deep_pct, light_pct, awakenings, bed_local, wake_local}]` por noite ASC, `floor_s` (25200), `below_floor` (`nights` e `pct` das noites abaixo do piso na janela), `rem_band` [21, 31], `weekday_pattern` com 7 entradas `{weekday, avg_duration_s, nights}` e `regularity` com horários médios de deitar/acordar em minutos locais (`avg_bed_min`, `avg_wake_min`). <!-- ubiquitous -->
5. The system SHALL converter `bed_time`/`wake_time` para o fuso configurado em `APP_TIMEZONE` (env nova, default `America/Sao_Paulo`) antes de expor `bed_local`/`wake_local` — o GMT armazenado nunca é exposto como horário local. <!-- ubiquitous -->
6. The system SHALL montar o bloco `hrv` com `points[{date, value, status}]` ASC e `current` (`value` e `status` do último dia com dado). <!-- ubiquitous -->
7. The system SHALL montar o bloco `rhr` com `points[{date, value}]` ASC e `baseline` (média da janela, 1 casa decimal). <!-- ubiquitous -->
8. The system SHALL montar o bloco `stress` com `points[{date, avg}]` ASC e `avg_window` (média da janela, 1 casa decimal). <!-- ubiquitous -->
9. The system SHALL montar `dose_response` com os buckets `short` (`duration_s < 21600`) e `adequate` (`duration_s >= 24300`), cada um com `{nights, avg_hrv, avg_score}` cruzando sono↔HRV/score **da mesma data**, além de `neutral_nights` (noites 6h–6h45 fora da comparação); média de bucket sem noites é NULL. <!-- ubiquitous -->
10. The system SHALL montar `lifestyle` com `strength` `{streak_weeks, weeks_hit, weeks_total, current_week_sessions}` e `yoga` `{sessions, per_week_avg}` derivados das `activities` por typeKey em tempo de leitura. <!-- ubiquitous -->
11. IF um domínio de saúde está vazio na janela THEN o bloco correspondente SHALL ser `null` (sono/HRV/RHR/estresse) e o `dose_response` SHALL manter os buckets com `nights=0` e médias `null` (estado vazio, não erro). <!-- unwanted-behavior -->
12. WHILE a streak de força é calculada THEN o sistema SHALL contar semanas ISO completas consecutivas com ≥2 sessões terminando na última semana completa (mesmo que exceda a janela), limitar `weeks_hit`/`weeks_total` à janela e reportar a semana corrente em andamento separadamente em `current_week_sessions` (parcial, nunca quebra a streak). <!-- state-driven -->

**Independent Test**: Com o banco real → payload com 60 noites de sono, 52/62 abaixo de 7h na série completa, HRV 77,5 médio, dose-resposta 17 vs 27 noites (HRV 69,5 vs 81,3), sexta com 5,74h; `days=6` → 422; conta sem sono → `sleep=null`.

---

### P1: UI Sono (duração vs piso + score + REM% + regularidade + padrão semanal) ⭐ MVP

**User Story**: Como corredor, quero ver meu sono contra o piso de 7h com REM% e regularidade, para enxergar se estou recuperando de verdade.

**Why P1**: É o coração do painel (§4.5) — 84% das noites abaixo do piso é o dado que muda comportamento.

**Acceptance Criteria**:

1. WHEN a UI renderiza o bloco `sleep` THEN ela SHALL exibir o gráfico de duração por noite com a linha de referência do piso (`floor_s`) visível e tooltip com score e REM% da noite. <!-- event-driven -->
2. WHEN a UI renderiza o bloco `sleep` THEN ela SHALL exibir o resumo "X% das noites abaixo do piso" (`below_floor.pct`). <!-- event-driven -->
3. WHEN a UI renderiza o bloco `sleep` THEN ela SHALL exibir o REM% por noite com a banda ideal (`rem_band` 21–31%) visível no gráfico. <!-- event-driven -->
4. WHEN a UI renderiza o bloco `sleep` THEN ela SHALL exibir a regularidade (horários médios de deitar/acordar em horário local) e o padrão por dia da semana (`weekday_pattern`, média por weekday). <!-- event-driven -->
5. WHEN a UI renderiza o bloco `sleep` THEN ela SHALL exibir a composição de fases por noite (leve/profundo/REM empilhados, fechando em 100%) com o número de despertares visível no tooltip. <!-- event-driven -->

**Independent Test**: Abrir `/saude` com dados reais: barras de duração com linha em 7h, ~84% de noites abaixo, REM com banda 21–31% (média real ~14%), deitar ~22:20 local (não 01:20 GMT), sexta como menor média semanal.

---

### P1: UI HRV + RHR ⭐ MVP

**User Story**: Como corredor, quero as linhas de HRV noturna e RHR com seus referenciais, para acompanhar recuperação autonômica ao longo da janela.

**Why P1**: §4.5 "HRV noturno: linha 60d + status; RHR: linha vs baseline" — insumo direto da pergunta do painel.

**Acceptance Criteria**:

1. WHEN a UI renderiza o bloco `hrv` THEN ela SHALL desenhar a linha dos valores e exibir o status do último dia (`current.status` — BALANCED/UNBALANCED/LOW) como destaque textual. <!-- event-driven -->
2. WHEN a UI renderiza o bloco `rhr` THEN ela SHALL desenhar a linha dos valores com a linha de referência do `baseline` visível. <!-- event-driven -->
3. IF `hrv` ou `rhr` é `null` THEN a UI SHALL exibir estado vazio orientando o primeiro sync (sem erro, sem tela branca). <!-- unwanted-behavior -->

**Independent Test**: Abrir `/saude` → HRV 52–103 com status BALANCED/UNBALANCED do último dia; RHR ~44 com baseline da janela; conta vazia → estado vazio orientando sync.

---

### P1: UI Dose-resposta (o gráfico que convence a dormir) ⭐ MVP

**User Story**: Como corredor, quero ver o custo real das noites curtas (HRV/score médios <6h vs ≥6h45), para sentir os juros que meu corpo cobra.

**Why P1**: §4.5: "o gráfico que provou o ponto na análise de saúde... mostrar isso me convence a dormir".

**Acceptance Criteria**:

1. WHEN a UI renderiza `dose_response` THEN ela SHALL exibir os dois buckets lado a lado com `{nights, avg_hrv, avg_score}` de cada um. <!-- event-driven -->
2. WHEN a UI renderiza `dose_response` THEN ela SHALL exibir a nota da faixa neutra (`neutral_nights` noites fora da comparação). <!-- event-driven -->
3. IF a média de um bucket é `null` (bucket sem noites) THEN a célula SHALL exibir "—" (nenhum número inventado). <!-- unwanted-behavior -->

**Independent Test**: Dados reais: `<6h` → 17 noites, HRV 69,5, score 60,2 vs `≥6h45` → 27 noites, HRV 81,3, score 80,2; nota "18 noites fora da comparação"; bucket vazio → "—".

---

### P1: UI Equilíbrio de vida (força + yoga + estresse) ⭐ MVP

**User Story**: Como corredor, quero o checklist de força 2×/semana, yoga e estresse médio, para ver se o corpo tem a base muscular e a calma para absorver o treino.

**Why P1**: §4.5 "equilíbrio de vida"; força 2× é o ponto fraco declarado (14 sessões no histórico) — o painel deve mostrá-lo honestamente.

**Acceptance Criteria**:

1. WHEN a UI renderiza `lifestyle.strength` THEN ela SHALL exibir a streak atual em semanas, as semanas atingidas na janela (`weeks_hit`/`weeks_total`) e as sessões da semana corrente em andamento. <!-- event-driven -->
2. WHEN a UI renderiza `lifestyle.yoga` THEN ela SHALL exibir as sessões na janela e a média por semana. <!-- event-driven -->
3. WHEN a UI renderiza o bloco `stress` THEN ela SHALL exibir a linha da média diária e a média da janela no bloco de equilíbrio de vida. <!-- event-driven -->
4. IF `stress` é `null` THEN a UI SHALL omitir a linha e exibir a média como "—" (sem quebrar o bloco). <!-- unwanted-behavior -->

**Independent Test**: Dados reais: streak baixa e honesta (14 sessões em ~26 semanas), yoga com média ~2,4/semana, estresse médio ~24; conta vazia de estresse → "—".

---

### P2: Estados, erro e responsividade do painel ⭐ MVP

**User Story**: Como corredor no celular, quero o painel legível em 390px e mensagens claras quando algo falha, para confiar no que vejo.

**Why P2**: Padrão já travado nos painéis anteriores (workouts-list, potential-panel); sem ele o painel não é utilizável na LAN do celular.

**Acceptance Criteria**:

1. IF a chamada à API falha THEN a UI SHALL exibir mensagem de erro na página sem quebrar a navegação. <!-- unwanted-behavior -->
2. WHEN o painel inteiro está vazio (nenhum dado de saúde) THEN a UI SHALL exibir estado vazio orientando fazer o primeiro sync. <!-- event-driven -->
3. WHEN o painel renderiza em 390px THEN todos os blocos SHALL permanecer legíveis sem scroll horizontal (padrão dos painéis anteriores). <!-- event-driven -->

**Independent Test**: Derrubar o backend → mensagem inline; `/saude` em viewport 390px → nenhum scroll horizontal.

---

## Edge Cases

- IF as fases de uma noite não somam 100% (±0,5) THEN a composição é exibida como veio, sem normalização (nenhum número ajustado — hoje a série real soma 100,0–100,2%).
- IF a janela contém noites sem HRV THEN essas noites ficam fora do dose-resposta (o cruzamento exige as duas linhas na mesma data) — contadas em `neutral_nights` apenas se caírem na faixa 6h–6h45.
- IF todas as noites da janela estão na faixa neutra THEN ambos os buckets têm `nights=0` e médias `null` (UI exibe "—" e a nota da faixa neutra com o total).
- IF `bed_time`/`wake_time` são NULL em alguma noite THEN a noite entra nos gráficos de duração/score/REM, mas fica fora do cálculo de `regularity` (nenhum horário inventado).
- IF a semana corrente ainda tem 0 sessões de força THEN `current_week_sessions=0` e a streak não é quebrada por ela (semana incompleta não julgada — honesto com quem treina força sábado).
- IF a última semana completa tem <2 sessões THEN a streak é 0 (não herda streak antiga) e `weeks_hit` mostra a realidade da janela.
- IF o fuso `APP_TIMEZONE` é inválido THEN o backend SHALL usar o default `America/Sao_Paulo` em vez de crashar (log de warning).
- IF uma atividade de força/yoga tem `duration_s` nulo THEN ela ainda conta para sessões/semana (presença importa, não duração).
- IF duas noites têm a mesma data (impossível pelo unique constraint) — n/a: o upsert por `(user_id, date)` garante uma linha por noite.
- IF `days` é maior que o histórico existente THEN as séries devolvem tudo que existe (janela pedida, não inventada — padrão do painel Potencial).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| HLT-01 | P1: Endpoint /api/health/summary | - | Pending |
| HLT-02 | P1: Endpoint /api/health/summary | - | Pending |
| HLT-03 | P1: Endpoint /api/health/summary | - | Pending |
| HLT-04 | P1: Endpoint /api/health/summary | Tasks | Verified |
| HLT-05 | P1: Endpoint /api/health/summary | Tasks | Verified |
| HLT-06 | P1: Endpoint /api/health/summary | - | Pending |
| HLT-07 | P1: Endpoint /api/health/summary | - | Pending |
| HLT-08 | P1: Endpoint /api/health/summary | - | Pending |
| HLT-09 | P1: Endpoint /api/health/summary | Tasks | Verified |
| HLT-10 | P1: Endpoint /api/health/summary | Tasks | Verified |
| HLT-11 | P1: Endpoint /api/health/summary | Tasks | Verified |
| HLT-12 | P1: Endpoint /api/health/summary | Tasks | Verified |
| HLT-13 | P1: UI Sono | - | Pending |
| HLT-14 | P1: UI Sono | - | Pending |
| HLT-15 | P1: UI Sono | - | Pending |
| HLT-16 | P1: UI Sono | - | Pending |
| HLT-17 | P1: UI HRV + RHR | - | Pending |
| HLT-18 | P1: UI HRV + RHR | - | Pending |
| HLT-19 | P1: UI HRV + RHR | - | Pending |
| HLT-20 | P1: UI Dose-resposta | - | Pending |
| HLT-21 | P1: UI Dose-resposta | - | Pending |
| HLT-22 | P1: UI Dose-resposta | - | Pending |
| HLT-23 | P1: UI Equilíbrio de vida | - | Pending |
| HLT-24 | P1: UI Equilíbrio de vida | - | Pending |
| HLT-25 | P1: UI Equilíbrio de vida | - | Pending |
| HLT-26 | P1: UI Equilíbrio de vida | - | Pending |
| HLT-27 | P2: Estados e responsividade | - | Pending |
| HLT-28 | P2: Estados e responsividade | - | Pending |
| HLT-29 | P2: Estados e responsividade | - | Pending |
| HLT-30 | P1: UI Sono | - | Pending |

**Coverage:** 30 total, 30 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] `/saude` mostra as 60 noites com linha no piso 7h e o resumo ~84% de noites abaixo; REM com banda 21–31% e média real ~14%
- [ ] Composição de fases (leve ~60% / profundo ~26% / REM ~14%) empilhada por noite com despertares no tooltip — stack fecha em 100%
- [ ] Regularidade em horário local (deitar ~22:20, nunca o GMT de ~01:20) e padrão semanal com sexta como o buraco (5,74h)
- [ ] HRV com status do último dia e RHR vs baseline (~44); estresse médio ~24 no equilíbrio de vida
- [ ] Dose-resposta pina o recado do §4.5: `<6h` (17 noites, HRV 69,5, score 60,2) vs `≥6h45` (27 noites, HRV 81,3, score 80,2) + 18 noites neutras
- [ ] Força com streak honesta (baixa) e semana corrente separada; yoga ~2,4/semana
- [ ] Zero chamadas à API do Garmin a partir do endpoint de leitura (verificável por código: nenhum import/uso do gateway no domínio `health/`)
- [ ] Suite de testes do backend verde no Postgres do compose, pinando os valores acima com fixtures
