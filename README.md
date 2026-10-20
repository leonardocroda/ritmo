# Ritmo

Plataforma pessoal de corrida: sync do Garmin, painéis que importam
(**Treinos · Performance · Saúde**) e avaliação de treino com IA sob demanda.

> Plano completo, decisões travadas e roadmap: [`docs/PLANO_PLATAFORMA.md`](docs/PLANO_PLATAFORMA.md) — fonte de verdade do produto.
>
> Status: **Fase 0 concluída** · Infra Postgres + compose concluída · Fase 1: sync Garmin ✅ · painel Treinos ✅ · painel Performance ✅ (ex-Potencial, AD-017) · painel Saúde ✅ · **Avaliar com IA** ✅ — MVP da Fase 1 completo · painel Hoje adiado e fora da nav (AD-011/AD-016 — volta pós-08/11, redesenhado com uso real) · **Fase 1.5 em andamento** (AD-012..015): **auth próprio + convite ✅** (login, sessão sliding 30d, Sair no header, bootstrap por CLI — §Login e acesso) · **user-scope ✅** (toda query por usuário da sessão + isolamento A×B) · zonas/LTHR no banco, cofre de tokens Garmin criptografado e `/perfil` a seguir.

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

O frontend chama a API **pelo próprio Next** (rewrite same-origin: `/api/*` →
`BACKEND_URL`, AD-020) — o cookie de sessão vale para o host que você abriu e
`localhost:3000` e `http://<IP-da-LAN>:3000` funcionam igual. Mudou o IP do PC
(DHCP)? **Nada muda**: o acesso pelo celular continua `http://<novo-IP>:3000`, sem
rebuild (o `BACKEND_URL` é o hostname interno do compose, não o IP externo).

## Login e acesso

Auth própria (feature auth, AD-013): **toda tela e todo endpoint de dado exigem sessão** —
sem ela, a API responde 401 e as telas caem no `/login`. Fica público só o que precisa:
`GET /api/health` (liveness) e as telas de auth (`/login`, `/registrar`).

### Primeiro acesso (bootstrap do dono)

O usuário seed (id 1) nasce sem credenciais. Defina o email+senha pela CLI:

```bash
docker compose exec backend python -m app.auth.set_password
# fora do compose: cd backend && uv run python -m app.auth.set_password
```

Email via `input`, senha via `getpass` (vincula o seed preservando o display_name). A CLI
também serve de **reset de suporte**: conta existente troca o hash da senha sem tocar no
nome; email desconhecido cria conta nova.

### Convidados (cadastro por convite)

1. Defina `INVITE_CODE` no `.env` do backend e reinicie — **vazio = registro desabilitado**
   (403 na tela de cadastro). O acesso por usuário (`user-scope`) já está no ar: cada
   convidado vê só os próprios dados.
2. Compartilhe `http://<host>:3000/registrar` + o código. Cadastro válido **já entra logado**
   (auto-login) e aterrissa nos painéis.

### Sessão

- Cookie `ritmo_session` **HttpOnly** + `SameSite=Lax`, host-only **do host que você abriu**
  (o rewrite same-origin do AD-020 entrega o cookie no próprio frontend — `localhost:3000` e
  `http://<IP-da-LAN>:3000` funcionam igual), 30 dias com renewal **sliding**: request
  autenticado com ≤15 dias restantes estende a validade para +30d — usuário ativo nunca é
  deslogado no meio do uso.
- **Sair** (header, ao lado do sync) revoga só a sessão do dispositivo corrente; celular e
  PC podem estar logados ao mesmo tempo.
- Sessão expirou em uso? O primeiro fetch recebe 401 e o client redireciona para
  `/login?next=<rota atual>` — após o login, volta à rota original. Logado abrindo
  `/login` ou `/registrar`, vai direto para `/treinos`.

> **Acesso por usuário (`user-scope`) ativo**: toda query de leitura e gravação usa o
> `user_id` do usuário da sessão — painéis, sync e avaliações são isolados por dono
> (teste A×B ponta a ponta na suíte). O registro via convite pode ser ligado.

## Painel Treinos

A lista de corridas em `/treinos` (navegação no header: **Treinos ·
Performance · Saúde**). Tudo lido do banco próprio: **nenhuma chamada à API do Garmin**
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

## Painel Performance (ex-Potencial)

"Qual meu máximo e a que distância dele estou?" — `/performance` responde
em 4 blocos narrativos, abertos pela linha-guia no topo (a pergunta do
painel + a régua de leitura: provas e testes de campo medem,
estimativas do relógio só aproximam) e com o retrato honesto (AD-004:
**faixa, nunca número único mágico**). Leitura 100% do banco próprio:
**zero chamadas à API do Garmin** (AD-002); o sync é quem ganhou a
etapa de **predições de prova** (`get_race_predictions`, 1 chamada
sequencial por sync, upsert por evento).

- **Onde estou** — a lacuna e a régua: card da lacuna com a narrativa
  honesta de §9.5 ("você já demonstrou X; o teste atual valida Y — o
  meio é o alvo honesto") + timeline VDOT: cada teste/prova máxima
  datada vira um ponto (VDOT recalculado pela forma fechada de
  Daniels), linha no VDOT corrente e **faixa sombreada até o
  demonstrado**; provas com PR certificado na mesma data não duplicam
  ponto e PRs sem data não viram ponto (não há como plotar sem
  inventar). O subtítulo da seção define VDOT (régua de equivalência
  de Daniels), corrente (último teste calibrado), demonstrado (melhor
  prova máxima) e a lacuna %.
- **O que isso prevê** — estimativas por método contra os PRs: 4
  estimativas lado a lado por distância (5K/10K/meia/maratona) com
  **legenda por método sempre visível** — **Garmin** (preditor
  sincronizado), **Riegel** (T2 = T1 × (D2/5000)^1.06, âncora fixa no
  PR de 5K — sem âncora, "—"), **equivalência VDOT** (do número do
  `vdot_zones.json`, nunca parse das strings de pace) e **média
  honesta** (só das estimativas presentes) — + PR histórico com data.
  Seguido do **decay por distância**: pace real (PR) vs ideal
  (equivalência VDOT corrente), Δ% sinalizado com o maior gap
  destacado e explicação do sinal (negativo = gap de
  execução/especificidade, não de motor).
- **O que o relógio estima** — VO2max: linha do `vO2MaxValue` do
  relógio com selo "estimativa" e nota de hierarquia (provas/testes >
  algoritmo — AD-005); bloco inteiro ausente quando não há dados
  (POT-27).
- **Carga de treino** — a curva PMC de volta ao painel (AD-017 reverte
  a CLR-03): CTL/ATL em linhas e TSB em barras (janela fixa de 60 dias)
  com os destaques do último dia — fitness, fadiga, forma e ACWR ("—"
  até 28 dias completos de carga, SYNC-24).

Com a curva PMC de volta ao painel (AD-017 — o bloco mudou de endpoint
junto com a tela, AD-009): `GET /api/potential` entrega `{vdot,
predictions, vo2max, decay, pmc}` com janela fixa de 60d — o `?days=`
segue fora do contrato (um valor qualquer é query não declarada,
ignorada). Estado vazio (timeline só com o teste de calibração, sem
VO2max, sem PRs canônicos e sem linhas de carga) orienta o primeiro
sync.

Validação real (16/10/2026): sync com `predictions: 4` no stats e
`pr_date` auto-curado nas 7 PRs (fix do key-case `prStartTimeGmt`);
endpoint pinado contra o código — demonstrado 51,62 (5K 19:23,8),
lacuna 97,3%, Riegel 10K 2426,5s, decaimento da maratona −22,1% (gap de
execução: 5K/meia rendem no ideal, maratona não); suite com 228 testes
no Postgres do compose.

## Painel Saúde

O corpo sob o treino — `/saude` conta a história em 4 seções numeradas,
ligadas pela linha-guia no topo (o fio: o sono recupera, o corpo
responde, dormir mal custa — e a vida fora da corrida sustenta tudo).
A curva PMC mudou-se pro Painel Performance (AD-017 reverte a CLR-03).
Um round-trip: `GET /api/health/summary?days=60`
(`days` 7–365 validado, 422 fora do intervalo) traz o painel inteiro;
blocos de série vazios vêm `null` — estado vazio honesto, não erro.
Leitura 100% do banco próprio (AD-002).

- **1. Sono**: duração de cada noite contra o piso de 7h, fases do sono,
  REM na banda de 21–31% e o padrão por dia da semana.
- **2. Recuperação**: HRV noturna e frequência cardíaca de repouso —
  os sinais diários de quanto da carga está virando adaptação.
- **3. Dose-resposta**: noites curtas (<6h) contra adequadas (≥6h45) —
  o preço de dormir mal em HRV e score médios.
- **4. Equilíbrio de vida**: força por semana, yoga e estresse médio —
  a base fora da corrida que sustenta (ou sabota) a recuperação.

Com nada pessoal no banco, o estado vazio orienta o primeiro sync; a
série de carga sozinha não acende mais nada aqui — a curva mora no
Painel Performance (AD-017).

Os dois painéis seguem o padrão de clareza **AD-009**: cabeçalho forte
por seção (índice + título + subtítulo "o que é / por que importa"
sempre visível), selo de fonte/método quando o número precisa de
origem e o payload de cada endpoint espelhando exatamente o que o
painel renderiza.

Validação real (17/10/2026, feature panel-clarity): UAT aprovado no
celular 390px via LAN — 5 seções e 3 blocos distinguíveis de relance,
Carga de treino com os valores do dia (CTL 132,2 · ATL 141,3 · TSB
−9,2 · ACWR 1,1), sem scroll horizontal; contrato verificado ao vivo
(`pmc` entre `stress` e `dose_response`, potencial sem `pmc`/`days`);
suite com 268 testes no Postgres do compose, migração 1:1 dos testes
de PMC para a suite de saúde (262 → 268).

## Avaliar com IA

No detalhe de uma corrida: campo de **intenção** (tipo pré-preenchido com
o inferido — chaves 1:1 — + texto livre opcional) → botão **Avaliar com
IA**. O backend monta o **payload determinístico em Python** (zonas por
volta, % por zona e na zona alvo por intenção, consistência, contexto do
dia, PMC, PRs datados, padrões ativos, VDOT e LTHR — só o que existir),
grava a avaliação como **`pending` e responde 201 na hora** — a NIM é
consumida por um worker em background (padrão do sync, BackgroundTasks).
A resposta é validada contra o JSON de veredito do plano §9.2 e a linha
concluída com `model`, `prompt_version`, `tokens_in/out` e o payload
inteiro (auditoria AD-003). A UI polla o status (~2s): card "Analisando
treino…" → card do veredito quando pronto.

- **Zero alucinação de número**: o `pct_zona_alvo` do card é sempre o
  calculado em Python — o eco do LLM é sobrescrito antes de gravar.
- **A tentativa nunca se perde** (emenda job, 18/10): NIM fora, timeout
  ou JSON fora do contrato → a linha fica `status=error` com o **motivo
  no histórico** (ex.: `finish_reason=length`, HTTP 429) e o card de
  erro mostra a causa; key ausente/404/422 continuam síncronos e nada
  criam. Sem retry automático — cada pedido custa tokens e é explícito.
- **Restart seguro**: pending órfãs viram `error` "interrompida" no
  startup (padrão `recover_stale_jobs`).
- **Re-avaliação**: linha nova, nunca sobrescreve; a mais recente é o
  card, as anteriores ficam listadas (⏳ pendente, ⚠️ falhou); badge
  "Avaliado" na lista de treinos acende quando o veredito chega.
- **Config** (`backend/.env`): `NVIDIA_API_KEY` (build.nvidia.com — sem
  ela o botão responde 503), `NVIDIA_MODEL` (default `z-ai/glm-5.3`;
  o flash `z-ai/glm-5.3-flash` é a opção rápida para o dia a dia),
  `NVIDIA_TIMEOUT_S` (default 420 — o glm-5.3 raciocina além de 120s),
  `LTHR_BPM` (default 177 — a recalibração sobrepõe por env).

Validação (18/10/2026): suite com 362 testes no Postgres do compose —
NIM 100% mockada nos testes, nenhum teste chama a API real. UAT aprovado
no celular via LAN: glm-5.3 (thinking) e flash testados com treino real;
HTTP 429 virou linha de erro com motivo — a emenda job nasceu desse UAT.

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
11. **Fase 1.5 (AD-012..015)**: auth próprio self-hosted (email+senha+sessão, cadastro por
    convite) · zonas VDOT e LTHR por usuário no banco (JSON vira seed) · tokens Garmin no
    banco criptografados (Fernet, refresh persistido) · login Garmin segue CLI
    operador-assistida (`login --user`) · MVP segue no PC/LAN — HTTPS/deploy na Fase 2.5

Detalhes, arquitetura e roadmap completo: [`docs/PLANO_PLATAFORMA.md`](docs/PLANO_PLATAFORMA.md).
