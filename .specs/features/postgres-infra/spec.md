# Infra Postgres + Docker Compose — Especificação

> Pré-requisito da Fase 1 · AD-007: Postgres desde a v1, stack local sobe por compose

## Problem Statement

A Fase 0 usou SQLite como banco provisório do esqueleto, mas a decisão agora é Postgres direto desde a v1 (AD-007) — eliminando qualquer migração futura. O app ainda aponta para SQLite por default, não roda em container, e não existe compose: a infra precisa existir antes da primeira feature de dados (sync do Garmin).

## Goals

- [ ] `docker compose up -d` sobe o stack completo — postgres + backend + frontend — e tudo fica saudável
- [ ] Backend conecta ao Postgres exclusivamente via `DATABASE_URL` de env (requisito travado: config 100% env)
- [ ] pytest roda contra o Postgres do compose (banco `ritmo_test`), com estado limpo entre testes
- [ ] Zero código específico de SQLite remanescente no app (Postgres é o único caminho)

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| ------- | ------ |
| Migrations formais (Alembic) | v1 continua com `create_all` (schema novo, sem dados); entra quando houver schema mutável em produção |
| Migração de dados do SQLite antigo | Não há dados — a Fase 0 criou só schema vazio |
| Backups agendados / pg_dump scripts | Ops da Fase 2.5 |
| Deploy em nuvem, HTTPS, auth de usuários | Fase 2.5 (AD-006) |
| Hot-reload dentro dos containers | Dev diário usa `docker compose up -d postgres` + `uvicorn --reload` local; o compose full é o jeito de subir o stack |

---

## Assumptions & Open Questions

Toda ambiguidade resolvida ou registrada aqui.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Onde o pytest roda | Postgres do compose, banco `ritmo_test` dedicado | Decisão do usuário (14/10/2026): paridade com o banco real; upserts do sync serão testados no dialeto de verdade | y |
| Credenciais locais do Postgres | `ritmo:ritmo` no compose (dev only, não é segredo) | Ambiente local single-user; segredo real entra na Fase 2.5 | n |
| Imagem e versão | `postgres:16` + `python:3.x-slim` (mesma versão do `.venv`) | Versões estáveis; manter imagem alinhada ao runtime local | n |
| Driver Python | `psycopg[binary]` (v3, dialect `postgresql+psycopg`) | Driver moderno oficial para SQLAlchemy 2.x | n |
| Frontend no compose | Next.js build standalone (`output: 'standalone'`) | Imagem enxuta, padrão Next.js em container | n |
| Persistência | Volume nomeado `postgres-data` | Dados sobrevivem a `docker compose down` (sem `-v`) | n |
| Branch SQLite do engine | Removida (Postgres único caminho) | AD-007 elimina o SQLite; código morto confunde | n |
| Portas | 5432 (postgres), 8000 (backend), 3000 (frontend) | Convenção; dev tools (DBeaver etc.) acessam 5432 direto | n |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Stack local sobe por compose e app roda em Postgres ⭐ MVP

**User Story**: Como usuário/desenvolvedor do Ritmo, quero `docker compose up -d` e ter o stack completo rodando em Postgres, para desenvolver e usar o app sem setup manual e sem risco de migração futura de banco.

**Why P1**: A AD-007 trocou o banco da v1 para Postgres; nenhuma feature de dados (sync) pode ser construída antes disso.

**Acceptance Criteria**:

1. WHEN o usuário executa `docker compose up -d` THEN o compose SHALL subir os serviços postgres, backend e frontend, com o backend aguardando o healthcheck do postgres (`pg_isready`, `service_healthy`) antes de iniciar. <!-- event-driven -->
2. WHEN o stack está de pé THEN o backend SHALL responder `GET /api/health` com HTTP 200 em `localhost:8000` e o frontend SHALL responder com HTTP 200 em `localhost:3000`. <!-- event-driven -->
3. The system SHALL conectar o backend ao Postgres exclusivamente pela env var `DATABASE_URL` (nenhuma URL ou credencial no código). <!-- ubiquitous -->
4. WHEN o backend inicia THEN o sistema SHALL criar o schema (`create_all`) e semear o usuário default no Postgres. <!-- event-driven -->
5. WHEN o pytest roda THEN os testes SHALL executar contra o banco `ritmo_test` do Postgres do compose com estado limpo entre testes (nenhum teste enxerga dados de outro). <!-- event-driven -->
6. IF o Postgres do compose não estiver acessível quando o pytest roda THEN o pytest SHALL falhar imediatamente com uma mensagem que instrui `docker compose up -d postgres`. <!-- unwanted-behavior -->
7. WHEN o serviço postgres inicia pela primeira vez THEN um script de init SHALL criar o banco `ritmo_test` além do `ritmo`. <!-- event-driven -->
8. The system SHALL persistir os dados do Postgres em volume nomeado, de modo que `docker compose down` (sem `-v`) preserve os dados. <!-- ubiquitous -->
9. The system SHALL usar o driver psycopg3 (`postgresql+psycopg://`) sem nenhum código específico de SQLite remanescente no engine. <!-- ubiquitous -->

**Independent Test**: `docker compose up -d` → `curl localhost:8000/api/health` (200) + `curl -I localhost:3000` (200) + `uv run pytest` verde contra o Postgres + reiniciar o compose e confirmar que o schema e o volume persistem.

---

## Edge Cases

- WHEN o host já ocupa a porta 5432 THEN o compose não sobe — documentar override de porta no README (ex.: `5433:5432`) sem esconder o erro
- IF o container do backend subir antes do postgres aceitar conexões THEN o `depends_on: condition: service_healthy` retém o start até o healthcheck passar
- WHEN o pytest roda em paralelo com o backend dev THEN os bancos são distintos (`ritmo_test` vs `ritmo`) — nenhum conflito
- IF a imagem postgres:16 não existir local THEN o compose faz pull — documentado como primeiro `up` mais lento

---

## Requirement Traceability

| Requirement ID | Story (AC) | Phase | Status |
| -------------- | ---------- | ----- | ------ |
| INFRA-01 | P1 · AC1 (compose 3 serviços + healthcheck) | Design | Verified |
| INFRA-02 | P1 · AC2 (backend 200 em 8000, frontend 200 em 3000) | Design | Verified |
| INFRA-03 | P1 · AC3 (DATABASE_URL só por env) | Design | Verified |
| INFRA-04 | P1 · AC4 (create_all + seed no Postgres) | Design | Verified |
| INFRA-05 | P1 · AC5 (pytest em ritmo_test, estado limpo) | Design | Verified |
| INFRA-06 | P1 · AC6 (Postgres fora → erro claro) | Design | Verified |
| INFRA-07 | P1 · AC7 (init cria ritmo_test) | Design | Verified |
| INFRA-08 | P1 · AC8 (volume nomeado persiste) | Design | Verified |
| INFRA-09 | P1 · AC9 (psycopg3, zero código SQLite) | Design | Verified |

**ID format**: `INFRA-NN` · **Status values**: Pending → In Design → In Tasks → Implementing → Verified

**Coverage**: 9 total (1:1 com as ACs), 0 mapped to tasks (fase Tasks pendente), 9 unmapped

---

## Success Criteria

Como sabemos que a feature é um sucesso:

- [ ] `docker compose up -d` de um clone limpo sobre os 3 serviços saudáveis, sem passo manual além do `.env`
- [ ] `GET /api/health` 200 no backend em container, conectado ao Postgres
- [ ] `uv run pytest` verde contra o Postgres do compose, sem estado vazando entre testes
- [ ] `docker compose down && docker compose up -d` preserva o schema e o usuário default (volume nomeado)
- [ ] Nenhuma string `sqlite://` no código ou no default de config
