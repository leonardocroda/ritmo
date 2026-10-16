# Painel Saúde — Design

**Spec**: `.specs/features/health-panel/spec.md`
**Status**: Draft

---

## Architecture Overview

Espelho do `potential/`: um domínio de leitura novo `health/` (router + service + funções puras em `calc.py`), zero Garmin (AD-002), todo número determinístico em Python (AD-003). **Nenhuma mudança de schema e nenhuma mudança de sync** — todas as 6 fontes (sleep, hrv, rhr, stress, activities) já existem e já são populadas pelo sync do garmin-sync. O endpoint é `GET /api/health/summary` porque `/api/health` exato já é o health check de infra (contrato INFRA-02 validado — spec, premissa "Caminho do endpoint").

A única infraestrutura nova é uma env var: `APP_TIMEZONE` (default `America/Sao_Paulo`), usada para converter os `bed_time`/`wake_time` GMT naive do banco em horário local exibível — o docker-compose já roda o backend com `TZ=America/Sao_Paulo`, mas a conversão usa `zoneinfo` com a env própria para ser determinística em dev local e em teste.

```mermaid
graph TD
    subgraph Leitura (health/)
        RT[health/router GET /api/health/summary] --> SVC[health/service]
        SVC --> CAL[calc.py · dose_response / weekday_pattern / regularity / strength_weeks · puro]
        SVC --> DB[(Postgres<br/>sleep · hrv · rhr · stress · activities)]
        SVC --> TZ[zoneinfo APP_TIMEZONE]
    end
    RT --> FE[frontend /saude · HealthPanel]
    FE -->|Recharts AD-008| CH[SleepChart · RemChart · WeekdayPattern<br/>HrvChart · RhrChart · StressChart]
    FE --> CARDS[DoseResponse · Lifestyle]
```

**Abordagens consideradas** — (a) **domínio novo `health/` com agregação em tempo de leitura** — escolhida: espelha `potential/`, zero escrita duplicada, escala pessoal (~63 linhas/tabela) torna a agregação trivial; (b) estender `activities/` com o endpoint — descartada: o painel agrega sono/HRV/RHR/estresse + estilo de vida derivado das atividades, não é subconjunto da listagem; (c) pré-calcular resumos durante o sync (novas tabelas de agregados) — descartada: o padrão do projeto é derivar em leitura (tipo inferido, timeline VDOT), e as janelas/réguas (60d, piso 7h, buckets) são parâmetros de leitura, não verdades persistidas.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| ---------- | -------- | ---------- |
| Padrão router Pydantic + `Query` bounds (422 antes da query) | `backend/app/potential/router.py:99-117` | `health/router.py` idem (`days: Query(60, ge=7, le=365)`) — sem `ZoneConfigError` (o painel Saúde não depende do `vdot_zones.json`) |
| Padrão service de leitura (janela `ORDER BY date DESC LIMIT days` + `reversed`) | `backend/app/potential/service.py:39-56` | Mesma query das 4 séries (sleep/hrv/rhr/stress) |
| Funções puras de cálculo | `backend/app/potential/calc.py` | `health/calc.py` mesmo papel: `dose_response`, `weekday_pattern`, `regularity`, `strength_weeks` |
| Filtro de atividades por typeKey em Python | `backend/app/potential/service.py:139-143` + AD-001 | Carregar atividades do usuário e filtrar `strength_training`/`yoga` em memória (~233 linhas) |
| `_gmt_ms_to_naive_datetime` (convenção GMT naive) | `backend/app/garmin/mappers.py` | Contraparte no `calc.py`: `local_wall(bed/wake, tz)` converte naive UTC → local (o inverso da leitura) |
| Cliente tipado + `parseError` | `frontend/src/lib/api.ts` | Extend: tipos + `getHealthSummary(days = 60)` |
| Formatadores PT-BR | `frontend/src/lib/format.ts` | Reuso de `formatDuration` (tooltip), `formatDateTime`; novos `formatHours` (6,3 h), `formatClock` (min → "22:16") |
| Padrão page-shell fetch/estados | `frontend/src/components/potential/PotentialPanel.tsx` | `HealthPanel` idem (loading/error/empty, `Section`) |
| Padrão ComposedChart + ReferenceLine + Tooltip + StatCards | `frontend/src/components/potential/PmcChart.tsx` | Base direta de SleepChart/RhrChart/StressChart (`ReferenceArea` para a banda de REM) |
| Fixtures de payloads reais de saúde | `backend/tests/helpers.py:156-241` | Referência de shapes (SLEEP/HRV/RHR/STRESS_PAYLOAD); para a API, seeds ORM diretos (padrão `test_potential_api.py`) |
| Página placeholder | `frontend/src/app/saude/page.tsx` | Troca pelo `<HealthPanel />` (rota já no Nav) |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| Postgres | Somente leitura — zero tabela nova, zero migração |
| `app.core.config` | +1 campo `app_timezone: str = "America/Sao_Paulo"` (env `APP_TIMEZONE`) |
| Router mounting | `app.main` ganha `include_router(health_router)` (antes do health check de infra não importa: paths distintos) |
| Navegação | `/saude` troca o placeholder pelo painel (rota já existe no Nav) |
| docker-compose | Nada muda (TZ do container já casa com o default da env; a env é adicionada ao compose por clareza) |

---

## Components

### Backend — `app/health/`

#### `app/health/calc.py` (novo)

- **Purpose**: Toda a matemática do painel como funções puras — pinável em teste (AD-003).
- **Interfaces**:
  - Constantes: `SLEEP_FLOOR_S = 25200`, `REM_BAND = (21.0, 31.0)`, `SHORT_MAX_S = 21600` (<6h), `ADEQUATE_MIN_S = 24300` (≥6h45)
  - `dose_response(nights: list[dict]) -> dict` — cruza sono↔HRV/score **da mesma data**; buckets `short`/`adequate` com `{nights, avg_hrv, avg_score}` (média `None` em bucket vazio) + `neutral_nights`; noites sem HRV na mesma data ficam fora, contando como neutra só se caírem na faixa 6h–6h45
  - `weekday_pattern(nights: list[dict]) -> list[dict]` — 7 entradas `{weekday: 0..6 (seg..dom), avg_duration_s, nights}` pelo weekday da data de acordar; dia sem noites → `avg_duration_s: None, nights: 0`
  - `regularity(nights: list[dict]) -> dict | None` — `{avg_bed_min, avg_wake_min}` em minutos locais; noite sem `bed_time`/`wake_time` fica fora; sem noites elegíveis → `None`
  - `local_minute(naive_utc: datetime, tz: ZoneInfo) -> int` — minuto do dia local (a conversão cruza a meia-noite: 01:16 GMT → 1336 min local); média com o truque do deslocamento de ±12h (meia-noite não vira meio-dia na média)
  - `strength_weeks(sessions: list[datetime | date], today: date, window_start: date) -> dict` — `{streak_weeks, weeks_hit, weeks_total, current_week_sessions}` por semana ISO (≥2 sessões; streak conta semanas completas consecutivas terminando na última semana completa, podendo exceder a janela; `weeks_hit`/`weeks_total` limitados à janela; semana corrente reportada à parte)
  - `below_floor(nights: list[dict]) -> dict` — `{nights, pct}` das noites `duration_s < SLEEP_FLOOR_S` (pct 1 casa)
- **Dependencies**: stdlib (`datetime`, `zoneinfo`) — nenhuma query, nenhum ORM.

#### `app/health/service.py` (novo)

- **Purpose**: Montar o payload a partir do banco; conversão de fuso acontece aqui (config injetada).
- **Interfaces**: `get_health(db: Session, days: int, tz: ZoneInfo) -> dict` — 4 queries de série (sleep/hrv/rhr/stress, `user_id` + janela + ASC), 1 query de atividades (para lifestyle); blocos `null` quando a série está vazia (HLT-11); `dose_response`/`lifestyle` sempre presentes (com zeros honestos).
- **Reuses**: padrão de query/janela do `potential/service.py`; `DEFAULT_USER_ID`.

#### `app/health/router.py` (novo)

- **Interfaces**: `GET /api/health/summary?days=60` — `days: int = Query(60, ge=7, le=365)` (422 fora, HLT-03); modelos Pydantic inline (`SleepPoint`, `SleepBlock`, `HrvBlock`, `RhrBlock`, `StressBlock`, `DoseBucket`, `DoseResponse`, `Lifestyle`, `HealthSummaryOut`); `tz` resolvido de `get_settings().app_timezone` com fallback `America/Sao_Paulo` + warning log se inválido (edge da spec).
- **Reuses**: padrão do `potential/router.py`.

### Backend — config/mounting

#### `app/core/config.py`

- **Interfaces**: + `app_timezone: str = "America/Sao_Paulo"` (100% env vars — requisito Fase 1).

#### `app/main.py`

- **Interfaces**: `include_router(health_router)`; o `@app.get("/api/health")` de infra permanece intocado.

### Frontend

#### `frontend/src/lib/api.ts`

- **Interfaces**: tipos espelhando `HealthSummaryOut` (`SleepBlock`, `HrvBlock`, `RhrBlock`, `StressBlock`, `DoseResponse`, `Lifestyle`) + `getHealthSummary(days = 60): Promise<HealthSummaryOut>` (`cache: "no-store"`).

#### `frontend/src/lib/format.ts`

- **Interfaces**: `formatHours(seconds)` → "6,3 h"; `formatClock(minuteOfDay)` → "22:16"; `formatWeekday(0..6)` → "seg".."dom" (a API usa número, o rótulo é camada de exibição — padrão ASCII na API/acento na UI).

#### `frontend/src/components/health/HealthPanel.tsx` (novo)

- **Purpose**: Page-shell do painel: fetch, estados loading/error/empty, seções.
- **Interfaces**: client component (padrão `PotentialPanel`); renderiza Sono (SleepChart + SleepStagesChart + RemChart + regularidade + WeekdayPattern), HRV/RHR (HrvChart + RhrChart), Dose-resposta (DoseResponse), Equilíbrio de vida (Lifestyle + StressChart); bloco `null` → estado vazio próprio do bloco; painel inteiro vazio (todas as séries null) → estado vazio apontando o sync (HLT-28).
- **Reuses**: `Section`, padrão de estados e empty state do `PotentialPanel`.

#### `frontend/src/components/health/SleepChart.tsx` (novo)

- **Purpose**: Duração por noite vs piso (HLT-13/14).
- **Interfaces**: Recharts `ComposedChart` — `Bar` duração (h) + `ReferenceLine y=floor` tracejada + tooltip com score/REM%; resumo "% das noites abaixo do piso" acima do gráfico.
- **Dependencies**: recharts.

#### `frontend/src/components/health/RemChart.tsx` (novo)

- **Purpose**: REM% por noite com a banda ideal (HLT-15).
- **Interfaces**: Recharts `ComposedChart` — `Line` rem_pct + `ReferenceArea` 21–31 (banda sombreada, visível) + domínio Y fixo 0–40.

#### `frontend/src/components/health/SleepStagesChart.tsx` (novo)

- **Purpose**: Composição de fases por noite (HLT-30).
- **Interfaces**: Recharts `BarChart` empilhado (`stackId` único) — `Bar` light_pct (base, neutra), `Bar` deep_pct, `Bar` rem_pct; domínio Y 0–100; tooltip com as 3 fases + despertares ("2 despertares", omitido quando null). Sem normalização: os pcts passam como gravados (série real soma 100,0–100,2%).
- **Dependencies**: recharts.

#### `frontend/src/components/health/WeekdayPattern.tsx` (novo)

- **Purpose**: Média de duração por dia da semana (HLT-16).
- **Interfaces**: Recharts `BarChart` com 7 entradas (rótulo `formatWeekday`) + a regularidade (deitar/acordar médios em horário local via `formatClock`) como cards acima do gráfico.

#### `frontend/src/components/health/HrvChart.tsx` / `RhrChart.tsx` / `StressChart.tsx` (novos)

- **Purpose**: Linhas das séries (HLT-17/18/25).
- **Interfaces**: Recharts `LineChart`/`ComposedChart` — HRV com badge textual do `current.status` (BALANCED/UNBALANCED/LOW) + valor do último dia; RHR com `ReferenceLine y=baseline`; Estresse com média da janela em card (`"—"` quando null — HLT-26).

#### `frontend/src/components/health/DoseResponse.tsx` (novo)

- **Purpose**: O comparativo que convence a dormir (HLT-20..22).
- **Interfaces**: Sem gráfico — dois cards lado a lado (`<6h` vs `≥6h45`) com noites, HRV média e score médio ("—" quando null) + nota da faixa neutra ("N noites fora da comparação").

#### `frontend/src/components/health/Lifestyle.tsx` (novo)

- **Purpose**: Checklist de força e yoga (HLT-23/24).
- **Interfaces**: Cards: força (streak em semanas, `weeks_hit`/`weeks_total`, sessões da semana corrente "em andamento"), yoga (sessões + média/semana).

#### `frontend/src/app/saude/page.tsx`

- Server page renderizando `<HealthPanel />` (placeholder sai).

---

## Data Models

Sem tabela nova. O contrato `GET /api/health/summary` (valores reais de hoje, ilustrativos):

```json
{
  "sleep": {
    "days": 60,
    "floor_s": 25200,
    "rem_band": [21.0, 31.0],
    "below_floor": {"nights": 50, "pct": 84.7},
    "regularity": {"avg_bed_min": 1336, "avg_wake_min": 388},
    "weekday_pattern": [
      {"weekday": 0, "avg_duration_s": 23148, "nights": 8},
      {"weekday": 4, "avg_duration_s": 20664, "nights": 9}
    ],
    "points": [
      {"date": "2026-10-15", "duration_s": 22020, "score": 74, "rem_pct": 13.8,
       "deep_pct": 25.1, "light_pct": 61.1, "awakenings": 2,
       "bed_local": "22:16", "wake_local": "05:02"}
    ],
  },
  "hrv": {
    "points": [{"date": "2026-10-15", "value": 77.5, "status": "BALANCED"}],
    "current": {"date": "2026-10-16", "value": 80.0, "status": "BALANCED"}
  },
  "rhr": {"points": [{"date": "2026-10-15", "value": 44}], "baseline": 44.1},
  "stress": {"points": [{"date": "2026-10-15", "avg": 24}], "avg_window": 24.0},
  "dose_response": {
    "short": {"nights": 17, "avg_hrv": 69.5, "avg_score": 60.2},
    "adequate": {"nights": 27, "avg_hrv": 81.3, "avg_score": 80.2},
    "neutral_nights": 18
  },
  "lifestyle": {
    "strength": {"streak_weeks": 0, "weeks_hit": 2, "weeks_total": 9, "current_week_sessions": 1},
    "yoga": {"sessions": 13, "per_week_avg": 1.4}
  }
}
```

`sleep`/`hrv`/`rhr`/`stress` = `null` quando a série está vazia na janela; `regularity` = `null` sem noites com horários; `dose_response` e `lifestyle` sempre presentes (com zeros/"—" honestos). `bed_local`/`wake_local` são strings "HH:MM" já no fuso de `APP_TIMEZONE` — a UI nunca faz conversão de fuso (o formato.ts mantém a postura "wall clock exibido como vem").

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| `days` fora de [7, 365] | 422 FastAPI antes da query (padrão POT) | UI nunca envia; visível em dev |
| `APP_TIMEZONE` inválido | Fallback `America/Sao_Paulo` + warning log (spec, edge) | Painel segue no fuso default, sem crash |
| Série vazia na janela | Bloco `null` → estado vazio do bloco na UI | Mensagem orientando o sync, resto do painel intacto |
| Noite sem `bed_time`/`wake_time` | Fora de `regularity`; presente nos gráficos | Nenhum horário inventado |
| Bucket do dose-resposta sem noites | Médias `null` → "—" na UI | Comparativo honesto com o que existe |
| API fora do ar | Mensagem inline no painel (padrão workouts/potential) | Navegação segue funcionando |
| Sem nenhum dado de saúde | Painel inteiro vazio → estado vazio apontando o sync | Padrão `WorkoutsList` |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | -------------------- | ------ | ---------- |
| Média de horário perto da meia-noite (23:50 e 00:10 → média errada 12:00) | `health/calc.py` (`local_minute`/`regularity`) | Regularidade sem sentido para quem dorme depois da meia-noite | Truque do deslocamento ±12h na média (minutos medidos a partir do meio-dia); hoje os dados do usuário (deitar ~22:20 local) estão longes do edge, mas a função é pura e testada para o caso |
| `bed_time`/`wake_time` GMT naive podem cair no dia anterior ao `date` da noite | `sleep` (banco) vs conversão local | Se alguém associar o horário ao dia errado, o padrão semanal muda de dia | A conversão usa o datetime completo (cruza a meia-noite corretamente: 01:16 GMT → 22:16 do dia anterior local); o `weekday_pattern` continua usando o `date` da linha (convenção do sync, premissa da spec) |
| Streak ISO perto da virada de ano | `health/calc.py` (`strength_weeks`) | Streak errada na primeira semana de janeiro | `date.isocalendar()` é o mecanismo padrão para semana ISO (segunda-basedo, semana 1 contém a 1ª quinta) — teste com fixture na virada de ano |
| `ReferenceArea` do Recharts 3.x pode divergir da documentação 2.x | `RemChart.tsx` | Banda de REM não renderiza | Mesmo risco já navegado no potential-panel (design §Riscos): verificar contra os tipos instalados (`node_modules/recharts/types`) na implementação; fallback: banda via dois `ReferenceLine` + fill de área |
| `test_health.py` já existe (infra check) — nome de arquivo conflita | `backend/tests/test_health.py:1` | Novo arquivo de teste com mesmo nome colidiria no pytest | Novos testes como `test_health_api.py` + `test_health_calc.py` (padrão `test_potential_api/calc`) |
| Série de estresse tem dias sem `avg` (NULL) | `stress` (banco) | Linha com buracos ou crash no payload | Pontos com `avg` NULL ficam fora da série (mesma postura "filtra o que existe" do mappers); o bloco só é null quando a janela inteira está vazia |
| Janelas 60d com séries de 62-63 dias reais | Postgres | A janela corta as 2-3 noites mais antigas — os pins da spec (62 noites) são da série completa | Testes usam fixtures curtas e pinam contra a janela pedida; os valores reais dos Success Criteria são conferidos no UAT (mesmo padrão do potential-panel) |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Caminho do endpoint | `GET /api/health/summary` | `/api/health` exato é o health check de infra (INFRA-02 validado + README); renomear quebraria contrato verificado — descoberta registrada como premissa na spec |
| Fuso via `zoneinfo` + env própria (`APP_TIMEZONE`), não `TZ` do container | `app_timezone` em `Settings` | Determinístico em dev local (sem docker), testável por env var e explícito no contrato; o `TZ` do compose (America/Sao_Paulo) casa com o default — zero mudança de comportamento no container |
| Agregação em tempo de leitura (sem tabelas de resumo) | `health/calc.py` puro | Padrão do projeto (tipo inferido, timeline VDOT); janelas/réguas são parâmetros de leitura; escala pessoal (~63 linhas/tabela) não justifica materialização |
| `bed_local`/`wake_local` como string "HH:MM" no payload (não datetime ISO) | Contrato do router | A UI não lida com fuso algum (format.ts exibe como vem); já vem pronta para tooltip/card |
| Dose-resposta sem gráfico (cards lado a lado) | `DoseResponse.tsx` | 2 buckets × 3 números = leitura direta; gráfico comparativo adicionaria ruído sem responder mais nada (princípio §2: "cada painel responde uma pergunta") |
| Semanas ISO via `isocalendar()` nativo | `health/calc.py` | Sem dependência de lib de calendário; segunda-basedo é a convenção do treino (bloco semanal) |
| Rótulos de weekday PT-BR só na UI | `formatWeekday` em format.ts | Padrão ASCII na API/acento na exibição (designs anteriores) |
| Estresse fora dos cards do topo (vai no equilíbrio de vida) | `StressChart` dentro de Lifestyle | §9.1 não o lista como série principal; no equilíbrio ele cumpre o papel do §4.5 sem inflar o topo |

> Nenhuma decisão nova de nível de projeto (AD): Recharts já é AD-008; leitura-pura e derivado-em-leitura já são padrão dos domínios anteriores. O caminho `/api/health/summary` é exceção local (colisão com o health check), registrada na spec.

---

## Test Plan (resumo — vira tasks)

- `test_health_calc.py` — pins puros: `dose_response` (buckets com as 3 faixas, noites sem HRV, bucket vazio → médias None), `weekday_pattern` (7 entradas, dia vazio → None/0), `regularity` (minutos locais com cruzamento de meia-noite, truque ±12h, noite sem horário fora, None sem elegíveis), `local_minute` (01:16 GMT → 1336), `strength_weeks` (streak, virada de ano, semana corrente separada, janela), `below_floor`.- `test_health_api.py` — TestClient + Postgres (padrão `test_potential_api.py`): seeds ORM de sleep/hrv/rhr/stress/activities → payload completo pinado (floor_s 25200, rem_band, below_floor, regularity, dose_response, lifestyle, deep_pct/light_pct/awakenings nos pontos de sono); `days=6`/`days=366` → 422; janela corta séries corretamente; conta vazia → blocos null; `dose_response`/`lifestyle` presentes com zeros; `APP_TIMEZONE` inválido → fallback (monkeypatch).
- UAT real ao final: `/saude` com os dados do usuário (padrão workouts-list/potential-panel).
