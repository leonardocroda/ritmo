# Lista de Treinos + Gráfico de Splits — Especificação

> Feature 2 da Fase 1 · Painel "Treinos": lista + detalhe com gráfico de splits por zona VDOT, métricas de consistência e faixa de contexto

## Problem Statement

O banco tem dados reais validados (garmin-sync: atividades, splits, sono, HRV, RHR), mas não existe tela para vê-los — o produto ainda não demonstra valor. O plano define este painel como a visualização central do produto (§4.3): lista de treinos e um gráfico de splits que "julga pacing à primeira vista", colorido por zona VDOT pessoal.

## Goals

- [ ] Lista de treinos (padrão: corridas) com data, tipo inferido, distância, ritmo, FC e badge "Avaliado"
- [ ] Detalhe com **gráfico de splits**: barras de pace por volta coloridas por zona VDOT (verde=easy, azul=marathon, laranja=threshold, vermelho=interval, roxo=repetition) + linha de FC + relevo por volta
- [ ] Métricas de consistência para corridas ≥8km: equilíbrio de metades, drift cardíaco, fade de cadência, decoupling FC/pace
- [ ] Faixa de contexto no detalhe: sono, HRV, RHR, temperatura média e elevação — só o que existir
- [ ] Navegação dos 4 painéis (Hoje/Treinos/Potencial/Saúde) no header, com placeholders para os painéis futuros
- [ ] Zero chamadas à API do Garmin em qualquer endpoint de leitura (AD-002)

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| -------- | ------ |
| Card de avaliação IA + execução vs intenção no detalhe | Feature própria da Fase 1 ("Avaliar com IA"); aqui só o badge `evaluated` |
| Selo ✅⚠️❌ de veredito na lista | Depende de avaliações existirem (feature "Avaliar com IA") |
| Botão "Gerar story" no detalhe | Fase 2 (§4.3 item 6) |
| Mapa do trajeto, comparação lado a lado | Cortado na v1 (§9.1) |
| Calibração de zonas no app / popular tabela `zones` | Fase 2 (§6); v1 lê `vdot_zones.json` (fonte de verdade) |
| Editar/excluir atividades | Banco próprio é fonte da verdade; exclusão manual fica para depois |
| Busca por nome/filtro por período na lista | Não está no plano §4.3; paginação simples cobre o uso pessoal |
| Acesso via LAN no celular (CORS/IP do compose) | Preocupação de infra pré-existente (CORS_ORIGINS default localhost:3000; `NEXT_PUBLIC_API_URL` aponta localhost) — resolver quando o uso mobile começar |
| Alertas proativos, painel Hoje/Potencial/Saúde de verdade | Features próprias da Fase 1; aqui só placeholders de navegação |
| Re-sync retroativo para preencher cadência/temperatura em voltas antigas | Voltas fora da janela de re-pull ficam sem os campos novos até serem re-sincronizadas naturalmente; métricas omitem o que não existe |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Semântica de cor das barras | Zona VDOT por pace (§4.3 + §9.1 do plano), NÃO o intensityType do `generate_image.py` | O plano pede cor por zona VDOT explicitamente (verde/azul/laranja/vermelho/roxo); §8 chama de "cores por zona do generate_image.py", mas o arquivo validado colore por tipo de passo — prevalece o §4.3 (mais específico e reconfirmado no §9.1) | n |
| Cor da linha de FC | Distinta da cor da zona interval (ex.: rosa/vermelho diferente), legenda rotula ambas | Na imagem validada FC é vermelha (#ef4444); aqui vermelho é a zona interval — colidir confunde a leitura central (pacing) | n |
| Fronteiras entre zonas (gaps no JSON) | Cut points no meio dos limites adjacentes: `cut(easy,marathon)=(easy.ms_max+marathon.ms)/2`, `cut(marathon,threshold)=(marathon.ms+threshold.ms_min)/2`, `cut(threshold,interval)=(threshold.ms_max+interval.ms_min)/2`, `cut(interval,repetition)=(interval.ms_max+repetition.ms)/2`; pace abaixo do primeiro cut → easy; acima do último → repetition | Determinístico e recalculável quando as zonas forem recalibradas; com VDOT 50.2 os cuts são 4:41, 4:29, 4:07 e 3:45/km | n |
| Fonte das zonas na v1 | `vdot_zones.json` via env `VDOT_ZONES_PATH` (default `backend/data/vdot_zones.json`) | Plano §1: "arquivo de zonas como fonte de verdade"; a tabela `zones` é da feature de calibração (Fase 2) | n |
| Cadência por volta | Nova coluna `Split.avg_cadence`; mapper lê `averageRunCadence` (nome aterrissado por sonda real em 14/10/2026, garmin_id 24719288630 — o nome do payload de listagem, `averageRunningCadenceInStepsPerMinute`, NÃO existe no lapDTO) | Plano §9.1 pede fade de cadência; sem a coluna a métrica é incomputável | n |
| Temperatura por volta | Nova coluna `Split.avg_temperature`; mapper lê `averageTemperature`; contexto deriva média ponderada por duração | Plano §4.3 pede "clima" na faixa de contexto; o campo existe no payload de voltas (sonda: 22.0 °C) | n |
| Escala do gráfico | Pace clampado entre 3:00 e 7:00/km (port do `generate_image.py` validado) | Voltas de recuperação/caminhada (>7:00) não podem gerar barras negativas/invisíveis | n |
| Largura das barras | Proporcional à duração da volta (port do validado); eixo X = voltas rotuladas pelo km acumulado | Decisão do usuário (15/10/2026): "pausa de 30s entre tiros não pode ter o mesmo tamanho que um tiro de 3km" | y |
| Metades para consistência | Divisão por distância acumulada: 1ª metade = voltas até somar ≥50% da distância total, 2ª metade = restante (a volta que atravessa o meio conta na 1ª) | Mais honesto que dividir por contagem quando há voltas de tamanho variável (strides, trail); imprecisão do atravessamento é documentada | n |
| Tipo inferido — regras | Prioridade fixa: prova (raw_json eventType.typeKey=="race" ou eventTypeDTO.typeKey=="race") > intervalado (≥2 grupos de voltas consecutivas em zona interval/repetition separados por volta de recuperação: zona easy/marathon OU intensityType REST/RECOVERY/WALK) > limiar (≥3 voltas consecutivas em zona threshold somando ≥2000m) > tempo (≥3 voltas consecutivas em zona marathon somando ≥2000m) > progressivo (pace médio da 2ª metade ≤ 92% do da 1ª, sem bloco limiar/marathon) > longão (distance_m ≥ 16000, sem bloco) > fácil (restante) | Categorias = vocabulário do plano §4.6; regras determinísticas testáveis; rótulo é heurística honesta, revisável com uso | n |
| Tipo inferido — quando | Calculado em tempo de leitura (função pura sobre splits+zonas), nunca persistido | Recalibração de zonas re-classifica automaticamente; escala pessoal é irrelevante para 30 corridas/página | n |
| Limiar de longão | 16km | Corredor de ~52km/semana tem longão típico 16–24km; abaixo disso é "corrida normal" | n |
| Paginação | `limit` (default 30, máx 100) + `offset` (default 0); resposta `{items, total, limit, offset}`; UI com "Carregar mais" | Escala pessoal (180d de backfill ≈ 150–250 atividades); offset/limit basta | n |
| Lista padrão | Corridas (running/trail_running) ordenadas por `start_time DESC`; `activity_type=all` inclui as demais | Decisão do usuário (14/10/2026): corridas + filtro "todas" | y |
| Não-corrida na lista | Exibe data, nome, tipo, duração e FC, sem pace/zonas | Yoga/força não têm pace; distância é 0.0 por design do mapper | n |
| Contexto — quais noites/dias | Sono, HRV e RHR da **data local de início** da atividade (a noite que termina na manhã daquele dia) | Garmin data o sono pela manhã do despertar; corrida vespertina ainda tem a noite relevante mais próxima; regra única, determinística | n |
| Navegação | Header com os 4 painéis; `/hoje`, `/potencial`, `/saude` como placeholders; `/` redireciona para `/treinos` | Decisão do usuário (14/10/2026): nav completa agora, estrutura pronta para as próximas features | y |
| Fuso/exibição de datas | Horários exibidos como gravados (wall clock local do Garmin), sem conversão | Mesma decisão do garmin-sync (mapper); converter seria inventar dado | n |
| Decoupling FC/pace | Variação % do razão FC-média/pace-médio entre metades | Definição operacional determinística do plano §4.3 ("decoupling FC/pace") | n |
| Estrutura derivada (P2) | String somando passos por intensityType (port de `derive_structure`) | Quase grátis: os grupos já são computados para o tipo inferido | n |

**Open questions:** none — todas resolvidas com o usuário ou registradas como premissa acima.

---

## User Stories

### P1: Navegação dos 4 painéis ⭐ MVP

**User Story**: Como usuário, quero navegar entre Hoje/Treinos/Potencial/Saúde de qualquer tela, para a plataforma existir como produto e não como páginas soltas.

**Why P1**: Os painéis são a espinha dorsal do produto (§4); o header global já existe (decisão do garmin-sync) e ganha a nav — estrutura que as próximas features da Fase 1 preenchem.

**Acceptance Criteria**:

1. WHEN qualquer página carrega THEN a UI SHALL exibir no header a navegação com os 4 painéis (Hoje, Treinos, Potencial, Saúde) alongside ao botão "Puxar do Garmin" existente, legível em 390px de largura. <!-- event-driven -->
2. WHEN o usuário está em um dos painéis THEN a UI SHALL marcar visualmente o painel ativo no header. <!-- state-driven -->
3. WHEN o usuário abre `/hoje`, `/potencial` ou `/saude` THEN a UI SHALL exibir placeholder com o nome do painel e "em construção"; WHEN o usuário abre `/treinos` THEN a UI SHALL exibir a lista de treinos. <!-- complex -->

**Independent Test**: Abrir cada rota no navegador (e em viewport de 390px) e ver nav completa, ativo marcado e placeholder/lista corretos.

---

### P1: Lista de treinos (padrão corridas, filtro todas) ⭐ MVP

**User Story**: Como corredor, quero ver minhas corridas em ordem recente com data, tipo, distância, ritmo e FC, para escolher qual treino inspecionar.

**Why P1**: É a porta de entrada do painel; sem lista não há detalhe. Padrão = corridas (decisão do usuário); filtro traz yoga/força.

**Acceptance Criteria**:

1. WHEN a UI pede a lista THEN o sistema SHALL responder `GET /api/activities` com as corridas (`activity_type` em {running, trail_running}) ordenadas por `start_time DESC` (desempate por `id DESC`), paginadas por `limit` (default 30, máximo 100) e `offset` (default 0), retornando `{items, total, limit, offset}`. <!-- event-driven -->
2. WHEN o parâmetro `activity_type` vale `all` THEN o sistema SHALL incluir atividades de qualquer tipo na mesma ordenação; IF o parâmetro é omitido THEN o sistema SHALL retornar somente corridas. <!-- complex -->
3. The system SHALL derivar o pace de cada item como `duration_s × 1000 / distance_m` quando `distance_m > 0`, e `null` caso contrário; a UI SHALL exibir pace somente quando não-nulo. <!-- ubiquitous -->
4. The system SHALL inferir o tipo de cada corrida (prova, intervalado, limiar, tempo, progressivo, longão, fácil) por regras determinísticas na ordem de prioridade da tabela de premissas, usando somente dados do banco (splits, zonas, raw_json) — nunca a API do Garmin. <!-- ubiquitous -->
5. WHEN a corrida tem `evaluated=true` THEN a UI SHALL exibir o badge "Avaliado" no item da lista. <!-- event-driven -->
6. IF `limit` fora de [1, 100] ou `offset` negativo THEN o sistema SHALL responder HTTP 422 sem executar a query. <!-- unwanted-behavior -->
7. WHEN não existem atividades no banco THEN a UI SHALL exibir estado vazio com a mensagem apontando para o botão "Puxar do Garmin" (sem erro, sem tela branca). <!-- event-driven -->
8. WHEN a lista renderiza THEN cada item SHALL exibir data, nome, tipo inferido, distância, pace (ou duração quando não-corrida no modo `all`), FC média quando existir. <!-- event-driven -->
9. IF a chamada à API falhar THEN a UI SHALL exibir mensagem de erro na página sem quebrar a navegação. <!-- unwanted-behavior -->

**Independent Test**: Após sync real, abrir `/treinos` → corridas recentes com tipo inferido; alternar para "todas" → yoga/força aparecem sem pace; puxar "Carregar mais" → próxima página sem duplicatas.

---

### P1: Detalhe do treino com gráfico de splits por zona VDOT ⭐ MVP

**User Story**: Como corredor, quero ver o gráfico de splits do treino com barras coloridas pela zona VDOT, linha de FC e relevo, para julgar meu pacing à primeira vista.

**Why P1**: É a visualização central do produto (§4.3) e a razão de ser do painel.

**Acceptance Criteria**:

1. WHEN a UI pede `GET /api/activities/{id}` com id inexistente THEN o sistema SHALL responder HTTP 404. <!-- unwanted-behavior -->
2. The system SHALL classificar cada volta com pace válido em exatamente uma zona VDOT (easy, marathon, threshold, interval, repetition) pelos cut points de midpoint definidos nas premissas; IF a volta não tem pace válido (distância ou duração ≤ 0) THEN o sistema SHALL devolver `zone=null`. <!-- ubiquitous -->
3. WHEN o detalhe é montado THEN o payload SHALL incluir os metadados das zonas (chave, rótulo, faixa de pace exibível) para a legenda do gráfico. <!-- event-driven -->
4. WHEN o detalhe carrega com splits THEN a UI SHALL renderizar gráfico composto: barras de pace (uma por volta, largura proporcional à duração, cor pela zona classificada) + linha de FC (pontos por volta) + relevo por volta em eixo secundário, com legenda de zonas e de FC. <!-- event-driven -->
5. The system SHALL desenhar a linha de FC em cor distinta da cor da zona interval. <!-- ubiquitous -->
6. WHEN um pace de volta está fora da escala [180, 420] s/km THEN a UI SHALL exibir a barra clampada à escala em vez de quebrar o layout; o valor real permanece no tooltip. <!-- event-driven -->
7. WHEN a atividade não tem splits THEN a UI SHALL exibir o resumo (cabeçalho, contexto) sem gráfico e sem métricas de consistência, com nota "sem voltas registradas". <!-- event-driven -->
8. WHEN a atividade é de corrida THEN o cabeçalho do detalhe SHALL exibir data, nome, tipo inferido, distância, duração, pace médio, FC média/máxima, cadência média e ganho de elevação — cada métrica omitida quando `null` no banco. <!-- event-driven -->

**Independent Test**: Abrir o detalhe de um treino fácil e de um treino com strides: barras nas cores certas por zona, linha de FC sobreposta, relevo atrás, legenda legível; sem splits → resumo sem gráfico.

---

### P1: Métricas de consistência (corridas ≥8km) ⭐ MVP

**User Story**: Como corredor, quero ver o equilíbrio de metades, drift cardíaco, fade de cadência e decoupling do treino, para detectar fade e inconsistência sem avaliação de IA.

**Why P1**: Plano §9.1 lista essas métricas como conteúdo v1 do detalhe; são determinísticas (AD-003) e completam o "como foi esse treino, de verdade".

**Acceptance Criteria**:

1. WHILE a corrida tem `distance_m ≥ 8000` e ≥4 voltas THEN o payload do detalhe SHALL incluir o bloco `consistency` com: equilíbrio de metades (Δ pace em s/km e %), drift cardíaco (Δ FC média em bpm), decoupling (variação % do razão FC/pace entre metades) e fade de cadência (Δ spm) quando ≥2 voltas com cadência em cada metade. <!-- state-driven -->
2. WHILE a corrida tem `distance_m < 8000` ou <4 voltas THEN o payload SHALL devolver `consistency=null` e a UI SHALL ocultar a tabela. <!-- state-driven -->
3. The system SHALL calcular as metades por distância acumulada (premissa) e todas as métricas como funções puras: a mesma atividade devolve sempre os mesmos valores. <!-- ubiquitous -->
4. WHEN a UI exibe o drift cardíaco THEN ela SHALL exibir junto o Δ pace das metades, para leitura honesta (drift só se interpreta a ritmo constante — AD-005). <!-- event-driven -->
5. IF não há cadência em voltas suficientes THEN o payload SHALL omitir o campo de fade de cadência (nenhum número inventado). <!-- unwanted-behavior -->

**Independent Test**: Abrir um longão ≥8km → tabela com 4 métricas e valores estáveis ao recarregar; abrir um treino de 5km → sem tabela.

---

### P1: Faixa de contexto (só o que existir) ⭐ MVP

**User Story**: Como corredor, quero sono, HRV, RHR, temperatura e elevação do dia do treino no detalhe, para interpretar a execução com contexto fisiológico e ambiental.

**Why P1**: §4.3 item 4 e §9.1 — "faixa de contexto" é conteúdo v1; alimenta a futura avaliação IA.

**Acceptance Criteria**:

1. WHEN o detalhe é montado THEN o payload SHALL incluir sono, HRV e RHR da data local de início da atividade quando existirem no banco, cada um `null` quando ausente; a UI SHALL exibir somente os presentes. <!-- event-driven -->
2. WHEN ≥1 volta tem `avg_temperature` THEN o payload SHALL incluir a temperatura média do treino ponderada pela duração das voltas com temperatura; IF nenhuma volta tem THEN o campo SHALL ser omitido. <!-- complex -->
3. The system SHALL nunca chamar a API do Garmin em nenhum endpoint desta feature — toda leitura vem do banco próprio (AD-002). <!-- ubiquitous -->

**Independent Test**: Detalhe de uma corrida matinal com sono registrado → faixa mostra noite, HRV e RHR do dia; dia sem HRV → linha ausente sem placeholder vazio.

---

### P1: Cadência e temperatura por volta no sync (base de dados) ⭐ MVP

**User Story**: Como corredor, quero cadência e temperatura por volta gravadas no sync, para fade de cadência e clima serem computáveis.

**Why P1**: As métricas de consistência e contexto dependem dessas colunas; o mapper é o único ponto de mudança.

**Acceptance Criteria**:

1. WHEN o sync processa uma volta com `averageRunCadence` no payload THEN o upsert SHALL gravar `Split.avg_cadence`; IF o campo não existe THEN `avg_cadence` SHALL ficar `NULL`. <!-- complex -->
2. WHEN o sync processa uma volta com `averageTemperature` no payload THEN o upsert SHALL gravar `Split.avg_temperature`; IF o campo não existe THEN `avg_temperature` SHALL ficar `NULL`. <!-- complex -->
3. WHEN uma volta existente é re-upsertada THEN o upsert SHALL preservar a idempotência por `(activity_id, idx)` sem duplicar linhas (comportamento herdado do garmin-sync, agora com os campos novos). <!-- event-driven -->

**Independent Test**: Rodar o sync com payload falso contendo `averageRunCadence`/`averageTemperature` → colunas preenchidas; payload sem os campos → NULL; reexecutar → mesma contagem de linhas.

---

### P2: Estrutura do treino no detalhe

**User Story**: Como corredor, quero ver a estrutura da sessão ("Aquecimento 2,0km + Corrida 7,1km + Desaquecimento 2,0km"), para identificar o formato sem ler o gráfico.

**Why P2**: Quase gratuito (os grupos por intensityType já são computados para o tipo inferido), mas não está no núcleo §4.3 v1.

**Acceptance Criteria**:

1. WHEN a atividade tem voltas com `intensity_type` THEN o payload SHALL incluir a string de estrutura derivada somando passos consecutivos por tipo (port de `derive_structure`); IF todas as voltas são do mesmo tipo THEN a estrutura SHALL ser o rótulo único desse tipo. <!-- complex -->

**Independent Test**: Detalhe de treino estruturado (strides) mostra a soma de passos; corrida livre mostra "Corrida".

---

## Edge Cases

- IF a atividade não é corrida e é aberta no detalhe (modo `all`) THEN a UI SHALL exibir resumo (duração, FC, data, nome) sem gráfico, zonas ou consistência.
- IF uma volta tem `avg_hr=null` THEN o ponto de FC da volta fica ausente da linha (linha conecta os pontos existentes), sem inventar valor.
- IF o `vdot_zones.json` não existe ou está inválido THEN o endpoint de detalhe SHALL responder HTTP 500 com mensagem "zonas VDOT não configuradas" — cor de zona é requisito, não opcional.
- IF todas as voltas ficam sem pace válido THEN o gráfico exibe eixo vazio com a nota "sem voltas com pace" (sem barras quebradas).
- WHEN duas corridas têm o mesmo `start_time` THEN o desempate é `id DESC` (ordenação estável entre páginas).
- IF `total` é menor que o `offset` pedido THEN a resposta devolve `items=[]` (página além do fim não é erro).
- IF a corrida tem exatamente 8000m THEN a tabela de consistência aparece (limite inclusivo).
- IF o payload da volta traz `distance=0` ou `duration=0` THEN pace é `null`, zona é `null`, e a volta conta para estrutura/relevo mas não para médias de pace.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TRN-01 | P1: Navegação | Design | Pending |
| TRN-02 | P1: Navegação | Design | Pending |
| TRN-03 | P1: Navegação | Design | Pending |
| TRN-04 | P1: Lista | Design | Pending |
| TRN-05 | P1: Lista | Design | Pending |
| TRN-06 | P1: Lista | Design | Pending |
| TRN-07 | P1: Lista | Design | Pending |
| TRN-08 | P1: Lista | Design | Pending |
| TRN-09 | P1: Lista | Design | Pending |
| TRN-10 | P1: Lista | Design | Pending |
| TRN-11 | P1: Lista | Design | Pending |
| TRN-12 | P1: Lista | Design | Pending |
| TRN-13 | P1: Detalhe+gráfico | Design | Pending |
| TRN-14 | P1: Detalhe+gráfico | Design | Implemented |
| TRN-15 | P1: Detalhe+gráfico | Design | Implemented |
| TRN-16 | P1: Detalhe+gráfico | Design | Pending |
| TRN-17 | P1: Detalhe+gráfico | Design | Implemented |
| TRN-18 | P1: Detalhe+gráfico | Design | Pending |
| TRN-19 | P1: Detalhe+gráfico | Design | Pending |
| TRN-20 | P1: Detalhe+gráfico | Design | Pending |
| TRN-21 | P1: Consistência | Design | Implemented |
| TRN-22 | P1: Consistência | Design | Implemented |
| TRN-23 | P1: Consistência | Design | Implemented |
| TRN-24 | P1: Consistência | Design | Pending |
| TRN-25 | P1: Consistência | Design | Pending |
| TRN-26 | P1: Contexto | Design | Pending |
| TRN-27 | P1: Contexto | Design | Pending |
| TRN-28 | P1: Contexto | Design | Pending |
| TRN-29 | P1: Cadência/tempo no sync | Design | Implemented |
| TRN-30 | P1: Cadência/tempo no sync | Design | Implemented |
| TRN-31 | P1: Cadência/tempo no sync | Design | Implemented |
| TRN-32 | P2: Estrutura | Design | Pending |

**Coverage:** 32 total, 32 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] Após sync real, `/treinos` lista corridas reais com tipo inferido, e o detalhe renderiza o gráfico com todas as voltas classificadas em zona (nenhuma volta com pace válido fica sem zona)
- [ ] Zero chamadas à API do Garmin a partir dos endpoints desta feature (verificável por código: nenhum import/uso do gateway em `activities/`)
- [ ] Métricas de consistência determinísticas: recarregar o detalhe devolve valores idênticos; testes pinam valores exatos com fixtures
- [ ] Navegação completa e painéis placeholders acessíveis em 390px; lista e detalhe legíveis no celular (LAN) quando a infra de CORS/IP estiver configurada
- [ ] Suite de testes do backend verde no Postgres do compose, incluindo os casos extremos de voltas curtas (strides), pace nulo e atividade sem splits
