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

### AD-011
- **Decision**: O painel Hoje (§4.2/§9.1) sai da Fase 1: só volta pós-meia (08/11/2026), redesenhado a partir de evidência de uso real — não se ressuscita a composição §9.1.
- **Reason**: Decisão do usuário (17/10/2026) na discussão de escopo: o card de readiness duplica o que o painel Saúde já mostra (HRV status AD-010, sono, RHR, ACWR/TSB); os alertas — o real valor do painel — são Fase 2 por design; a semana "planejada vs executada" não tem fonte de dados de plano; e o countdown vale só até a prova. A meta da Fase 1 ("substituir o pedir análise no OpenCode") é o Avaliar com IA, e o bloco da meia está ativo agora.
- **Trade-off**: Perde-se o countdown da The Best Açaí durante os 22 dias finais do bloco em troca de não pagar design especulativo sem evidência; após 08/11 o countdown hibernaria até o próximo objetivo de qualquer forma.
- **Scope**: Roadmap Fase 1 (§6 do plano), `/hoje` (permanece placeholder), qualquer spec futura do painel Hoje — retomar exige spec novo a partir de uso observado.
- **Date**: 2026-10-17
- **Status**: superseded by AD-025 (a Home volta antes da meia, como painel-raiz com spec própria `home-panel`)

### AD-012
- **Decision**: Criada a **Fase 1.5 — Identidade e dados por usuário** no roadmap (antes da Fase 2), antecipando o núcleo da Fase 2.5: auth, perfil, zonas no banco, LTHR por usuário e cofre de tokens Garmin. O MVP continua no PC/LAN, sem HTTPS — deploy em nuvem, fila de sync multiusuário e LGPD completa seguem na Fase 2.5.
- **Reason**: Decisão do usuário (18/10/2026): zonas/tokens/LTHR por usuário são pré-requisito de qualquer multiusuário (MVP de 5–20 convidados) e o custo agora é mínimo — `user_id` já existe em toda tabela, o lock de sync já é por usuário e a tabela `zones` já existe (ociosa).
- **Trade-off**: Adia a Fase 2 (revisão semanal, story, alertas) por ~2 fins de semana em troca da plataforma pronta para receber convidados sem retrofit.
- **Scope**: Roadmap §6 (Fases 1.5/2.5/3), módulos novos `auth/` e `user/`, todos os módulos que leem `DEFAULT_USER_ID` em query.
- **Date**: 2026-10-18
- **Status**: active

### AD-013
- **Decision**: Auth **próprio self-hosted**: email+senha (argon2id) + sessão em banco via cookie HttpOnly SameSite=Lax; cadastro por **código de convite** (env `INVITE_CODE`); bootstrap do usuário 1 e suporte via CLI (`app.auth.set_password`). Substitui a menção a Supabase Auth/Clerk da Fase 2.5 para o MVP.
- **Reason**: Decisão do usuário (18/10/2026): o app já tem Postgres próprio e espírito local-first — dependência externa de auth não funciona offline, adiciona conta/serviço e não reduz custo real num MVP de 5–20 pessoas. Convite dá controle de entrada com zero UI de admin.
- **Trade-off**: ~1–2 dias de código de sessão/hasheamento próprios (e responsabilidade de segurança própria) em troca de zero dependência externa e revogação trivial; migrar para provedor gerenciado no futuro fica contido no módulo `auth/`.
- **Scope**: `backend/app/auth/` (modelos, router, dependência `current_user`), `frontend` (`/login`, `/registrar`, layout protegido, 401 → redirect), fix da sequência `users_pkey`, CORS explícito (cookie credentials não aceita `*`), rate limit simples no login.
- **Date**: 2026-10-18
- **Status**: active

### AD-014
- **Decision**: Tokens Garmin migram do tokenstore filesystem para o **banco, criptografados em repouso** (Fernet, `TOKEN_ENCRYPTION_KEY` no env): tabela por usuário, gateway `GarminGateway.from_user(db, user_id)`, refresh do oauth2 **persistido de volta** no banco, seed dos tokens atuais do usuário 1 e login de convidados via **CLI operador-assistida** (`python -m app.garmin.login --user <email>`, MFA interativo).
- **Reason**: Decisão do usuário (18/10/2026): com múltiplos usuários, o tokenstore único em filesystem não escala e o refresh perdido hoje mata a sessão silenciosamente. CLI em vez de fluxo web evita o convidado digitar a senha Garmin no site (barreira de confiança do plano §10.6) e mantém o MFA interativo funcionando.
- **Trade-off**: Operador conecta cada convidado manualmente (custo de operação) em troca de zero coleta de credenciais Garmin no site; criptografia com chave no `.env` protege contra vazamento do dump do banco, não contra quem tem acesso ao host — aceitável no MVP, LGPD completa na 2.5.
- **Scope**: `garmin/tokens_store.py` (cofre), `garmin/client.py` (`from_user`), `garmin/login.py` (`--user`), seed dos tokens do usuário 1, `/perfil` (status da conexão), spike para definir o formato exato de dump/resume da lib `garth`.
- **Date**: 2026-10-18
- **Status**: active

### AD-015
- **Decision**: **Zonas VDOT e LTHR passam a ser dados por usuário no banco**: seed do `vdot_zones.json` → tabela `zones` (já existente, passa a ser usada), `ZoneConfig` lê do banco por usuário, `LTHR_BPM` sai do env e vira campo do perfil. A entrevista de calibração de zonas no app segue na Fase 2.
- **Reason**: Decisão do usuário (18/10/2026): arquivo single-user não serve a múltiplos corredores; LTHR (177) e zonas entram no payload da avaliação IA e precisam vir do perfil de cada um. O JSON calibrado continua como seed — nada é re-digitação.
- **Trade-off**: Leitura de zona passa pelo banco (uma query a mais por classificação) em troca de zonas/LTHR corretos por usuário; calibração self-service fica para a Fase 2 como planejado.
- **Scope**: `vdot/zones.py` (fonte), `core/config.py` (`lthr_bpm` vira fallback), `users` (coluna `lthr_bpm`), seed no `init_db`, endpoint/página do perfil (zonas ativas).
- **Date**: 2026-10-18
- **Status**: partially superseded by AD-021 (a parte LTHR/FC: coluna única → métricas effective-dated com zonas de FC por método; a parte "zonas VDOT por usuário" segue planejada, adiada — `vdot_zones.json` permanece a fonte)

### AD-016
- **Decision**: A aba Hoje sai da navegação e a rota `/hoje` é deletada (junto com o `PanelPlaceholder`, cujo único usuário era ela): AD-011 adiou o painel pra pós-meia mas manteve o placeholder — o placeholder na nav ocupa espaço sem entregar nada na Fase 1. A home já redireciona pra `/treinos` (workouts-list); nenhum redirect extra é necessário.
- **Reason**: Decisão do usuário (18/10/2026): aba vazia não paga o espaço na nav. Quando o Hoje voltar (pós-08/11), volta redesenhado a partir de evidência de uso real (AD-011) e a rota nasce de novo com spec própria.
- **Trade-off**: Quem bookmarkava `/hoje` toma 404 em troca de nav honesta; nenhum dado é perdido (o painel era placeholder).
- **Scope**: `frontend/src/components/Nav.tsx`, `frontend/src/app/hoje/` (deletada), `frontend/src/components/PanelPlaceholder.tsx` (deletado), README; estende a AD-011 (que mantinha o placeholder vivo).
- **Date**: 2026-10-18
- **Status**: active

### AD-017
- **Decision**: O painel Potencial vira **Performance** (rota `/performance`, `components/performance/`, `PerformancePanel`) e a curva PMC (**Carga de treino**) volta pra ele como 4ª seção narrativa — reverte a CLR-03 do panel-clarity. Pela AD-009 (bloco muda de endpoint junto com a tela), `pmc` sai de `GET /api/health/summary` e volta ao payload de `GET /api/potential` com **janela fixa de 60d** (o default que a Saúde usava); o query param `days` segue morto lá (CLR-04 vigente — query não declarada é ignorada). O endpoint e o domínio backend **mantêm o nome `potential`** (`/api/potential`, `app/potential/`, tipos `PotentialOut`): potencial é o vocabulário do domínio (VDOT/predições), Performance é o nome do painel na UI. O PLANO (§4.4) segue como referência histórica — o plano não é reescrito, o mapeamento é este registro.
- **Reason**: Decisão do usuário (18/10/2026): a carga de treino é performance — "quanta carga imponho e o que ela prevê" conta a história completa no mesmo painel; no Saúde a curva ficava sem contexto de resultado (e o fio da Saúde não precisa dela: sono → resposta → dose-resposta → vida). O painel renomeado porque "Performance" cobre potencial + carga; "Potencial" só cobria metade.
- **Trade-off**: A Saúde perde a seção que justificava linhas de `load` no payload (5 → 4 seções) e seu estado vazio endurece (só `load` no banco = painel vazio apontando sync); a PMC na Performance perde o seletor de janela que tinha na Saúde — janela fixa 60d, seletor próprio volta como spec se o uso pedir.
- **Scope**: `backend/app/potential/{router,service}.py` (+`PmcBlock`, `PMC_WINDOW_DAYS=60`), `backend/app/health/{router,service}.py` (−pmc), `backend/app/db/models.py` (docstring), `frontend/src/app/performance/`, `frontend/src/components/performance/` (PmcChart movido, seção nova), `frontend/src/components/health/HealthPanel.tsx` (4 seções), `frontend/src/lib/api.ts`, `backend/tests/test_{health,potential}_api.py` (migração 1:1 de volta), README.
- **Date**: 2026-10-18
- **Status**: active

### AD-018
- **Decision**: Modelo de sessão **stateful** (cookie HttpOnly host-only + token opaco de 32 bytes guardado como hash SHA-256 na tabela `sessions` — revogação, sliding e kill-switch de senha triviais) e proteção de telas **API-autoritativa com proxy otimista** (FastAPI aplica 401 e decide tudo; `proxy.ts` do Next 16 olha apenas a *presença* do cookie e redireciona — nunca valida token). JWT/Bearer stateless foi avaliado e descartado: revogação exigiria denylist, sliding exigiria re-emissão — reconstruindo o estado que o banco dá de graça — e os ganhos (escala horizontal, ausência de lookup) não existem neste deploy (1 container, Postgres no mesmo host).
- **Reason**: Decisão do usuário (19/10/2026) na discussão do design do auth, a partir da análise de trade-offs: "Sair no header" e sliding de 30d são requisitos (AUTH-09/12); o lookup por request custa <1ms no Postgres local; e o proxy otimista segue o padrão do guia oficial de auth do Next 16 sem BFF (que reescreveria o fluxo client→API por ganho nulo).
- **Trade-off**: 1 query de sessão por request (irrelevante na escala) e flash raro de shell quando o cookie está morto no browser (proxy não consulta banco, por design) em troca de zero dependência de assinatura e revogação imediata. Cookie host-only exige frontend e API no mesmo host (portas diferem) — constraint documentada no README §LAN.
- **Scope**: `app/auth/` (futura), `frontend/src/proxy.ts`, `frontend/src/lib/api.ts`, qualquer feature futura que consuma sessão (`/perfil`, tokens por usuário); Fase 3 pode revisar se surgir app nativo/multi-serviço.
- **Date**: 2026-10-19
- **Status**: active

### AD-019
- **Decision**: **Evolução de schema = ALTERs idempotentes condicionais no `init_db`** (ao lado do `create_all` e do `setval`): cada feature que altera colunas de tabelas já existentes inclui sua migração idempotente checando `information_schema.columns`; **Alembic fica para a Fase 2.5** (nuvem, se o schema crescer).
- **Reason**: Emenda UAT (20/10): o `create_all` só cria tabela AUSENTE, nunca altera tabela existente — o banco de dev pré-auth crashou no startup (`UndefinedColumn: users.email`) e a suite não pega porque o conftest derruba o schema a cada teste. Zero-ops do projeto (mesmo espírito do setval da AUTH-27) > introduzir ferramenta de migração no MVP.
- **Trade-off**: Migração ad hoc por feature (checagem manual da coluna) vs versionamento de schema da Alembic — aceitável num schema pequeno e single-instância; revisitar na 2.5 ou quando houver mais de um ambiente de verdade.
- **Scope**: `backend/app/db/engine.py`; toda feature futura que altere colunas de tabelas existentes; Fase 2.5 (adotar Alembic).
- **Date**: 2026-10-20
- **Status**: active

### AD-020
- **Decision**: **Transporte da API pelo próprio Next** — rewrite same-origin (`/api/:path*` → `BACKEND_URL`) em `next.config.ts`; `API_BASE` relativo; `BACKEND_URL=http://backend:8000` chega como **build arg** (o Next materializa as rewrites no build output). O cookie de sessão passa a valer para o host que o usuário abriu: o proxy otimista o vê em **qualquer** host, CORS deixa de ser requisito do app e a constraint same-host (trade-off da AD-018) **deixa de existir**. `NEXT_PUBLIC_API_URL` sai do compose.
- **Reason**: UAT real (20/10): abrir por `localhost:3000` prendia o usuário no login (login 200, cookie no host da API, proxy cego) e o IP-da-LAN nem logava (CORS sem a origem). Duas falhas empilhadas de transporte cross-host; o rewrite é transporte puro — nenhuma lógica de auth no Next, então **AD-018 segue de pé** (API autoritativa + proxy otimista). Matou a classe do problema: múltiplos hosts, mudança de IP da LAN sem rebuild e o caminho para HTTPS (Fase 2.5).
- **Trade-off**: todo fetch passa por um hop no servidor Next (irrelevante em LAN — inclusive o polling de 2s do sync); rewrites materializam no build → `BACKEND_URL` exige rebuild ao mudar (compose default fixa o hostname interno do serviço, imune a DHCP); `npm run dev` usa o fallback `http://localhost:8000`.
- **Scope**: `frontend/next.config.ts`, `frontend/src/lib/api.ts`, `frontend/Dockerfile`, `docker-compose.yml`, README §LAN/§Sessão; Fase 2.5 (HTTPS + cookie Secure continuam compatíveis).
- **Date**: 2026-10-20
- **Status**: active

### AD-021
- **Decision**: **Zonas de frequência cardíaca por usuário com séries effective-dated** (feature `hr-zones`, renomeia `zones-db`): `fcmax`, `fcrest` e `fclthr` em tabela append-only (`user_hr_metrics`: valor, `source` garmin|manual, `valid_from`) + config de zonas append-only (`hr_zone_configs`: método `lthr|fcr|fcmax` + percentuais editáveis com defaults por método — lthr 65/80/89/95/100 do usuário; fcr e fcmax 50/60/70/80/90); **zonas em bpm derivadas por função pura na leitura, vigentes na data consultada** (padrão Strava — treino antigo lido com zonas da época, sem reclassificação retroativa); **o sync é a fonte das três métricas** (emenda do usuário, 20/10: "pegar todas as infos no sync, inclusive LTHR"): fcmax de `user settings`, fclthr de `latestLactateThreshold` (ambas read-only), fcrest do mínimo-7d da série `rhr` própria — update-if-changed a cada sync; **manual vence**: sync nunca sobrescreve `source=manual`; **nenhuma métrica é seedada** (seed manual bloquearia o Garmin para sempre) — só a config lthr (defaults) do usuário 1; `LTHR_BPM` vira fallback do payload até o sync popular; zonas VDOT de **pace** seguem no `vdot_zones.json` (per-user adiado). Supersede parcialmente a AD-015.
- **Reason**: Decisão do usuário (20/10/2026) na discussão do spec: dois corredores não compartilham limiar; zonas são configuração (3 métodos, percentuais editáveis estilo Garmin/Strava), valores precisam de histórico (evolução + leitura honesta do passado) e devem ser editáveis independentemente do Garmin.
- **Trade-off**: Duas queries de resolução por leitura de zonas (métrica + config vigentes) em troca de zero snapshots/jobs de recompute e correção retroativa de graça; a série de fcrest cresce com as mudanças reais do mínimo-7d (evolução que o usuário pediu) em troca de histórico mais movimentado.
- **Scope**: `app/profile/` (calc/service/router), `app/db/models.py` (`user_hr_metrics`, `hr_zone_configs`), `app/db/engine.py` (seed user 1), `app/garmin/{client,service,upserts}.py` (fase physio, read-only), `app/evaluation/payload.py` (`lthr_bpm` por métrica + bloco `zonas_fc`), `frontend` (`/perfil`, proxy, UserMenu), roadmap (zones-db → hr-zones).
- **Date**: 2026-10-20
- **Status**: active

### AD-022
- **Decision**: **Identidade visual v0.3 adotada como sistema de design da plataforma** — referência canônica: `docs/design/identidade-visual-v0.3.html` (mock aprovado: tokens + Home 390px): paleta tinted dark (Night `#0B0F12` · Surface `#121815` · Forest `#1B241A` · Lime `#B7F36B` como acento funcional, nunca fundo geral), borda decorativa `#354039` vs interativa `#4A574E`, Instrument Sans 400–700 com números tabulares, tema de gráfico **"contexto em neutro, um único destaque lime"**, semântica de saúde própria (bom=lime · atenção `#E9B44C` · alerta `#EF6757`, sempre com texto) e shell de app **responsivo** — **tab bar inferior no mobile (<768px), top bar no header no desktop**, com os mesmos itens (ícones + labels) e o mesmo padrão de ativo. Cores das zonas VDOT **mantidas e restritas a contexto de treino** (regra de coexistência: lime da marca ≠ verde-easy de zona). Interface em **sentence case** — caps só em eyebrow. Materialização = feature `design-system` (tokens, tipografia, tema de gráfico, tab bar, skeletons); Home e retrofits de composição seguem em specs próprias.
- **Reason**: Decisão do usuário (22/10/2026): o mock v0.3 — Home 390px inteira na linguagem nova — foi aprovado visualmente e o usuário pediu o início da spec. A identidade sai de "direção visual" e vira fundação de código antes das features que a consomem (Home, que supersede a AD-011); o produto migra de "métricas pra especialista" para "decisão diária pra corredor comum" e precisa ser reconhecível no primeiro olhar — os defaults da stack (zinc/lime-400, Geist, Recharts cru) produzem exatamente o "cara de dashboard" que se quer eliminar. Emenda do usuário na revisão da spec (22/10): em telas largas a navegação permanece no topo — tab bar inferior em desktop ficaria estranha.
- **Trade-off**: Re-pele geral via swap de tokens (toda a superfície muda de pele de uma vez) em vez de redesign gradual por painel — mudança visual grande num commit, em troca de consistência imediata e zero retrofit de cor depois. Zonas VDOT fora do sistema de cor (dupla linguagem de verde, documentada) em vez de unificação — preserva o significado semântico das zonas nos treinos.
- **Scope**: `frontend/src/app/globals.css` (tokens + `@theme inline`), `frontend/src/app/layout.tsx` (fonte, themeColor, favicon), novo `frontend/src/lib/chartTheme.ts`, `frontend/src/components/Nav.tsx` (tab bar), os 11 componentes de gráfico (estilo, não dado), `docs/design/`; features futuras (home-panel, retrofit de painéis) consomem os tokens.
- **Date**: 2026-10-22
- **Status**: active

### AD-023
- **Decision**: **O botão "Puxar do Garmin" sai do header global e passa a viver no `/perfil`, dentro da seção "Conexão Garmin"** — status de conexão (ConnectionCard) e ação de sync no mesmo lugar; o header fica com wordmark + menu do usuário (Sair) em qualquer largura, sem ações globais. Emende a DSN-21 do design-system.
- **Reason**: Decisão do usuário no UAT do design-system (22/10/2026): no mobile o botão de sync no topo ficava estranho ao lado da top bar; sync é ato de configuração da conexão, não de navegação diária — coerente morar junto do status da conexão (ConnectionCard, feature garmin-tokens-db).
- **Trade-off**: O sync deixa de estar a um clique de qualquer painel (agora: 1 tap na tab Perfil) em troca de um header limpo e da coerência semântica do lugar do botão.
- **Scope**: `frontend/src/components/Header.tsx` (remove), `frontend/src/components/SyncButton.tsx` (alinhamento), `frontend/src/app/(app)/perfil/page.tsx` (seção Conexão), `README.md` §Sync, spec design-system (emenda DSN-21).
- **Date**: 2026-10-22
- **Status**: active

### AD-024
- **Decision**: **Habit tracker adiado para feature própria** — a visão é registro temporal de consumo com estimativa de dose (hora do café + cafeína estimada, álcool, leitura etc.) cruzado com os outputs automáticos do Garmin (a tese "Whoop-of-Garmin"); nada de quick-log raso de checkboxes na Home v1. O card "Padrão observado" (correlação hábito×sono) fica adiado junto — depende desses dados acumulados.
- **Reason**: Decisão do usuário (23/10/2026) na spec do home-panel: a feature merece desenho de dados próprio (timestamp + dose por hábito) e está imatura para começar; o bloco de registro do mock v0.3 §03 não vira código agora.
- **Trade-off**: A Home v1 perde o "registro de 10 segundos" do mock e adia o flywheel de dados manuais em troca de não travar o modelo com um design apressado; a composição da Home dispensa o bloco (veredito + chips + recomendações sustentam o above-the-fold).
- **Scope**: mock v0.3 §03 (quick-log), specs futuras de habit tracker/insights, `docs/design/` — o bloco volta pela spec da feature própria.
- **Date**: 2026-10-23
- **Status**: active

### AD-025
- **Decision**: **A Home volta antes da meia como painel-raiz** (supersede a AD-011): `/` renderiza o painel Home (o redirect para `/treinos` sai; a rota `/hoje` permanece 404 — AD-016 segue ativa), tab "Home" em primeiro lugar (nome "Hoje" rejeitado pelo usuário), veredito diário por **regras determinísticas em Python** (tabela curada V1–V6, prioridade fixa, sinal nulo é neutro, sem score e sem LLM — AD-003 intacta), 1–3 recomendações por regra com why, chips que roteiam e countdown com **seed da The Best Açaí** no `init_db` (08/11/2026, idempotente).
- **Reason**: Decisão do usuário (23/10/2026): pediu a spec antes da meia; a evidência que a AD-011 pedia chegou por outro caminho — o pivot estratégico (saúde/recuperação primeiro) e o mock v0.3 aprovado definiram a composição com precisão de pixel.
- **Trade-off**: A composição nasce antes de evidência de uso real em troca do produto diário funcionando já no bloco da meia; o risco é contido porque o veredito é auditável — regras puras, baratas de ajustar, e o countdown some sozinho pós-prova.
- **Scope**: `frontend/src/app/(app)/page.tsx`, `frontend/src/components/Nav.tsx`, `frontend/src/components/home/` (novo), `backend/app/home/` (novo), `backend/app/db/engine.py` (seed), roadmap Fase 1.
- **Date**: 2026-10-23
- **Status**: active

## Handoff

- **Feature**: `home-panel` — **concluída, validada (PASS 39/39, sensor 5/5) e MESCLADA na main** (`2217aed`, 23/10/2026, UAT do usuário aprovado com "merge"). Compose rebuilt: stack da porta 3000 com a Home. Fix pós-merge no mesmo ciclo: proxy/login/registrar levavam `/treinos` como destino pós-login (herança AUTH-20, invisível pro Verifier — sem AC de proxy no spec); agora a raiz Home é a porta de frente
- **Phase / Task**: feature encerrada — 15 tasks em 2 batches + Verifier PASS + fix pós-merge
- **Completed**: veredito determinístico V1–V6 + recomendações R1–R5 + `GET /api/home/today` (consistência AD-010 por construção) + seed da The Best Açaí + Home em `/` (tab "Home" 1ª, 5 itens) + card-veredito/chips/strip/recomendações/digests + estados + fix do destino pós-login (proxy ×2, login, registrar)
- **In-progress**: none
- **Next step**: próxima feature da fila a definir — a **AD-024 (habit tracker com registro temporal de consumo)** é a candidata natural (tese Whoop-of-Garmin; desenhar com o usuário). Push executado neste commit com go-ahead explícito do usuário (23/10)
- **Blockers**: none
- **Uncommitted files**: none (após o commit do fix)
- **Branch**: `main` (worktree principal + worktree `ritmo-design-system` na branch `home-panel` sincronizada por merge)
- **Pendências menores vivas**: flake pré-existente `test_garmin_tokens_store` (monotonicidade de relógio no Windows, ~2/4 runs) · habit tracker (AD-024 — feature futura) · advisory `braces` high dev-only · NVIDIA_MODEL default no `.env` · CLI `set_password` sem política ≥8 · 2 docstrings de teste defasadas
