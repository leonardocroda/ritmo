# Avaliar com IA (ai-evaluation) — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/ai-evaluation/design.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` §Testes/§Rodando (`uv run pytest` no Postgres do compose, a partir do host); `frontend/AGENTS.md` (Next.js com breaking changes — ler `node_modules/next/dist/docs/` antes de codar frontend); AD-003/AD-005/AD-009 no `STATE.md`. Sem CONTRIBUTING/CI — fortes defaults onde não há padrão. Base atual: **280 testes** no HEAD (verificado na T1 — o "268" do README estava defasado; 284 com os testes novos da T1) — a contagem nunca cai dentro de uma task.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domínio puro evaluation (`schemas.py`, `prompt.py`) | unit | 1:1 com ACs de validação (EVAL-04/11): enums, obrigatórios, extras ignorados, ≤500 chars; marcadores estruturais do prompt (EVAL-03) | `backend/tests/test_evaluation_schemas.py`, `backend/tests/test_evaluation_prompt.py` | `cd backend; uv run pytest` |
| Payload determinístico (`payload.py`) | integration (DB semeados — padrão da suite) | 1:1 com EVAL-02/16: blocos presentes só com o que existir, `% zona alvo` com aritmética exata, progressivo/prova sem alvo, sem voltas → bloco omitido | `backend/tests/test_evaluation_payload.py` | `cd backend; uv run pytest` |
| Cliente NIM (`nim.py`) | unit (httpx MockTransport — **nenhum teste chama a NIM real**) | Todos os caminhos (EVAL-03/13): 200, JSON cercado, `usage` ausente, HTTP erro, timeout, corpo não-JSON | `backend/tests/test_evaluation_nim.py` | `cd backend; uv run pytest` |
| Service evaluation (`service.py`) | integration (NIM mockada via monkeypatch) | 1:1 com EVAL-04/06/19: persiste todos os campos, sanitiza eco numérico, `evaluated=true`, re-avaliação = linha nova, falha → 0 linhas | `backend/tests/test_evaluation_service.py` | `cd backend; uv run pytest` |
| Router evaluation (`router.py`) | integration (TestClient + Postgres) | Todas as rotas: 200 happy + cada erro mapeado (404/422×3/503/502×2/504/500) — EVAL-09..15 | `backend/tests/test_evaluation_api.py` | `cd backend; uv run pytest` |
| Detalhe activities estendido | integration (mesma suite) | EVAL-17: lista mais-recente-primeiro, vazia sem avaliações; `activity_type` no contrato | `backend/tests/test_activities_api.py` (extensão) | `cd backend; uv run pytest` |
| Frontend (`lib/api.ts`, componentes) | none | Sem runner de teste no projeto (`frontend/package.json`) — `npm run build` + `npm run lint` por task; verificação de comportamento no UAT (padrão das features anteriores) | `frontend/src/**` | `cd frontend; npm run build; npm run lint` |
| Docs (`README.md`, `docs/PLANO_PLATAFORMA.md`) | none | build gate only (docs honestas sobre o novo contrato) | - | - |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (suite roda no banco `ritmo_test` do compose, a partir do host). Gates de commit: `python .opencode/skills/tlc-spec-driven/scripts/check_commit.py --message "<msg>"` antes de cada commit.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks backend com testes novos | `cd backend; uv run pytest` |
| Full | Fim de fase com integração | `cd backend; uv run pytest` |
| Build | Tasks frontend / docs | backend da task mudou: `cd backend; uv run pytest` · frontend: `cd frontend; npm run build; npm run lint` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação do domínio evaluation (backend)

Config, contratos, prompt e payload — cada peça testável isolada.

```
T1 → T4

T2

T3
```

### Phase 2: Motor e endpoint (backend)

Cliente NIM, orquestração, endpoint com mapa de erros e detalhe estendido.

```
T5 → T6 → T7

T8
```

### Phase 3: Frontend + docs

Contrato espelhado, formulário, card, composição e documentação.

```
T9 → T10
T9 → T11
T10 → T12
T11 → T12
T12 → T13
```

---

## Task Breakdown

### Phase 1: Fundação do domínio evaluation (backend)

#### T1: Config NIM (timeout) + LTHR + httpx runtime

**What**: `nvidia_timeout_s: float = 120.0` e `lthr_bpm: int = 177` em Settings (documentados em docstring citando EVAL); httpx sai do dev-group e vira dependência runtime no pyproject; `.env.example` ganha `NVIDIA_TIMEOUT_S=120` e `LTHR_BPM=177` (comentados — defaults vivem no código, env sobrepõe).
**Where**: `backend/app/core/config.py` (modify)
**Depends on**: None
**Reuses**: padrão de settings `SYNC_*` (docstring por campo, grupo NVIDIA já existe)
**Requirement**: EVAL-02 (LTHR no payload), EVAL-13 (timeout configurável)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `Settings.nvidia_timeout_s == 120.0` e `Settings.lthr_bpm == 177` por default; env `NVIDIA_TIMEOUT_S`/`LTHR_BPM` sobrepõem
- [x] `httpx` em `dependencies` (runtime) do pyproject — `uv sync` verde com o import usado na T5
- [x] `.env.example` documenta as duas vars novas junto ao bloco NVIDIA
- [x] Testes de config no padrão do `test_sync_config.py`: defaults + override por env
- [x] Gate passa; contagem da suite sobe (baseline real 280 — o "268" do README estava defasado; 284 = 280 + 4 novos; nunca cai)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(evaluation): nim timeout and lthr settings`

---

#### T2: Schemas do domínio (EvaluateIn, EvaluationOut, VerdictJson)

**What**: `backend/app/evaluation/schemas.py` com os três contratos do design: `EvaluateIn` (Literal dos 7 tipos + `intent_text` `max_length=500`), `EvaluationOut` (shape de saída persistido) e `VerdictJson` (§9.2: enums `veredito`/`confianca`, `execucao_vs_intencao{pct_zona_alvo, principais_desvios}`, 3 listas; `extra="ignore"` — extras ignorados, obrigatórios ausentes rejeitam — Decisão E). Docstrings citam os EVALs.
**Where**: `backend/app/evaluation/schemas.py` (new)
**Depends on**: None
**Reuses**: convenção de modelos inline dos routers (extraída para módulo próprio — evita ciclo activities↔evaluation)
**Requirement**: EVAL-04, EVAL-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `VerdictJson` aceita o JSON §9.2 válido completo; rejeita `veredito` fora do enum de 5; rejeita campo obrigatório ausente; ignora chave extra
- [x] `EvaluateIn` rejeita `intent_type` fora dos 7 tipos e `intent_text` com 501 chars (422 automático via FastAPI na T7; teste unitário no pydantic)
- [x] `EvaluationOut` espelha exatamente os campos gravados (`model`, `prompt_version`, `tokens_in/out`, `verdict_json`, `created_at`…)
- [x] Gate passa; contagem sobe (300 = 284 + 16; o teste de obrigatório-ausente pegou um default espúrio nas listas §9.2 e a implementação conformou ao spec)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(evaluation): request and verdict schemas`

---

#### T3: System prompt v1 destilado de analyze-garmin-run

**What**: `backend/app/evaluation/prompt.py` com `PROMPT_VERSION = "v1"` e `SYSTEM_PROMPT_V1` (~2k tokens, PT-BR): papel (avaliador de execução vs intenção declarada), regras dos 5 vereditos com quando usar cada, intenção primeiro (fácil rápido demais é falha), hierarquia AD-005 (pace/zona decide, FC corrobora contra o LTHR), regra do calor (>25°C julga fácil por esforço), elevação por volta explica desvio, contexto muda ou confirma (nunca decora), formato de saída: **exatamente** o JSON §9.2 usando **exclusivamente os números do payload** (nunca recalcular, `pct_zona_alvo` ecoado ou null).
**Where**: `backend/app/evaluation/prompt.py` (new)
**Depends on**: None
**Reuses**: `C:\Users\leona\projects\garmin_mcp\.opencode\skills\analyze-garmin-run\SKILL.md` (regras §C/§D, hierarquia, calor, bordas — destilado, não copiado)
**Requirement**: EVAL-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `PROMPT_VERSION == "v1"` casado com `SYSTEM_PROMPT_V1` (toda avaliação rastreia o prompt — AD-003)
- [x] Prompt contém os marcadores contratuais: os 5 vereditos, as 7 chaves do JSON de saída (§9.2), instrução de não recalcular, hierarquia pace>FC, regra do calor, PT-BR
- [x] Testes unitários de marcadores estruturais (asserts de conteúdo — qualidade do texto é UAT, os asserts pegam o contrato)
- [x] Gate passa; contagem sobe (308 = 300 + 8)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(evaluation): distilled verdict system prompt v1`

---

#### T4: Payload determinístico do banco próprio

**What**: `backend/app/evaluation/payload.py`: `TARGET_ZONES` (facil→easy · tempo→threshold · limiar→threshold · intervalado→interval · longao→easy+marathon · progressivo/prova→None) e `build_evaluation_payload(db, activity, detail, intent_type, intent_text)` — base `get_activity_detail` + blocos: `intencao`, `tempo_por_zona_pct` (sobre a duração das voltas com zona), `zona_alvo` com `pct_zona_alvo` (Σ duração nas zonas alvo ÷ Σ duração com zona, 1 decimal — omitido sem alvo/voltas), `carga_do_dia` (linha de `load` da data local), `vdot` (do arquivo de zonas), `lthr_bpm`, `prs` (canônicos com data), `padroes` (ativos). Números legíveis (pace "MM:SS/km", duração humanizada), chaves PT-BR — artefato de prompt e auditoria.
**Where**: `backend/app/evaluation/payload.py` (new)
**Depends on**: T1
**Reuses**: `activities.service.get_activity_detail` (base — voltas classificadas, consistência, contexto, zonas meta); padrão PR→canônico do `potential/calc.py` (`_PR_EVENT_TO_CANONICAL`)
**Requirement**: EVAL-02, EVAL-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Corrida completa semeada → payload com todos os blocos; `pct_zona_alvo` com aritmética exata pinada (valores literais derivados das fixtures — padrão L-001/L-002)
- [x] `tempo_por_zona_pct` soma 100,0 quando todas as voltas têm zona válida
- [x] Progressivo e prova → sem bloco `zona_alvo`; corrida sem voltas → blocos de voltas/zona omitidos, resumo e contexto seguem (EVAL-16)
- [x] Blocos honestos: sem linha de PMC → `carga_do_dia` omitida; padrões vazios → omitidos; PR canônico sem data → fora da lista (EVAL-02 "só o que existir")
- [x] Nenhum import do gateway Garmin (EVAL-07 — payload 100% banco; teste lê a fonte e nega o import)
- [x] Gate passa; contagem sobe (314 = 308 + 6)

**Tests**: integration
**Gate**: quick

**Commit**: `feat(evaluation): deterministic evaluation payload`

---

### Phase 2: Motor e endpoint (backend)

#### T5: Cliente NIM (httpx, uma chamada, erros tipados)

**What**: `backend/app/evaluation/nim.py`: `chat_completion(system, user, settings) -> tuple[dict, dict]` (veredito parseado, `usage`) via httpx `Client` — Bearer, body `{model, messages, temperature: 0.2, max_tokens: 2000}`, timeout `nvidia_timeout_s`; conteúdo em cercas de código markdown é aceito (strip antes do `json.loads`); `usage` ausente → zeros (edge do spec). Erros: `NimError` (HTTP ≠ 200), `NimTimeout`, `NimInvalidJSON` (corpo não-JSON).
**Where**: `backend/app/evaluation/nim.py` (new)
**Depends on**: T1
**Reuses**: settings `NVIDIA_*`; httpx (runtime desde T1)
**Requirement**: EVAL-03, EVAL-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 200 com JSON limpo → devolve (dict, usage com `prompt_tokens`/`completion_tokens`)
- [ ] JSON cercado (\`\`\`json) parseia igual; `usage` ausente → `{0, 0}`
- [ ] HTTP 500 → `NimError`; timeout do httpx → `NimTimeout`; corpo lixo → `NimInvalidJSON`
- [ ] **Zero chamada à NIM real nos testes** — httpx MockTransport em todos os casos (Success Criteria do spec)
- [ ] Gate passa; contagem sobe

**Tests**: unit
**Gate**: quick

**Commit**: `feat(evaluation): nvidia nim client`

---

#### T6: Orquestração + persistência (nada gravado em falha)

**What**: `backend/app/evaluation/service.py`: `evaluate(db, activity_id, intent_type, intent_text, zone_config) -> dict | None` — detail → `build_evaluation_payload` → `SYSTEM_PROMPT_V1` → `nim.chat_completion` → `validate_verdict` (schemas) → **sanitiza o eco** (`pct_zona_alvo` ← valor Python, ou null) → cria `Evaluation` (payload_json, model, prompt_version, tokens do usage) + `activity.evaluated = True` → commit; `list_evaluations(db, activity_id)` para o detalhe. Falha em qualquer etapa → nenhuma linha, `evaluated` inalterado.
**Where**: `backend/app/evaluation/service.py` (new)
**Depends on**: T2, T3, T4, T5
**Reuses**: `activities.service.get_activity_detail`; `schemas.VerdictJson`; nim/prompt/payload
**Requirement**: EVAL-04, EVAL-06, EVAL-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Avaliação happy path (NIM mockada via monkeypatch) persiste TODOS os campos: `intent_type`, `intent_text`, `payload_json`, `model`, `prompt_version="v1"`, `verdict`, `verdict_json`, `tokens_in/out` do usage — e `activity.evaluated` vira True (EVAL-04/06)
- [ ] Sanitização: LLM ecoa `pct_zona_alvo` errado → linha gravada com o valor Python (AD-003 sem brecha)
- [ ] Re-avaliação do mesmo treino → 2 linhas, primeira intacta (EVAL-19 — nunca sobrescreve)
- [ ] `NimError`/veredito inválido → 0 linhas de `Evaluation` e `evaluated` inalterado (Decisão E)
- [ ] `activity_id` inexistente → None (404 na T7)
- [ ] Gate passa; contagem sobe

**Tests**: integration
**Gate**: quick

**Commit**: `feat(evaluation): evaluate orchestration and persistence`

---

#### T7: Endpoint POST /evaluate + mapa de erros

**What**: `backend/app/evaluation/router.py`: `POST /api/activities/{activity_id}/evaluate` com `EvaluateIn` → 200 `EvaluationOut`; sequência de validação do design (zonas 500 via dependency `get_zone_config` → 404 → 422 não-corrida → 422 intent automático → 503 key vazia → payload → NIM → 502/504 → 200). Montagem do router em `app/main.py` (mesma task). Mensagens de erro em PT-BR.
**Where**: `backend/app/evaluation/router.py` (new)
**Depends on**: T6
**Reuses**: dependency `get_zone_config` do activities (500 "zonas VDOT não configuradas" — padrão EVAL-15); `evaluation/schemas.py` (modelos de entrada/saída)
**Requirement**: EVAL-09, EVAL-10, EVAL-11, EVAL-12, EVAL-13, EVAL-14, EVAL-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 200 happy path (NIM mockada) devolve `EvaluationOut` completo via HTTP
- [ ] 404 id inexistente; 422 atividade não-corrida (yoga semeada); 422 `intent_type` inválido; 422 `intent_text` 501 chars (pydantic automático)
- [ ] 503 com `NVIDIA_API_KEY` vazia (monkeypatch) — sem chamada à NIM; 502 `NimError`; 502 veredito fora do schema; 504 `NimTimeout`; 500 zonas (arquivo inválido)
- [ ] Cada erro com mensagem PT-BR clara; nada gravado em nenhum caso de falha (checado no banco)
- [ ] Gate full passa; contagem sobe

**Tests**: integration
**Gate**: full

**Commit**: `feat(evaluation): post evaluate endpoint with error map`

---

#### T8: Detalhe expõe avaliações + activity_type

**What**: `get_activity_detail` ganha `evaluations` (query em `Evaluation` por activity, `created_at` DESC com desempate `id` DESC) e o dict `activity` ganha `activity_type`; modelos de saída do router de activities estendidos aditivamente: `ActivityOut.activity_type: str` e `ActivityDetailOut.evaluations: list[EvaluationOut]` (import de `evaluation/schemas.py` — sem ciclo).
**Where**: `backend/app/activities/service.py` (modify)
**Depends on**: T2
**Reuses**: `EvaluationOut` de `evaluation/schemas.py`; padrão de query do próprio `get_activity_detail`
**Requirement**: EVAL-17 (+ `activity_type` suporta EVAL-10: a UI decide se rende o formulário)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Detalhe de treino com 2 avaliações → `evaluations` com a mais recente primeiro (ordem pinada)
- [ ] Detalhe sem avaliações → `evaluations: []` (estado vazio, não erro)
- [ ] `ActivityOut` traz `activity_type` (não-corrida também — a UI precisa distinguir)
- [ ] Testes de regressão do detalhe existente seguem verdes (contrato só ganhou campos)
- [ ] Gate full passa; contagem sobe

**Tests**: integration
**Gate**: full

**Commit**: `feat(activities): expose evaluations and activity type in detail`

---

### Phase 3: Frontend + docs

#### T9: Contrato frontend (tipos + evaluateActivity)

**What**: `frontend/src/lib/api.ts`: tipos `VerdictJson`, `EvaluationOut`, `EvaluateRequest` (`intent_type: InferredType` — chaves 1:1, zero enum novo), extensões `ActivityOut.activity_type` e `ActivityDetailOut.evaluations: EvaluationOut[]`, e `evaluateActivity(id, body)` (POST, mesmo padrão `parseError`/`no-store`).
**Where**: `frontend/src/lib/api.ts` (modify)
**Depends on**: T8
**Reuses**: `InferredType` como enum de intenção; padrão `startSync`/`parseError` do próprio arquivo
**Requirement**: EVAL-01 (contrato espelhado)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Tipos espelham exatamente os contratos novos do backend (§9.2 + EvaluationOut)
- [ ] `evaluateActivity` faz POST com body `EvaluateRequest` e devolve `EvaluationOut`; erros via `ApiError` (status preservado)
- [ ] `npm run build` + `npm run lint` verdes (gate frontend — matrix: none)

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): evaluation api contract`

---

#### T10: EvaluateForm (intenção + estados)

**What**: `frontend/src/components/workouts/EvaluateForm.tsx`: select dos 7 tipos (rótulos PT-BR com acento, valores ASCII; pré-preenchido com `inferred_type`), textarea opcional (≤500, placeholder "era pra ser 30min a 4:15"), botão "Avaliar com IA" — desabilitado com "Analisando treino…" durante a chamada (EVAL-08), erro inline em PT-BR no lugar do card, sucesso via callback `onEvaluated`. Confirmar padrões de client component no guia do Next em `node_modules/next/dist/docs/` antes de codar (AGENTS.md).
**Where**: `frontend/src/components/workouts/EvaluateForm.tsx` (new)
**Depends on**: T9
**Reuses**: vocabulário visual do WorkoutDetail (cards `rounded-xl border bg-card`, botão accent, `text-muted`)
**Requirement**: EVAL-01, EVAL-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Formulário renderiza com o select pré-preenchido (quando `inferred_type` existe) e o botão "Avaliar com IA"
- [ ] Durante a chamada: botão desabilitado + "Analisando treino…" — nenhum clique duplo dispara segunda chamada (EVAL-08)
- [ ] Erro (404/422/502/503/504): mensagem inline em PT-BR, botão volta ao normal
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): evaluate intent form`

---

#### T11: EvaluationCard (veredito + histórico)

**What**: `frontend/src/components/workouts/EvaluationCard.tsx`: card da avaliação — selo ✅/⚠️/❌ (✅ on_target/context_explained · ⚠️ too_easy/fatigue_signal · ❌ too_hard), headline, % na zona alvo quando existir, desvios, listas "o que funcionou"/"corrigir na próxima vez"/"contexto relevante", confiança, rodapé de método (modelo · tokens · data — selo de fonte AD-009) — e as entradas de histórico das avaliações anteriores (data, selo, headline).
**Where**: `frontend/src/components/workouts/EvaluationCard.tsx` (new)
**Depends on**: T9
**Reuses**: padrão de cabeçalho forte + selo de método dos painéis (AD-009); `formatDateTime` do lib/format
**Requirement**: EVAL-05, EVAL-17 (render das anteriores)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Card renderiza todos os campos do `VerdictJson` com o selo mapeado por veredito
- [ ] `pct_zona_alvo` null → linha omitida (nada inventado); confiança com sinal visual discreto
- [ ] Rodapé: modelo · tokens · data (auditoria visível)
- [ ] Histórico: cada avaliação anterior como entrada resumida (data, selo, headline)
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): evaluation verdict card`

---

#### T12: Composição no detalhe do treino

**What**: `WorkoutDetail.tsx`: só `activity_type` de corrida rende o `EvaluateForm` (EVAL-10); avaliações do `detail.evaluations` renderizadas — mais recente como card, anteriores no histórico; `onEvaluated` prependa no estado local + `activity.evaluated = true` (sem refetch — EVAL-18); badge "Avaliado" do cabeçalho reflete o estado.
**Where**: `frontend/src/components/workouts/WorkoutDetail.tsx` (modify)
**Depends on**: T10, T11
**Reuses**: estados existentes (loading/not-found/error/ready); seção de badge do próprio arquivo
**Requirement**: EVAL-01, EVAL-10, EVAL-18, EVAL-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Detalhe de corrida: formulário + card da mais recente + histórico das anteriores
- [ ] Detalhe de não-corrida (yoga/força): sem formulário (EVAL-10)
- [ ] Avaliação concluída: nova avaliação vira a mais recente na hora (prepend local), `evaluated` true, badge "Avaliado" visível (EVAL-18/20)
- [ ] Re-avaliação: lista cresce, card troca para a nova, anteriores continuam no histórico
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): wire evaluation into workout detail`

---

#### T13: Docs — README + PLANO

**What**: Seção "Avaliar com IA" no README (fluxo, contrato, config nova, guardas); status da Fase 1 no README atualizado; checkbox do botão "Avaliar com IA" marcado no `docs/PLANO_PLATAFORMA.md` (§6 Fase 1).
**Where**: `README.md` (modify)
**Depends on**: T12
**Reuses**: seções de painel do README como padrão de escrita (veredito + validação real)
**Requirement**: EVAL-01..20 (documentação da feature)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] README documenta o fluxo de avaliação (intenção → payload → NIM → card), as vars `NVIDIA_TIMEOUT_S`/`LTHR_BPM` e o comportamento de falha (nada gravado)
- [ ] PLANO: item da Fase 1 marcado como concluído
- [ ] Nenhuma mudança de código nesta task (docs puras)

**Tests**: none
**Gate**: build (docs — nenhum comando de código)

**Commit**: `docs(evaluation): document ai evaluation feature`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 → T4
          T2 e T3 sem dependências (executam em sequência na fase)

Phase 2:  T5 → T6 → T7
          T8 depende de T2 (fase 1) — seta cross-phase fora do diagrama

Phase 3:  T9 → T10 → T12 → T13
          T9 → T11
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**How phase-based execution works:**

At Execute, the agent counts total tasks and packs phases into **task-budgeted batches** (~7 tasks per worker, whole phases - the benchmarked sweet spot is ~20 tasks → ~3 workers). A **phase** is the semantic/dependency unit; a **batch** is one or more *consecutive whole phases* assigned to one worker. The cut only ever lands on a phase boundary - a phase is never split across workers. When packing yields more than one batch (> ~8 tasks), the agent offers to dispatch batch sub-agents. Batches run sequentially: each worker executes ALL its tasks in order, then reports a compact summary before the next batch starts.

When the whole feature fits a single batch (≤ ~8 tasks), execution happens inline in the main window with no sub-agents spawned.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Config NIM/LTHR | 1 arquivo de config + env example | ✅ Granular |
| T2: Schemas do domínio | 1 módulo (3 modelos pydantic coesos) | ✅ Granular |
| T3: System prompt v1 | 1 constante versionada | ✅ Granular |
| T4: Payload determinístico | 1 função + 1 mapa | ✅ Granular |
| T5: Cliente NIM | 1 função + 3 exceções | ✅ Granular |
| T6: Orquestração/persistência | 2 funções do service | ✅ Granular |
| T7: Endpoint POST | 1 endpoint + montagem | ✅ Granular |
| T8: Detalhe estendido | 1 contrato aditivo (service + router do activities) | ⚠️ 2 arquivos coesos — mesmo contrato, mesma task |
| T9: Contrato frontend | 1 arquivo (tipos + 1 função) | ✅ Granular |
| T10: EvaluateForm | 1 componente | ✅ Granular |
| T11: EvaluationCard | 1 componente (card + histórico) | ✅ Granular |
| T12: Composição no detalhe | 1 componente (modify) | ✅ Granular |
| T13: Docs | README + PLANO (docs puras) | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | — | ✅ |
| T2 | None | — | ✅ |
| T3 | None | — | ✅ |
| T4 | T1 | T1 → T4 (Phase 1) | ✅ Match |
| T5 | T1 (cross-phase) | sem seta (backward — dispensada) | ✅ Match |
| T6 | T2, T3, T4 (cross-phase), T5 | T5 → T6 (Phase 2) | ✅ Match |
| T7 | T6 | T6 → T7 (Phase 2) | ✅ Match |
| T8 | T2 (cross-phase) | sem seta (backward — dispensada) | ✅ Match |
| T9 | T8 (cross-phase) | sem seta (backward — dispensada) | ✅ Match |
| T10 | T9 | T9 → T10 (Phase 3) | ✅ Match |
| T11 | T9 | T9 → T11 (Phase 3) | ✅ Match |
| T12 | T10, T11 | T10 → T12 · T11 → T12 (Phase 3) | ✅ Match |
| T13 | T12 | T12 → T13 (Phase 3) | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Config/entidade | unit (padrão test_sync_config) | unit | ✅ OK |
| T2 | Domínio puro | unit | unit | ✅ OK |
| T3 | Domínio puro | unit | unit | ✅ OK |
| T4 | Payload (domínio + DB) | integration | integration | ✅ OK |
| T5 | Cliente NIM | unit (MockTransport) | unit | ✅ OK |
| T6 | Service | integration | integration | ✅ OK |
| T7 | Router | integration | integration | ✅ OK |
| T8 | Detalhe activities | integration | integration | ✅ OK |
| T9 | Frontend api.ts | none (build gate) | none | ✅ OK |
| T10 | Frontend componente | none (build gate) | none | ✅ OK |
| T11 | Frontend componente | none (build gate) | none | ✅ OK |
| T12 | Frontend componente | none (build gate) | none | ✅ OK |
| T13 | Docs | none | none | ✅ OK |
