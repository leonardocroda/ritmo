# STATE

## Decisions

### AD-001
- **Decision**: Arquitetura multiusuário-pronta desde o dia 1, mesmo single-user: `user_id` em toda tabela, SQLAlchemy como ORM, SQLite (WAL) na v1 — migrar para Postgres é trocar a connection string.
- **Reason**: As 5 decisões de custo zero (plano §10) destravam o beta controlado da Fase 2.5 sem refactor de isolamento.
- **Trade-off**: Verbosidade agora (coluna `user_id` com `DEFAULT_USER_ID = 1`) em troca de escala depois.
- **Scope**: Todo o schema (`backend/app/db/models.py`), toda query, todo job.
- **Date**: 2026-10-14
- **Status**: superseded by AD-007 (cláusula de armazenamento: SQLite → Postgres; `user_id` + SQLAlchemy seguem vigentes)

### AD-002
- **Decision**: Integração Garmin é sempre sequencial (nunca paralela), isolada em `SyncJob(user_id, janela)`, re-puxando os últimos 3 dias + atividades novas; a UI lê exclusivamente do banco próprio.
- **Reason**: Lição paga: ~40 chamadas paralelas derrubaram uma sessão (rate limit + re-auth MFA); o Garmin reprocessa dados por até 72h.
- **Trade-off**: Sync mais lento em troca de nunca matar a sessão OAuth. Teto ~15 chamadas sequenciais por sync.
- **Scope**: `backend/app/garmin/`, qualquer código que toque a API do Garmin, botão "Puxar do Garmin".
- **Date**: 2026-10-14
- **Status**: active

### AD-003
- **Decision**: Motor de avaliação híbrido: Python calcula deterministicamente todos os números (zonas, drift, decoupling, splits) e o LLM só interpreta, devolvendo JSON estruturado de veredito; toda chamada grava `model`, `prompt_version` e tokens.
- **Reason**: Zero alucinação de número; auditoria de custo por avaliação (medidor para futura cobrança por tokens); veredito consumível pela UI campo a campo.
- **Trade-off**: Mais código Python testável vs. simplicidade de "mandar tudo pro LLM".
- **Scope**: Endpoint de avaliação, payload builder, schema `evaluations`.
- **Date**: 2026-10-14
- **Status**: active

### AD-004
- **Decision**: "Potencial máximo" é exibido como faixa honesta — VDOT demonstrado em prova máxima (5K 19:23 ≈ 53) vs. VDOT corrente calibrado (50,2) — nunca um número único.
- **Reason**: Número mágico único desrespeita a variabilidade real; a lacuna entre demonstrado e corrente é a narrativa do painel.
- **Trade-off**: Menos "precision theater" no UI em troca de honestidade sobre o que o teste atual valida.
- **Scope**: Painel Potencial, vereditos de IA, previsões de prova.
- **Date**: 2026-10-14
- **Status**: active

### AD-005
- **Decision**: Hierarquia de confiança de métricas: pace/GPS decide; FC de pulso (óptica) apenas corrobora, nunca fundamenta veredito sozinha.
- **Reason**: FC óptica tem lag e deriva (desarranjo aeróbico, dias quentes); tratá-la como juiz gera veredito errado.
- **Trade-off**: Exige contexto (clima, sono) antes de interpretar FC alta — julgamento menos automático, mais correto.
- **Scope**: Motor de avaliação, painéis, qualquer análise de esforço.
- **Date**: 2026-10-14
- **Status**: active

### AD-006
- **Decision**: Postura de distribuição: local-first para uso pessoal; beta convidado (5–20 usuários) é viável com ~1–2 semanas (Fase 2.5); lançamento comercial é bloqueado pela API não-oficial `garminconnect` (ToS), não pela infra.
- **Reason**: A API oficial (Garmin Health API) exige revisão e é paga; para uso pessoal e beta pequeno o risco é aceitável.
- **Trade-off**: Teto de crescimento deliberado em troca de zero custo e zero burocracia agora.
- **Scope**: Roadmap (Fases 2.5/3), qualquer feature que assuma dados Garmin.
- **Date**: 2026-10-14
- **Status**: active

### AD-007
- **Decision**: Postgres desde a v1 (substitui o "SQLite (WAL) na v1" da AD-001); o ambiente local sobe por `docker-compose.yml` (postgres + backend + frontend); SQLAlchemy e `user_id` em toda tabela seguem como na AD-001.
- **Reason**: Decisão do usuário (14/10/2026): elimina a migração futura de banco e valida o caminho de produção desde o dia 1; compose dá ambiente reproduzível no PC.
- **Trade-off**: Exige Docker rodando local e um pouco mais de ops (container + volume do Postgres) em troca de zero migração de banco depois.
- **Scope**: `DATABASE_URL`/engine (`app/db/engine.py`), `docker-compose.yml`, Dockerfiles, `.env`, docs de setup, conftest de testes.
- **Date**: 2026-10-14
- **Status**: active

### AD-008
- **Decision**: Recharts é o renderer padrão dos gráficos de série temporal dos painéis (Potencial, Saúde, Hoje); SVG próprio fica reservado para geometrias especiais que a lib não modela (ex.: barras de splits com largura proporcional à duração da volta).
- **Reason**: Série temporal é o caso padrão da lib (menos código, eixos/tooltip/responsividade grátis); o gráfico de splits do workouts-list provou que o custo do SVG próprio só se paga quando a geometria exige. Decisão registrada no design do potential-panel (15/10/2026).
- **Trade-off**: Dependência de API da lib (mitigado: Recharts 3.10 já declarado; verificar tipos instalados na implementação) em troca de consistência visual entre painéis.
- **Scope**: `frontend/src/components/` — qualquer gráfico novo de linha/área/barra de série temporal.
- **Date**: 2026-10-15
- **Status**: active

### AD-009
- **Decision**: Padrão de clareza dos painéis: toda seção de painel tem cabeçalho forte (índice quando a ordem forma um passo a passo, título, subtítulo explicativo sempre visível cobrindo "o que é / por que importa", selo de fonte/método quando aplica) e o payload de cada endpoint espelha exatamente o que o painel correspondente renderiza — bloco muda de endpoint junto com a tela.
- **Reason**: Painéis empilhavam gráficos sem fronteira nem explicação (confusão VDOT×VO2max×Riegel; PMC no painel errado); contexto sempre visível (nada atrás de clique/tooltip — mobile-first 390px) e payload 1:1 com a tela evitam acoplamento entre painéis (o 500 de calibração do potencial não pode derrubar a saúde).
- **Trade-off**: Espaço de tela e copy constante em troca de zero interação para entender; endpoints menos "reusáveis" (o Hoje consumirá o bloco pmc da health summary em vez de um endpoint próprio de load).
- **Scope**: Todos os painéis (`frontend/src/components/`, páginas `/potencial` `/saude` e futuras), domínios de leitura do backend (`health/`, `potential/`); decidido no design do panel-clarity (16/10/2026).
- **Date**: 2026-10-16
- **Status**: active

### AD-010
- **Decision**: Modelo de avaliação de HRV = Altini/HRV4Training: linha = média móvel de 7 dias (sobre os valores disponíveis na janela — lacuna de captura não quebra a linha); banda normal por dia = janela móvel de 60 dias, média ± 0,75 × DP amostral (smallest worthwhile change, Plews et al.), emitida só com ≥14 valores na janela; status local BALANCED/UNBALANCED (média 7d vs banda do dia, limites inclusos), null = "coletando linha de base". O status cru da Garmin sai da UI do Saúde (continua persistido na tabela `hrv`); backfill de saúde sobe para 120 dias (60 de exibição + 59 de lookback de banda).
- **Reason**: Decisão do usuário (17/10/2026): a Garmin compara média 7d com um range pessoal mas não publica a fórmula; o método Altini é publicado, cientificamente ancorado (SWC) e reproduz o comportamento com fórmula aberta e testável. Banda móvel por dia (usuário vetou banda plana) requer histórico além da janela exibida.
- **Trade-off**: Status local pode divergir do relógio (bandas diferentes) em troca de transparência total — os números que decidem o status estão visíveis no card e no gráfico; primeira sync pós-mudança traz só o histórico antigo (a banda dos primeiros dias fica ausente até um re-sync completo com `sync_state` limpa).
- **Scope**: `health/calc.py` (modelo puro), `health/service.py` (janela + montagem), `health/router.py` (contrato), `core/config.py` (backfill 120), `HrvChart`/`HrvTable` (Saúde), futuro Painel Hoje (§4.2 — readiness usará o mesmo modelo).
- **Date**: 2026-10-17
- **Status**: active

## Handoff

- **Feature**: `health-window` — **concluída, validada e aprovada no UAT** (Verifier PASS it.1: 13/13 ACs com evidência `file:line`, 0/4 mutantes comportamentais derrubados pelo gate automatizado da camada UI — limitação estrutural documentada, 4/4 pegos por inspeção spec-anchored + UAT, controle positivo 1/1, `.specs/features/health-window/validation.md`; UAT real 17/10/2026 aprovado pelo usuário — seletor 7/30/42/60/90d, default 60d, troca aplicada a todas as seções)
- **Phase / Task**: n/a — 1 commit de feature (`68857ee` feat(ui): add time window filter to health panel) + fechamento (`03b1b50` validation PASS, `efb3215` lição L-006, UAT neste commit); execução inline (Small scope); traceability 13/13 ✅ Verified (HWF-01..13)
- **Completed**: discuss (conjunto 7/30/42/60/90d + default 60d confirmados pelo usuário 17/10/2026; âncoras: ATL/WHOOP 7d, mês 30d, CTL 42d TrainingPeaks, banda HRV 60d AD-010, longa 90d) → spec (13 ACs, `validate_spec` 0 erros) → execute inline (gate `npm run build` + `npm run lint` verdes; backend intocado — contrato `days` 7–365 já validado por HLT-02/03) → Verifier PASS → UAT aprovado
- **In-progress**: none
- **Next step**: **Avaliar com IA** (§4.6, motor híbrido Python+LLM) ou **Painel Hoje** (§4.2, readiness + countdown + CRUD `races` — usará o modelo HRV da AD-010 e herda o seletor de janela por consumir `/api/health/summary`); ops opcional do usuário: re-sync completo (`DELETE FROM sync_state WHERE data_type IN ('sleep','hrv','rhr','stress','body_battery')` + "Puxar do Garmin") para a banda cobrir os 60 dias exibidos com janela cheia; pendências menores vivas: sync de passos/NEAT como feature própria, sequência `users_pkey` desincronizada no `init_db` (Fase 2.5), lições L-005/L-006 (candidates)
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main
