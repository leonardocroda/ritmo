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

## Handoff

- **Feature**: `potential-panel` — implementação completa (T1–T16 commitadas; aguardando Verifier independente)
- **Phase / Task**: Verifier (sensor de mutação + spec-anchored check + `validation.md`) — próximo passo automático
- **Completed**: spec → design → tasks (16 tarefas) → execute em 2 lotes (sub-agents glm-5.3-flash; 2 primeiras tentativas abortadas por loop degenerado do glm-5.3 default) + T16 inline; suite **228 testes** no Postgres do compose; UAT real aprovado pelo usuário (sync com `predictions: 4`, `pr_date` auto-curado, pins conferidos: demonstrado 51,62, lacuna 97,3%, decay maratona −22,1%)
- **In-progress**: none
- **Next step**: Verifier → fechar Fase 1 com o próximo painel (**Saúde** §4.5) ou **Avaliar com IA** (§4.6); pendências menores: alvo da próxima prova entra com o painel Hoje (CRUD `races`), média ponderada dos PRs é v2 (Out of Scope da spec)
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main
