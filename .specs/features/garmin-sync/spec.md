# Sync do Garmin — Especificação

> Feature 1 da Fase 1 · Botão "Puxar do Garmin" + sync incremental para o banco próprio

## Problem Statement

A UI do Ritmo lê exclusivamente do banco próprio (AD-002 / lição nº 1: rajada de chamadas paralelas derrubou a sessão Garmin), mas hoje o banco tem schema e nenhum dado — sem sync não existem painéis. Precisamos do botão "Puxar do Garmin": um job sequencial, incremental e idempotente que popula atividades+splits, sono, HRV, RHR, body battery, stress, recordes de corrida e a série de carga (PMC) — sem jamais arriscar a sessão OAuth do Garmin.

## Goals

- [ ] Botão "Puxar do Garmin" que popula o banco de ponta a ponta, com status visível ("Puxando 12 atividades…") e resultado resumido ao terminar
- [ ] Sync incremental idempotente: re-puxa os últimos 3 dias + atividades novas; executar 2× não cria duplicatas
- [ ] Primeiro sync (backfill): 180 dias de atividades + 60 dias de saúde + recordes pessoais de corrida (sempre, independente de janela)
- [ ] Carga (PMC: CTL/ATL/TSB/ACWR) calculada deterministicamente em Python a partir do `training_load` das atividades — zero chamadas extras
- [ ] Teto de chamadas sequenciais por sync (~15–20 em steady-state) e guard rail configurável contra runaway
- [ ] Estado "Reconectar Garmin" claro quando o token morre, sem corromper dados

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| ------- | ------ |
| Previsões de prova (`get_race_predictions`) | Sem tabela nem consumidor na v1; entra na feature Painel Potencial |
| Painéis que consomem os dados (Hoje/Treinos/Saúde/Potencial) | Features próprias da Fase 1; este spec só escreve dados |
| Espelho de exclusão (atividade apagada no Garmin) | Banco próprio é a fonte da verdade; exclusão local fica manual na v1 |
| Re-auth MFA dentro da UI web | Exigiria UX de credenciais (Fase 2.5); na v1 re-auth é CLI e a UI só sinaliza |
| Sync agendado/automático | Princípio do produto: sync explícito no botão (§2 do plano) |
| Envio de dados ao Garmin (treinos, upload) | Fase 2 ("Montar treino") |
| Auth de API / multiusuário | Fase 2.5 (AD-006); v1 roda local na LAN |
| Migrations formais (Alembic) | v1 usa `create_all`; migrations entram quando houver schema mutável em produção |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Janela de re-pull em steady-state | 3 dias (`SYNC_REPULL_DAYS=3`) | Garmin reprocessa sono/carga por até 72h (§9.4 do plano, AD-002) | y |
| Backfill do primeiro sync | Atividades 180d, saúde 60d (env-configurável) | Decisão do usuário (14/10/2026); cobre o bloco atual e a linha de HRV 60d do painel Saúde | y |
| Tipos de dado sincronizados | Atividades+splits, sono, HRV, RHR, body battery, stress, recordes de corrida, carga | Decisão do usuário: todos os tipos com tabela | y |
| Origem de CTL/ATL/TSB/ACWR | Calculado em Python a partir do `training_load` das atividades | Determinístico e auditável (espírito AD-003); zero chamadas extras; histórico = janela de atividades | y |
| Recordes pessoais | `get_personal_record()` em todo sync (1 chamada), filtrados para corrida, upsert por `(user_id, evento)` | Decisão do usuário: "independente da data"; PRs mudam quando há prova | y |
| Cadência de chamadas | Sequencial, pausa `SYNC_CALL_INTERVAL_S` (default 1,0s), retry 3× com backoff 2/4/8s | AD-002: nunca rajadas; ~40 paralelas derrubaram a sessão | n |
| Splits | Buscados apenas para atividades de corrida (running/trail), 1 chamada por atividade | Yoga/força não têm splits úteis; economiza o orçamento de chamadas | n |
| Tabelas novas | `personal_records` e `sync_state` (last_sync por tipo de dado) adicionadas ao `models.py` via `create_all` | Recordes não têm tabela; incremental por tipo exige memória de last_sync | n |
| Re-auth na v1 | CLI interativa (`python -m app.garmin.login`); a UI apenas sinaliza "Reconectar Garmin" | MFA é interativo; fluxo web de credenciais é barreira de confiança da Fase 2.5 (§10) | n |
| Atividade deletada no Garmin | Permanece no banco local | Banco próprio é a fonte da UI; espelhamento de exclusão fica fora da v1 | n |
| Timezone | Datas de calendário do Garmin gravadas como vêm (campo `Date` local) | Garmin já entrega a data de calendário correta por dia; converter fuso seria inventar dado | n |
| `raw_json` | Sempre preservado em atividades e recordes | Auditoria de campos não mapeados sem re-puxar do Garmin | n |
| Onde fica o botão | Header global do layout (desktop e mobile) | "4 painéis + 2 botões" (§4): visível de qualquer painel | n |
| Idioma da UI | PT-BR | Projeto é pessoal, todo o material está em PT-BR | n |

**Open questions:** none — todas resolvidas com o usuário ou registradas como premissa acima.

---

## User Stories

### P1: Botão "Puxar do Garmin" com job sequencial e status visível ⭐ MVP

**User Story**: Como corredor, quero clicar em "Puxar do Garmin" e ver o progresso, para ter meus dados no banco sem nunca arriscar a sessão OAuth.

**Why P1**: É a porta de entrada de todos os dados; a lição nº 1 (nunca paralelo, nunca ao renderizar) vira requisito estrutural aqui.

**Acceptance Criteria**:

1. WHEN o usuário clica em "Puxar do Garmin" THEN o sistema SHALL criar um `SyncJob` (`status=pending`) e responder HTTP 201 com o id do job, executando o sync em background (FastAPI BackgroundTasks). <!-- event-driven -->
2. WHILE existe um `SyncJob` com `status=running` para o usuário THEN o sistema SHALL recusar novo sync com HTTP 409 e o estado do job corrente (id, status, started_at). <!-- state-driven -->
3. The system SHALL fazer todas as chamadas à API do Garmin exclusivamente em sequência (nunca concorrentes), com pausa mínima de `SYNC_CALL_INTERVAL_S` (default 1,0s) entre chamadas. <!-- ubiquitous -->
4. WHEN o job inicia THEN o sistema SHALL transitar `pending → running` gravando `started_at`, e WHEN o job termina THEN o sistema SHALL transitar para `done` ou `error` gravando `finished_at` — transições fora dessa sequência são proibidas. <!-- complex -->
5. WHILE o job está `running` THEN o sistema SHALL expor contadores parciais atualizados em `stats_json` via `GET /api/sync/jobs/{id}` e `GET /api/sync/jobs/latest`. <!-- state-driven -->
6. WHEN o job finaliza THEN o sistema SHALL gravar em `stats_json` contadores por tipo: atividades novas, atividades atualizadas, splits, noites de sono, dias de HRV, dias de RHR, dias de body battery, dias de stress, recordes, chamadas API feitas e duração. <!-- event-driven -->
7. IF uma chamada ao Garmin responder 429 ou erro transitório de conexão THEN o sistema SHALL retentar até 3 vezes com backoff exponencial (2s, 4s, 8s) antes de tratar o tipo como falho. <!-- unwanted-behavior -->
8. WHEN um job está `running` THEN a UI SHALL desabilitar o botão de sync e exibir o progresso (ex.: "Puxando 12 atividades…"); WHEN o job termina THEN a UI SHALL exibir o resumo dos contadores ou a mensagem de erro correspondente. <!-- complex -->
9. IF o job atinge `SYNC_MAX_CALLS` (default 1500) chamadas THEN o sistema SHALL interromper com `status=error` e as estatísticas das chamadas já feitas — guard rail contra runaway. <!-- unwanted-behavior -->

**Independent Test**: Com cliente Garmin falso (injetado) ou tokens reais: clicar no botão → job criado, progresso visível, resumo ao final; clicar de novo durante o sync → 409 e botão já desabilitado.

---

### P1: Atividades + splits incrementais e idempotentes ⭐ MVP

**User Story**: Como corredor, quero minhas atividades com splits no banco, para que os painéis (e a futura avaliação IA) tenham a base de análise.

**Why P1**: É o dado central do produto (gráfico de splits, avaliação de execução); sem idempotência o sync diário duplicaria tudo.

**Acceptance Criteria**:

1. WHEN o sync executa THEN o sistema SHALL buscar atividades com `get_activities_by_date(inicio, hoje)` onde `inicio = last_sync_activities − SYNC_REPULL_DAYS` (ou janela de backfill quando não houver last_sync). <!-- event-driven -->
2. The system SHALL gravar cada atividade por upsert em `garmin_id` (preservando `raw_json`) e cada split por `(activity_id, idx)` de modo que reexecuções do sync não criem duplicatas (contagens estáveis). <!-- ubiquitous -->
3. WHEN a atividade é do tipo corrida THEN o sistema SHALL buscar seus splits com exatamente 1 chamada `get_activity_splits` por atividade; IF a atividade não é corrida THEN o sistema SHALL gravá-la sem chamada de splits. <!-- complex -->
4. WHEN o tipo atividades é concluído THEN o sistema SHALL atualizar `last_sync_activities` no `sync_state` do usuário. <!-- event-driven -->
5. IF a busca de atividades falhar após os retries THEN o sistema SHALL finalizar o job com `status=error` e a mensagem do erro (atividades são tipo crítico). <!-- unwanted-behavior -->

**Independent Test**: Rodar o sync 2× seguidas → número de atividades/splits idêntico; nova corrida registrada no Garmin aparece com splits após o próximo sync.

---

### P1: Primeiro sync (backfill) + recordes pessoais ⭐ MVP

**User Story**: Como corredor, quero que o primeiro sync já traga histórico suficiente (180d de atividades, 60d de saúde) e meus recordes, para os painéis nascerem cheios.

**Why P1**: Sem backfill os painéis começam vazios e o produto não demonstra valor; recordes alimentam o painel Potencial (decisão explícita do usuário).

**Acceptance Criteria**:

1. WHEN não existe `last_sync` para um tipo de dado THEN o sistema SHALL usar a janela de backfill do tipo: atividades `SYNC_BACKFILL_ACTIVITIES_DAYS` (default 180), saúde `SYNC_BACKFILL_HEALTH_DAYS` (default 60). <!-- event-driven -->
2. The system SHALL buscar os recordes pessoais de corrida em todo sync (1 chamada `get_personal_record`) e gravá-los por upsert em `(user_id, evento)` na tabela `personal_records`, independentemente da janela de datas. <!-- ubiquitous -->
3. WHEN o job conclui THEN o sistema SHALL registrar em `stats_json` o total de chamadas API feitas (`calls_made`), para auditoria do orçamento de chamadas. <!-- event-driven -->

**Independent Test**: Banco vazio → primeiro sync popula ~180d de atividades, 60d de saúde e a tabela de recordes; segundo sync usa janela incremental (calls_made muito menor).

---

### P1: Dados de saúde (sono, HRV, RHR, body battery, stress) ⭐ MVP

**User Story**: Como corredor, quero sono/HRV/RHR/battery/stress no banco por dia, para os painéis Saúde e Hoje responderem prontas.

**Why P1**: Painéis Saúde e Hoje são MVP da Fase 1; a decisão do usuário foi sincronizar todos os tipos com tabela.

**Acceptance Criteria**:

1. WHEN o sync executa THEN o sistema SHALL re-puxar a janela `SYNC_REPULL_DAYS` (default 3) de sono, HRV, RHR e stress (1 chamada por dia por tipo) e body battery (1 chamada de range), gravando por upsert em `(user_id, date)`. <!-- event-driven -->
2. IF a chamada de um dia retorna vazio/None THEN o sistema SHALL pular o dia sem erro e sem gravar linha. <!-- unwanted-behavior -->
3. IF um tipo de saúde falhar após os retries THEN o sistema SHALL concluir os demais tipos e finalizar `status=done` com `warnings: [{tipo, erro}]` em `stats_json`. <!-- unwanted-behavior -->
4. WHEN um tipo de saúde é concluído THEN o sistema SHALL atualizar `last_sync_<tipo>` no `sync_state` do usuário. <!-- event-driven -->

**Independent Test**: Após sync, `sleep`/`hrv`/`rhr`/`body_battery`/`stress` têm uma linha por dia da janela; dia sem HRV no Garmin não quebra o job.

---

### P1: Carga determinística (PMC: CTL/ATL/TSB/ACWR) ⭐ MVP

**User Story**: Como corredor, quero CTL/ATL/TSB/ACWR por dia no banco, para o painel Potencial mostrar fitness/fadiga desde já.

**Why P1**: "Carga" está no checklist do sync da Fase 1; decisão do usuário: calcular em Python, determinístico.

**Acceptance Criteria**:

1. WHEN o sync grava ou atualiza atividades THEN o sistema SHALL recalcular a série diária em `load` com CTL = EWMA diária (α = 1/42) e ATL = EWMA diária (α = 1/7) sobre o `training_load` diário, TSB = CTL − ATL e ACWR = soma(7d) / (soma(28d) / 4). <!-- event-driven -->
2. The system SHALL recalcular a série apenas do dia mais antigo alterado no sync até hoje, preservando o histórico anterior já calculado. <!-- ubiquitous -->
3. IF uma atividade não tem `training_load` THEN o sistema SHALL tratá-la como carga 0 naquele dia. <!-- unwanted-behavior -->

**Independent Test**: Após backfill, conferir CTL/ATL/TSB/ACWR de 3 dias quaisquer contra o cálculo manual em Python puro a partir das atividades.

---

### P2: Reconectar Garmin (token morto)

**User Story**: Como corredor, quero saber claramente quando o token Garmin morreu e como renovar, para não perder syncs achando que "está tudo bem".

**Why P2**: Token expira em ~6 meses (evento raro), mas a lição nº 2 do plano pede mensagens claras quando acontecer.

**Acceptance Criteria**:

1. IF o login com os tokens falhar por expiração/401 THEN o sistema SHALL finalizar o job com `status=error`, a mensagem do erro no campo `error` e `reauth_needed: true` em `stats_json`. <!-- unwanted-behavior -->
2. WHEN o job termina com `reauth_needed` THEN a UI SHALL exibir o estado "Reconectar Garmin" com a instrução do comando CLI de re-auth (`python -m app.garmin.login`) no lugar do resumo. <!-- event-driven -->
3. WHEN o usuário renova os tokens e clica "Puxar do Garmin" novamente THEN o sistema SHALL retomar o sync incremental normal, sem backfill. <!-- event-driven -->

**Independent Test**: Apontar `GARMINTOKENS` para um diretório inválido → job `error` com `reauth_needed`; UI mostra estado "Reconectar Garmin".

---

## Edge Cases

Edge cases como critérios indesejados (IF/THEN) ou de fronteira (WHEN):

- IF uma atividade foi editada no Garmin dentro da janela de re-pull THEN o upsert por `garmin_id` atualiza os campos (o re-pull de 3 dias existe para isso)
- WHEN uma corrida é na esteira sem GPS THEN os splits podem não existir; o sistema grava o que existir e a atividade permanece válida
- WHEN o dia cruza virada de ano/fuso THEN as datas são as de calendário locais entregues pelo Garmin, sem conversão
- IF `get_activity_splits` devolve estrutura vazia THEN o sistema grava a atividade sem splits, sem warning
- IF a API do Garmin mudar endpoint e quebrar THEN o job termina `error` com mensagem clara e o banco mantém o último estado bom (nada parcialmente corrompido)
- WHEN dois cliques no botão quase simultâneos THEN apenas um job é criado; o segundo recebe 409 (lock por usuário, AD-002)

---

## Requirement Traceability

| Requirement ID | Story (AC) | Phase | Status |
| -------------- | ---------- | ----- | ------ |
| SYNC-01 | P1 Botão/job · AC1 (POST cria job, 201) | Design | Pending |
| SYNC-02 | P1 Botão/job · AC2 (409 se running) | Design | Pending |
| SYNC-03 | P1 Botão/job · AC3 (sequencial + intervalo) | Design | Pending |
| SYNC-04 | P1 Botão/job · AC4 (máquina de estados) | Design | Pending |
| SYNC-05 | P1 Botão/job · AC5 (stats parciais via GET) | Design | Pending |
| SYNC-06 | P1 Botão/job · AC6 (stats finais por tipo) | Design | Pending |
| SYNC-07 | P1 Botão/job · AC7 (retry backoff 429) | Design | Pending |
| SYNC-08 | P1 Botão/job · AC8 (UI: progresso/resumo) | Design | Pending |
| SYNC-09 | P1 Botão/job · AC9 (guard rail SYNC_MAX_CALLS) | Design | Pending |
| SYNC-10 | P1 Atividades · AC1 (janela incremental) | Design | Pending |
| SYNC-11 | P1 Atividades · AC2 (upsert dedup garmin_id/idx) | Design | Pending |
| SYNC-12 | P1 Atividades · AC3 (splits só corrida) | Design | Pending |
| SYNC-13 | P1 Atividades · AC4 (last_sync_activities) | Design | Pending |
| SYNC-14 | P1 Atividades · AC5 (falha → job error) | Design | Pending |
| SYNC-15 | P1 Backfill · AC1 (janelas 180d/60d) | Design | Pending |
| SYNC-16 | P1 Backfill · AC2 (recordes todo sync) | Design | Pending |
| SYNC-17 | P1 Backfill · AC3 (calls_made auditável) | Design | Pending |
| SYNC-18 | P1 Saúde · AC1 (re-pull 3d, upsert (user,date)) | Design | Pending |
| SYNC-19 | P1 Saúde · AC2 (dia vazio → skip) | Design | Pending |
| SYNC-20 | P1 Saúde · AC3 (falha tipo → done + warnings) | Design | Pending |
| SYNC-21 | P1 Saúde · AC4 (last_sync por tipo) | Design | Pending |
| SYNC-22 | P1 PMC · AC1 (CTL/ATL/TSB/ACWR de training_load) | Design | Pending |
| SYNC-23 | P1 PMC · AC2 (recompute janela afetada) | Design | Pending |
| SYNC-24 | P1 PMC · AC3 (sem load → carga 0) | Design | Pending |
| SYNC-25 | P2 Reconectar · AC1 (error + reauth_needed) | Design | Pending |
| SYNC-26 | P2 Reconectar · AC2 (UI estado reconectar) | Design | Pending |
| SYNC-27 | P2 Reconectar · AC3 (retomada incremental) | Design | Pending |

**ID format**: `SYNC-NN` · **Status values**: Pending → In Design → In Tasks → Implementing → Verified

**Coverage**: 27 total (1:1 com as ACs), 0 mapped to tasks (fase Tasks pendente), 27 unmapped

---

## Success Criteria

Como sabemos que a feature é um sucesso:

- [ ] Clicar "Puxar do Garmin" com tokens válidos termina em `done` com dados no banco e zero chamadas paralelas (verificável: log sequencial + `calls_made`)
- [ ] Steady-state (pós-backfill) faz ≤ ~20 chamadas sequenciais por sync — dentro do espírito do teto do plano
- [ ] Rodar o sync 2× não altera contagens de nenhuma tabela (idempotente)
- [ ] Primeiro sync em banco vazio: ~180d de atividades, 60d de saúde, recordes gravados
- [ ] Token inválido → job `error` com `reauth_needed`, UI clara, nenhum dado corrompido; renovar tokens retoma incremental
- [ ] Toda escrita carrega `user_id` (AD-001) e toda configuração vem de env vars (requisito travado)
