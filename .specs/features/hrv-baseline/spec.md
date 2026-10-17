# HRV Baseline Científico Specification

## Problem Statement

O bloco de HRV do painel Saúde plota as noites individuais como uma linha e exibe o status cru da Garmin (BALANCED/UNBALANCED) sem contexto numérico. Não é assim que HRV é avaliado: o status compara a média móvel de 7 dias com uma faixa de referência pessoal — hoje uma noite de 69 ms aparece como BALANCED sem que o painel explique por quê (média 7d de 76 ms dentro da faixa 70–98 ms).

## Goals

- [ ] Gráfico de HRV no modelo científico (Altini/Plews): pontos das noites individuais + linha de média móvel de 7 dias + banda móvel por dia da faixa normal (janela móvel de 60 dias, média ± 0,75 DP)
- [ ] Status calculado localmente e explicável (média 7d vs faixa), substituindo o status cru da Garmin na UI do painel Saúde
- [ ] Tabela com os valores dos últimos 7 dias (data, HRV, média 7d), paginada de 7 em 7 sobre a janela de 60 dias
- [ ] Estado explícito de "coletando linha de base" quando não há dados suficientes

## Out of Scope

Explicitamente excluído. Documentado para prevenir scope creep.

| Feature | Reason |
| --- | --- |
| Replicar a fórmula exata da Garmin | Não é publicada; usamos o método publicado (Altini/Plews — smallest worthwhile change) |
| Status LOW/POOR e regras crônicas da Garmin | Regras proprietárias não publicadas; nosso modelo local tem apenas BALANCED/UNBALANCED |
| Chip "Contexto do dia" no detalhe do treino | Continua usando o status cru da Garmin; superfície fora do painel Saúde, mudança futura |
| Alertas proativos de HRV / correlação sono×HRV | Já cortados da v1 do health-panel (Fase 2) |
| Painel Hoje / readiness score | Feature futura independente (§4.2 do PLANO_PLATAFORMA) |
| Aumentar a janela de exibição além de 60 dias | O gráfico mantém 60 dias corridos, consistente com os demais gráficos do Saúde; ver valores além disso na tabela é P3 (HRV-14) |

---

## Assumptions & Open Questions

Toda ambiguidade está resolvida ou registrada aqui — nada fica silenciosamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Método da faixa normal | Média dos valores disponíveis na janela de 60 dias corridos ± 0,75 × desvio padrão amostral (n−1) | Método publicado do HRV4Training (Altini), ancorado no smallest worthwhile change (Plews et al.); reproduz o comportamento da Garmin com fórmula aberta e testável | y (pesquisa) |
| Banda móvel por dia | Cada dia exibido calcula a própria banda sobre a janela móvel de 60 dias corridos terminando naquele dia; dia com menos de 14 valores na janela fica sem banda | Decisão do usuário (vetou banda plana); reproduz a baseline page do HRV4Training, onde a banda desliza junto com o histórico | y |
| Mínimo de dados por banda | ≥14 valores na janela móvel de 60 dias do dia avaliado | Entre o "aprende desde o começo" do HRV4Training e as ~3 semanas que a Garmin exige; abaixo disso a faixa não é confiável | n |
| Preenchimento de lacunas | A linha de média 7d tem um ponto por dia corrido da janela cuja janela móvel de 7 dias contenha ≥1 valor; dia sem captura é preenchido pela média dos valores disponíveis | Comportamento descrito pelo usuário; nunca inventa leituras | y |
| Janela de exibição | 60 dias corridos terminando na data mais recente com dado (mudança em relação às 60 linhas atuais) | Alinha série, faixa e threshold sob a mesma semântica de dias corridos | n |
| Backfill de saúde | `sync_backfill_health_days` 60 → 120: a exibição de 60 dias precisa de 119 dias de histórico (60 de exibição + 59 de lookback de banda) | Autorizado pelo usuário ("se precisar buscar mais que 60 dias"); a base existente ganha o histórico extra no próximo re-sync completo | y |
| Arredondamento | Exibição com 1 casa decimal; cálculos internos sem arredondamento intermediário | Consistente com baseline de RHR e formatters existentes | n |
| Rótulos de status | BALANCED / UNBALANCED em inglês | Consistência com o relógio e com a prática atual "sem tradução inventada" | n |
| Tabela lista só dias com dado | Sem linhas "—" para dias sem captura | Mantém a tabela informativa; lacunas ficam visíveis no gráfico | n |
| Status cru da Garmin | Sai da UI do painel Saúde e do payload do summary (AD-009 — payload espelha render); continua persistido na tabela `hrv` | Decisão do usuário: o status exibido é 100% local | y |
| ACs afetados do health-panel | HLT-06/HLT-17 (exibição do bloco HRV) são substituídos pelos HRV-01..HRV-15 desta feature; a spec antiga não é editada retroativamente | Specs são registro histórico; o rastro da substituição vive aqui | n |

**Open questions:** none — all resolved or logged above.

---

## User Stories

### P1: Gráfico no modelo científico (noites + média 7d + faixa normal) ⭐ MVP

**User Story**: Como corredor, quero ver minhas noites individuais, a média móvel de 7 dias e a faixa normal no mesmo gráfico, para interpretar o HRV do jeito cientificamente correto.

**Why P1**: É a correção central da feature — o gráfico atual plota o dado errado (noite em vez de média 7d) e não tem faixa de referência.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o painel Saúde carrega com pelo menos 1 dia de HRV THEN o gráfico SHALL exibir um ponto discreto para cada noite individual da janela de 60 dias corridos. <!-- event-driven -->
2. WHEN o painel Saúde carrega com pelo menos 1 dia de HRV THEN a linha SHALL ter um ponto por dia corrido da janela cuja janela móvel de 7 dias contenha pelo menos 1 valor, onde o valor do ponto é a média dos valores disponíveis na janela de 7 dias corridos terminando naquele dia. <!-- event-driven -->
3. IF a janela móvel de 7 dias de um dia corrido não contém nenhum valor THEN o gráfico SHALL exibir esse dia sem ponto na linha. <!-- unwanted-behavior -->
4. WHERE a janela móvel de 60 dias corridos de um dia exibido contém pelo menos 14 valores THEN o gráfico SHALL exibir, para esse dia, a banda da faixa normal — média ± 0,75 × desvio padrão amostral dos valores da janela móvel daquele dia — atrás da série. <!-- optional-feature -->
5. IF a janela móvel de 60 dias corridos de um dia exibido contém menos de 14 valores THEN o gráfico SHALL exibir esse dia sem banda. <!-- unwanted-behavior -->

**Independent Test**: Semear 119 dias de HRV e conferir pontos + linha contínua + banda deslizando dia a dia na janela de 60; semear 10 dias e conferir ausência de banda.

---

### P1: Status local explicável no card ⭐ MVP

**User Story**: Como corredor, quero um status calculado localmente (média 7d vs faixa) com os números visíveis, para entender por que o dia é BALANCED ou UNBALANCED sem depender da caixa-preta da Garmin.

**Why P1**: O status cru sem contexto é a dor original que abriu esta feature.

**Acceptance Criteria**:

1. WHEN a janela móvel de 60 dias corridos do último dia com dado contém pelo menos 14 valores THEN o card SHALL exibir o status local: BALANCED quando a média 7d desse dia está dentro da banda daquele dia (limites inclusos), UNBALANCED quando fora. <!-- event-driven -->
2. WHEN o status local é exibido THEN o card SHALL exibir junto a média 7d e os limites da banda do último dia com dado, com 1 casa decimal. <!-- event-driven -->
3. IF a janela móvel de 60 dias do último dia com dado contém menos de 14 valores THEN o card SHALL manter o valor da última noite e exibir "coletando linha de base" no lugar do status local. <!-- unwanted-behavior -->
4. A UI do bloco HRV do painel Saúde SHALL exibir apenas o status local, omitindo o status cru da Garmin em todas as superfícies do bloco. <!-- ubiquitous -->

**Independent Test**: Semear 119 dias onde a média 7d do último dia cai fora da banda daquele dia e conferir UNBALANCED; semear 8 dias e conferir "coletando linha de base".

---

### P1: Histórico que sustenta a banda ⭐ MVP

**User Story**: Como corredor, quero que o sync traga histórico suficiente (119 dias), para que a banda móvel tenha janela completa em todos os 60 dias exibidos do gráfico.

**Why P1**: Sem o lookback de 59 dias além da janela, os primeiros dias exibidos teriam banda truncada ou ausente.

**Acceptance Criteria**:

1. WHEN o backfill inicial de saúde executa THEN o sync SHALL buscar pelo menos 119 dias corridos de histórico por tipo de dado (60 de exibição + 59 de lookback de banda). <!-- event-driven -->

**Independent Test**: Configurar backfill de 120 dias, executar sync completo contra a Garmin fake e conferir ≥119 dias de HRV persistidos.

---

### P1: Tabela diária com paginação ⭐ MVP

**User Story**: Como corredor, quero uma tabela com os valores dos últimos 7 dias e paginação para navegar pelos valores mais antigos, para inspecionar cada noite individual.

**Why P1**: Pedida explicitamente; complementa o gráfico com o dado bruto por dia.

**Acceptance Criteria**:

1. WHEN o bloco HRV renderiza com pelo menos 1 dia com dado THEN a tabela SHALL exibir os até 7 dias com dado mais recentes em ordem decrescente, com as colunas Data (PT-BR), HRV e média 7d, valores com 1 casa decimal. <!-- event-driven -->
2. WHEN existem mais de 7 dias com dado THEN a tabela SHALL exibir controles de paginação que avançam de 7 em 7 dias e um indicador de página atual no formato "atual/total" sobre a janela de 60 dias. <!-- event-driven -->
3. IF existem 7 dias com dado ou menos THEN a tabela SHALL exibir as linhas disponíveis sem controles de paginação. <!-- unwanted-behavior -->

**Independent Test**: Semear 30 dias, conferir as 7 linhas mais recentes e navegar até a última página; semear 5 dias e conferir ausência de controles.

---

### P2: Noites fora da faixa destacadas

**User Story**: Como corredor, quero noites fora da faixa com cor diferenciada, para enxergar de relance as quedas/anomalias agudas.

**Why P2**: Valor interpretativo real (Altini destaca supressões), mas o gráfico já comunica a relação com a banda sem isso.

**Acceptance Criteria**:

1. WHERE a faixa normal está presente THEN os pontos das noites fora da faixa (abaixo ou acima) SHALL usar cor diferenciada das noites dentro da faixa. <!-- optional-feature -->

---

### P3: Histórico além de 60 dias

**User Story**: Como corredor, quero paginar além de 60 dias, para revisar valores antigos sem perder o padrão visual atual.

**Why P3**: O endpoint já suporta até 365 dias, mas o caso de uso é raro e a janela científica (faixa normal) é de 60 dias.

**Acceptance Criteria**:

1. WHEN o usuário alcança a última página da janela de 60 dias THEN a UI SHALL carregar valores adicionais até o limite de 365 dias do endpoint. <!-- event-driven -->

---

## Edge Cases

- IF não existe nenhum dado de HRV THEN o bloco SHALL exibir o estado vazio existente (sem gráfico e sem tabela). <!-- unwanted-behavior -->
- WHEN o histórico começa dentro da janela THEN as médias 7d dos primeiros dias SHALL usar os valores disponíveis (janela móvel truncada no início do histórico).
- WHEN o histórico total é menor que o lookback (primeiro sync de uma base nova) THEN os dias cuja janela móvel acumulou menos de 14 valores SHALL ficar sem banda até a janela completar o threshold. <!-- boundary -->
- IF a média 7d é exatamente igual a um limite da faixa THEN o status local SHALL ser BALANCED (limites inclusos). <!-- boundary -->

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------- |
| HRV-01 | P1: Gráfico no modelo científico | Design | ✅ Verified |
| HRV-02 | P1: Gráfico no modelo científico | Design | ✅ Verified |
| HRV-03 | P1: Gráfico no modelo científico | Design | ✅ Verified |
| HRV-04 | P1: Gráfico no modelo científico | Design | ✅ Verified |
| HRV-05 | P1: Gráfico no modelo científico | Design | ✅ Verified |
| HRV-06 | P1: Status local explicável | Design | ✅ Verified |
| HRV-07 | P1: Status local explicável | Design | ✅ Verified |
| HRV-08 | P1: Status local explicável | Design | ✅ Verified |
| HRV-09 | P1: Status local explicável | Design | ✅ Verified |
| HRV-10 | P1: Tabela diária com paginação | Design | ✅ Verified |
| HRV-11 | P1: Tabela diária com paginação | Design | ✅ Verified |
| HRV-12 | P1: Tabela diária com paginação | Design | ✅ Verified |
| HRV-15 | P1: Histórico que sustenta a banda | Design | ✅ Verified |
| HRV-13 | P2: Noites fora da faixa destacadas | - | ✅ Verified |
| HRV-14 | P3: Histórico além de 60 dias | - | Pending |

**ID format**: `HRV-NN` (categoria HRV)

**Status values**: Pending → In Design → In Tasks → Implementing → Verified

**Coverage**: 15 total, 13 mapped to P1/P2 implementation (P3 HRV-14 deferred), 0 unmapped ⚠️

---

## Success Criteria

- [ ] No exemplo real do usuário (última noite 69, média 7d ~76, faixa ~70–98): card exibe BALANCED com média 7d e banda do dia visíveis, e a linha do gráfico aparece dentro da banda, que desliza dia a dia
- [ ] Após re-sync completo com backfill de 120 dias, todos os dias da janela de exibição têm banda com janela completa
- [ ] O status exibido deriva sempre da regra visível (média 7d vs faixa local) — zero dependência do campo `status` da Garmin na UI do Saúde
- [ ] Tabela pagina pelos 60 dias no mobile 390px sem quebra de layout
- [ ] Suite existente (268 testes) + testes novos passando no Postgres do compose
