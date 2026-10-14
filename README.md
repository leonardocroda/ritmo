# Ritmo

Plataforma pessoal de corrida: sync do Garmin, painéis que importam
(**Hoje · Treinos · Potencial · Saúde**) e avaliação de treino com IA sob demanda.

> Plano completo, decisões travadas e roadmap: [`docs/PLANO_PLATAFORMA.md`](docs/PLANO_PLATAFORMA.md) — fonte de verdade do produto.
>
> Status: **Fase 0 concluída** · Infra Postgres + compose concluída · Fase 1 (sync Garmin) em andamento.

## Estrutura

```
ritmo/
├── backend/            # FastAPI + SQLAlchemy (Postgres, AD-007)
│   ├── app/
│   │   ├── core/       # config 100% por env vars
│   │   ├── db/         # engine + modelos (user_id em TODA tabela)
│   │   ├── garmin/     # token_utils portado do garmin_mcp (tokens existentes)
│   │   └── vdot/       # calibrate_vdot.py (portar p/ funções puras na Fase 1)
│   ├── data/           # vdot_zones.json — zonas atuais (VDOT 50.2, teste 10K 41:15)
│   └── tests/          # rodam no Postgres do compose (banco ritmo_test)
├── frontend/           # Next.js + Tailwind + Recharts (tema escuro, mobile-first)
├── docker-compose.yml  # stack local: postgres + backend + frontend
├── docs/               # PLANO_PLATAFORMA.md
└── .opencode/skills/   # tlc-spec-driven — workflow de desenvolvimento
```

## Rodando

### Stack completo (recomendado)

```bash
docker compose up -d          # postgres (healthcheck) + backend :8000 + frontend :3000
curl http://localhost:8000/api/health
```

Pré-requisito: Docker. No primeiro `up` a imagem `postgres:16` é baixada (mais lenta);
depois fica cacheada. O init script cria os bancos `ritmo` e `ritmo_test` na primeira
inicialização do volume.

### Dev diário (hot-reload fora do compose)

```bash
docker compose up -d postgres  # só o banco
cd backend
cp .env.example .env           # DATABASE_URL aponta para localhost:5432
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs

cd ../frontend
npm install
npm run dev                    # http://localhost:3000
```

### Testes

```bash
docker compose up -d postgres  # obrigatório: a suite roda no banco ritmo_test
cd backend
uv run pytest
```

Sem o Postgres de pé, o pytest falha imediatamente instruindo
`docker compose up -d postgres` — nenhum teste roda em SQLite.

### Porta 5432 ocupada no host?

Sobrescreva o binding com um `docker-compose.override.yml`:

```yaml
services:
  postgres:
    ports:
      - "5433:5432"
```

Dentro do compose nada muda (o backend usa o hostname `postgres`); apenas o
`DATABASE_URL` do `.env` passa a apontar para `localhost:5433`.

## Workflow de desenvolvimento — spec-driven

Toda feature nasce de um **spec validado**, vira **tasks atômicas** e termina em
**commits atômicos** com verificação independente (author ≠ verifier).

A skill [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills)
(Tech Lead's Club, v3.3.0, CC-BY-4.0, autor: Felipe Rodrigues) já está instalada
em `.opencode/skills/tlc-spec-driven/`.

Frases-gatilho no agente:

| Frase | Fase |
|---|---|
| "specify feature X" | requisitos EARS testáveis (`.specs/features/X/spec.md`) |
| "discuss feature X" | decisões de pontos cinzentos (`context.md`) |
| "design X" / "tasks X" | arquitetura e tasks atômicas (quando o escopo pede) |
| "implement X" | execução: gate de teste por task + commit atômico |
| "validate X" / "UAT" | verificação independente com evidência `file:line` |
| "record decision" / "pause" / "resume" | memória do projeto (`.specs/STATE.md`) |

Gates determinísticos (rodam antes de qualquer revisão humana):

```bash
python .opencode/skills/tlc-spec-driven/scripts/validate_spec.py <feature>
python .opencode/skills/tlc-spec-driven/scripts/validate_tasks.py <feature>
python .opencode/skills/tlc-spec-driven/scripts/check_commit.py --message "<msg>"
python .opencode/skills/tlc-spec-driven/scripts/validate_state.py <feature>
```

Memória do projeto: `.specs/STATE.md` (decisões AD-NNN + handoff) e
`.specs/LESSONS.md` — criados automaticamente pela primeira feature.

## Decisões travadas (resumo)

1. `user_id` em todas as tabelas (usuário único default na v1)
2. SQLAlchemy + **Postgres desde a v1** (AD-007) — stack local sobe por `docker-compose.yml`
3. Sync = job isolado `SyncJob(user_id, janela)` — **sequencial, nunca paralelo**
   (rate limit do Garmin), re-puxa últimos 3 dias + atividades novas
4. Toda avaliação grava `model`, `prompt_version` e tokens
5. Config 100% por env vars — nada hardcoded
6. Python calcula os números (determinístico); o LLM só interpreta → JSON de veredito
7. Potencial = faixa honesta (VDOT demonstrado ~53 vs corrente 50.2), nunca número único
8. UI lê **só** do banco próprio; Garmin só é chamado pelo botão de sync
9. Hierarquia de confiança: pace/GPS > FC de pulso (FC corrobora, não decide)
10. Intenção declarada > números brutos — avaliação só sob pedido (custo de tokens)

Detalhes, arquitetura e roadmap completo: [`docs/PLANO_PLATAFORMA.md`](docs/PLANO_PLATAFORMA.md).
