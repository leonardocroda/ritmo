# Análise comparativa entre tênis — Specification

## Problem Statement

O Ritmo já tem quilometragem por tênis (feature tenis) e running dynamics por volta (feature tenis-running-dynamics), mas ainda não consegue responder "qual tênis me faz correr melhor?". A análise agregada de pace bruto é enganosa por confounding de seleção (Adizero vira tiro, Kayano vira rodagem — o tênis não causa a diferença, o tipo de treino causa). Esta feature entrega comparação pareada entre tênis, fatiada por tipo de treino e banda de pace, com ajuste de running dynamics por ritmo e sinal de confiança, para o corredor decidir com dados, não com achismo.

## Goals

- [ ] Perfil por tênis fatiado por tipo de treino inferido e banda de pace (nunca pace bruto agregado)
- [ ] Comparação pareada (matched runs): pares de corridas com distância e pace próximos (±5%), data livre, tênis diferentes
- [ ] Nível de confiança exibido (baixo/médio/alto) baseado na quantidade de pares válidos — sem gate mínimo rígido para mostrar
- [ ] Running dynamics ajustados por ritmo via resíduo de regressão (depende de tenis-running-dynamics)
- [ ] EF (velocidade/FC) por tênis
- [ ] HR drift por tênis
- [ ] Janela fresco vs fadiga (primeiros km vs últimos km da corrida)
- [ ] Sem UI obrigatória nesta entrega: dados via endpoint + cálculo puro, consumível por UI futura

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Alerta de aposentadoria por degradação (baseline multi-sinal) | Feature C, depende de A |
| UI de comparação de tênis (tela, gráfico, visual lado a lado) | Sem demanda de UI nesta entrega |
| Teste A/B guiado back-to-back (mesma rota, dois tênis alternados) | Ideia futura do contexto; requer UI e fluxo guiado |
| Captura de running dynamics | Feature B (pré-requisito, já especificada separadamente) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Critério de par válido | Distância ±5% e pace ±5%; data livre (não é critério) | Similaridade de desempenho importa mais que proximidade de datas; evita pares perdidos por corrida em dias diferentes | y (usuário decidiu) |
| Gate de confiança | Exibir sempre com qualquer quantidade de pares; sinalizar baixo/médio/alto | Usuário optou por Opção C (confiança sinalizada, não gate rígido) | y (usuário decidiu) |
| Confunding de seleção | Fatiar por tipo de treino + banda de pace; nunca pace bruto agregado | Adizero → tiro, Kayano → rodagem; agregado bruto invalida comparação | y (do contexto tenis) |
| Running dynamics ajustados por ritmo | Resíduo de regressão de GCT/passada/oscilação vs pace | Remove o efeito do ritmo na métrica biomecânica | y (do contexto tenis) |
| Fonte dos dados | Banco próprio (splits com running dynamics de B, atividades com shoe_id) | 100% leitura do banco (AD-002), zero Garmin em tempo de análise | y |
| Ejecução | Cálculo puro, endpoint de leitura, sem persistência de resultado salvo cache opcional | Análise sob demanda, reprodutível | y |

**Open questions:** none — todas resolvidas acima.

---

## User Stories

### P1: Perfil por tênis (tipo de treino × banda de pace) ⭐ MVP

**User Story**: Como corredor, quero ver o desempenho médio de cada tênis separado por tipo de treino e banda de pace, para saber se um tênis é realmente melhor ou só era usado em treinos mais fáceis.

**Why P1**: Corrige o confounding de seleção que torna a comparação bruta inútil.

**Acceptance Criteria** (EARS):

1. WHEN o usuário consulta o perfil de um tênis THEN o sistema SHALL agrupar as corridas por tipo de treino inferido (fácil/tempo/limiar/intervalado/repetição/longão/progressivo/prova/outro).
2. DENTRO de cada tipo de treino THEN o sistema SHALL subdividir por banda de pace (ex.: fácil 5:30–6:30/km, limiar 4:00–4:45/km, etc.) com média de pace, FC média, cadência média e contagem de corridas.
3. The system SHALL NUNCA apresentar pace bruto agregado de um tênis sem o fatiamento (confunding de seleção).

**Independent Test**: calcular perfil de um tênis com corridas de tipos diferentes e confirmar agrupamento por tipo × banda.

---

### P1: Comparação pareada (matched runs) ⭐ MVP

**User Story**: Como corredor, quero comparar dois tênis em corridas equivalentes (mesma distância e pace próximos), para ver qual rende melhor em condições similares.

**Why P1**: É o núcleo da análise — comparação em condições controladas.

**Acceptance Criteria** (EARS):

1. WHEN o usuário solicita comparação entre dois tênis THEN o sistema SHALL formar pares de corridas (um de cada tênis) com distância dentro de ±5% e pace médio dentro de ±5%.
2. A data das corridas em um par SHALL ser livre (não há critério de proximidade de datas).
3. WHEN não há pares válidos THEN o sistema SHALL retornar lista vazia com nível de confiança "baixo" e motivo "sem pares suficientes".
4. Cada par SHALL trazer: tênis A, tênis B, distância, pace A, pace B, Δ pace (B − A), FC média A, FC média B, Δ FC.

**Independent Test**: criar 4 corridas (2 tênis × 2 similares) e confirmar formação de pares com Δ correto.

---

### P1: Nível de confiança (baixo/médio/alto) ⭐ MVP

**User Story**: Como corredor, quero saber o nível de confiança de cada comparação, para não basear decisão em poucos dados.

**Why P1**: Evita superestimar diferença com 1 ou 2 pares.

**Acceptance Criteria** (EARS):

1. WHEN a comparação tem < 3 pares válidos THEN o nível de confiança SHALL ser "baixo".
2. WHEN a comparação tem de 3 a 5 pares válidos THEN o nível de confiança SHALL ser "médio".
3. WHEN a comparação tem > 5 pares válidos THEN o nível de confiança SHALL ser "alto".
4. O nível de confiança SHALL acompanhar cada resultado de comparação e cada perfil de tênis.

**Independent Test**: verificar classificação com 2, 4 e 6 pares.

---

### P2: Running dynamics ajustados por ritmo (resíduo de regressão) ⭐

**User Story**: Como corredor, quero ver GCT, passada e oscilação ajustados pelo ritmo da corrida, para saber se um tênis realmente muda minha biomecânica ou só o ritmo muda.

**Why P2**: GCT e passada dependem fortemente do ritmo; sem ajuste, a comparação é enviesada. Depende de B.

**Acceptance Criteria** (EARS):

1. WHEN há running dynamics (GCT/passada/oscilação) de B para as corridas dos tênis THEN o sistema SHALL calcular o resíduo de regressão linear de cada métrica vs pace (por tipo de treino).
2. IF não há dados de running dynamics suficientes (sem colunas preenchidas de B) THEN o sistema SHALL omitir o bloco de running dynamics ajustados e não inventar valores.
3. O ajuste SHALL ser por tipo de treino (mesmo conjunto de corridas do perfil).

**Independent Test**: calcular resíduos com fixture de GCT × pace e confirmar que remove a tendência de ritmo.

---

### P2: EF (velocidade/FC) por tênis ⭐

**User Story**: Como corredor, quero ver o EF (Efficiency Factor = velocidade / FC média) de cada tênis, para comparar eficiência cardiovascular independente do ritmo.

**Why P2**: Métrica estabelecida de eficiência de corrida.

**Acceptance Criteria** (EARS):

1. WHEN houver FC média nas voltas/corridas THEN o sistema SHALL calcular EF = pace (ou velocidade) / FC média por tênis.
2. IF FC média ausente THEN EF SHALL ser null para aquele treino.
3. EF SHALL ser apresentado fatiado por tipo de treino × banda de pace (mesma convenção do perfil).

**Independent Test**: calcular EF de corridas com e sem FC, confirmar null quando ausente.

---

### P2: HR drift por tênis ⭐

**User Story**: Como corredor, quero ver o drift cardíaco (aumento de FC no decorrer da corrida a ritmo constante) de cada tênis, para ver se um tênis cansa mais que outro.

**Why P2**: Drift indica fadiga e eficiência; comparar entre tênis revela diferença de esforço real.

**Acceptance Criteria** (EARS):

1. WHEN houver splits com FC e pace THEN o sistema SHALL calcular drift = FC segunda metade − FC primeira metade (por distância acumulada), apenas para corridas com pace estável (Δ pace ≤ X% entre metades).
2. IF o pace não for estável entre metades THEN o drift SHALL ser omitido para aquela corrida (drift só se interpreta a ritmo constante — AD-005 do tenis).
3. Drift SHALL ser agregado por tênis, fatiado por tipo de treino.

**Independent Test**: calcular drift com fixture de splits FC × pace estável e instável.

---

### P2: Janela fresco vs fadiga ⭐

**User Story**: Como corredor, quero comparar os primeiros ~30% vs últimos ~30% da corrida em cada tênis, para ver qual tênis sustenta o pace melhor no fim.

**Why P2**: Revela degradação de desempenho dentro da própria corrida por tênis.

**Acceptance Criteria** (EARS):

1. WHEN houver splits ordenados THEN o sistema SHALL dividir a corrida em janela inicial (primeiros ~30% da distância) e final (últimos ~30%).
2. Para cada janela SHALL calcular pace médio e FC média.
3. O delta (final − inicial) de pace e FC SHALL ser apresentado por tênis.

**Independent Test**: calcular janelas com fixture de 10 splits e confirmar divisão ~30/30.

---

## Edge Cases

- WHEN dois tênis têm corridas com distância idêntica mas pace diferente (>5%) THEN não formam par (critério de ±5% em ambos).
- WHEN um tênis tem 0 corridas THEN o perfil retorna vazio e confiança "baixa", sem erro.
- WHEN a mesma corrida aparece com os dois tênis (impossível por shoe_id 1:1) THEN não acontece; shoe_id é único por atividade.
- WHEN running dynamics de B estão ausentes para todas as corridas THEN o bloco de running dynamics ajustados é omitido, não erro.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TAC-01 | P1: Perfil por tipo de treino | Implementing | Verified |
| TAC-02 | P1: Subdivisão por banda de pace | Implementing | Verified |
| TAC-03 | P1: Sem pace bruto agregado sem fatiamento | Implementing | Verified |
| TAC-04 | P1: Pares distância ±5% e pace ±5% | Implementing | Verified |
| TAC-05 | P1: Data livre nos pares | Implementing | Verified |
| TAC-06 | P1: Sem pares -> vazio + confiança baixa | Implementing | Verified |
| TAC-07 | P1: Par traz tênis A/B, distância, pace, Δ pace, FC, Δ FC | Implementing | Verified |
| TAC-08 | P2: Confiança <3 = baixo | Implementing | Verified |
| TAC-09 | P2: Confiança 3-5 = médio | Implementing | Verified |
| TAC-10 | P2: Confiança >5 = alto | Implementing | Verified |
| TAC-11 | P2: Resíduo de regressão running dynamics vs pace | Implementing | Verified |
| TAC-12 | P2: Sem running dynamics -> bloco omitido | Implementing | Verified |
| TAC-13 | P2: EF = velocidade / FC média | Implementing | Verified |
| TAC-14 | P2: EF sem FC -> null | Implementing | Verified |
| TAC-15 | P2: HR drift só se pace estável (AD-005) | Implementing | Verified |
| TAC-16 | P2: Janela fresco/fadiga ~30% inicial vs final | Implementing | Verified |
| TAC-17 | P2: Delta pace/FC das janelas por tênis | Implementing | Verified |

**ID format:** `TAC-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 17 total, 17 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Perfil por tênis fatiado por tipo de treino × banda de pace (sem pace bruto agregado)
- [ ] Comparação pareada com pares distância ±5% e pace ±5%, data livre
- [ ] Nível de confiança baixo/médio/alto (<3 / 3–5 / >5 pares)
- [ ] Running dynamics ajustados por ritmo via resíduo de regressão (depende de B)
- [ ] EF, HR drift e janela fresco vs fadiga por tênis
- [ ] Todos os blocos omitidos (não inventados) quando o dado faltar
