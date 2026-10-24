# Decisões de Arquitetura (AD-NNN)

O código do Ritmo cita decisões por ID em comentários, specs e testes.
Esta tabela resume as **AD (Architecture Decisions)** — o registro completo,
com motivo, trade-off e escopo, vive em `.specs/STATE.md` (fonte de
verdade). Regras de feature (SYNC-\*, EVAL-\*, HRZ-\*, AUTH-\*, HOME-\*,
CLR-\*, DSN-\*, GTDB-\*…) moram nos specs de cada feature em
`.specs/features/*/spec.md`.

| ID | Decisão | Data | Status |
|---|---|---|---|
| AD-001 | Multiusuário-pronto desde o dia 1: `user_id` em toda tabela + SQLAlchemy como ORM | 14/10/2026 | superseded¹ |
| AD-002 | Integração Garmin **sempre sequencial** (nunca paralela), isolada em `SyncJob`; a UI lê exclusivamente do banco próprio | 14/10/2026 | ativa |
| AD-003 | Avaliação híbrida: Python calcula deterministicamente, o LLM só interpreta (JSON de veredito); toda chamada grava `model`, `prompt_version` e tokens | 14/10/2026 | ativa |
| AD-004 | "Potencial máximo" é exibido como **faixa honesta** (demonstrado vs corrente), nunca número único | 14/10/2026 | ativa |
| AD-005 | Hierarquia de confiança: pace/GPS decide; FC óptica apenas corrobora | 14/10/2026 | ativa |
| AD-006 | Distribuição local-first; comercial bloqueado pela API não-oficial do Garmin (ToS), não pela infra | 14/10/2026 | ativa |
| AD-007 | Postgres desde a v1; ambiente local sobe por `docker-compose.yml` | 14/10/2026 | ativa |
| AD-008 | Recharts é o renderer padrão de séries temporais; SVG próprio só para geometrias especiais (splits com largura proporcional) | 15/10/2026 | ativa |
| AD-009 | Padrão de clareza dos painéis: cabeçalho forte por seção + **payload espelha exatamente o que o painel renderiza** (bloco muda de endpoint junto com a tela) | 16/10/2026 | ativa |
| AD-010 | Modelo de HRV = Altini/HRV4Training: média móvel 7d; banda = 60d média ±0,75×DP (≥14 valores); status local BALANCED/UNBALANCED | 17/10/2026 | ativa |
| AD-011 | O painel "Hoje" sai da Fase 1 (voltaria pós-meia, redesenhado) | 17/10/2026 | superseded por AD-025 |
| AD-012 | Fase 1.5 — Identidade e dados por usuário: auth, zonas no banco, LTHR por usuário, cofre de tokens | 18/10/2026 | ativa |
| AD-013 | Auth **próprio self-hosted** (argon2id + sessão em banco + convite), substituindo Supabase Auth/Clerk | 18/10/2026 | ativa |
| AD-014 | Tokens Garmin no **banco, cifrados com Fernet**; login de usuários via CLI operador-assistida (a UI nunca pede credenciais Garmin) | 18/10/2026 | ativa |
| AD-015 | Zonas VDOT e LTHR viram dados por usuário no banco (JSON vira seed) | 18/10/2026 | parcialmente superseded² |
| AD-016 | Rota `/hoje` deletada junto com o placeholder — nada revive (404) | 18/10/2026 | ativa |
| AD-017 | Painel Potencial vira **Performance** e a curva PMC volta pra ele (janela fixa 60d); o endpoint mantém o nome `potential` | 18/10/2026 | ativa |
| AD-018 | Sessão **stateful** (cookie HttpOnly + token opaco com hash SHA-256 no banco) e proteção **API-autoritativa com proxy otimista**; JWT descartado | 19/10/2026 | ativa |
| AD-019 | Evolução de schema = ALTERs idempotentes condicionais no `init_db`; Alembic fica para a Fase 2.5 | 20/10/2026 | ativa |
| AD-020 | **Transporte da API pelo próprio Next**: rewrite same-origin `/api/*` → `BACKEND_URL`; o cookie vale para o host aberto; CORS deixa de ser requisito | 20/10/2026 | ativa |
| AD-021 | Zonas de FC por usuário com **séries effective-dated** (padrão Strava): métricas append-only (`user_hr_metrics`), config append-only, **manual vence o sync**, nada seedado | 20/10/2026 | ativa |
| AD-022 | **Identidade visual v0.3 = sistema de design** (tinted dark + lime funcional, tab bar mobile, tema de gráfico "contexto em neutro, um destaque lime") | 22/10/2026 | ativa |
| AD-023 | Botão "Puxar do Garmin" sai do header e mora no `/perfil` junto do status da conexão | 22/10/2026 | ativa |
| AD-024 | Habit tracker adiado para feature própria (registro temporal de consumo — tese "Whoop-of-Garmin") | 23/10/2026 | ativa |
| AD-025 | **Home volta antes da meia como painel-raiz** (`/`): veredito diário determinístico V1–V6, sem score e sem LLM; supersede a AD-011 | 23/10/2026 | ativa |

¹ Cláusula de armazenamento (SQLite → Postgres) superseded pela AD-007;
`user_id` + SQLAlchemy seguem vigentes.
² Parte LTHR/FC superseded pela AD-021 (métricas effective-dated); a parte
"zonas VDOT de pace por usuário" segue planejada — o `vdot_zones.json`
permanece a fonte.

## Como uma decisão nasce

Features seguem o workflow **spec-driven** (skill `tlc-spec-driven`): a
decisão é registrada em `.specs/STATE.md` durante a discussão do spec e
recebe o próximo número AD. `validate_state.py` cuida da estrutura. O
código que implementa uma AD cita o ID em comentário — esta tabela é o
mapa entre o que o código diz e o porquê.
