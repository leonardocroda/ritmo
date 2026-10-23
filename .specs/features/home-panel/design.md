# Home Panel — Design

**Spec**: `.specs/features/home-panel/spec.md`
**Status**: Draft

---

## Architecture Overview

Três camadas no backend seguindo o espírito da AD-003 (matemática/decisão em função pura; service só lê e monta; router só contrato) + um painel client-side no frontend consumindo um único endpoint — payload 1:1 (AD-009).

```mermaid
graph TD
    PAGE["/ (page.tsx) → <HomePanel/>"] --> API["lib/api.ts getHomeToday()"]
    API -->|GET /api/home/today| RT["app/home/router.py (HomeOut)"]
    RT -->|require_session| SVC["app/home/service.py — montagem"]
    SVC -->|get_health(db, uid, 8, tz)| HLT["app/health/service.py (AD-010 — status idêntico ao Saúde)"]
    SVC -->|aggregate_daily_loads| PMC["app/garmin/pmc.py (strip 7d)"]
    SVC -->|queries diretas| DB[(activities · load · races)]
    SVC --> CALC["app/home/calc.py — veredito V1–V6 + recomendações R1–R5 (puro)"]
    SVC -->|P2: load_calibration + predictions| POT["app/potential (digest de previsões)"]
    CALC --> SVC
    NAV["Nav.tsx PANELS — 5 itens, Home 1ª (href /)"]
```

**Abordagens consideradas** (Large — exploração exigida) — o fork arquitetural é **como o payload obtém os sinais de saúde**:

1. **Reuso do service de saúde com janela 8 (escolhida: A)** — `get_health(db, uid, 8, tz)` devolve `hrv.current` com o status AD-010 (a janela de banda de 60d é interna ao bloco — `_hrv_history` estende por `HRV_BASELINE_DAYS`) e as 8 últimas noites pro delta de sono. Consistência com o Saúde **por construção** — mesma função, nunca duas interpretações. Custo: computa blocos que a Home descarta (dose_response, lifestyle) — queries pequenas, desprezível num endpoint de abertura.
2. **Reimplementação mínima + `hrv_model` importado** — menos desperdício, mas duplica a montagem da janela (`days + 58` lookback) e cria exatamente o risco de divergência que o AC de consistência do spec proíbe.
3. **Frontend compõe endpoints existentes** (client chama health + potential + activities) — viola a AD-009 (payload 1:1), 3 fetches com staleness inconsistente entre si, acoplamento cross-painel.

**A** entrega a garantia estrutural ("mesmo dado, mesma resposta") ao preço de computo morto insignificante.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --------- | -------- | ---------- |
| `get_health(db, uid, days, tz)` | `app/health/service.py:217` | Chamada única com `days=8`: fonte do `hrv.current` (status AD-010) e das noites do delta de sono |
| `SLEEP_FLOOR_S` | `app/health/calc.py:21` | Import direto — mesmo piso do painel Saúde |
| `aggregate_daily_loads(db, uid)` | `app/garmin/pmc.py:24` | Strip de 7 dias — a mesma fonte de carga da PMC |
| `RUNNING_TYPES` | `app/activities/service.py:24` | Filtro de corrida para volume e último treino |
| `Activity.evaluated` | `app/db/models.py` (propriedade) | Selo "avaliado ✓" sem nova query de avaliações |
| `load_calibration(settings.vdot_zones_path)` | `app/vdot/calibration.py` | P2: digest de previsões com a mesma calibração do painel Performance |
| `predictions(...)` / `_garmin_by_event(...)` | `app/potential/{calc,service}.py` | P2: extrair `get_predictions(db, uid, calibration)` fino que `get_potential` também usa (zero duplicação) |
| `_resolve_tz` → `app/core/tz.py` | novo, extraído de `health/router.py:159` | `app_tz()` único; health delega (o teste de edge de tz do health vira a rede de regressão) |
| `PanelState` `{kind: loading|error}` + fetch pattern | `components/health/HealthPanel.tsx:41-120` | HomePanel replica o padrão + kind `empty` |
| `Skeleton` | `components/Skeleton.tsx` | Carregamento com a cara da identidade (DSN-23) |
| Tokens/`chartTheme` | `globals.css` · `lib/chartTheme.ts` | Herói `bg-raised`, tons semânticos, strip neutro com hoje lime — zero cor literal |
| `formatKm`/`formatDuration`/`formatDateTime`/`formatWeekday` | `lib/format.ts` | Formatação pt-BR dos chips e do eyebrow |
| Ícone de casa do mock | `docs/design/identidade-visual-v0.3.html:330` | SVG line 22px inline no Nav (mesmo estilo dos 4 existentes) |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| API / backend | Novo `GET /api/home/today` (session-scoped, 401 pré-query); nenhum endpoint existente muda — health/potential são lidos via service, não via HTTP |
| Navegação | `PANELS` ganha Home em 1º (href `/`); `activePanel` trata raiz: ativo **somente** em `pathname === "/"` (o `startsWith("/")` casaria tudo — bug estrutural) |
| Próximo do Next 16 | `(app)/page.tsx` deixa de fazer `redirect()` e vira página — nenhuma convenção nova (docs Next 16 consultadas se algo além do padrão surgir no Execute) |
| Seed | `init_db` semeia The Best Açaí (2026-11-08, 21097.5m, goal null) quando `races` vazio p/ usuário 1 — mesmo espírito idempotente dos seeds existentes |

---

## Components

### `app/home/calc.py` — motor puro

- **Purpose**: Veredito V1–V6, recomendações R1–R5, delta de sono, volume semanal — tudo função pura, testável sem banco.
- **Location**: `backend/app/home/calc.py`
- **Interfaces**:
  - `verdict(signals: Signals) -> Verdict | None` — cadeia de prioridade fixa V1→V6; `None` quando nenhum sinal existe (estado vazio orientando sync); sinal `None` é neutro (nunca dispara regra)
  - `recommendations(rule: str, countdown_days: int | None) -> list[Recommendation]` — R1–R5 por prioridade, cap 3, cada `{text, support, why, tone}`
  - `sleep_delta(durations: list[float | None]) -> float | None` — última noite vs média das 7 anteriores **com dado**
  - `weekly_volume(runs: list[tuple[date, float]], today: date) -> WeeklyVolume` — semanas ISO (segunda), corrente + média das 4 completas + série de 10 semanas
  - Constantes: `TSB_QUALITY = 0`, `TSB_FATIGUE = -10`, `ACWR_HIGH = 1.5`, `TAPER_DAYS = 14` + tabela de frases V1–V6 (pt-BR, sentence case)
- **Dependencies**: nenhuma (módulo stdlib puro).
- **Reuses**: nomenclatura de tom `good|attention|alert|neutral` = tokens semânticos do design-system.

### `app/home/service.py` — montagem

- **Purpose**: Ler as fontes uma vez e montar o payload 1:1 do painel; zero regra de negócio aqui.
- **Location**: `backend/app/home/service.py`
- **Interfaces**: `get_home(db: Session, user_id: int, tz: ZoneInfo) -> dict`
- **Assembly**:
  - `health = get_health(db, uid, 8, tz)` → `hrv.current` (status/valor/data) + 8 noites (delta) + `floor_s`
  - `load`: última linha de `DailyLoad` (tsb, acwr, data) → sinal "Forma"
  - `strip`: `aggregate_daily_loads(db, uid)` → fatia dos últimos 7 dias corridos preenchendo lacunas com 0.0
  - `last_activity`: última `Activity` em `RUNNING_TYPES` → `{id, date, distance_m, evaluated}`; sem corridas → `None`
  - `volume` + `volume_weeks`: atividades dos últimos ~70d em `RUNNING_TYPES` → `calc.weekly_volume`
  - `countdown`: próxima `Race` com `date >= today` → `{name, date, days_left}`; "é hoje" quando 0; passadas ignoradas
  - `predictions` (P2): `load_calibration` + `get_predictions` extraído do potential; `ZoneConfigError` → `None` (degrada, nunca 500)
  - `verdict`/`recommendations`: delegados ao calc
- **Dependencies**: `health.service`, `garmin.pmc`, `activities.service.RUNNING_TYPES`, `potential.service` (P2), `home.calc`
- **Reuses**: `_today(tz)` 3-liner local (documentado: duplicar 3 linhas < acoplar a private de outro módulo)

### `app/home/router.py` — contrato

- **Purpose**: `GET /api/home/today` → `HomeOut`, sessão obrigatória, `app_tz()`.
- **Location**: `backend/app/home/router.py`
- **Interfaces** (Pydantic, espelho 1:1):
  - `HomeOut{date, verdict | None, signals{hrv | None, sleep | None, fitness | None}, strip[7], last_activity | None, volume | None, countdown | None, recommendations[1..3], volume_weeks[10] | None, predictions | None}`
  - `VerdictOut{phrase, tone, rule}` · `SignalOut{value, label_parts, as_of, state}` · `CountdownOut{name, date, days_left}` · `RecommendationOut{text, support, why, tone}`
- **Dependencies**: `auth.require_session`, `db.get_db`, `core.tz.app_tz`
- **Reuses**: padrão dos routers existentes (401 pré-query via dependency)

### `app/core/tz.py` — fuso único (refactor fino)

- **Purpose**: `app_tz() -> ZoneInfo` — extrai o resolvedor (inválida → default + `logger.warning`) que hoje vive como `_resolve_tz` no health router.
- **Location**: `backend/app/core/tz.py`; `health/router.py` delega em 1 linha (comportamento idêntico; o teste de edge existente vira a prova de não-regressão)
- **Reuses**: `get_settings().app_timezone`, `DEFAULT_TIMEZONE`

### Seed da prova — `app/db/engine.py`

- **Purpose**: A meia no banco para o countdown; idempotente.
- **Interfaces**: dentro do `init_db`, após os seeds existentes: `count(Race user 1) == 0` → insert `{name: "The Best Açaí", date: date(2026, 11, 8), distance_m: 21097.5, goal_time_s: None}`
- **Dependencies**: models.Race
- **Reuses**: padrão dos seeds idempotentes existentes (sem setval — id auto)

### `frontend/src/lib/api.ts` — cliente

- **Purpose**: `HomeToday` (espelho tipado do `HomeOut`) + `getHomeToday()`.
- **Reuses**: `API_BASE = ""` (rewrite same-origin, AD-020); padrão dos fetchers existentes.

### `frontend/src/app/(app)/page.tsx` — raiz

- **Purpose**: Renderiza `<HomePanel />`; o `redirect("/treinos")` morre.
- **Reuses**: composição das outras páginas de painel (server component mínimo + client panel).

### `frontend/src/components/home/HomePanel.tsx` — painel

- **Purpose**: Fetch + máquina de estados + composição (veredito → chips → recomendações → digests).
- **Interfaces**: `PanelState = {kind: "loading"} | {kind: "error", message} | {kind: "empty"} | {kind: "ready", data: HomeToday}` — `empty` derivado de `verdict == null && strip vazia && last_activity == null` (orienta primeiro sync com link `/perfil`, padrão CLR-11).
- **Reuses**: pattern `useEffect` + `catch` do HealthPanel; `Skeleton`.

### `frontend/src/components/home/VerdictCard.tsx` — herói

- **Purpose**: O card memorizável: `bg-raised`, eyebrow `"Hoje · sexta, 23 de outubro"` (`formatWeekday` + `Intl`), frase display 38–40px sentence case, 3 chips de sinal (dot semântico + valor + estado + data quando stale) e o strip.
- **Interfaces**: props `{verdict, signals, strip, date}`; strip = 7 barras neutras com hoje lime, caption `"carga · últimos 7 dias"`; dia sem carga = barra zero (informação, não lacuna).
- **Reuses**: tokens (`text-good/attention/alert`, `bg-raised`, `tabular-nums`); nenhuma cor literal.

### `frontend/src/components/home/RoutingChips.tsx` + `RecommendationCards.tsx`

- **Purpose**: Chips `Último treino → /treinos/{id}` · `Volume → /performance` · `Meia · faltam N → /performance` (um dado, um verbo, um destino; ≥44px); cards `Recomendação · regra` com texto, linha de apoio e tag why.
- **Reuses**: `formatKm`, `Link` do Next, `bg-card` + `rounded-card`.

### P2: `VolumeMini.tsx` + `PredictionsDigest.tsx`

- **Purpose**: Mini de 10 semanas (barras neutras, corrente lime, sentença `Xkm · ±Y% · ACWR Z`) + linha de previsões 10K/meia com `ver Performance →`.
- **Reuses**: dados já no payload P1 (`volume_weeks`, `predictions`) — P2 é pura renderização.

### `frontend/src/components/Nav.tsx` — 5 itens

- **Purpose**: Home em 1º lugar.
- **Interfaces**: `PANELS` com `{href: "/", label: "Home", Icon: HomeIcon}` no índice 0; `activePanel` special-case raiz (`href === "/" ? pathname === "/" : ...`); tab bar `grid-cols-4` → `grid-cols-5`.
- **Reuses**: o pill ativo, o `aria-current`, as boundaries Suspense existentes.

---

## Data Models

Nenhuma tabela nova. O seed escreve na `races` existente (`Race: name, date, distance_m, goal_time_s` — AD-001 `user_id` default 1). Contrato novo:

```python
class HomeOut(BaseModel):
    date: date                                   # hoje em APP_TIMEZONE
    verdict: VerdictOut | None                   # None = sem dado nenhum → estado vazio
    signals: SignalsOut                          # hrv/sleep/fitness, cada | None
    strip: list[StripPoint]                      # exatamente 7 (date, load)
    last_activity: LastActivityOut | None         # RUNNING_TYPES, evaluated
    volume: VolumeOut | None                      # week_km, avg4_km, delta_pct | None
    countdown: CountdownOut | None                # name, date, days_left
    recommendations: list[RecommendationOut]      # 1..3, {text, support, why, tone}
    volume_weeks: list[WeekPoint] | None          # P2: 10 semanas {week_start, km}
    predictions: list[PredictionDigest] | None    # P2: [{event, time_s}]
```

**Relação com models existentes**: leitura de `hrv`/`sleep`/`load`/`activities`/`races` via services/pmc já cobertos por testes — a Home não reescreve nenhuma interpretação.

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| Sem sessão | 401 pela dependency antes de qualquer query | Login (padrão existente) |
| `APP_TIMEZONE` inválida | `app_tz()` → default + `logger.warning` | Painel funcional no fuso default (mesma edge do Saúde) |
| Banco sem dado nenhum | `verdict: None` + blocos nulos → frontend estado `empty` com link `/perfil` | Orientação de primeiro sync, sem frase falsa |
| Sinal parcial (ex.: só sono) | Sinal ausente é neutro (nunca dispara regra); chip com estado vazio | "Dia comum" honesto sobre o que existe |
| Dado antigo (sem sync hoje) | Chip exibe a data do dado (`HRV 68ms · 21/10`) | Nunca apresenta antigo como hoje |
| `ZoneConfigError` no digest (P2) | `predictions: None` | Digest omitido — a Home nunca 500 por causa de um bloco P2 |
| Falha do fetch no client | `kind: "error"` com mensagem (contrato existente) | Estado de erro padrão do painel |
| Semana sem corridas | Barra/chip zero ou `—` (delta) | Descanso é informação |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | -------------------- | ------ | ---------- |
| `activePanel` com `href="/"` casa TODA rota (`startsWith("/")`) | `components/Nav.tsx:102-108` | Tab Home sempre ativa — quebra a nav inteira | Special-case raiz no design; gate: UAT + teste estrutural (grep do special-case) na task da nav |
| Conflito `init_db` semear meia em TODOS os testes (conftest re-cria schema) | `backend/tests/conftest.py` | Testes de countdown null precisam limpar `races` no setup; fixtures existentes ganham uma prova inesperada | Task do seed documenta: teste do countdown calcula `days_left` dinamicamente; caso "sem prova" faz `DELETE FROM races` no arrange |
| `get_health(8)` computa blocos mortos (dose/lifestyle) | `app/health/service.py:217` | Custo desprezível, mas acoplamento ao contrato do Saúde | Aceito por design (abordagem A); se o Saúde mudar bloco, o teste de consistência (home status == saúde status) acusa |
| `aggregate_daily_loads` retorna histórico inteiro | `app/garmin/pmc.py:24` | Lista cresce com o tempo; fatiar os últimos 7 em Python é O(n) | Volume de dados pessoal (centenas de linhas) — fatiar direto, sem query nova |
| Extrair `get_predictions` toca `potential/service.py` | `app/potential/service.py:153-173` | Refactor em módulo validado por outro painel | Extração pura (mesma chamada interna, `get_potential` passa a usá-la); suite existente do potential é a rede |
| `app/core/tz.py` muda o health router | `app/health/router.py:159-169` | Regressão na edge de timezone | O teste de edge do health (existe) vira prova de não-regressão; mudança é delegação 1:1 |
| Semana corrente parcial infla o `+8%` do chip | volume (qualquer) | Leitura injusta ("+8%" com 3 dias) | Chip compara semana corrente vs média de 4 COMPLETAS — a parcial é o ponto (mostra o rumo); UAT decide o tom da copy |
| `predictions.average_s` pode ser None (evento sem dado) | `app/potential/calc.py` | Digest com "—" inventado | AC do spec: evento sem predição é omitido, não exibido |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Fonte dos sinais de saúde | `get_health(db, uid, 8, tz)` — reuso integral (abordagem A) | Consistência com o Saúde por construção; o AC do spec exige mesmo status, mesma função |
| Fuso | `app/core/tz.py::app_tz()` extraído; health delega | Uma resposta por pergunta; o teste de edge do health prova a não-regressão |
| Digest de previsões (P2) | Extrair `get_predictions(db, uid, calibration)` no potential/service (usado pelo `get_potential` também) + `ZoneConfigError → None` | Zero duplicação da montagem; Home nunca 500 por bloco P2 |
| Volume/último treino | Filtro `RUNNING_TYPES` (`running`, `trail_running`) | Força/yoga não são "treino" no contexto de corrida nem volume; constante única já existente |
| Semanas ISO segunda-feira | `calc.weekly_volume` puro sobre `(date, meters)` | Convenção pt-BR; sem input do banco no calc (testável) |
| `evaluated` | Propriedade do model `Activity.evaluated` | Mesma definição da lista de treinos — zero divergência |
| Veredito `None` vs "Dia comum" | `None` = banco vazio (estado vazio); "Dia comum" = existe dado, nenhuma regra específica | O AC do estado vazio exige distinção; o payload deriva sem campo extra |
| Strip com lacuna | Fatiar os últimos 7 dias corridos e preencher 0.0 | "Dia de descanso é informação" (spec) |
| Tab bar 5 itens | `grid-cols-5` + Home 1ª + special-case do `activePanel` | Mock §06; sem o special-case a nav quebra inteira |

> **Project-level decisions**: nenhuma AD nova além das já registradas na spec (AD-024 hábitos adiado, AD-025 Home painel-raiz). As decisões aqui são feature-local.
