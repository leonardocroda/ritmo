# hr-zones Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/hr-zones/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `README.md` (§Testes — suite no Postgres do compose, nada em SQLite), `backend/tests/conftest.py` (schema dropado por teste, lifespan re-semeia, `session_client` com sessão real), `backend/pyproject.toml` (pytest, sem thresholds), `frontend/package.json` (sem test runner — lint/build apenas). Sem thresholds de cobertura configurados → strong defaults aplicados na profundidade.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Domínio puro (`profile/calc.py`) | unit | Todas as branches 1:1 aos ACs HRZ-08..11 + edge cases (defaults por método, bounds inválidos de cada tipo, arredondamento, Z5 aberta do lthr, classify, métrica ausente → None) | `backend/tests/test_hr_zones_calc.py` | `uv run pytest tests/test_hr_zones_calc.py` (workdir `backend/`) |
| Models + seed (`db/models.py`, `db/engine.py`) | integration | Insert/FK; duas linhas no mesmo dia (sem unique de valid_from); seed idempotente e só do usuário 1 | `backend/tests/test_hr_zones_models.py` | `uv run pytest tests/test_hr_zones_models.py` (workdir `backend/`, Postgres do compose no ar) |
| Service (`profile/service.py`) | integration | Resolução effective-dating (vigente em D, tie-break id), idempotência, manual-wins, validação cross-field 422 — 1:1 a HRZ-01..04/07/12 | `backend/tests/test_hr_zones_service.py` | `uv run pytest tests/test_hr_zones_service.py` (workdir `backend/`) |
| API (`profile/router.py`, `main.py`) | integration | Rotas em escopo: happy + 422 por campo + 401 sem sessão + isolamento A×B (métricas/config de Y não vazam) | `backend/tests/test_hr_zones_api.py` | `uv run pytest tests/test_hr_zones_api.py` (workdir `backend/`) |
| Gateway (`garmin/client.py`) | integration | 2 métodos passam pelo `_call` (contagem + sleep); FakeGateway estendido para os testes de sync | `backend/tests/test_garmin_gateway.py` (extensão) | `uv run pytest tests/test_garmin_gateway.py` (workdir `backend/`) |
| Sync physio (`garmin/upserts.py`, `garmin/service.py`) | integration | HRZ-05/06: update-if-changed, manual-wins, fcrest do mínimo-7d da série `rhr`, valor ausente pula, falha → warning + done, +3 chamadas no stats | `backend/tests/test_garmin_upserts.py`, `backend/tests/test_garmin_service.py`, `backend/tests/test_sync_api.py` (extensões) | `uv run pytest tests/test_garmin_upserts.py tests/test_garmin_service.py tests/test_sync_api.py` (workdir `backend/`) |
| Payload (`evaluation/payload.py`) | integration | HRZ-17/18/19: lthr da métrica vigente na data + fallback env; bloco zonas_fc com tempo por zona exato; sem FC → bloco omitido | `backend/tests/test_evaluation_payload.py` (extensão) | `uv run pytest tests/test_evaluation_payload.py` (workdir `backend/`) |
| Frontend (`api.ts`, `proxy.ts`, `UserMenu`, página, components) | none | - (build gate only; comportamento verificado por UAT 390px — padrão do projeto) | - | build gate only |
| Config/docs (`README.md`, `.env.example`) | none | - (build gate only) | - | build gate only |

## Gate Check Commands

> Generated from codebase - confirm before Execute. Pré-requisito de todo gate backend: `docker compose up -d postgres` (a suite falha rápido sem ele — padrão do repo).

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após task com testes novos em arquivo(s) próprio(s) da feature | `cd backend && uv run pytest tests/test_hr_zones_calc.py tests/test_hr_zones_models.py tests/test_hr_zones_service.py tests/test_hr_zones_api.py` (rode só os arquivos da task; extensões: os arquivos estendidos) |
| Full | Após task que toca gateway/sync/payload/engine (a suite inteira deve continuar verde) | `cd backend && uv run pytest` |
| Build | Após task frontend ou docs | `cd frontend && npm run lint && npm run build` |
| Build+Full (final) | Última task da feature | `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Fundação (modelos, matemática pura, seed)

```
T1 → T3
T2 → T3
```

### Phase 2: Service + API (resolução effective-dated + endpoints)

```
T1 → T4
T2 → T4
T4 → T5
```

### Phase 3: Sync (fontes Garmin → métricas)

```
T4 → T7
T6 → T8
T7 → T8
```

### Phase 4: Consumo na avaliação IA

```
T4 → T9
```

### Phase 5: Frontend (/perfil)

```
T5 → T10
T10 → T11
T11 → T12
```

### Phase 6: Documentação

```
T12 → T13
```

---

## Task Breakdown

### T1: Modelos UserHrMetric + HrZoneConfig

**What**: Duas classes em `db/models.py` — `UserHrMetric` (`user_hr_metrics`: `user_id` FK index, `kind` str(10) fcmax|fcrest|fclthr, `value_bpm` int, `source` str(10) garmin|manual, `valid_from` Date, `created_at`; índice composto `(user_id, kind, valid_from)`, SEM unique de `valid_from`) e `HrZoneConfig` (`hr_zone_configs`: `user_id` FK index, `method` str(10) lthr|fcr|fcmax, `bounds` JSON `{"zones": [{"low": int, "high": int|null}, ×5]}`, `valid_from` Date, `created_at`; índice `(user_id, valid_from)`).
**Where**: `backend/app/db/models.py`
**Depends on**: None
**Reuses**: convenção `user_id` FK + `_utcnow` das models existentes
**Requirement**: HRZ-01/02 (substrato de armazenamento das séries)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `UserHrMetric` com índice composto e sem unique de valid_from; `HrZoneConfig` com `bounds` JSON
- [x] Testes: insert das duas linhas no mesmo dia (mesma kind) funciona; FK em `user_id` impede usuário inexistente
- [x] Gate check passes: `uv run pytest tests/test_hr_zones_models.py` + Full suite verde
- [x] Test count: ~2 novos + 427 existentes (no silent deletions)

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(db): add user hr metrics and zone configs tables`

---

### T2: Matemática pura das zonas (`profile/calc.py`)

**What**: Módulo puro com `DEFAULT_BOUNDS` (lthr: 65/80/89/95/100 com Z5 high null; fcr e fcmax: 50/60/70/80/90 com Z5 high 100), `BoundsError(motivo)`, `validate_bounds(method, bounds)` (≠5 zonas, `z1.low ≤ 0`, cadeia não ascendente `z[n].high == z[n+1].low` crescente, zona <1pp, high em Z5 do lthr deve ser None / do fcr-fcmax deve ser 100), `zones_bpm(method, bounds, metrics)` (lthr: `round(pct × fclthr / 100)`; fcr: `fcrest + round(pct × (fcmax − fcrest) / 100)`; fcmax: `round(pct × fcmax / 100)`; Z5: lthr high None, fcr/fcmax high fcmax; None quando métrica exigida ausente) e `classify(hr, zones)` (`low ≤ hr < high`; Z5 aberta; None como guard).
**Where**: `backend/app/profile/calc.py`
**Depends on**: None
**Reuses**: padrão de `app/health/calc.py` (funções puras, zero I/O)
**Requirement**: HRZ-08, HRZ-09, HRZ-10, HRZ-11

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Defaults dos 3 métodos exatamente como o spec (tabela do usuário no lthr)
- [x] `validate_bounds` rejeita cada caso inválido com o primeiro ponto no motivo
- [x] `zones_bpm` pinado com aritmética exata (ex.: fclthr 177 lthr → [115, 141, 158, 168, 177+]; fcr com fcrest 45/fcmax 190 → Z1 [107, 120)) e devolve None sem métrica
- [x] `classify` cobre bordas (low inclusivo, high exclusivo, Z5 aberta)
- [x] Gate check passes: `uv run pytest tests/test_hr_zones_calc.py`
- [x] Test count: ~14 novos + existentes

**Tests**: unit
**Gate**: quick

**Commit**: `feat(hr-zones): pure zone math with method defaults and bounds validation`

---

### T3: Seed da config lthr do usuário 1 no init_db

**What**: No `init_db`, após o seed existente: se o usuário 1 (seed id 1) não tem config em `hr_zone_configs`, cria `method="lthr"` com `DEFAULT_BOUNDS["lthr"]` e `valid_from` = hoje. **Nenhuma métrica é seedada** (emenda do usuário 20/10: sync é a fonte; seed manual bloquearia o auto-update). Idempotente por guarda de existência.
**Where**: `backend/app/db/engine.py`
**Depends on**: T1, T2
**Reuses**: bloco de seed do init_db (padrão AD-019); `DEFAULT_BOUNDS` de T2
**Requirement**: HRZ-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] init_db cria config lthr/defaults para o usuário 1 uma única vez (re-executar não duplica)
- [x] Nenhuma linha em `user_hr_metrics` é criada pelo init_db
- [x] Testes: seed idempotente; segundo init não cria linha nova
- [x] Gate check passes: `uv run pytest tests/test_hr_zones_models.py` + Full suite verde (o init roda em todo lifespan)
- [x] Test count: ~1 novo + existentes

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(db): seed default lthr zone config for user 1`

---

### T4: Service de resolução e escrita effective-dated (`profile/service.py`)

**What**: Módulo com `metric_on(db, user_id, kind, on_date)` / `metrics_on` / `config_on` (resolução `ORDER BY valid_from DESC, id DESC LIMIT 1` com `valid_from ≤ on_date`), `zones_on(db, user_id, on_date)` (config + zonas derivadas via calc), `set_metric(db, user_id, kind, value, source, on_date=None) -> bool` (False quando valor igual ao vigente; False quando `source=garmin` e vigente é manual — manual-wins vive aqui; True insere), `set_config(db, user_id, method, bounds, on_date=None) -> bool` (idempotente vs método+bounds vigentes) e `validate_metrics_set(current, updates) -> None` (limites fcmax 100–230, fcrest 30–110, fclthr 100–220; incoerências `fcrest ≥ fcmax` e `fclthr ≥ fcmax` → `MetricValidationError(campo, motivo)` com mensagem PT-BR exata).
**Where**: `backend/app/profile/service.py`
**Depends on**: T1, T2
**Reuses**: padrão de exceções de domínio com mensagem exata (`auth/service.py`); `calc.zones_bpm`
**Requirement**: HRZ-01, HRZ-02, HRZ-03, HRZ-04, HRZ-06, HRZ-10, HRZ-11, HRZ-12

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Resolução vigente-na-data: linha de ontem lida com `on_date` de anteontem vs hoje; duas mudanças no mesmo dia → tie-break por id DESC
- [ ] `set_metric`: mesmo valor → False sem linha; garmin sobre manual → False (não cria); garmin sobre garmin/ausente com valor novo → True
- [ ] `set_config`: mesma config → False; método novo → True
- [ ] `validate_metrics_set`: cada limite e incoerência com campo+motivo exatos
- [ ] Gate check passes: `uv run pytest tests/test_hr_zones_service.py`
- [ ] Test count: ~12 novos + existentes

**Tests**: integration
**Gate**: quick

**Commit**: `feat(hr-zones): effective-dated metric and config resolution service`

---

### T5: Endpoints `/api/profile/hr-zones` (GET/PUT/history) + wiring

**What**: Router `app/profile/router.py` (prefixo `/api/profile`) com `GET /hr-zones` (`metrics` com `{value, source, valid_from}|null` por kind, `config|null`, `zones|[{n, low, high}]|null`, `defaults` dos 3 métodos), `PUT /hr-zones` (body `metrics? + method? + bounds?`; ao menos 1 campo senão 422; method sem bounds → defaults; validação `validate_metrics_set` + `validate_bounds` → 422 por campo; escrita `source=manual`; resposta = shape do GET) e `GET /hr-zones/history` (`metrics` + `configs` DESC por `(valid_from, id)`). `main.py` inclui o router com `dependencies=[Depends(require_session)]`. Endpoints recebem `user: User = Depends(require_session)` e passam `user.id` (padrão user-scope).
**Where**: `backend/app/profile/router.py`, `backend/app/main.py`
**Depends on**: T4
**Reuses**: padrão router com modelos inline (activities/potential); `require_session`
**Requirement**: HRZ-01, HRZ-02, HRZ-03, HRZ-04, HRZ-08, HRZ-09, HRZ-12, HRZ-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] GET com sessão devolve o shape completo; métricas ausentes → null; zonas null sem config/métrica exigida
- [ ] PUT de métrica cria linha manual (idempotente no repetido); PUT de método cria config com defaults; PUT de bounds inválidos → 422 com o ponto inválido; PUT vazio → 422
- [ ] History DESC com data e fonte (HRZ-15)
- [ ] Sem sessão → 401 nos 3 endpoints; usuário A não lê métricas/config de B (isolamento)
- [ ] Gate check passes: `uv run pytest tests/test_hr_zones_api.py` + Full suite verde
- [ ] Test count: ~9 novos + existentes

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(hr-zones): profile hr-zones endpoints`

---

### T6: Gateway lê user settings e LTHR (+ FakeGateway)

**What**: `GarminGateway` ganha `get_user_settings()` (`_call(self._garmin.get_user_settings)` — userData, fonte do `maxHeartRate`) e `get_lactate_threshold()` (`_call(lambda: self._garmin.get_lactate_threshold(latest=True))` — custa 2 chamadas internas da lib: power + HR; documentado no docstring). `tests/fake_garmin.py`: FakeGateway ganha os dois métodos com dados de fixture (`userData.maxHeartRate`, `speed_and_heart_rate.heartRate` — incluindo o caso `heartRate: None`). Extração resiliente: valor ausente → métrica pulada, sem exceção.
**Where**: `backend/app/garmin/client.py`, `backend/tests/fake_garmin.py`, `backend/tests/test_garmin_gateway.py`
**Depends on**: None
**Reuses**: `_call` (teto/retry/intervalo, AD-002); padrão do gateway
**Requirement**: HRZ-05 (fontes)

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] 2 métodos passam pelo `_call` (contagem + sleep conferidos nos testes)
- [ ] FakeGateway serve os 2 métodos para os testes de sync (T8) — incluindo ausência de LTHR
- [ ] Nenhum endpoint de escrita (read-only no perfil Garmin)
- [ ] Gate check passes: `uv run pytest tests/test_garmin_gateway.py` + Full suite verde
- [ ] Test count: ~3 novos + existentes

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(garmin): user settings and lactate threshold gateway reads`

---

### T7: Upsert de métricas physio com manual-wins (`garmin/upserts.py`)

**What**: `update_physio_metrics(db, user_id, *, fcmax=None, fclthr=None, fcrest=None) -> int` — para cada valor não-None chama `profile.service.set_metric(source="garmin")` e conta as linhas criadas; None (ausente) pula a métrica; retorno = nº de linhas novas (0 = nada mudou). Manual-wins e idempotência herdam de `set_metric` (T4) — regra vive num lugar só.
**Where**: `backend/app/garmin/upserts.py`
**Depends on**: T4
**Reuses**: `profile.service.set_metric` (T4 — manual-wins e idempotência vivem lá); padrão de upserts idempotentes do módulo
**Requirement**: HRZ-03, HRZ-05, HRZ-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Valor novo → linha `source=garmin`; mesmo valor → nenhuma linha; vigente manual → nenhuma linha (manual-wins)
- [ ] Valor ausente (None) → métrica pulada sem erro; retorno conta só as criadas
- [ ] As 3 kinds cobertas (fcmax, fclthr, fcrest)
- [ ] Gate check passes: `uv run pytest tests/test_garmin_upserts.py` + Full suite verde
- [ ] Test count: ~6 novos + existentes

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(hr-zones): physio metrics upsert with manual-wins`

---

### T8: Fase physio no sync (run_sync)

**What**: Fase final do `run_sync` (após predições): `get_user_settings()` → `userData.maxHeartRate` (extração resiliente), `get_lactate_threshold()` → `speed_and_heart_rate.heartRate` (None → pula), fcrest = mínimo das `value` dos últimos 7 dias da tabela `rhr` do usuário (query local, zero chamadas) → `update_physio_metrics`. try/except → warning `{tipo: "physio", erro}` no stats, job segue `done` (padrão SYNC-20). `calls_made` sobe +3 (1 settings + 2 do LTHR).
**Where**: `backend/app/garmin/service.py`
**Depends on**: T6, T7
**Reuses**: padrão de fases com stats/warnings; janela da `rhr` já sincronizada
**Requirement**: HRZ-05, HRZ-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Sync happy path (FakeGateway) cria as 3 métricas `source=garmin` e `calls_made` +3
- [ ] LTHR ausente (`heartRate: None` no fake) → fclthr pulada, sem warning, job done
- [ ] Vigente manual → sem linha nova (manual-wins ponta a ponta); valor igual → sem linha
- [ ] fcrest = mínimo-7d da série `rhr` do próprio usuário (duas syncs com séries diferentes → linha nova só quando muda)
- [ ] Falha do gateway na fase → warning `{tipo: "physio"}` + job `done` com as fases anteriores intactas
- [ ] Gate check passes: `uv run pytest tests/test_garmin_service.py tests/test_sync_api.py` + Full suite verde
- [ ] Test count: ~5 novos + existentes

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(hr-zones): sync physio phase updates fc metrics`

---

### T9: Payload da avaliação — lthr do perfil + bloco zonas_fc

**What**: Em `evaluation/payload.py`: `lthr_bpm` passa a vir de `profile.service.metric_on(db, user_id, "fclthr", activity.start_time.date())` com fallback `settings.lthr_bpm` quando a métrica não existe (HRZ-17); novo bloco `zonas_fc` — `zones_on(db, user_id, data do treino)` → se há zonas E ≥1 volta com `avg_hr`+`duration_s`: `{zonas: [{n, low, high}], tempo_por_zona: [{zona, segundos, pct}]}` (denominador único = duração das voltas com FC — mesma convenção do bloco de pace); sem FC nas voltas OU zonas inexistentes → bloco omitido (HRZ-18/19).
**Where**: `backend/app/evaluation/payload.py`
**Depends on**: T4
**Reuses**: `build_evaluation_payload` já recebe `user_id` (T6 do user-scope — assinatura inalterada); `_tempo_por_zona` como convenção de denominador
**Requirement**: HRZ-17, HRZ-18, HRZ-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `lthr_bpm` = fclthr vigente na data do treino; sem métrica → fallback do env (pinado nos dois ramos)
- [ ] Bloco `zonas_fc` com tempo/percentual por zona exato (aritmética das voltas com FC); zonas da ÉPOCA do treino (métrica antiga → zonas antigas, HRZ-12 no payload)
- [ ] Nenhuma volta com FC → bloco ausente; zonas inexistentes (sem config/métrica) → bloco ausente
- [ ] Gate check passes: `uv run pytest tests/test_evaluation_payload.py` + Full suite verde
- [ ] Test count: ~6 novos + existentes

**Tests**: integration
**Gate**: quick + full

**Commit**: `feat(hr-zones): evaluation payload lthr from profile and hr zones block`

---

### T10: Frontend — helpers de API, proxy e entrada no menu

**What**: `lib/api.ts` ganha tipos (`HrMetric`, `HrZoneConfig`, `HrZone`, `HrZonesOut`, `HrZonesUpdate`) e helpers `getHrZones`, `updateHrZones`, `getHrZonesHistory` (via `apiFetch`, mesmo padrão dos existentes). `proxy.ts`: `/perfil` entra nas rotas protegidas (sem cookie → `/login?next=/perfil`). `UserMenu`: display_name vira link para `/perfil` (ao lado do Sair).
**Where**: `frontend/src/lib/api.ts`, `frontend/src/proxy.ts`, `frontend/src/components/UserMenu.tsx`
**Depends on**: T5 (contrato dos endpoints)
**Reuses**: `apiFetch` + `ApiError`/`parseError` existentes; matcher do proxy
**Requirement**: HRZ-16 (proteção) + wiring da tela

**Tools**:

- MCP: NONE
- Skill: NONE (ler `frontend/node_modules/next/dist/docs/` se mexer em convenções Next)

**Done when**:

- [ ] Helpers tipados espelhando o contrato da T5; zero `fetch(` direto
- [ ] `/perfil` sem cookie → `/login?next=/perfil`; com cookie → renderiza
- [ ] UserMenu linka para `/perfil` sem quebrar o Sair
- [ ] Gate check passes: `npm run lint && npm run build`
- [ ] Test count: sem test runner no frontend (matrix "none") — build gate

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): hr zones api helpers and profile entry`

---

### T11: Página `/perfil` — seção Valores

**What**: `src/app/(app)/perfil/page.tsx` (client) com a seção 1 "Valores" (padrão AD-009: índice + título + subtítulo "o que é / por que importa"): cards de fcmax, fcrest e fclthr com input numérico, badge de fonte (Garmin/Manual) e vigência (`valid_from`), estado vazio honesto ("nunca configurado" + orientação), salvar → `updateHrZones({metrics})` → re-render com os dados da resposta; erros 422 inline por campo em PT-BR (HRZ-14). Placeholders para as seções 2-3 (T12).
**Where**: `frontend/src/app/(app)/perfil/page.tsx`, `frontend/src/components/profile/`
**Depends on**: T10
**Reuses**: tema dos painéis (escuro, 390px mobile-first); padrão de erro inline do `/login`
**Requirement**: HRZ-01, HRZ-13, HRZ-14, HRZ-16

**Tools**:

- MCP: NONE
- Skill: NONE (ler docs do Next 16 em `node_modules/next/dist/docs/` antes da página — `frontend/AGENTS.md`)

**Done when**:

- [ ] GET popula os três valores com badge de fonte e vigência; vazios mostram orientação
- [ ] Editar + salvar → PUT → valores re-renderizam (fonte Manual); 422 mostra erro inline no campo
- [ ] Sem sessão → redirect `/login` (comportamento herdado do proxy/apiFetch)
- [ ] Layout 390px sem scroll horizontal (tema escuro)
- [ ] Gate check passes: `npm run lint && npm run build`

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): profile page with hr values editing`

---

### T12: Página `/perfil` — seções Método/Zonas e Histórico

**What**: Seção 2 "Método e zonas": seletor dos 3 métodos (lthr/fcr/fcmax) com os defaults pré-carregados do GET (`defaults`), edição dos percentuais (5 zonas × low/high), preview das zonas resultantes em bpm (render das `zones` da resposta do PUT — "salvar → zonas mudam na hora", HRZ-14), 422 de bounds inline na zona apontada. Seção 3 "Histórico": timeline das mudanças de métricas e configs (`getHrZonesHistory`), mais recente primeiro, com data e fonte (HRZ-15).
**Where**: `frontend/src/app/(app)/perfil/page.tsx`, `frontend/src/components/profile/`
**Depends on**: T11
**Reuses**: cards da seção 1 (T11); `defaults` do GET para prefill
**Requirement**: HRZ-08, HRZ-09, HRZ-13, HRZ-14, HRZ-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Trocar de método prefilla os percentuais com os defaults e salvar cria a config
- [ ] Editar percentuais + salvar → preview das zonas em bpm atualiza; bounds inválidos → 422 inline
- [ ] Histórico lista métricas e configs DESC com data e fonte
- [ ] Layout 390px coerente com o resto do app
- [ ] Gate check passes: `npm run lint && npm run build`

**Tests**: none
**Gate**: build

**Commit**: `feat(frontend): zone method config and history sections`

---

### T13: Documentação (README + .env.example)

**What**: README: status da Fase 1.5 com `hr-zones ✅`; seção "Zonas de FC no /perfil" (os 3 métodos, defaults, histórico effective-dated, sync traz as métricas — fcmax/fclthr do Garmin + fcrest do mínimo-7d, manual vence, nada é seedado); nota de que `LTHR_BPM` vira fallback do payload; `.env.example` documenta `LTHR_BPM` como fallback. Registra também: o primeiro sync real (UAT) confirma as chaves do Garmin (`userData.maxHeartRate`, LTHR detectado) — spike runtime.
**Where**: `README.md`, `backend/.env.example`
**Depends on**: T12 (todas as anteriores)
**Reuses**: estrutura do README (§Login e acesso, §Sync do Garmin)
**Requirement**: suporte a HRZ-05/07/17 (operação); nenhum AC novo

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] README documenta a tela, os métodos, o comportamento do sync e o fallback do env
- [ ] `.env.example` coerente com `core/config.py`
- [ ] Gate check passes: Build+Full final — `cd backend && uv run pytest` + `cd frontend && npm run lint && npm run build`
- [ ] Test count: suite inteira verde (~486)

**Tests**: none
**Gate**: build+full

**Commit**: `docs(hr-zones): document hr zones sync and profile screen`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

Phase 1:  T1 → T3
          T2 → T3

Phase 2:  T4 → T5

Phase 3:  T6 → T8
          T7 → T8

Phase 4:  T9

Phase 5:  T10 → T11 → T12

Phase 6:  T13
```

Arestas cross-phase (backward, permitidas) estão desenhadas nos blocos do Execution Plan: T1/T2 → T4, T4 → T7/T9, T5 → T10, T6 → T8. Dentro de uma fase a execução é sequencial.

Execution is strictly sequential - there is no intra-phase parallelism. A single agent (or batch worker) works one task at a time, in order.

**Batch sizing (Execute):** 13 tasks total → 3 batches (whole phases): Phase 1+2 (5 tasks), Phase 3+4 (4 tasks), Phase 5+6 (4 tasks). > ~8 tasks → offer batch sub-agents before starting Execute; user decides.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Modelos | 1 arquivo (models.py) | ✅ Granular |
| T2: calc.py puro | 1 módulo | ✅ Granular |
| T3: Seed config | 1 função no init_db | ✅ Granular |
| T4: Service resolução/escrita | 1 módulo | ✅ Granular |
| T5: Router + wiring | 1 seam coeso (router + include no main — router sem include é não-testável) | ⚠️ Cohesive (justificado — merge-forward das regras do workflow) |
| T6: Gateway + fake | 1 seam coeso (gateway + dublê dos testes — um sem o outro deixa T8 não-testável) | ⚠️ Cohesive (justificado) |
| T7: upsert physio | 1 função | ✅ Granular |
| T8: Fase physio | 1 fase do run_sync | ✅ Granular |
| T9: Payload lthr + zonas_fc | 1 arquivo (payload.py, dois blocos do mesmo contrato) | ⚠️ Cohesive (justificado) |
| T10: Helpers + proxy + UserMenu | 1 seam de wiring frontend | ⚠️ Cohesive (justificado — entry sem rota protegida é incompleto) |
| T11: Página + seção valores | 1 página + 1 card | ✅ Granular |
| T12: Seções método + histórico | 2 cards da mesma página (sequência natural do T11) | ⚠️ Cohesive (justificado) |
| T13: Docs | 2 arquivos documentais | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | raiz da Phase 1 | ✅ Match |
| T2 | None | raiz da Phase 1 | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 | ✅ Match |
| T4 | T1, T2 (cross-phase backward) | T1 → T4, T2 → T4 (bloco da Phase 2) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | None | raiz da Phase 3 | ✅ Match |
| T7 | T4 (backward) | T4 → T7 (bloco da Phase 3) | ✅ Match |
| T8 | T6, T7 | T6 → T8, T7 → T8 | ✅ Match |
| T9 | T4 (backward) | T4 → T9 (bloco da Phase 4) | ✅ Match |
| T10 | T5 (backward) | T5 → T10 (bloco da Phase 5) | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | T12 | T12 → T13 | ✅ Match |

**Rules:**
- Every `Depends on` in a task body has a corresponding arrow in the Execution Plan blocks. ✅
- Every arrow corresponds to a `Depends on` in the target task's body. ✅
- No task depends on a task in a later phase. ✅

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Models (db) | integration | integration | ✅ OK |
| T2 | Domínio puro (calc) | unit | unit | ✅ OK |
| T3 | Seed (engine) | integration | integration | ✅ OK |
| T4 | Service (profile) | integration | integration | ✅ OK |
| T5 | API (router + main) | integration | integration | ✅ OK |
| T6 | Gateway (garmin) | integration | integration | ✅ OK |
| T7 | Sync upserts | integration | integration | ✅ OK |
| T8 | Sync fase | integration | integration | ✅ OK |
| T9 | Payload (evaluation) | integration | integration | ✅ OK |
| T10 | Frontend (api/proxy/menu) | none | none | ✅ OK |
| T11 | Frontend (página) | none | none | ✅ OK |
| T12 | Frontend (components) | none | none | ✅ OK |
| T13 | Docs | none | none | ✅ OK |

**Rules:**
- "Tested in another task" is NOT a valid justification for `Tests: none`. ✅ (none only where matrix says none)
- `Tests: none` only valid when the coverage matrix says "none" for that layer. ✅
- Tasks creating multiple code layers use the HIGHEST test type required. ✅ (T6 gateway = integration, fakes incluídos)

---

## Status

| Task | Status | Commit |
| ---- | ------ | ------ |
| T1 | ✅ Complete | feat(db): add user hr metrics and zone configs tables |
| T2 | ✅ Complete | feat(hr-zones): pure zone math with method defaults and bounds validation |
| T3 | ✅ Complete | feat(db): seed default lthr zone config for user 1 |
| T4 | Pending | - |
| T5 | Pending | - |
| T6 | Pending | - |
| T7 | Pending | - |
| T8 | Pending | - |
| T9 | Pending | - |
| T10 | Pending | - |
| T11 | Pending | - |
| T12 | Pending | - |
| T13 | Pending | - |
