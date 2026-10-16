# Ritmo

Plataforma pessoal de corrida: sync do Garmin, painéis que importam
(**Hoje · Treinos · Potencial · Saúde**) e avaliação de treino com IA sob demanda.

> Plano completo, decisões travadas e roadmap: [`docs/PLANO_PLATAFORMA.md`](docs/PLANO_PLATAFORMA.md) — fonte de verdade do produto.
>
> Status: **Fase 0 concluída** · Infra Postgres + compose concluída · Fase 1: sync Garmin ✅ · painel Treinos ✅ · painel Potencial ✅ · próximos: Saúde, Avaliar com IA, Hoje.

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

## Sync do Garmin

O botão **Puxar do Garmin** (header global, visível de qualquer painel) roda
um job sequencial que popula o banco: atividades + splits, sono, HRV, RHR,
body battery, stress, recordes de corrida e a série de carga
(CTL/ATL/TSB/ACWR, calculada localmente a partir do `training_load` — zero
chamadas extras à API).

- **Primeira sync (backfill)**: 180 dias de atividades + 60 dias de saúde +
  recordes. São ~400 chamadas sequenciais (1 por segundo, nunca em paralelo) —
  cerca de 10 minutos com o progresso visível no botão ("Puxando 231
  atividades…", "Puxando sono: 47 dias…").
- **Syncs seguintes**: janela incremental (re-puxa os últimos 3 dias) — ~23
  chamadas em ~35s. Rodar 2× não cria duplicatas: toda escrita é upsert por
  chave natural (`garmin_id`, `(user_id, data)`, `(user_id, evento)`,
  `(activity_id, idx)`).
- **Guard rails** (todas as `SYNC_*` documentadas em `backend/.env.example`):
  teto `SYNC_MAX_CALLS` (default 1500), intervalo mínimo
  `SYNC_CALL_INTERVAL_S` (default 1s), retry com backoff 2/4/8s.

Validação real (14/10/2026): backfill com 232 atividades + 1563 splits +
60–61 dias de cada tipo de saúde + 7 recordes, `calls_made` 408 em 606s;
sync incremental seguinte com 23 chamadas e contagens idênticas; PMC de 3
dias conferida contra cálculo manual; token inválido termina `error` com
`reauth_needed` e nenhuma chamada de dados feita.

### Reconectar Garmin (token expirado)

O token dura ~6 meses. Quando expira, o job termina `error` com
`reauth_needed` e o botão mostra **Reconectar Garmin** com a instrução da
CLI — a UI nunca pede credenciais (decisão do spec: re-auth é CLI):

```bash
cd backend
uv run python -m app.garmin.login   # email via input, senha via getpass, MFA quando exigido
```

No compose: `docker compose exec backend python -m app.garmin.login` — os
tokens do host (`~/.garminconnect`) já estão montados em `/garminconnect`.
Depois do login, clicar de novo no botão retoma o sync incremental, sem
backfill.

### Acessando pela LAN

O frontend chama a API pela URL de `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`), inlada no build do Next — mudar o valor exige
rebuild do frontend, não basta restart. Para usar o Ritmo de outro aparelho
da rede (ex.: celular), aponte para o IP do host:

```bash
NEXT_PUBLIC_API_URL=http://192.168.0.10:8000 docker compose up -d --build frontend
```

## Painel Treinos

A lista de corridas em `/treinos` (navegação no header: **Hoje · Treinos ·
Potencial · Saúde** — os outros painéis entram nas próximas features da
Fase 1). Tudo lido do banco próprio: **nenhuma chamada à API do Garmin**
ao navegar (AD-002).

- **Lista**: corridas ordenadas da mais recente, com tipo inferido
  determinístico (prova → intervalado → limiar → tempo → progressivo →
  longão ≥16km → fácil, calculado sobre splits + zonas VDOT), distância,
  pace, FC e badge "Avaliado" quando houver avaliação. Paginação de 30
  com "Carregar mais" e filtro "todas as atividades" (yoga/força sem pace).
- **Detalhe**: gráfico de splits com **largura da barra proporcional à
  duração da volta** (pausa de 30s ≠ tiro de 3km), cor por **zona VDOT
  pessoal** (verde=easy, azul=marathon, laranja=threshold, vermelho=
  interval, roxo=repetition; cortes no meio dos gaps do
  `backend/data/vdot_zones.json`), linha de FC e relevo. Tooltip com os
  valores reais; pace clampado a 3:00–7:00/km só no desenho.
- **Métricas de consistência** (corridas ≥8km com ≥4 voltas): equilíbrio
  1ª vs 2ª metade (por distância acumulada), drift cardíaco (exibido ao
  lado do Δ pace — AD-005: drift só se interpreta a ritmo constante),
  decoupling FC/pace e fade de cadência. Funções puras, determinísticas.
- **Faixa de contexto**: sono, HRV, RHR do dia do treino + temperatura
  média das voltas — **só o que existir** (treinos antigos, sincronizados
  antes das colunas de cadência/temperatura, mostram menos até o re-pull).

Validação real (15/10/2026): tipos inferidos conferidos em treinos
conhecidos (strides → intervalado, 8x800m → intervalado, 2x3km limiar →
limiar, 16km → longão); consistência do longão conferida contra cálculo
manual (Δ pace −4,65s/km · drift +9,98 bpm · decoupling +7,9%); suite com
170 testes no Postgres do compose.

## Painel Potencial

"Qual meu máximo e a que distância dele estou?" — `/potencial` responde
com o retrato honesto (AD-004: **faixa, nunca número único mágico**).
Leitura 100% do banco próprio: **zero chamadas à API do Garmin**
(AD-002); o sync é quem ganhou a etapa nova de **predições de prova**
(`get_race_predictions`, 1 chamada sequencial por sync, upsert por
evento).

- **Timeline VDOT**: cada teste/prova máxima datada vira um ponto (VDOT
  recalculado pela forma fechada de Daniels — a mesma que gerou o 50,2
  do teste de calibração), linha no VDOT corrente e **faixa sombreada até
  o demonstrado**, com a lacuna narrada ("você já demonstrou X; o teste
  atual valida Y — o meio é o alvo honesto", §9.5). Provas com PR
  certificado na mesma data não duplicam ponto; PRs sem data não viram
  ponto (não há como plotar sem inventar).
- **Previsões vs PRs**: 4 estimativas lado a lado por distância
  (5K/10K/meia/maratona) — **Garmin** (preditor sincronizado),
  **Riegel** (T2 = T1 × (D2/5000)^1.06, âncora fixa no PR de 5K — sem
  âncora, "—"), **equivalência VDOT** (do número do
  `vdot_zones.json`, nunca parse das strings de pace) e **média honesta**
  (só das estimativas presentes) — + PR histórico com data.
- **PMC**: CTL/ATL linhas + TSB barras (janela de 180 dias, `days`
  aceita 1–365), cards do último dia com ACWR ("—" até 28 dias completos
  de carga — SYNC-24).
- **Tendência VO2max**: linha do `vO2MaxValue` do relógio com selo
  "estimativa" e nota de hierarquia (provas/testes > algoritmo — AD-005).
- **Decay por distância**: pace real (PR) vs ideal (equivalência VDOT
  corrente) com Δ% sinalizado e o maior gap destacado — v1 em números,
  sem gráfico dedicado (§9.1).

Validação real (16/10/2026): sync com `predictions: 4` no stats e
`pr_date` auto-curado nas 7 PRs (fix do key-case `prStartTimeGmt`);
endpoint pinado contra o código — demonstrado 51,62 (5K 19:23,8),
lacuna 97,3%, Riegel 10K 2426,5s, decaimento da maratona −22,1% (gap de
execução: 5K/meia rendem no ideal, maratona não); suite com 228 testes
no Postgres do compose.

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
