# Alerta de degradação por tênis — Specification

## Problem Statement

O corredor não percebe quando um tênis está degradado (Cornwall 2017). Com os dados de tenis (quilometragem), tenis-running-dynamics (GCT/passada/oscilação por volta) e tenis-analise-comparativa (perfil, EF, HR drift), esta feature entrega sinais de degradação por tênis: compara primeiros ~100 km vs últimos ~50 km, sempre ritmo-pareado, com gate de mix de tipos. É **alerta de sinais, não veredito** — o corredor decide se aposenta o tênis.

## Goals

- [ ] Baseline de degradação por tênis: primeiros ~100 km vs últimos ~50 km, ritmo-pareado
- [ ] Gate de mix de tipos: não comparar tiro com rodagem (confounding de seleção)
- [ ] Sinais de degradação: ΔGCT, Δoscilação vertical, Δcadência, ΔEF (velocidade/FC), ΔHR drift, Δ feel-RPE — quando houver dado
- [ ] Resultado: "sinais, não veredito" — lista de sinais acionados + confiança, nunca "aposente" ou "continue" automático
- [ ] Cálculo puro, endpoint de leitura, depende de A (perfil/confiança) e B (running dynamics)

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Notificação ativa de vida útil (badge na Home) | Feature E do tenis — aguarda decisão futura |
| Recomendação automática de aposentadoria ("aposente este tênis") | "Sinais, não veredito" — decisão é do corredor |
| UI de alerta de degradação (tela, card, notificação push) | Sem demanda de UI nesta entrega |
| Sync contínuo para atualizar km em tempo real | Fora do escopo (D não entra) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Janela de baseline | Primeiros ~100 km vs últimos ~50 km de cada tênis | Contexto tenis: "baseline primeiros ~100 km vs últimos ~50 km" | y (usuário aceitou recomendada) |
| Ritmo-pareado | Comparar apenas dentro de mesma banda de pace + tipo de treino | Van Hooren 2024: GCT só comparável a ritmo pareado; evita confounding | y (usuário aceitou recomendada) |
| Gate de mix de tipos | Não comparar tipos de treino diferentes na mesma linha de baseline | Corrida fácil ≠ tiro; o tênis age diferente em cada um | y |
| Sinais de degradação | ΔGCT, Δoscilação vertical, Δcadência, ΔEF, ΔHR drift, Δ feel-RPE | Do contexto tenis; cada sinal quando houver dado | y (usuário aceitou recomendada) |
| "Sinais, não veredito" | O endpoint lista sinais acionados + confiança; NÃO diz "aposentar" | O corredor decide; evita falso positivo de modelo simples | y |
| Fonte dos dados | Banco próprio (tenis + A + B) | 100% leitura do banco (AD-002), zero Garmin em tempo de análise | y |
| Ejecução | Cálculo puro, endpoint de leitura, reprodutível por tênis | Análise sob demanda | y |

**Open questions:** none — todas resolvidas acima.

---

## User Stories

### P1: Baseline primeiros ~100 km vs últimos ~50 km ⭐ MVP

**User Story**: Como corredor, quero ver como meu tênis se comporta nos primeiros ~100 km versus os últimos ~50 km, para perceber se ele está degradando com o uso.

**Why P1**: É o núcleo do alerta de degradação — comparação temporal dentro do mesmo tênis.

**Acceptance Criteria** (EARS):

1. WHEN o usuário consulta degradação de um tênis THEN o sistema SHALL ordenar as corridas do tênis por data e separar em janela inicial (primeiros ~100 km acumulados) e janela final (últimos ~50 km acumulados).
2. IF o tênis tem menos de ~150 km totais THEN o sistema SHALL retornar "dados insuficientes" para baseline (não há janela final significativa).
3. As janelas SHALL ser definidas por distância acumulada do tênis (km derivada: initial_km + Σ activities.distance_m), não por data.
4. The system SHALL comparar apenas corridas running/trail_running com shoe_id preenchido.

**Independent Test**: criar tênis com 200 km de corridas ordenadas e confirmar divisão ~100 km inicial vs ~50 km final.

---

### P1: Gate de mix de tipos (ritmo-pareado) ⭐ MVP

**User Story**: Como corredor, quero que a comparação de degradação não misture tiro com rodagem, para o sinal não ser falso por mudança de tipo de treino.

**Why P1**: Sem esse gate, uma mudança de tipo de treino parece degradação do tênis.

**Acceptance Criteria** (EARS):

1. WHEN comparando janela inicial vs final THEN o sistema SHALL agrupar por tipo de treino inferido + banda de pace (mesma convenção de A).
2. IF não há pares válidos dentro de um tipo × banda THEN aquele grupo SHALL ser omitido do resultado (não comparar tipos diferentes).
3. The system SHALL NUNCA comparar uma corrida de tipo "intervalado" com uma de "fácil" na mesma linha de degradação.

**Independent Test**: criar corridas de tipos diferentes com mesmo tênis e confirmar que tipos diferentes não são comparados.

---

### P1: Sinais de degradação (Δ entre janelas) ⭐ MVP

**User Story**: Como corredor, quero ver quais métricas pioraram da janela inicial para a final, para saber se o tênis está perdendo desempenho.

**Why P1**: É o entregável visível — lista de sinais, não veredito.

**Acceptance Criteria** (EARS):

1. WHEN há dado suficiente THEN o sistema SHALL calcular, para cada sinal disponível, o delta da janela final menos a janela inicial:
   - ΔGCT (ms): tempo de contato com o chão
   - Δoscilação vertical (cm)
   - Δcadência (spm)
   - ΔEF (velocidade / FC média)
   - ΔHR drift (bpm entre metades da corrida)
   - Δ feel-RPE (se o usuário preencheu feel/rpe na atividade)
2. IF um sinal não tem dado em alguma janela (ex.: sem running dynamics de B) THEN aquele sinal SHALL ser omitido do resultado (não inventar zero).
3. Cada sinal SHALL trazer: valor inicial, valor final, delta, direção (piorou/melhorou/estável) e nível de confiança.

**Independent Test**: calcular deltas com fixture de janelas e confirmar omissão de sinais sem dado.

---

### P1: Resultado "sinais, não veredito" ⭐ MVP

**User Story**: Como corredor, quero receber uma lista de sinais com confiança, nunca um veredito automático de "aposentar", para eu decidir.

**Why P1**: Evita falso positivo; a decisão final é humana.

**Acceptance Criteria** (EARS):

1. WHEN o resultado é gerado THEN o sistema SHALL retornar lista de sinais acionados (delta acima do limiar de relevância) com nível de confiança (baixo/médio/alto, mesma convenção de A).
2. The system SHALL NUNCA retornar "aposentar este tênis" ou "continue usando" como conclusão automática.
3. WHEN não há sinal relevante THEN o sistema SHALL retornar lista vazia com confiança (não inventar sinal).

**Independent Test**: verificar que o payload nunca contém veredito binário de aposentadoria.

---

### P2: Limiar de relevância por sinal ⭐

**User Story**: Como corredor, quero que cada sinal tenha seu próprio limiar de "piorou", para não gerar alerta por variação normal.

**Why P2**: Cada métrica tem variabilidade natural diferente.

**Acceptance Criteria** (EARS):

1. WHEN comparando janelas THEN o sistema SHALL considerar um sinal "relevante" apenas se o delta exceder o limiar específico desse sinal (ex.: ΔGCT > X ms, ΔEF > Y %, etc.).
2. Os limiares SHALL ser configuráveis (não hardcoded de forma rígida no negócio) — defaults razoáveis por sinal.
3. IF o delta estiver dentro do limiar THEN o sinal SHALL ser classificado como "estável" (não acionado).

**Independent Test**: alterar limiar de um sinal e confirmar que o acionamento muda.

---

## Edge Cases

- WHEN o tênis tem 0 corridas THEN o resultado SHALL ser vazio com "dados insuficientes", sem erro.
- WHEN running dynamics de B estão ausentes para todas as corridas THEN os sinais de GCT/oscilação/cadência SHALL ser omitidos (não erro).
- WHEN feel/RPE não foi preenchido nas atividades THEN o sinal Δ feel-RPE SHALL ser omitido.
- WHEN o tênis foi aposentado THEN ele SHALL ainda poder ser consultado (dado histórico preservado — sem DELETE no tenis).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TDE-01 | P1: Baseline primeiros ~100 km | Implementing | Verified |
| TDE-02 | P1: Janela final ~50 km | Implementing | Verified |
| TDE-03 | P1: Menos de ~150 km -> dados insuficientes | Implementing | Verified |
| TDE-04 | P1: Ordenar por distância acumulada (não data) | Implementing | Verified |
| TDE-05 | P1: Apenas running/trail_running com shoe_id | Implementing | Verified |
| TDE-06 | P1: Agrupar por tipo × banda (gate de mix) | Implementing | Verified |
| TDE-07 | P1: Omitir grupo sem pares válidos | Implementing | Verified |
| TDE-08 | P1: Nunca comparar tipos diferentes | Implementing | Verified |
| TDE-09 | P1: Calcular ΔGCT, Δoscilação, Δcadência, ΔEF, ΔHR drift, Δ feel-RPE | Implementing | Verified |
| TDE-10 | P1: Sinal sem dado -> omitido (não zero) | Implementing | Verified |
| TDE-11 | P1: Cada sinal com valor inicial/final/delta/direção/confiança | Implementing | Verified |
| TDE-12 | P1: Resultado = sinais + confiança, nunca "aposentar" | Implementing | Verified |
| TDE-13 | P1: Sem sinal relevante -> lista vazia + confiança | Implementing | Verified |
| TDE-14 | P2: Limiar de relevância por sinal configurável | Implementing | Verified |
| TDE-15 | P2: Delta dentro do limiar = "estável" | Implementing | Verified |

**ID format:** `TDE-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 15 total, 15 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Baseline por tênis: primeiros ~100 km vs últimos ~50 km por distância acumulada
- [ ] Gate de mix de tipos: não compara tipo de treino diferente
- [ ] Sinais: ΔGCT, Δoscilação, Δcadência, ΔEF, ΔHR drift, Δ feel-RPE (quando houver dado)
- [ ] Resultado: lista de sinais + confiança, nunca veredito de aposentadoria
- [ ] Sinais sem dado omitidos (não zero inventado)
- [ ] Depende de A (perfil/confiança) e B (running dynamics)
