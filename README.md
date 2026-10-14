# Ritmo

Plataforma pessoal de corrida: sync do Garmin, painéis que importam
(**Hoje · Treinos · Potencial · Saúde**) e avaliação de treino com IA sob demanda.

> Plano completo, decisões travadas e roadmap: [`docs/PLANO_PLATAFORMA.md`](docs/PLANO_PLATAFORMA.md) — fonte de verdade do produto.
>
> Status: **Fase 0 concluída** (repo + esqueletos backend/frontend). As features da Fase 1 entram pelo workflow spec-driven abaixo.

## Estrutura

```
ritmo/
├── backend/            # FastAPI + SQLAlchemy (SQLite WAL na v1)
│   ├── app/
│   │   ├── core/       # config 100% por env vars
│   │   ├── db/         # engine + modelos (user_id em TODA tabela)
│   │   ├── garmin/     # token_utils portado do garmin_mcp (tokens existentes)
│   │   └── vdot/       # calibrate_vdot.py (portar p/ funções puras na Fase 1)
│   ├── data/           # vdot_zones.json — zonas atuais (VDOT 50.2, teste 10K 41:15)
│   └── tests/          # smoke tests da Fase 0
├── frontend/           # Next.js + Tailwind + Recharts (tema escuro, mobile-first)
├── docs/               # PLANO_PLATAFORMA.md
└── .opencode/skills/   # tlc-spec-driven — workflow de desenvolvimento
```

## Rodando

### Backend (FastAPI)

```bash
cd backend
cp .env.example .env                 # preencha NVIDIA_API_KEY (build.nvidia.com)
uv sync
uv run uvicorn app.main:app --reload # http://localhost:8000/docs
uv run pytest                       # testes
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

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
2. SQLAlchemy — Postgres na Fase 2.5 é só trocar a connection string
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
