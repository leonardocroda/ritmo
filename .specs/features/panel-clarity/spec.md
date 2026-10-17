# Painel Clareza (panel-clarity) — Especificação

> Rework dos painéis Potencial e Saúde (Fase 1): PMC migra para a Saúde como seção própria "Carga de treino", cabeçalhos fortes numerados com explicação sempre visível, selo de fonte/método (VDOT·Daniels, Riegel, Garmin, estimativa do relógio) e Potencial em 3 blocos narrativos

## Problem Statement

Os painéis Potencial e Saúde empilham gráficos sem hierarquia nem fronteira: os títulos são uma linha cinza de 14px, os cards são visualmente idênticos e nenhuma seção explica o que é, de onde vem ou por que importa. No Potencial, VDOT (Daniels), VO2max (estimativa do relógio) e Riegel aparecem sem distinção de método — o usuário não sabe qual número é qual; e o PMC (CTL/ATL/TSB), que responde "como estou absorvendo o treino", está perdido num painel cuja pergunta é "qual meu máximo". Na Saúde, as 4 seções atuais não têm começo nem fim identificáveis e não contam a história de como se conectam (decisões do usuário em `.specs/features/panel-clarity/context.md`).

## Goals

- [ ] PMC fora do Potencial e dentro da Saúde como seção própria "Carga de treino" (posição 2: Sono → Carga → Recuperação → Dose-resposta → Equilíbrio)
- [ ] Contrato acompanhando a mudança: bloco `pmc` entra em `GET /api/health/summary` e sai de `GET /api/potential` (junto com o query param `days`)
- [ ] Toda seção dos dois painéis com cabeçalho forte: índice numerado (Saúde, 1–5) + título + subtítulo explicativo sempre visível ("o que é / por que importa")
- [ ] Selo de fonte/método distinguível (VDOT·Daniels, estimativa do relógio, Riegel, Garmin) e legenda por método na tabela de previsões
- [ ] Potencial em 3 blocos narrativos: "Onde estou" / "O que isso prevê" / "O que o relógio estima"
- [ ] Linha-guia no topo de cada painel conectando as seções / a régua de leitura
- [ ] 390px legível sem scroll horizontal (padrão preservado dos painéis anteriores)

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| -------- | ------ |
| Painel Treinos (lista + detalhe) | Avaliado como OK pelo usuário (16/10/2026) — não mexe |
| Painel Hoje (readiness + countdown) | Ainda não existe; herda o padrão de cabeçalho/linha-guia quando nascer (Deferred Ideas do context.md) |
| Novos dados, métricas ou cálculos | Os números continuam exatamente os que o backend já produz — muda a apresentação e a casa do PMC |
| Explicação recolhível ("saiba mais" por seção) | Evolução futura se o subtítulo fixo ficar raso; a v1 não esconde contexto atrás de clique (context.md B) |
| Glossário global / página de aprendizado | Explicações moram no contexto de cada seção — nada centralizado (context.md B) |
| Seletor de janela na UI | Continua fixo (Saúde 60d); o Potencial perde a janela junto com o PMC |
| Alertas proativos de carga (ACWR alto, TSB muito negativo) | Fase 2 (§9.1); a v1 explica, não alerta |
| Avaliação com IA / motor de veredito | Feature própria da Fase 1; sequência definida pelo usuário fora desta spec |
| Correlações avançadas (sono × HRV do dia seguinte × FC do treino) | Continua cortado da v1 (§9.1, spec do health-panel) |
| Reordenamento configurável de seções | Ordem fixa narrada (context.md A); sem drag-and-drop/personalização |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Mecânica do contrato na migração do PMC | Bloco `pmc` (mesma forma: `days`/`points`/`current`) sai de `PotentialOut` e entra em `HealthSummaryOut` como `pmc: PmcBlock \| None`; `/api/potential` perde o query param `days` (era exclusivo da PMC) | Payload espelha o que o painel renderiza (padrão página-composição, 1 round-trip); a Saúde não pode herdar o 500 "zonas VDOT não configuradas" que `/api/potential` responde sem calibração | n |
| Janela da PMC na Saúde | Segue o `days` único da Saúde (7–365, default 60; UI fixa 60) | Janela única é padrão travado do health-panel (spec anterior); 60d cobrem o bloco atual de treino; sem segundo seletor | n |
| Copy das explicações | Texto estático PT-BR nos componentes (sem i18n, sem CMS); a spec pina a cobertura ("o que é / por que importa"), a redação é do design/implementação | Decisão do usuário (context.md B): subtítulo sempre visível, conteúdo mora na própria seção | y |
| Selo de fonte | Badge textual discreto ao lado do título quando o método importa distinguir; estilo visual é discreção do design (tema escuro existente) | Decisão do usuário (context.md B) | y |
| Fronteira de seção | Espaçamento entre seções claramente maior que entre gráficos internos + cabeçalho forte numerado; sem card envolvendo card | Decisão do usuário (context.md D): container aninhado pesa em 390px | y |
| Ordem das seções da Saúde | Sono → Carga de treino → Recuperação → Dose-resposta → Equilíbrio de vida | Decisão do usuário (context.md A): entrada (carga) antes da resposta (HRV/RHR); dose-resposta conecta sono×recuperação; equilíbrio fecha o fio | y |
| Valores intocados | Nenhum recálculo: ctl/atl/tsb/acwr seguem exatamente as linhas de `load`; o gráfico renderiza o mesmo payload de hoje | Fronteira da feature: mudança de casa e de apresentação, não de número | y |
| Estados vazios | PMC null na Saúde → estado vazio da seção orientando sync; estado vazio geral da Saúde passa a incluir `pmc` no check; estado vazio do Potencial recalculado sem pmc | Honestidade dos estados vazios (padrão HLT-19/28 e POT) preservada na nova composição | n |
| Réguas citadas na copy | Textos podem citar as réguas já travadas no payload (piso de sono 7h = `floor_s`, banda REM 21–31% = `rem_band`) — nunca número novo | Fonte única da régua é o backend (assumption do health-panel); a copy não inventa régua | n |
| Verificação de UI sem runner | Sem suite de teste frontend no projeto; ACs de UI verificáveis por inspeção de código + UAT 390px (padrão das features anteriores); ACs de contrato por pytest pinando fixtures | Estado real do repo (frontend/package.json sem vitest/jest); não introduzir runner novo nesta feature | n |

**Open questions:** none — todas resolvidas com o usuário ou registradas como premissa acima.

---

## User Stories

### P1: Contrato — PMC muda para `/api/health/summary` ⭐ MVP

**User Story**: Como corredor, quero a curva de carga no payload da Saúde, para o painel que fala do meu corpo ter a informação de treino que falta.

**Why P1**: A seção "Carga de treino" só existe na Saúde se o dado vier no round-trip único dela; mantê-lo no Potencial acoplaria a Saúde ao 500 de calibração.

**Acceptance Criteria**:

1. WHEN uma requisição `GET /api/health/summary` com `days` em [7, 365] é processada THEN o endpoint SHALL incluir no payload o bloco `pmc` com `{days, points[{date, ctl, atl, tsb, acwr}], current}` derivado das últimas `days` linhas da tabela `load`, na mesma forma que o bloco exposto hoje por `/api/potential`. <!-- event-driven -->
2. IF não existem linhas em `load` THEN o endpoint SHALL devolver `pmc=null` (estado vazio, não erro — mesma semântica de POT-12). <!-- unwanted-behavior -->
3. WHEN uma requisição `GET /api/potential` é processada THEN o endpoint SHALL responder 200 com payload contendo apenas `vdot`, `predictions`, `vo2max` e `decay` — sem o bloco `pmc`. <!-- event-driven -->
4. WHEN uma requisição `GET /api/potential?days=90` (parâmetro morto) é processada THEN o endpoint SHALL responder 200 normalmente, com o parâmetro removido da assinatura e nenhum efeito no payload. <!-- event-driven -->
5. The system SHALL computar o bloco `pmc` de `/api/health/summary` exclusivamente a partir do banco próprio, sem nenhuma chamada à API do Garmin (AD-002). <!-- ubiquitous -->
6. The system SHALL produzir os valores ctl/atl/tsb/acwr idênticos às linhas da tabela `load` já computadas pelo sync — migração de casa, não de cálculo (nenhum número recalculado). <!-- ubiquitous -->

**Independent Test**: pytest com fixtures de `load` → health summary traz `pmc` com valores pinados e `days` refletindo a janela; sem `load` → `pmc=null`; `/api/potential` → payload sem `pmc`; `?days=90` no potencial → 200 sem efeito.

---

### P1: Seção "Carga de treino" na Saúde ⭐ MVP

**User Story**: Como corredor, quero a curva CTL/ATL/TSB com ACWR numa seção própria e explicada da Saúde, para entender quanta carga estou impondo e se o corpo tem chance de absorver.

**Why P1**: É a migração pedida pelo usuário — o PMC responde "como estou absorvendo o treino" (§4.5), não "qual meu máximo" (§4.4).

**Acceptance Criteria**:

1. WHEN a página `/saude` renderiza com `pmc != null` THEN a UI SHALL exibir a seção "Carga de treino" na posição 2 (entre Sono e Recuperação) com o gráfico CTL/ATL/TSB e os destaques numéricos do último dia (CTL, ATL, TSB, ACWR), reutilizando o componente de curva PMC existente. <!-- event-driven -->
2. WHEN a seção Carga de treino renderiza THEN ela SHALL exibir subtítulo sempre visível explicando o que são fitness (CTL), fadiga (ATL) e forma (TSB) e por que importa (carga acima da que o corpo absorve compromete recuperação e adaptação). <!-- event-driven -->
3. IF `pmc=null` THEN a UI SHALL exibir a seção Carga de treino com estado vazio orientando o primeiro sync (sem gráfico quebrado — mesma semântica dos outros blocos, HLT-19). <!-- unwanted-behavior -->
4. IF o `acwr` do último dia é NULL THEN o destaque SHALL exibir "—" (janela de 28d incompleta — honestidade do SYNC-24 preservada). <!-- unwanted-behavior -->
5. WHEN o estado vazio geral da Saúde é avaliado THEN o check SHALL incluir o bloco `pmc` — painel "vazio" somente com sono, HRV, RHR, estresse e PMC todos ausentes; com PMC presente o painel renderiza. <!-- event-driven -->

**Independent Test**: Abrir `/saude` com dados reais → seção 2 "Carga de treino" com a curva de 60 dias e destaques do último dia; conta sem `load` → estado vazio da seção; conta só com `load` → painel renderiza apenas a seção Carga com dados.

---

### P1: Cabeçalhos fortes e explicação em todas as seções da Saúde ⭐ MVP

**User Story**: Como usuário, quero identificar onde cada seção começa, que pergunta ela responde e por que devo levar em conta, para não me perder num mar de gráficos.

**Why P1**: É a queixa central do usuário sobre a Saúde ("não está fácil identificar onde começa uma coisa e termina outra" — context.md D).

**Acceptance Criteria**:

1. WHEN a página `/saude` renderiza THEN cada uma das 5 seções (Sono, Carga de treino, Recuperação, Dose-resposta, Equilíbrio de vida) SHALL exibir cabeçalho com índice numerado (1–5), título e subtítulo explicativo sempre visível (1–2 linhas: o que a seção mostra e por que importa). <!-- event-driven -->
2. WHEN os cabeçalhos renderizam THEN cada seção SHALL indicar no subtítulo a pergunta que responde (Sono: durmo o suficiente para absorver o treino?; Carga: quanta carga imponho?; Recuperação: como o corpo responde?; Dose-resposta: o que dormir mal custa?; Equilíbrio: a base sustenta o treino?). <!-- event-driven -->
3. WHEN duas seções adjacentes renderizam THEN o espaçamento visual entre elas SHALL ser claramente maior que o espaçamento entre gráficos dentro da mesma seção (fronteira identificável sem container aninhado). <!-- event-driven -->
4. WHEN a página renderiza em 390px THEN todos os blocos SHALL permanecer legíveis sem scroll horizontal (padrão dos painéis anteriores). <!-- event-driven -->
5. IF a chamada à API falha THEN a UI SHALL exibir mensagem de erro inline sem quebrar a navegação (comportamento existente preservado). <!-- unwanted-behavior -->

**Independent Test**: Abrir `/saude` em 390px → as 5 seções numeradas distinguíveis de relance, cada subtítulo visível sem interação; derrubar o backend → mensagem inline.

---

### P1: Potencial em blocos narrativos com selo de fonte ⭐ MVP

**User Story**: Como corredor, quero o Potencial organizado em 3 blocos que contam a história (onde estou → o que isso prevê → o que o relógio estima), cada um explicando método e fonte, para saber o que é VDOT, o que é Riegel e o que é estimativa do relógio.

**Why P1**: Resolve "não sei onde é vdot, onde é vo2max do garmin, onde é riegel" (context.md) — a confusão de conceitos do painel.

**Acceptance Criteria**:

1. WHEN a página `/potencial` renderiza THEN o conteúdo SHALL estar organizado em 3 blocos nesta ordem: "Onde estou" (lacuna + timeline VDOT), "O que isso prevê" (previsões vs PRs + decaimento por distância), "O que o relógio estima" (VO2max, quando existir). <!-- event-driven -->
2. WHEN o bloco "Onde estou" renderiza THEN ele SHALL exibir subtítulo sempre visível explicando: o que é VDOT (régua de equivalência de Daniels — tempo numa distância → capacidade aeróbica), o que é o corrente (último teste calibrado) e o demonstrado (melhor prova máxima), e o que a lacuna % significa. <!-- event-driven -->
3. WHEN o bloco "O que isso prevê" renderiza THEN a tabela SHALL identificar cada método de forma distinguível com sua fonte: Garmin (preditor do Garmin Connect), Riegel (extrapolação ancorada no PR de 5K), VDOT (equivalência de Daniels do teste corrente) e média honesta (média das estimativas presentes) — legenda por método, além do nome da coluna. <!-- event-driven -->
4. WHEN o decaimento por distância renderiza THEN ele SHALL exibir explicação sempre visível do que compara (pace real dos PRs vs pace ideal da equivalência VDOT corrente) e por que importa (revela gap de execução/especificidade, não de motor). <!-- event-driven -->
5. WHEN o bloco "O que o relógio estima" renderiza THEN ele SHALL manter o selo "estimativa do relógio" e a nota de hierarquia (provas/testes > algoritmo — AD-005) sempre visíveis. <!-- event-driven -->
6. A página `/potencial` SHALL exibir apenas os blocos "Onde estou", "O que isso prevê" e "O que o relógio estima" — nenhuma seção de carga/PMC. <!-- ubiquitous -->
7. IF `vo2max=null` THEN o bloco "O que o relógio estima" SHALL ficar ausente (POT-27 preservado); IF `decay=[]` THEN o sub-bloco decaimento SHALL ficar fora do bloco "O que isso prevê". <!-- unwanted-behavior -->
8. IF a timeline tem ≤1 ponto, `vo2max=null` e `decay` vazio THEN a UI SHALL exibir o estado vazio orientando o sync (check recalculado sem o bloco pmc). <!-- unwanted-behavior -->
9. WHEN a página renderiza em 390px THEN todos os blocos SHALL permanecer legíveis sem scroll horizontal. <!-- event-driven -->

**Independent Test**: Abrir `/potencial` com dados reais → 3 blocos na ordem, nenhuma seção de carga; só com a tela, o usuário consegue dizer o que é cada número e de onde vem; conta vazia → estado vazio orientando sync.

---

### P2: Linha-guia de leitura no topo dos painéis

**User Story**: Como usuário, quero uma linha no topo de cada painel conectando as seções em uma frase, para saber como as infos se ligam antes de mergulhar nos gráficos.

**Why P2**: Atende "como as infos se conectam" (context.md) sem custo de tela — o fio condutor em 1 linha; hierarquia abaixo da explicação por seção.

**Acceptance Criteria**:

1. WHEN a página `/saude` renderiza THEN a UI SHALL exibir linha-guia sempre visível no topo conectando as 5 seções em uma frase (o fio: o treino impõe carga → o corpo responde → o sono decide o custo → o estilo de vida sustenta). <!-- event-driven -->
2. WHEN a página `/potencial` renderiza THEN a UI SHALL exibir linha-guia sempre visível no topo com a pergunta do painel (qual meu máximo e a que distância dele estou?) e a régua de leitura (provas/testes > estimativas — AD-005). <!-- event-driven -->

**Independent Test**: Abrir cada página → a linha-guia aparece acima da primeira seção, sem interação.

---

## Edge Cases

- IF `GET /api/potential` recebe `?days=90` (parâmetro morto) THEN responde 200 normalmente — query não declarado é ignorado; nenhuma validação nova herda o espaço do parâmetro.
- IF `pmc` existe mas sono/HRV/RHR/estresse não THEN `/saude` renderiza apenas a seção Carga de treino com dados — painel não-vazio (o estado vazio geral exige todos os blocos ausentes).
- IF uma estimativa da tabela de previsões é NULL THEN a célula exibe "—" e a média honesta usa só as presentes (POT-22 preservado — a legenda por método não muda o contrato de dado).
- IF um bloco interno é null (sono, HRV, RHR) THEN o estado vazio daquele bloco segue exibido dentro da seção (HLT-19) — o cabeçalho forte não substitui os estados vazios por bloco.
- IF a copy explica uma régua THEN o valor citado é o do payload (piso `floor_s` 25200, banda `rem_band` 21–31) — a UI não hardcoda régua nova.
- IF duas seções adjacentes têm quantidades muito diferentes de gráficos THEN a fronteira continua legível (o espaçamento entre seções é fixo, não proporcional ao conteúdo).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| CLR-01 | P1: Contrato PMC | Design | Implementing |
| CLR-02 | P1: Contrato PMC | Design | Implementing |
| CLR-03 | P1: Contrato PMC | Design | Pending |
| CLR-04 | P1: Contrato PMC | Design | Pending |
| CLR-05 | P1: Contrato PMC | Design | Implementing |
| CLR-06 | P1: Contrato PMC | Design | Implementing |
| CLR-07 | P1: Seção Carga de treino | Design | Implementing |
| CLR-08 | P1: Seção Carga de treino | Design | Implementing |
| CLR-09 | P1: Seção Carga de treino | Design | Implementing |
| CLR-10 | P1: Seção Carga de treino | Design | Implementing |
| CLR-11 | P1: Seção Carga de treino | Design | Implementing |
| CLR-12 | P1: Cabeçalhos Saúde | Design | Implementing |
| CLR-13 | P1: Cabeçalhos Saúde | Design | Implementing |
| CLR-14 | P1: Cabeçalhos Saúde | Design | Implementing |
| CLR-15 | P1: Cabeçalhos Saúde | Design | Implementing |
| CLR-16 | P1: Cabeçalhos Saúde | Design | Implementing |
| CLR-17 | P1: Potencial narrativo | Design | Pending |
| CLR-18 | P1: Potencial narrativo | Design | Pending |
| CLR-19 | P1: Potencial narrativo | Design | Implementing |
| CLR-20 | P1: Potencial narrativo | Design | Implementing |
| CLR-21 | P1: Potencial narrativo | Design | Pending |
| CLR-22 | P1: Potencial narrativo | Design | Pending |
| CLR-23 | P1: Potencial narrativo | Design | Pending |
| CLR-24 | P1: Potencial narrativo | Design | Pending |
| CLR-25 | P1: Potencial narrativo | Design | Pending |
| CLR-26 | P2: Linha-guia | Design | Implementing |
| CLR-27 | P2: Linha-guia | Design | Pending |

**Coverage:** 27 total, 27 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] `/potencial`: 3 blocos na ordem decidida, sem PMC; só com a tela, o usuário distingue VDOT (Daniels) de VO2max (estimativa do relógio) e sabe de onde vem cada estimativa (Garmin/Riegel/VDOT/média honesta)
- [ ] `/saude`: 5 seções numeradas distinguíveis de relance, cada subtítulo visível sem interação, fio condutor no topo; PMC na posição 2 com os mesmos valores de antes
- [ ] Contrato: `/api/health/summary` traz `pmc` (ou `null`) na janela da Saúde; `/api/potential` sem `pmc` e sem `days` — pytest verde pinando fixtures (testes de PMC migram de `test_potential_api.py` para a suite de saúde; nenhum teste deletado sem substituto)
- [ ] 390px sem scroll horizontal nos dois painéis (UAT no celular)
- [ ] Zero chamadas à API do Garmin nos endpoints de leitura (inalterado — verificável por código)
- [ ] Estados vazios honestos preservados: seção Carga com `pmc=null`, painel vazio geral só com tudo ausente, Potencial vazio recalculado sem pmc
