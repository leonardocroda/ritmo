# Home Panel Specification

## Problem Statement

A raiz `/` redireciona para `/treinos` (decisão workouts-list + AD-016) e a plataforma não tem um lugar que responde à pergunta diária do corredor: "o que eu faço hoje?". O usuário abre o app e precisa montar o próprio veredito navegando Saúde e Performance — o oposto do produto que se decidiu construir (pivot estratégico: saúde/recuperação em primeiro lugar, Home como veredito diário). A identidade v0.3 (AD-022) já desenhou e aprovou a Home 390px no mock — veredito em frase, porquê em chips, strip de 7 dias, chips que roteiam. Esta spec a materializa; supersede a AD-011 (o painel volta agora, redesenhado, com nome "Home").

## Goals

- [ ] O corredor abre `/` e entende em menos de 5 segundos o estado do corpo e o que fazer hoje — sem scroll
- [ ] Veredito determinístico e explicável: mesma regra, mesma frase, sempre — zero score inventado, zero LLM no caminho diário
- [ ] A Home roteia para os painéis — nunca duplica gráficos nem composição de painel
- [ ] Consistente com os painéis existentes por construção: HRV usa o modelo AD-010, piso de sono o `SLEEP_FLOOR_S` — mesmo dado, mesma resposta

## Out of Scope

Explicitamente excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| Habit tracker / quick-log ("Como você acordou?", pílulas de hábitos) | Adiado pelo usuário (23/10/2026): a feature merece desenho próprio — registro temporal de consumo (hora do café + estimativa de cafeína, álcool, leitura etc.) correlacionado com os outputs automáticos do Garmin. Feature futura; visão registrada na AD-024 |
| Card "Padrão observado" (correlação hábito×sono) | Depende dos dados do habit tracker — adiado junto (decisão do usuário, 23/10/2026) |
| Alertas/notificações | Fase 2 (AD-011: alertas são Fase 2 por design) |
| Semana planejada vs executada | Sem fonte de dados de plano (AD-011) |
| CRUD de provas (UI/CLI para criar/editar corridas) | MVP faz seed da meia (decisão do usuário) e lê; writer é spec futura |
| Registro de resultado da prova (pós-08/11) | O chip some quando a prova passa; o resultado entra pela spec de provas |
| Retrofit de composição dos outros painéis | Spec própria (design-system entregou a pele; composição é outra feature) |
| Veredito por LLM | AD-003 intacta: LLM fica no Avaliar; o veredito diário é regra pura (decisão do usuário, 23/10/2026) |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default  | Rationale | Confirmed? |
| --------------------- | --------------- | --------- | ---------- |
| Motor do veredito | Regras determinísticas em Python (tabela curada de frases), nunca LLM | Decisão do usuário (23/10/2026); testável, zero custo, zero latência | y |
| Habit tracker no MVP | Fora do escopo — feature futura com registro temporal de consumo | Decisão do usuário (23/10/2026); visão detalhada vira AD-024 | y |
| Nome da tab/da raiz | "Home" (não "Hoje") | Decisão do usuário (23/10/2026): "o nome hoje tá ruim, deviamos chamar de home mesmo" | y |
| Countdown da meia | Seed no `init_db`: The Best Açaí, 08/11/2026, 21097.5m, goal null | Decisão do usuário (23/10/2026); prova é fato real, não métrica — seed legítimo | y |
| Eyebrow do card | "Hoje · [dia da semana, data]" permanece — é conteúdo do card, não navegação | A rejeição do usuário foi ao nome da tab; o card fala do dia | n |
| Header da Home | Sem botão de sync — wordmark apenas | AD-023 (UAT do design-system) vence o mock, que é anterior à decisão | y |
| Valor do strip 7 dias | Carga diária via `aggregate_daily_loads` (`garmin/pmc.py`) — a mesma fonte da PMC | Uma fonte de verdade para "carga";CTL/ATL são estados acumulados, não o dia | n |
| Delta de sono | Última noite vs média das 7 noites anteriores | O mock ("Sono 7h42 · +32min") lê como variação pessoal, não vs piso | n |
| Chips de sinal | HRV (valor + status), Sono (duração + delta), Forma (TSB) — 3, do mock | Os 3 sinais que sustentam as frases; RHR/estresse ficam P3 | n |
| Thresholds | Janela de qualidade: TSB > 0 · fadiga: TSB < −10 · carga alta: ACWR > 1.5 · taper: ≤14 dias da prova | Convenções consolidadas de PMC; valores no payload, testáveis | n |
| Rota dos chips | Último treino → `/treinos/{id}` · Volume e countdown → `/performance` | Um dado, um verbo, um destino; carga e previsões moram na Performance | n |
| Previsões digest | Eventos 10K e meia (`average_s`) | A meia é o objetivo ativo; 10K é a referência corrente do usuário | n |
| `/hoje` | Permanece 404 (AD-016 intacta) | A Home mora na raiz; nada revive a rota deletada | y |
| Timezone | "Hoje" = data em `APP_TIMEZONE`, mesmo resolvedor do health (`_resolve_tz`) | Consistência com o painel Saúde; edge de tz inválida espelhado | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Veredito do dia (motor + endpoint) ⭐ MVP

**User Story**: As a corredor, I want abrir `/` e ver uma frase que resume meu estado de recuperação com os sinais que a sustentam so that eu saiba o que fazer hoje sem montar o quebra-cabeça sozinho.

**Why P1**: É o coração do produto pós-pivot — a decisão diária é a interface. Sem veredito não há Home.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN `GET /api/home/today` é chamado com sessão válida THEN the system SHALL responder `HomeOut` com os blocos `verdict`, `signals`, `strip`, `last_activity`, `volume`, `countdown`, `recommendations`, `predictions` — payload 1:1 com o painel, nenhum bloco de outro painel (AD-009). <!-- event-driven -->
2. The sistema SHALL compor o veredito por função pura determinística sobre os sinais (`hrv`, `sleep`, `fitness`) — mesma consulta, mesmo banco ⇒ mesmo veredito; nenhuma chamada de rede, LLM ou aleatoriedade no caminho. <!-- ubiquitous -->
3. WHEN `hrv.status == "UNBALANCED"` AND a última noite dormiu abaixo do piso (7h = `SLEEP_FLOOR_S`) THEN the system SHALL emitir a frase `"Recuperação em dívida"` com tom `alert`. <!-- event-driven -->
4. WHEN `hrv.status == "UNBALANCED"` (sem o agravante de sono) THEN the system SHALL emitir `"Corpo pedindo leve"` com tom `attention`. <!-- event-driven -->
5. WHEN `acwr > 1.5` THEN the system SHALL emitir `"Carga alta — segure o volume"` com tom `attention`. <!-- event-driven -->
6. WHEN `tsb < -10` THEN the system SHALL emitir `"Acúmulo de fadiga"` com tom `attention`. <!-- event-driven -->
7. WHEN `hrv.status == "BALANCED"` AND `tsb > 0` AND a última noite NÃO dormiu abaixo do piso THEN the system SHALL emitir `"Pronto pra qualidade"` com tom `good`. <!-- event-driven -->
8. WHEN nenhum sinal dispara regra específica (incluindo `hrv.status == null`/"coletando") THEN the system SHALL emitir `"Dia comum, sem urgências"` com tom `neutral`. <!-- event-driven -->
9. The motor SHALL avaliar as regras em ordem de prioridade fixa (V1 dívida de recuperação → V2 HRV fora → V3 carga alta → V4 fadiga → V5 janela de qualidade → V6 dia comum) e emitir exatamente o primeiro casamento — uma frase por dia, nunca duas. <!-- ubiquitous -->
10. WHEN um sinal individual é nulo (sem dado) THEN the system SHALL tratá-lo como neutro (nunca dispara regra de bom nem de ruim) e o chip correspondente SHALL renderizar seu estado vazio ("coletando linha de base" para HRV, "sem dado" para sono/forma). <!-- unwanted-behavior -->
11. IF a sessão é inválida/ausente THEN the system SHALL responder 401 antes de qualquer query (padrão dos demais routers). <!-- unwanted-behavior -->
12. WHILE `APP_TIMEZONE` é inválida THEN the system SHALL usar o fuso default com `logger.warning` — o veredito segue no fuso default (mesmo edge do health). <!-- state-driven -->

**Independent Test**: Com fixture de banco (HRV UNBALANCED + sono 6h), `GET /api/home/today` devolve `"Recuperação em dívida"` com chips de HRV e sono; trocando o fixture para HRV BALANCED + TSB +5,2, devolve `"Pronto pra qualidade"`.

---

### P1: Card-veredito + strip de 7 dias (frontend) ⭐ MVP

**User Story**: As a corredor, I want o veredito como card-herói com o porquê em chips e a carga dos últimos 7 dias as barras so that a decisão e a evidência sejam uma coisa só, memorizável.

**Why P1**: A anatomia que o usuário aprovou no mock v0.3 — display 38px, chips com valor+estado, strip neutro com hoje aceso.

**Acceptance Criteria**:

1. WHEN a Home renderiza com veredito THEN the card SHALL usar `bg-raised` (cartão-herói), eyebrow `"Hoje · [dia da semana, data]"`, frase display 38–40px sentence case e chips de sinal (valor + estado + tom semântico), na composição do mock v0.3. <!-- event-driven -->
2. The strip SHALL renderizar exatamente os últimos 7 dias de carga diária (`aggregate_daily_loads`) com barras em neutro e apenas o dia atual aceso em lime, caption `"carga · últimos 7 dias"`. <!-- ubiquitous -->
3. WHEN um dia da janela não tem carga THEN the barra desse dia SHALL renderizar com altura zero (dia de descanso é informação), não omitida. <!-- event-driven -->
4. WHEN o dado de um sinal é anterior à data de hoje THEN o chip SHALL exibir a data do dado (ex.: `HRV 68ms · 21/10`) — nunca apresentar dado antigo como se fosse de hoje. <!-- unwanted-behavior -->
5. WHILE o payload carrega THEN the sistema SHALL renderizar skeletons (blocos pulsando ~1,6s, sem spinner) no lugar do card e do strip (DSN-23). <!-- state-driven -->
6. The Home SHALL renderizar sem botão/ação de sync — sync mora no `/perfil` (AD-023). <!-- ubiquitous -->

**Independent Test**: Abrir `/` com dados no banco: card-herói com frase, 3 chips e strip de 7 barras (hoje lime); throttle/refresh mostra skeletons.

---

### P1: Chips de roteamento + countdown da meia ⭐ MVP

**User Story**: As a corredor, I want três chips com um dado, um verbo e um destino (último treino, volume da semana, countdown da prova) so that a Home me leve pra onde importa sem duplicar painel nenhum.

**Why P1**: "A Home roteia — nunca duplica painéis" é a regra estrutural do produto; os chips são a materialização.

**Acceptance Criteria**:

1. WHEN existe atividade THEN o chip "Último treino" SHALL exibir distância + data relativa + selo `avaliado ✓` quando `evaluated == true` e SHALL rotear para `/treinos/{id}`. <!-- event-driven -->
2. The chip "Volume" SHALL exibir os km da semana corrente vs a média das 4 semanas anteriores (ex.: `42km · +8%`). <!-- ubiquitous -->
3. WHEN a média de 4 semanas é 0 THEN o delta SHALL exibir `—` (nunca divisão por zero, nunca % inventado). <!-- unwanted-behavior -->
4. WHEN `days_left == 0` THEN o chip de countdown SHALL exibir `é hoje`; WHEN `days_left < 0` (prova passada) THEN the system SHALL omitir o chip. <!-- event-driven -->
5. WHEN `init_db` roda sem provas para o usuário 1 THEN the system SHALL semear The Best Açaí (2026-11-08, 21097.5m, goal null); WHEN roda de novo THEN the system SHALL não duplicar o seed (idempotente). <!-- event-driven -->
6. IF não há atividade THEN o chip "Último treino" SHALL ser omitido (não renderiza estado vazio onde o dado não existe). <!-- unwanted-behavior -->

**Independent Test**: `GET /api/home/today` num banco com seed + atividades devolve `countdown.days_left == 16` (hoje 23/10) e `last_activity.evaluated` coerente com a lista de treinos.

---

### P1: Recomendações determinísticas ⭐ MVP

**User Story**: As a corredor, I want 1–3 recomendações por regra, cada uma com o porquê visível, so that eu saiba o que fazer com o veredito sem interpretar métricas.

**Why P1**: Veredito sem ação é diagnóstico sem tratamento — o par frase+recomendação é o produto.

**Acceptance Criteria**:

1. The payload SHALL incluir 1–3 recomendações, cada uma `{texto, why[], tom}`, ordenadas por prioridade fixa, nunca mais de 3. <!-- ubiquitous -->
2. WHEN V5 dispara (janela de qualidade) THEN the system SHALL incluir `"Boa janela pra sessão de qualidade"` com why `HRV · sono · forma`. <!-- event-driven -->
3. WHEN V1 ou V2 dispara THEN the system SHALL incluir `"Priorize recuperação hoje — leve ou descanso"` com why `HRV · sono`. <!-- event-driven -->
4. WHEN V3 ou V4 dispara THEN the system SHALL incluir `"Segure o volume nesta semana"` com why `ACWR · forma`. <!-- event-driven -->
5. WHEN faltam ≤14 dias para a próxima prova THEN the system SHALL incluir `"Semana de prova — redução progressiva (taper)"` com why `prova em N dias` (independente do veredito). <!-- event-driven -->
6. WHEN V6 dispara (dia comum) THEN the system SHALL incluir `"Siga o leve de hoje"` com copy de apoio `"Tudo dentro da faixa"`. <!-- event-driven -->
7. The recomendações SHALL renderizar abaixo da dobra como cards `Recomendação · regra`, cada card com o texto, uma linha de apoio e a tag de why — mesma anatomia do mock. <!-- ubiquitous -->

**Independent Test**: Fixture HRV UNBALANCED devolve veredito "Corpo pedindo leve" + recomendação "Priorize recuperação…"; com a meia a ≤14 dias, a recomendação de taper aparece junto.

---

### P1: Home na raiz + navegação + estados ⭐ MVP

**User Story**: As a corredor, I want a Home como primeira tab (raiz `/`, label "Home") com estados desenhados pro dia comum, banco vazio e erro so that a Home seja o ponto de entrada honesto em qualquer dia.

**Why P1**: Sem rota e nav não há produto; os estados são metade das visitas (mock §05).

**Acceptance Criteria**:

1. WHEN navego em `/` THEN the system SHALL renderizar o painel Home (o redirect para `/treinos` é removido); `/hoje` permanece 404 (AD-016). <!-- event-driven -->
2. The navegação SHALL ter 5 itens com "Home" em primeiro lugar (ícone de casa do mock), os mesmos itens/labels/ícones atuais nas demais posições, tab bar em 5 colunas e top bar com o mesmo padrão de ativo — uma fonte de verdade (`PANELS`). <!-- ubiquitous -->
3. WHEN não existe nenhum dado de saúde/carga/atividade THEN the painel SHALL renderizar estado vazio orientando o primeiro sync com link para `/perfil` (padrão CLR-11), sem veredito. <!-- event-driven -->
4. WHEN o fetch falha THEN the painel SHALL renderizar o estado de erro existente (contrato atual), sem frase de veredito. <!-- event-driven -->
5. The painel SHALL tocar apenas em tokens/tema do design-system (zero cor literal fora de `chartTheme.ts`/`globals.css`), alvos de toque ≥44px e `tabular-nums` em todos os números. <!-- ubiquitous -->

**Independent Test**: `/` mostra a Home com tab ativa "Home" no mobile e no desktop; banco zerado mostra o vazio orientando sync.

---

### P2: Digest abaixo da dobra (volume 10 semanas + previsões)

**User Story**: As a corredor, I want um mini de volume das últimas 10 semanas e uma linha de previsões de prova so that o contexto da temporada esteja a um glance, roteando pra Performance.

**Why P2**: Enriquece sem decidir — o above-the-fold é o MVP; os digests são valor de contexto, não de decisão.

**Acceptance Criteria**:

1. The mini "Volume · últimas 10 semanas" SHALL renderizar barras neutras com a semana corrente acesa em lime e a sentença `Xkm · ±Y% vs média de 4 semanas · ACWR Z` (valores do payload). <!-- ubiquitous -->
2. The digest de previsões SHALL exibir os tempos de 10K e meia (`average_s`) formatados e o link `ver Performance →`. <!-- ubiquitous -->
3. WHEN um evento não tem predição THEN o digest SHALL omitir o evento (sem número inventado). <!-- unwanted-behavior -->

**Independent Test**: Scroll na Home: mini de 10 barras com a corrente acesa + linha "10K 41:15 · meia 1:29:2x · ver Performance →".

---

### P3: Sinais extras no porquê (RHR, estresse, body battery)

**User Story**: As a corredor, I want RHR e estresse como sinais complementares nos chips e no why so that o veredito fique mais sensível a contextos que HRV/sono não pegam.

**Why P3**: Os 3 sinais do mock sustentam as regras MVP; os extras entram quando o uso real pedir mais nuance.

**Acceptance Criteria**:

1. WHEN RHR da última noite está ≥5 bpm acima da linha de base THEN o chip de RHR SHALL entrar no porquê com tom `attention`. <!-- event-driven -->

---

## Edge Cases

Edge cases are usually unwanted-behavior (IF/THEN) or boundary (WHEN) criteria:

- IF sessão ausente THEN 401 antes de qualquer query (HOME: P1-1 AC11)
- WHEN app_timezone inválida THEN fuso default + warning, painel funcional (P1-1 AC12)
- WHEN todos os sinais nulos mas existe dado de sono/histórico THEN veredito `"Dia comum"` com chips em estado vazio — nunca frase de alerta sem evidência
- WHEN dia de prova (`days_left == 0`) THEN chip "é hoje"; WHEN prova passada THEN chip omitido (P1-3 AC4)
- WHEN média de 4 semanas é 0 THEN delta de volume `—` (P1-3 AC3)
- WHEN evento de predição sem dado THEN evento omitido do digest (P2 AC3)
- WHEN semana sem atividades THEN barras do mini com altura zero — dia de descanso é informação (P1-2 AC3)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------- |
| HOME-01 | P1: Veredito (endpoint) | Design | Verified |
| HOME-02 | P1: Veredito (pureza determinística) | Design | Verified |
| HOME-03 | P1: Veredito (regra V1) | Design | Verified |
| HOME-04 | P1: Veredito (regra V2) | Design | Verified |
| HOME-05 | P1: Veredito (regra V3) | Design | Verified |
| HOME-06 | P1: Veredito (regra V4) | Design | Verified |
| HOME-07 | P1: Veredito (regra V5) | Design | Verified |
| HOME-08 | P1: Veredito (regra V6) | Design | Verified |
| HOME-09 | P1: Veredito (prioridade fixa, frase única) | Design | Verified |
| HOME-10 | P1: Veredito (sinal nulo = neutro + chip vazio) | Design | Verified |
| HOME-11 | P1: Veredito (401) | Design | Verified |
| HOME-12 | P1: Veredito (edge timezone) | Design | Verified |
| HOME-13 | P1: Card (composição herói) | Design | Pending |
| HOME-14 | P1: Card (strip 7 dias) | Design | Verified |
| HOME-15 | P1: Card (dia sem carga = barra zero) | Design | Verified |
| HOME-16 | P1: Card (stale mostra data) | Design | Verified |
| HOME-17 | P1: Card (skeletons) | Design | Pending |
| HOME-18 | P1: Card (sem sync na Home) | Design | Pending |
| HOME-19 | P1: Chips (último treino + rota) | Design | Verified |
| HOME-20 | P1: Chips (volume vs média 4s) | Design | Verified |
| HOME-21 | P1: Chips (delta zero = "—") | Design | Verified |
| HOME-22 | P1: Chips (countdown hoje/passada) | Design | Verified |
| HOME-23 | P1: Chips (seed idempotente da meia) | Design | Verified |
| HOME-24 | P1: Chips (sem atividade = chip omitido) | Design | Verified |
| HOME-25 | P1: Recomendações (1–3, shape + prioridade) | Design | Verified |
| HOME-26 | P1: Recomendações (R1 qualidade) | Design | Verified |
| HOME-27 | P1: Recomendações (R2 recuperação) | Design | Verified |
| HOME-28 | P1: Recomendações (R3 volume) | Design | Verified |
| HOME-29 | P1: Recomendações (R4 taper ≤14d) | Design | Verified |
| HOME-30 | P1: Recomendações (R5 leve) | Design | Verified |
| HOME-31 | P1: Recomendações (card abaixo da dobra) | Design | Pending |
| HOME-32 | P1: Rota (Home em `/`, `/hoje` 404) | Design | Pending |
| HOME-33 | P1: Nav (5 itens, Home 1ª) | Design | Pending |
| HOME-34 | P1: Estados (vazio orientando sync) | Design | Pending |
| HOME-35 | P1: Estados (erro) | Design | Pending |
| HOME-36 | P1: Tokens/44px/tabular-nums | Design | Pending |
| HOME-37 | P2: Mini volume 10 semanas | - | Verified |
| HOME-38 | P2: Digest previsões | - | Pending |
| HOME-39 | P2: Predição ausente omitida | - | Pending |
| HOME-40 | P3: RHR no porquê | - | Pending |

**Coverage:** 40 total, 36 mapped to P1/P2 stories, 4 mapped to P3 (P3 é nice-to-have) ⚠️ 0 unmapped

---

## Success Criteria

How we know the feature is successful:

- [ ] `GET /api/home/today` devolve o mesmo veredito para o mesmo estado de banco (teste de determinismo: duas execuções, payload idêntico)
- [ ] O status de HRV da Home é idêntico ao do painel Saúde para a mesma data — mesma função AD-010, não reimplementação (teste de consistência)
- [ ] `git grep -n "redirect" -- frontend/src/app/(app)/page.tsx` → vazio (raiz é a Home)
- [ ] `git grep -nE "#[0-9A-Fa-f]{6}" -- frontend/src/components/home` → vazio (só tokens)
- [ ] `git grep -n "Carregando" -- frontend/src/app/(app)/page.tsx frontend/src/components/home` → vazio (skeletons)
- [ ] Suite backend verde com testes novos: cada regra V1–V6 ≥1 teste, cada recomendação R1–R5 ≥1 teste, seed idempotente ≥1 teste, 401 ≥1 teste, timezone edge ≥1 teste
- [ ] Lint + build do frontend verdes com a Home compondo em 390px sem scroll acima da dobra (veredito + chips + strip visíveis)
- [ ] UAT visual do usuário contra o mock v0.3 (o "olho" dele é o critério final de aceite)
