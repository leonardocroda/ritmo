# Avaliar com IA — Especificação

> Botão 2 do plano (§4.6): motor de avaliação híbrido Python+LLM — no detalhe de uma corrida, o usuário declara a intenção, o backend monta o payload determinístico do banco próprio, uma chamada NVIDIA NIM interpreta e devolve o JSON de veredito (§9.2), que é validado, persistido e renderizado em card.

## Problem Statement

A avaliação de treino hoje é conversacional no OpenCode com a skill `analyze-garmin-run`: exige sessão de chat, fetch ao vivo do Garmin (contra AD-002, com risco de rate-limit) e montagem manual do contexto a cada pedido. A meta declarada da Fase 1 (AD-011) é substituir esse fluxo — avaliação sob demanda dentro do app, com payload determinístico do banco próprio e veredito salvo e auditável.

## Goals

- [ ] No detalhe de uma corrida, declarar a intenção (tipo + texto livre) e receber um veredito de execução vs intenção em card
- [ ] Zero alucinação de número (AD-003): todo número do veredito vem do payload calculado em Python; o LLM só interpreta
- [ ] Toda avaliação auditável: `model`, `prompt_version`, `tokens_in/out`, payload e veredito persistidos
- [ ] Avaliação 100% banco próprio (AD-002): nenhuma chamada ao Garmin na avaliação
- [ ] Intenção declarada > números brutos: fácil rápido demais é veredito negativo mesmo sendo "impressionante"

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| ------- | ------ |
| Seletor de modelo flash/full na UI | Decisão B (17/10/2026): `NVIDIA_MODEL` do env é suficiente na v1; uso pessoal tem custo marginal (plano §5) |
| Feed do veredito no painel Potencial + agregação "últimas 10 avaliações" | Fase 2 (roadmap §6) — Decisão D; v1 entrega card no detalhe + badge na lista |
| Zonas de FC formais (sync da config RUNNING + time-in-zone) | Decisão A: v1 envia FC por split + LTHR de referência; estender o sync é outra feature |
| Revisão semanal por IA (série de treinos) | Fase 2 (plano §6) |
| Gerar story com veredito | Fase 2 (plano §6) |
| Alertas proativos / recalibração de zonas por PR novo | Fase 2 (plano §6) |
| Retry automático de avaliação falha | Decisão E: cada tentativa custa tokens; o pedido é sempre explícito |
| Avaliação de atividades não-corrida (yoga/força) | O motor julga execução de corrida contra zonas VDOT; non-running recebe 422 |
| CRUD de padrões pessoais (`patterns`) | O payload lê a tabela quando povoada; editar padrões é outra feature |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Zonas de FC na v1 | FC média por split + `LTHR_BPM` (env, default 177 calibrado) como referência; sem Z1–Z5 formal | Decisão A (confirmada): sync não puxa a config RUNNING e a skill veta hardcode; interpretar FC vs LTHR é papel do LLM (AD-003) | y |
| Modelo na v1 | Fixo pelo env `NVIDIA_MODEL` (glm-5.3); sem seletor | Decisão B (confirmada): uso pessoal, custo marginal, seletor é UI a mais | y |
| Re-avaliação | Sempre cria linha nova (não sobrescreve, não apaga); card = mais recente; anteriores como entradas resumidas | Decisão C (confirmada): histórico é auditoria e base da Fase 2 | y |
| Alcance v1 do veredito | Card no detalhe + badge "Avaliado" na lista; Potencial/agregações na Fase 2 | Decisão D (confirmada) — o roadmap já coloca "histórico + % no alvo" na Fase 2 | y |
| Falhas | Nada gravado em qualquer falha; erro claro em PT-BR no lugar do card; sem retry automático | Decisão E (confirmada): veredito inventado ou meia-avaliação é pior que erro honesto | y |
| Pré-preenchimento da intenção | Seletor pré-preenchido com `inferred_type` (chaves 1:1: prova, intervalado, limiar, tempo, progressivo, longao, facil) | O tipo inferido é determinístico e já visível; confirmar é 1 toque, contrariar é 0 | n |
| Mapeamento intenção → zona(s) alvo | facil→easy; tempo→threshold; limiar→threshold; intervalado→interval; longao→easy∪marathon; progressivo e prova→sem zona alvo única (payload manda % por zona + sequência; prova recebe PRs como referência) | Derivado das zonas Daniels (`vdot_zones.json`: threshold = "tempo runs", longão é base aeróbica); prova se julga contra norms de prova, não zonas de treino (edge da skill) | n |
| Síncrono vs job | POST síncrono (bloqueante até veredito ou timeout), sem job em background | Um usuário local; a chamada NIM leva segundos; job + polling é complexidade sem ganho | n |
| Corrida sem voltas | Avalia com payload honesto (bloco de voltas omitido; agregados + contexto) | Padrão do produto "só o que existir" (contexto, gate de consistência); avaliação fraca é melhor que porta trancada | n |
| Selo do veredito na UI | ✅ on_target e context_explained; ⚠️ too_easy e fatigue_signal; ❌ too_hard | §9.2 pede ✅⚠️❌; context_explained é "ajuste adequado" (positivo); fatigue_signal é alerta, não erro de execução | n |
| Limite do texto livre | ≤500 caracteres (422 acima) | Contexto além disso raramente ajuda; dá teto natural ao payload | n |
| Códigos HTTP das falhas | 404 inexistente; 422 non-running/intenção inválida; 503 sem API key; 502 erro NIM/JSON inválido; 504 timeout; 500 zonas | Espelha o vocabulário dos endpoints existentes (422 antes da query, 404, 500 de config) | n |
| Precedência 503 vs 404/422 | Key ausente responde 503 antes de qualquer consulta ao banco — erro de config não depende do dado | Fix 6 do Verifier (spec-precision): os ACs exigem 503 sem chamada à NIM e nada gravado, sem ordenar contra 404; a checagem é barata e vem primeiro | n |

**Open questions:** none — as cinco áreas cinzentas (A–E) foram confirmadas com o usuário (17/10/2026); os demais defaults são de agente, marcados `n`.

---

## User Stories

### P1: Avaliar um treino e ver o veredito ⭐ MVP

**User Story**: Como corredor, no detalhe de uma corrida quero declarar a intenção do treino e pedir a avaliação, para receber um veredito honesto de execução vs intenção sem sair do app.

**Why P1**: É a meta declarada da Fase 1 (AD-011) — substituir o "pedir análise no OpenCode"; sem o motor, o painel Treinos mostra dados mas não os interpreta.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o usuário abre o detalhe de uma corrida THEN the system SHALL exibir o formulário de intenção (seletor com os 7 tipos, pré-preenchido com `inferred_type` quando existir + texto livre opcional) e o botão "Avaliar com IA". <!-- event-driven -->
2. WHEN o usuário envia uma intenção válida THEN the backend SHALL montar em Python — sem LLM — o payload com: resumo da corrida (distância, duração, pace médio, FC média/máx, cadência, elevação ganha, TE aeróbico/anaeróbico, carga de treino, feel, RPE), voltas classificadas por zona VDOT (km acumulado, pace, FC, cadência, temperatura, elevação, zona), % de duração por zona, % de duração na(s) zona(s) alvo da intenção (mapeamento da tabela de assumptions), consistência sob o gate vigente (≥8km e ≥4 voltas), contexto do dia (sono, HRV, RHR, temperatura média ponderada), PMC do dia (CTL/ATL/TSB/ACWR), zonas vigentes, LTHR de referência, PRs canônicos datados, testes VDOT e padrões ativos — cada bloco presente só com o que existir no banco. <!-- event-driven -->
3. WHEN o payload está montado THEN the backend SHALL fazer exatamente uma chamada à NIM (`NVIDIA_BASE_URL`, `NVIDIA_MODEL`) com o system prompt da versão vigente — regras de veredito destiladas da skill `analyze-garmin-run` (intenção primeiro, contexto muda ou confirma mas nunca decora, hierarquia AD-005: pace decide e FC corrobora, calor, elevação), instrução de responder em PT-BR no JSON de veredito do plano §9.2 e de usar exclusivamente os números do payload, nunca recalcular. <!-- event-driven -->
4. WHEN a resposta da NIM chega THEN the backend SHALL validar o JSON contra o schema de veredito (enum `veredito` com os 5 valores, `headline`, `execucao_vs_intencao`, listas `o_que_funcionou`/`corrigir_prox_vez`/`contexto_relevante`, enum `confianca` alta|média|baixa; campos extras ignorados) e, válido, persistir a avaliação com `intent_type`, `intent_text`, `payload_json`, `model`, `prompt_version`, `verdict`, `verdict_json`, `tokens_in`/`tokens_out` do usage da resposta, e marcar `activity.evaluated = true`. <!-- event-driven -->
5. WHEN a avaliação é persistida THEN the system SHALL exibir o card de avaliação no detalhe: headline, selo do veredito (✅/⚠️/❌), % na zona alvo quando existir, principais desvios, listas "o que funcionou", "corrigir na próxima vez" e "contexto relevante", confiança, modelo, tokens e data. <!-- event-driven -->
6. The system SHALL gravar `model`, `prompt_version`, `tokens_in` e `tokens_out` em toda avaliação persistida (AD-003). <!-- ubiquitous -->
7. The system SHALL montar o payload lendo exclusivamente o banco próprio — nenhuma chamada à API do Garmin na avaliação (AD-002). <!-- ubiquitous -->
8. WHILE a chamada de avaliação está em curso THEN a UI SHALL manter o botão desabilitado com indicador de andamento ("Analisando treino…") — nenhum clique duplo gera segunda chamada. <!-- state-driven -->
9. IF o `activity_id` não existe THEN o endpoint SHALL responder 404 "atividade não encontrada". <!-- unwanted-behavior -->
10. IF a atividade não é corrida (running/trail_running) THEN o endpoint SHALL responder 422 sem chamar a NIM e a UI SHALL omitir o formulário no detalhe. <!-- unwanted-behavior -->
11. IF `intent_type` fora dos 7 tipos ou `intent_text` acima de 500 caracteres THEN o endpoint SHALL responder 422 antes de montar payload ou chamar a NIM. <!-- unwanted-behavior -->
12. IF `NVIDIA_API_KEY` está vazia THEN o endpoint SHALL responder 503 com mensagem clara, sem chamada à NIM e nada gravado. <!-- unwanted-behavior -->
13. IF a NIM devolve erro HTTP ou não responde até o timeout THEN o endpoint SHALL responder 502/504 com mensagem em PT-BR, sem gravar avaliação e sem alterar `evaluated`. <!-- unwanted-behavior -->
14. IF o JSON da NIM não valida contra o schema de veredito THEN o endpoint SHALL responder 502 sem gravar — veredito nunca é inventado (Decisão E). <!-- unwanted-behavior -->
15. IF o arquivo de zonas falha ao carregar THEN o endpoint SHALL responder 500 "zonas VDOT não configuradas" (padrão dos endpoints de activities). <!-- unwanted-behavior -->
16. WHEN a corrida não tem voltas THEN o payload SHALL omitir o bloco de voltas e a avaliação SHALL prosseguir com os agregados e o contexto. <!-- event-driven -->

**Independent Test**: Avaliar uma corrida real do banco com intenção declarada → card com veredito ✅/⚠️/❌, listas, tokens e data; recarregar o detalhe → card persistido; lista de treinos → badge "Avaliado".

---

### P2: Histórico e re-avaliação

**User Story**: Como corredor, quero reavaliar um treino (quando minha leitura da intenção mudar ou quiser um segundo olhar) e ver as avaliações anteriores, para acompanhar como meu julgamento e a análise evoluem.

**Why P2**: Re-avaliação é explícita por design (custo de tokens), mas nunca deve apagar o passado — o histórico é auditoria e base da Fase 2 (Decisão C).

**Acceptance Criteria**:

1. WHEN o detalhe de um treino avaliado é aberto THEN o endpoint SHALL incluir a lista de avaliações do treino (mais recente primeiro) e a UI SHALL renderizar a mais recente como card e as anteriores como entradas resumidas (data, selo, headline). <!-- event-driven -->
2. WHEN o usuário reavalia um treino THEN the system SHALL criar uma avaliação nova (linha nova) e a UI SHALL exibi-la como a mais recente, mantendo as anteriores na lista. <!-- event-driven -->
3. The system SHALL nunca sobrescrever nem apagar avaliações anteriores — re-avaliação só adiciona. <!-- ubiquitous -->
4. WHEN o treino é avaliado THEN a lista de treinos SHALL exibir o badge "Avaliado" (flag `evaluated`, agora alimentada pelo motor). <!-- event-driven -->

**Independent Test**: Reavaliar um treino já avaliado → duas entradas no histórico, a nova como card, badge "Avaliado" na lista.

---

## Edge Cases

- IF a resposta da NIM vem sem `usage` THEN a avaliação persiste com `tokens_in`/`tokens_out` = 0 (custo desconhecido, não avaliação perdida).
- IF a NIM devolve campos além do schema THEN a validação ignora os extras — obrigatórios ausentes rejeitam (Decisão E).
- IF a tabela de padrões está vazia ou os PRs não têm data THEN os blocos são omitidos do payload (nada inventado).
- IF o dia da corrida não tem linha de PMC THEN o bloco de carga é omitido do payload.
- IF o usuário sai do detalhe durante a avaliação THEN nada quebra: o POST conclui no servidor e o detalhe recarregado reflete o banco (avaliação presente quando persistida).
- IF duas abas avaliam o mesmo treino concorrentemente THEN duas avaliações são criadas (sem lock no backend na v1 — usuário único; o guarda é o botão desabilitado por aba).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| EVAL-01 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-02 | P1: Avaliar um treino e ver o veredito | Execute | ❌ Needs Fix (pinos de campo/mapa — validation.md Fix 1-2) |
| EVAL-03 | P1: Avaliar um treino e ver o veredito | Execute | ❌ Needs Fix (marcadores do prompt + chamada única — Fix 3) |
| EVAL-04 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-05 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-06 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-07 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-08 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-09 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-10 | P1: Avaliar um treino e ver o veredito | Execute | ❌ Needs Fix (aceitação trail_running — Fix 4) |
| EVAL-11 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-12 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-13 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-14 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-15 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-16 | P1: Avaliar um treino e ver o veredito | Execute | ✅ Verified |
| EVAL-17 | P2: Histórico e re-avaliação | Execute | ✅ Verified |
| EVAL-18 | P2: Histórico e re-avaliação | Execute | ✅ Verified |
| EVAL-19 | P2: Histórico e re-avaliação | Execute | ✅ Verified |
| EVAL-20 | P2: Histórico e re-avaliação | Execute | ✅ Verified |

**Coverage:** 20 total, 20 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] Avaliar uma corrida real: clique → card com veredito em PT-BR, % na zona alvo quando existir, listas, tokens e data; os tokens gravados conferem com o usage da NIM
- [ ] Toda avaliação no banco tem `model`, `prompt_version`, `tokens_in/out`, `payload_json` e `verdict_json` (query de auditoria)
- [ ] Spot-check de intenção primeiro: treino fácil acima da zona easy nunca sai com veredito ✅
- [ ] Nenhuma chamada ao Garmin na avaliação — payload 100% do banco (revisão de código)
- [ ] Falha da NIM (key ausente/NIM fora/JSON inválido) → erro claro em PT-BR, nada gravado, `evaluated` inalterado
- [ ] Suite pytest verde no Postgres do compose (NIM mockada nos testes — nenhum teste chama a API real) + `npm run build`/`npm run lint` verdes
