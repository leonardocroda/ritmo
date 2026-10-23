# Home Panel Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/home-panel/design.md`
**Status**: In Progress

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `frontend/AGENTS.md` (regras do Next 16 — ler `node_modules/next/dist/docs/` antes de código frontend; bloco é reescrito por `next dev`); nenhum framework de teste frontend (decisão documentada em `design-system/validation.md` — gates = lint+build+greps estruturais). Backend: pytest 9 com conftest que derruba o schema por teste (`backend/tests/conftest.py:36`), fixtures `session_client`/`login_client`/`_make_user`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| `app/home/calc.py` (domínio puro — veredito, recomendações, volume, delta) | unit | Todas as branches; 1:1 com os ACs V1–V6, R1–R5, edges de null-neutro, cap 3, ISO weeks, delta 7 noites | `backend/tests/test_home_*.py` | `uv run pytest backend/tests/test_home_verdict.py backend/tests/test_home_recommendations.py backend/tests/test_home_volume.py` (no dir `backend/`) |
| `app/home/service.py` (montagem) | integration | Caminhos-chave com fixtures de banco: sinais via `get_health(8)`, strip com lacuna zerada, RUNNING_TYPES, countdown, consistência HRV == Saúde | `backend/tests/test_home_service.py` | `uv run pytest backend/tests/test_home_service.py` (no dir `backend/`) |
| `app/home/router.py` (rota) | integration | Happy path + 401 + estado vazio (payload sem veredito) + contrato 1:1 | `backend/tests/test_home_api.py` | `uv run pytest backend/tests/test_home_api.py` (no dir `backend/`) |
| `app/core/tz.py` + health delegando | unit | Edge de tz inválida (default + warning) — suite do health como não-regressão | `backend/tests/test_home_api.py` (+ suite existente) | `uv run pytest` (suite cheia, no dir `backend/`) |
| `app/db/engine.py` (seed) | integration | Idempotência (2× init_db → 1 linha), days_left dinâmico, caso "sem prova" limpando `races` no arrange | `backend/tests/test_home_seed.py` | `uv run pytest backend/tests/test_home_seed.py` (no dir `backend/`) |
| `app/potential/service.py` (extração `get_predictions`) | integration | Digest com dados por evento, evento sem predição omitido, `ZoneConfigError → None`; suite do potential como não-regressão | `backend/tests/test_home_predictions.py` | `uv run pytest backend/tests/test_home_predictions.py` (no dir `backend/`) |
| Frontend (api.ts, componentes, page, Nav) | none — build gate | Sem framework de teste (house pattern): lint + build + greps estruturais dos Success Criteria do spec | - | `npm run lint` + `npm run build` (no dir `frontend/`) |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks backend com testes unitários novos | `uv run pytest tests/test_home_verdict.py tests/test_home_recommendations.py tests/test_home_volume.py` (workdir `backend/`) |
| Full | Tasks com testes de integração (service/router/seed/predictions) | `uv run pytest` (workdir `backend/` — suite cheia, baseline 550) |
| Build | Fim de fase, tasks frontend, tasks config/docs | Full + `npm run lint` e `npm run build` (workdir `frontend/`) |

**Notas de ambiente para os workers:** o nudge de security do build foi **extinto** pelo upgrade Next 16.4.2 — `npm run build` não deve mais abortar com `SecurityFatalError` (se ocorrer 1×, retry é o protocolo legado). Conftest re-cria schema a cada teste → o seed da meia aparece em TODOS os testes após T7; testes de countdown calculam `days_left` dinamicamente e o caso "sem prova" faz `DELETE FROM races` no arrange.

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order. As arestas abaixo são exatamente os `Depends on` de cada task (a execução intra-fase é sequencial mesmo sem aresta).

### Phase 1: Motor puro (backend)

```
T1 → T2
T1 → T3
```

### Phase 2: Integração backend

```
T4 → T5
T1 → T5
T2 → T5
T3 → T5
T5 → T6
T5 → T7
```

### Phase 3: Frontend

```
T6 → T8
T8 → T10
T8 → T11
T9 → T12
T10 → T12
T11 → T12
```

### Phase 4: P2 + fecho

```
T6 → T13
T12 → T14
T13 → T14
T14 → T15
```

---

## Task Breakdown

### T1: Motor de veredito V1–V6

**What**: Criar `app/home/calc.py` com o motor puro de veredito — regras V1..V6 do spec em cadeia de prioridade fixa, sinais como dataclass/dict tipado, sinal `None` é neutro, nenhum sinal → `None` (estado vazio).
**Where**: `backend/app/home/calc.py` (novo) + `backend/app/home/__init__.py`
**Depends on**: None
**Reuses**: nomenclatura de tons `good|attention|alert|neutral` (tokens do design-system); espírito AD-003 (pureza testável)
**Requirement**: HOME-02, HOME-03..HOME-09, HOME-10

**Tools**:

- MCP: NONE (ferramentas de arquivo do harness)
- Skill: `tlc-spec-driven` (ativa por nome no Execute)

**Done when**:

- [x] V1..V6 cada uma com frase, tom e regra exatamente como na spec
- [x] Prioridade fixa V1→V6: primeiro casamento vence, uma frase por dia
- [x] Sinal ausente nunca dispara regra (neutro); banco sem sinal → `None`
- [x] Gate: `uv run pytest tests/test_home_verdict.py` verde (workdir `backend/`)
- [x] Test count: ≥10 testes novos (V1–V6 individual, prioridade, null-neutro, sem-dado, determinismo — 2 chamadas idênticas → mesmo resultado)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(home): motor de veredito v1-v6 puro com regras de prioridade` (3bf8f27)

---

### T2: Recomendações R1–R5

**What**: Adicionar ao `calc.py` as recomendações determinísticas R1–R5 — mapeadas às regras do veredito, taper independente (≤14 dias), cap de 3, cada uma `{text, support, why, tone}`.
**Where**: `backend/app/home/calc.py` (modifica)
**Depends on**: T1
**Reuses**: constantes de threshold do T1 (`TAPER_DAYS = 14` etc.)
**Requirement**: HOME-25..HOME-30, HOME-09

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [x] R1 (janela de qualidade), R2 (recuperação), R3 (segurar volume), R4 (taper), R5 (leve de hoje) com textos/why da spec
- [x] R4 (taper) dispara independentemente do veredito; cap 3 respeitado por prioridade
- [x] Gate: `uv run pytest tests/test_home_recommendations.py` verde
- [x] Test count: ≥8 testes novos (R1–R5, taper com/sem prova, cap 3, why correto por regra)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(home): recomendacoes r1-r5 deterministicas com why` (93f7daf)

---

### T3: Delta de sono e volume semanal (puro)

**What**: Adicionar ao `calc.py` as funções puras `sleep_delta` (última noite vs média das 7 anteriores com dado) e `weekly_volume` (semanas ISO segunda-feira: corrente, média das 4 completas, série de 10 semanas, `delta_pct` com guarda de divisão por zero).
**Where**: `backend/app/home/calc.py` (modifica)
**Depends on**: T1
**Reuses**: nenhuma dependência externa — stdlib puro
**Requirement**: HOME-20, HOME-21, HOME-14 (volume/delta), HOME-37 (série 10 semanas)

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [x] `sleep_delta`: ignora noites sem dado na média; sem noite anterior → `None`
- [x] `weekly_volume`: semanas ISO a partir de `(date, meters)`; média de 4 semanas COMPLETAS; avg4 == 0 → `delta_pct` `None` (chip "—")
- [x] Gate: `uv run pytest tests/test_home_volume.py` verde
- [x] Test count: ≥8 testes novos (delta normal/sem-dado/uma-noite, ISO boundary, avg4 zero, série 10, semana parcial)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(home): delta de sono e volume semanal iso puros` (b264298)

---

### T4: Fuso único em `app/core/tz.py`

**What**: Extrair `app_tz() -> ZoneInfo` (inválida → default + `logger.warning`) para `app/core/tz.py`; health router passa a delegar em 1 linha.
**Where**: `backend/app/core/tz.py` (novo), `backend/app/health/router.py` (modifica — só `_resolve_tz`)
**Depends on**: None
**Reuses**: corpo do `_resolve_tz` existente (`health/router.py:159-169`); `get_settings().app_timezone`, `DEFAULT_TIMEZONE`
**Requirement**: HOME-12

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [x] `app_tz()` com o mesmo comportamento do `_resolve_tz` (default + warning em valor inválido)
- [x] Health router delega sem mudança de comportamento; suite do health verde (não-regressão)
- [x] Gate: `uv run pytest` (suite cheia) verde
- [x] Test count: baseline 550 + os de T1–T3, zero falha — nenhuma exclusão silenciosa

**Tests**: unit (edge coberta pela suite existente do health + novo uso)
**Gate**: full
**Commit**: `refactor(core): app_tz extraido do health router` (8d67c29)

---

### T5: Serviço de montagem `get_home`

**What**: Criar `app/home/service.py::get_home(db, user_id, tz)` — lê `get_health(db, uid, 8, tz)` (hrv current + noites + floor), última linha de `load` (forma), `aggregate_daily_loads` fatiado 7 dias com lacuna zerada, último treino `RUNNING_TYPES` com `evaluated`, volume semanal, countdown da próxima prova, e delega veredito/recomendações ao calc.
**Where**: `backend/app/home/service.py` (novo)
**Depends on**: T1, T2, T3, T4
**Reuses**: `health.service.get_health`, `garmin.pmc.aggregate_daily_loads`, `activities.service.RUNNING_TYPES`, `Activity.evaluated`, `home.calc`
**Requirement**: HOME-01, HOME-10, HOME-14, HOME-15, HOME-16, HOME-19, HOME-20, HOME-24

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [x] Sinais hrv/sono extraídos de `get_health(8)`; fitness da última linha de `load`
- [x] Strip: exatamente 7 dias corridos terminando hoje, lacunas com 0.0
- [x] Último treino só `RUNNING_TYPES`; sem corridas → `None`
- [x] Countdown: prova com `date >= hoje` mais próxima; "é hoje" quando 0; passada ignorada
- [x] Consistência: fixture de HRV → status em `get_home` == status em `get_health` (mesma data)
- [x] Gate: `uv run pytest` verde (inclui `tests/test_home_service.py` novo)
- [x] Test count: ≥12 testes novos (sinais, strip com lacuna, RUNNING_TYPES vs strength, countdown hoje/passada/sem prova, consistência HRV, banco vazio → verdict None)

**Tests**: integration
**Gate**: full
**Commit**: `feat(home): servico monta payload de hoje das fontes existentes`

---

### T6: Contrato `HomeOut` + `GET /api/home/today`

**What**: Criar `app/home/router.py` com os modelos Pydantic espelho 1:1 (`HomeOut`, `VerdictOut`, `SignalOut`, `StripPoint`, `LastActivityOut`, `VolumeOut`, `CountdownOut`, `RecommendationOut`) e a rota com `require_session` + `app_tz()`.
**Where**: `backend/app/home/router.py` (novo), registro no app (main/router include)
**Depends on**: T5
**Reuses**: padrão dos routers existentes (401 pré-query via dependency); `core.tz.app_tz`
**Requirement**: HOME-01, HOME-11, HOME-12

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] `GET /api/home/today` 200 com payload completo no happy path (fixture com dados)
- [ ] 401 sem sessão antes de qualquer query
- [ ] Estado vazio: banco sem dado de saúde/carga/atividade → `verdict: null` + blocos nulos (sem frase)
- [ ] Contrato 1:1: cada campo do `HomeOut` renderiza no painel (checagem estrutural no teste)
- [ ] Gate: `uv run pytest` verde (inclui `tests/test_home_api.py`)
- [ ] Test count: ≥8 testes novos (happy, 401, vazio, date no payload = hoje no fuso, recomendações 1..3)

**Tests**: integration
**Gate**: full
**Commit**: `feat(home): endpoint GET /api/home/today com contrato HomeOut`

---

### T7: Seed idempotente da The Best Açaí

**What**: No `init_db`, semear `Race` da meia (The Best Açaí, 2026-11-08, 21097.5m, goal null) quando `races` vazio para o usuário 1; testes de idempotência e de countdown dinâmico.
**Where**: `backend/app/db/engine.py` (modifica — bloco de seeds)
**Depends on**: T5
**Reuses**: padrão dos seeds idempotentes existentes do `init_db` (sem setval — id auto)
**Requirement**: HOME-22, HOME-23

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] `init_db` em banco zerado cria a meia; segunda execução não duplica
- [ ] `days_left` calculado dinamicamente (teste não crava 16)
- [ ] Caso "sem prova": arrange com `DELETE FROM races` → `countdown: null` no payload
- [ ] Gate: `uv run pytest` verde (inclui `tests/test_home_seed.py`)
- [ ] Test count: ≥4 testes novos (seed cria, 2× não duplica, days_left dinâmico, sem prova → null)

**Tests**: integration
**Gate**: full
**Commit**: `feat(home): seed da the best acai para o countdown`

---

### T8: Cliente de API `HomeToday`

**What**: Adicionar a `lib/api.ts` o tipo `HomeToday` (espelho tipado do `HomeOut`) e o fetcher `getHomeToday()`.
**Where**: `frontend/src/lib/api.ts` (modifica)
**Depends on**: T6
**Reuses**: `API_BASE = ""` (rewrite same-origin, AD-020) e o padrão dos fetchers existentes
**Requirement**: HOME-01 (espelho do contrato)

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] `HomeToday` espelha campo a campo o `HomeOut` do backend (incl. unions `| null`)
- [ ] `getHomeToday()` segue o padrão de fetch/erro dos fetchers existentes
- [ ] Gate: `npm run lint` + `npm run build` verdes (workdir `frontend/`)

**Tests**: none (matrix: frontend = build gate)
**Gate**: build
**Commit**: `feat(frontend): tipo hometoday e fetcher no cliente de api`

---

### T9: Nav com Home em primeiro (5 itens)

**What**: `Nav.tsx`: `PANELS` ganha `{href: "/", label: "Home", Icon: HomeIcon}` no índice 0 (SVG line 22px do mock), `activePanel` com special-case raiz (`href === "/"` ativo só em `pathname === "/"`), tab bar `grid-cols-4` → `grid-cols-5`.
**Where**: `frontend/src/components/Nav.tsx` (modifica)
**Depends on**: None
**Reuses**: o pill ativo, `aria-current`, boundaries Suspense e ícones existentes (estilo idêntico)
**Requirement**: HOME-33 (+ HOME-32 parcial — nav pronta pra raiz)

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] 5 itens com Home em 1º, mesmo estilo de ícone/label dos demais
- [ ] Special-case raiz no `activePanel` — Home ativo SÓ em `/` (o `startsWith("/")` cru casaria tudo)
- [ ] Tab bar 5 colunas sem quebra em 390px (alvo de toque ≥44px preservado)
- [ ] Gate: `npm run lint` + `npm run build` verdes; `git grep -n "grid-cols-5" -- frontend/src/components/Nav.tsx` não-vazio e `grid-cols-4` vazio no TabBar

**Tests**: none (build gate + greps estruturais)
**Gate**: build
**Commit**: `feat(frontend): nav ganha home em primeiro com 5 itens`

---

### T10: Card-veredito herói

**What**: Criar `VerdictCard.tsx` — herói `bg-raised`: eyebrow `"Hoje · [dia, data]"`, frase display 38–40px sentence case, 3 chips de sinal (dot semântico + valor + estado + data quando stale) e strip de 7 barras (neutras, hoje lime, lacuna = zero) com caption.
**Where**: `frontend/src/components/home/VerdictCard.tsx` (novo)
**Depends on**: T8
**Reuses**: tokens (`text-good/attention/alert`, `bg-raised`, `tabular-nums`), `formatDuration`/`formatKm`/`formatWeekday` de `lib/format.ts`, estilo do mock v0.3 §03
**Requirement**: HOME-13, HOME-14, HOME-15, HOME-16

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] Composição do mock: herói raised, eyebrow, display 38–40px, chips, strip + caption `"carga · últimos 7 dias"`
- [ ] Chip stale mostra a data do dado; sinal null mostra estado vazio ("coletando linha de base"/"sem dado")
- [ ] Barra de dia sem carga tem altura zero (não omitida)
- [ ] Zero cor literal: `git grep -nE "#[0-9A-Fa-f]{6}" -- frontend/src/components/home` vazio
- [ ] Gate: `npm run lint` + `npm run build` verdes

**Tests**: none (build gate + greps estruturais)
**Gate**: build
**Commit**: `feat(frontend): card-veredito heroi com chips e strip de 7 dias`

---

### T11: Chips de roteamento + cards de recomendação

**What**: Criar `RoutingChips.tsx` (último treino → `/treinos/{id}` com selo avaliado ✓; volume → `/performance`; meia com days_left → `/performance`, "é hoje" quando 0) e `RecommendationCards.tsx` (cards `Recomendação · regra`: texto, linha de apoio, tag why).
**Where**: `frontend/src/components/home/RoutingChips.tsx`, `frontend/src/components/home/RecommendationCards.tsx` (novos)
**Depends on**: T8
**Reuses**: `Link` do Next, `formatKm`, tokens `bg-card`/`rounded-card`, anatomia dos icards do mock
**Requirement**: HOME-19, HOME-21, HOME-22, HOME-24, HOME-31

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] Chips como `Link` com alvo ≥44px; um dado, um verbo, um destino
- [ ] Volume com avg4 == 0 renderiza "—"; sem atividade → chip de último treino omitido
- [ ] Countdown "é hoje" quando `days_left == 0`
- [ ] Cards de recomendação com why em tag, tom semântico no dot
- [ ] Gate: `npm run lint` + `npm run build` verdes

**Tests**: none (build gate)
**Gate**: build
**Commit**: `feat(frontend): chips de roteamento e cards de recomendacao`

---

### T12: HomePanel na raiz com estados

**What**: Criar `HomePanel.tsx` (fetch `getHomeToday`, `PanelState` loading/error/empty/ready, skeleton DSN-23, composição veredito → chips → recomendações) e trocar `page.tsx` de `redirect("/treinos")` para renderizar o painel.
**Where**: `frontend/src/components/home/HomePanel.tsx` (novo), `frontend/src/app/(app)/page.tsx` (modifica)
**Depends on**: T9, T10, T11
**Reuses**: pattern `PanelState`/`useEffect`/`catch` do HealthPanel; `Skeleton`; estado vazio CLR-11 (link `/perfil`)
**Requirement**: HOME-17, HOME-18, HOME-32, HOME-34, HOME-35, HOME-36

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven` (o bloco AGENTS.md manda consultar `node_modules/next/dist/docs/` se algo além do padrão atual for necessário)

**Done when**:

- [ ] `/` renderiza o painel: `git grep -n "redirect" -- "frontend/src/app/(app)/page.tsx"` vazio
- [ ] `empty` (verdict null + strip vazia + sem atividade) orienta o primeiro sync com link `/perfil`
- [ ] `error` com mensagem (contrato existente); loading = skeletons, sem spinner e sem "Carregando": `git grep -n "Carregando" -- "frontend/src/app/(app)/page.tsx" frontend/src/components/home` vazio
- [ ] Sem ação de sync na Home (AD-023): `git grep -n "SyncButton" -- frontend/src/components/home` vazio
- [ ] Gate: `npm run lint` + `npm run build` verdes + greps acima

**Tests**: none (build gate + greps estruturais dos Success Criteria)
**Gate**: build
**Commit**: `feat(frontend): homepanel na raiz com estados vazio erro skeleton`

---

### T13: Digest de previsões + série de 10 semanas no payload

**What**: Extrair `get_predictions(db, user_id, calibration)` no `potential/service.py` (`get_potential` passa a usá-lo), adicionar ao `get_home` os blocos P2: `volume_weeks` (10 semanas) e `predictions` (10K e meia, `average_s`; `ZoneConfigError → None`).
**Where**: `backend/app/potential/service.py` (modifica), `backend/app/home/service.py` + `router.py` (modificam — novos campos), `frontend/src/lib/api.ts` (modifica — tipos P2)
**Depends on**: T6
**Reuses**: `load_calibration(settings.vdot_zones_path)` + montagem de predictions existente; `calc.weekly_volume` do T3
**Requirement**: HOME-37, HOME-38, HOME-39

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] `get_potential` usa `get_predictions` (suite do potential verde — não-regressão)
- [ ] `predictions` com 10K e meia quando há dado; evento sem predição omitido (nunca "—")
- [ ] `ZoneConfigError` → `predictions: null` no payload (a Home não 500 por bloco P2)
- [ ] `volume_weeks` com exatamente as 10 últimas semanas ISO
- [ ] Gate: `uv run pytest` verde (inclui `tests/test_home_predictions.py` + suite do potential); `npm run lint` + `npm run build` verdes (tipos P2)
- [ ] Test count: ≥6 testes novos (digest por evento, omitido sem dado, zone error → null, série 10, potential não-regressão)

**Tests**: integration
**Gate**: build
**Commit**: `feat(home): digest de previsoes e series de 10 semanas no payload`

---

### T14: Mini de volume + digest de previsões (renderização P2)

**What**: Criar `VolumeMini.tsx` (10 barras neutras, semana corrente lime, sentença `Xkm · ±Y% vs média 4 semanas · ACWR Z`) e `PredictionsDigest.tsx` (linha 10K · meia + `ver Performance →`), integrados à composição do HomePanel.
**Where**: `frontend/src/components/home/VolumeMini.tsx`, `frontend/src/components/home/PredictionsDigest.tsx` (novos), `HomePanel.tsx` (modifica — composição)
**Depends on**: T12, T13
**Reuses**: dados já no payload (`volume_weeks`, `predictions`); tokens/chartTheme (nenhuma cor literal); `formatDuration` para tempos
**Requirement**: HOME-37, HOME-38, HOME-39

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] Mini com 10 barras, corrente acesa, sentença com os valores do payload
- [ ] Digest de previsões com link para `/performance`; bloco omitido quando `predictions: null`
- [ ] Zero cor literal no diretório `components/home` (grep)
- [ ] Gate: `npm run lint` + `npm run build` verdes

**Tests**: none (build gate + greps estruturais)
**Gate**: build
**Commit**: `feat(frontend): mini de volume e digest de previsoes abaixo da dobra`

---

### T15: Docs + varredura final

**What**: Atualizar README (a Home é a raiz; navegação de 5 itens; o countdown lê `races`) e rodar a varredura final dos greps dos Success Criteria do spec.
**Where**: `README.md` (modifica)
**Depends on**: T14
**Reuses**: seções existentes do README (§Sync, §LAN — intocadas)
**Requirement**: fechamento dos Success Criteria

**Tools**:

- MCP: NONE
- Skill: `tlc-spec-driven`

**Done when**:

- [ ] README descreve Home como raiz e a nav de 5 itens; nada de `/hoje`
- [ ] Varredura final verde: `git grep -n "redirect" -- "frontend/src/app/(app)/page.tsx"` vazio · `git grep -nE "#[0-9A-Fa-f]{6}" -- frontend/src/components/home` vazio · `git grep -n "Carregando" -- "frontend/src/app/(app)/page.tsx" frontend/src/components/home` vazio · `git grep -n "SyncButton" -- frontend/src/components/home` vazio
- [ ] Gate build final: suite backend cheia + lint + build verdes
- [ ] `git grep -n "grid-cols-4" -- frontend/src/components/Nav.tsx` vazio

**Tests**: none (docs — varredura é o gate)
**Gate**: build
**Commit**: `docs(home-panel): readme e varredura final de greps`

---

## Phase Execution Map

Visual representation of task ordering. Cada aresta é um `Depends on` real (lista completa — a mesma do Execution Plan):

```
T1 → T2
T1 → T3
T4 → T5
T1 → T5
T2 → T5
T3 → T5
T5 → T6
T5 → T7
T6 → T8
T8 → T10
T8 → T11
T9 → T12
T10 → T12
T11 → T12
T6 → T13
T12 → T14
T13 → T14
T14 → T15
```

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**How phase-based execution works:**

At Execute, the agent counts total tasks and packs phases into **task-budgeted batches** (~7 tasks per worker, whole phases). This feature: 15 tasks → **Batch A = Phases 1+2 (T1–T7, backend)** e **Batch B = Phases 3+4 (T8–T15, frontend + P2)** — 2 workers. Batches run sequentially; each worker executes ALL its tasks in order, then reports a compact summary before the next batch starts.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Motor de veredito | 1 módulo puro + testes | ✅ Granular |
| T2: Recomendações | 1 conjunto de funções (mesmo módulo) | ✅ Granular |
| T3: Delta + volume | 2 funções coesas (mesmo módulo) | ✅ Granular |
| T4: tz extraction | 1 módulo novo + delegação 1 linha | ✅ Granular |
| T5: get_home service | 1 arquivo de montagem + testes | ✅ Granular |
| T6: Router + contrato | 1 endpoint + Pydantic | ✅ Granular |
| T7: Seed | 1 bloco no init_db + testes | ✅ Granular |
| T8: api.ts tipos | 1 arquivo (modificação) | ✅ Granular |
| T9: Nav 5 itens | 1 arquivo (modificação) | ✅ Granular |
| T10: VerdictCard | 1 componente | ✅ Granular |
| T11: RoutingChips + Recs | 2 componentes coesos (chips roteiam, cards recomendam — mesmo bloco do mock) | ✅ OK coeso |
| T12: HomePanel + page | 1 painel + troca de 7 linhas na page | ✅ OK coeso |
| T13: Digest P2 backend | 1 extração + 2 blocos no payload | ✅ Granular |
| T14: VolumeMini + Digest | 2 componentes coesos (mesma seção abaixo da dobra) | ✅ OK coeso |
| T15: Docs + greps | 1 arquivo + varredura | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | raiz da Phase 1 | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T1 | T1 → T3 | ✅ Match |
| T4 | None | raiz da Phase 2 (sem seta de entrada) | ✅ Match |
| T5 | T1, T2, T3, T4 | T4 → T5 (Phase 1 completa atrás; setas T1–T3 implícitas por sequência de fase) | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T5 | T5 → T7 | ✅ Match |
| T8 | T6 | T6 → T8 (transição de fase) | ✅ Match |
| T9 | None | raiz sem seta | ✅ Match |
| T10 | T8 | T8 → T10 | ✅ Match |
| T11 | T8 | T8 → T11 | ✅ Match |
| T12 | T9, T10, T11 | T9, T10, T11 → T12 | ✅ Match |
| T13 | T6 | T6 → T13 (dependência de fase anterior) | ✅ Match |
| T14 | T12, T13 | T12, T13 → T14 | ✅ Match |
| T15 | T14 | T14 → T15 | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Veredito | `home/calc.py` (domínio) | unit | unit | ✅ OK |
| T2: Recomendações | `home/calc.py` (domínio) | unit | unit | ✅ OK |
| T3: Delta/volume | `home/calc.py` (domínio) | unit | unit | ✅ OK |
| T4: app_tz | `core/tz.py` + health router | unit + não-regressão | unit | ✅ OK |
| T5: get_home | `home/service.py` | integration | integration | ✅ OK |
| T6: Router | `home/router.py` (rota) | integration | integration | ✅ OK |
| T7: Seed | `db/engine.py` | integration | integration | ✅ OK |
| T8: api.ts | frontend | none (build gate) | none | ✅ OK |
| T9: Nav | frontend | none (build gate) | none | ✅ OK |
| T10: VerdictCard | frontend | none (build gate) | none | ✅ OK |
| T11: Chips/Recs | frontend | none (build gate) | none | ✅ OK |
| T12: HomePanel/page | frontend | none (build gate) | none | ✅ OK |
| T13: Digest P2 | `potential/service.py` + `home/service`+`router` + `api.ts` | integration (backend) | integration + build | ✅ OK (usa o MAIS ALTO: integration) |
| T14: Mini/Digest | frontend | none (build gate) | none | ✅ OK |
| T15: Docs | docs | none (varredura) | none | ✅ OK |

**Nenhuma dependência aponta para fase futura** (T13 → T6 é backward; todas as demais backward ou intra-fase). ✅
