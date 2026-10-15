# Painel Potencial — Design

**Spec**: `.specs/features/potential-panel/spec.md`
**Status**: Draft

---

## Architecture Overview

Dois lados, ambos dentro dos padrões existentes:

1. **Base de dados (sync)**: o domínio `garmin/` ganha a etapa de predições (gateway method + mapper + upsert + step do service) e a correção da data dos PRs — mesma arquitetura do records: 1 chamada sequencial por sync, tolerante a falha, upsert por `(user_id, event)`. Nova tabela `race_predictions` (snapshot latest, sem histórico — spec).

2. **Leitura (painel)**: novo domínio de leitura `potential/` (router + service + funções puras em `calc.py`), espelhando o `activities/`: zero Garmin (AD-002), todo número determinístico em Python (AD-003), faixa honesta nunca número único (AD-004). As equações de Daniels saem do script CLI `calibrate_vdot.py` para um módulo próprio `vdot/daniels.py` (fonte única — o script vira consumidor fino).

```mermaid
graph TD
    subgraph Sync (garmin/)
        GW[client.get_race_predictions] --> MP[mappers.map_race_records]
        MP --> UP[upserts.upsert_race_predictions]
        SV[service._sync_predictions] --> UP
        SV2[service._sync_records] --> FIX[mappers.map_personal_records<br/>fix prStartTimeGmt]
    end
    UP --> DB[(Postgres<br/>race_predictions / personal_records)]
    subgraph Leitura (potential/)
        RT[potential/router GET /api/potential] --> SVC[potential/service]
        SVC --> CAL[calc.py · riegel/timeline/predictions/decay · puro]
        SVC --> DAN[vdot/daniels · calculate_vdot/equivalent_time]
        SVC --> CALIB[vdot/calibration · load_calibration]
        SVC --> DB
        SVC --> LOAD[load · PMC 182d]
        SVC --> ACT[activities.raw_json · vO2MaxValue + eventType=race]
    end
    RT --> FE[frontend /potencial · PotentialPanel]
    FE -->|Recharts| CH[VdotTimeline · PmcChart · Vo2maxTrend]
    FE --> TB[PredictionsTable · DecayTable]
```

**Abordagens consideradas** — (a) domínio novo `potential/` + extração das equações para `vdot/daniels.py` — escolhida; (b) estender `activities/` com os endpoints — descartada: potencial agrega PRs/predições/PMC, não é subconjunto de atividades; (c) endpoints granulares por bloco — descartada: uma página, um payload (menos round-trips, um estado de loading).

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| ---------- | -------- | ---------- |
| `calculate_vdot`, `equivalent_time` (equações de Daniels) | `backend/app/vdot/calibrate_vdot.py` | **Mover** (não copiar) para `vdot/daniels.py`; script CLI importa do módulo — fonte única |
| `_gmt_ms_to_naive_datetime` | `backend/app/garmin/mappers.py` | Reusar no fix da data dos PRs (`activityStartDateTimeLocal` é ms local) |
| `upsert_records` | `backend/app/garmin/upserts.py` | Padrão copiado pelo `upsert_race_predictions` (por `(user_id, event)`, sem delete) |
| `_sync_records` + tolerância a falha | `backend/app/garmin/service.py` | Padrão do `_sync_predictions` (warning `{tipo}`, continue) |
| Padrão router Pydantic + `get_zone_config` 500 | `backend/app/activities/router.py` | `potential/router.py` idem; `load_calibration` levanta a mesma `ZoneConfigError` |
| `aggregate/recompute` PMC | `backend/app/garmin/pmc.py` | Nenhuma mudança — o painel só lê `load` |
| Cliente tipado + `parseError` | `frontend/src/lib/api.ts` | Extend: tipos + `getPotential()` |
| `formatPace`/`formatDuration`/`formatKm` | `frontend/src/lib/format.ts` | Reuso direto; novo `formatVdot` (1 casa, vírgula) |
| Padrão client component fetch/estado | `frontend/src/components/SyncButton.tsx`, `workouts/WorkoutDetail.tsx` | `PotentialPanel` idem (loading/error/empty) |
| Fixtures/factories | `backend/tests/helpers.py`, `fake_garmin.py` | Extend: payload real de predições (sonda 15/10) + PR fixture com keys reais |
| **Recharts 3.10** (já declarado) | `frontend/package.json` | Renderer dos 3 gráficos — reservado pelo design workouts-list: "Recharts permanece no stack para os painéis futuros (PMC, sono, timeline)" |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| Postgres | 1 tabela nova (`race_predictions`); leitura de `personal_records`, `load`, `activities` — sem mudança de schema existente |
| `vdot_zones.json` | Lido por `vdot/calibration.py` (campos raiz: `vdot`, `source`, `test_date`, `distancia_metros`, `tempo_segundos`) + teste de calibração vira ponto da timeline |
| Sync orchestrator | `_sync_predictions` entre `_sync_records` e `_sync_pmc`; `_initial_stats` ganha `predictions: 0` |
| Router mounting | `app.main` ganha `include_router(potential_router)` |
| Navegação | `/potencial` troca o placeholder pelo painel (rota já existe no Nav) |

---

## Components

### Backend — base (sync)

#### `app/vdot/daniels.py` (novo)

- **Purpose**: Equações clássicas de Daniels como funções puras — fonte única para o painel e para o script de calibração.
- **Interfaces**: `vo2_cost(speed_m_min)`, `fraction_vo2max(time_min)`, `calculate_vdot(distance_m, total_s)`, `speed_for_vo2(vo2)`, `pace_for_fraction(vdot, fraction)`, `equivalent_time(vdot, distance_km)` — assinaturas idênticas às atuais (move puro).
- **Reuses**: código existente em `calibrate_vdot.py:58-102`; o script passa a importar do módulo (comportamento do CLI inalterado).

#### `app/vdot/calibration.py` (novo)

- **Purpose**: Carregar os campos raiz do `vdot_zones.json` (a calibração vigente).
- **Interfaces**: `load_calibration(path) -> Calibration` (dataclass: `vdot: float`, `source: str`, `test_date: date`, `distance_m: float`, `time_s: float`); ausente/inválido → `ZoneConfigError` (mesma exceção de `zones.py` — é o mesmo arquivo).
- **Reuses**: padrão de parse/erro de `vdot/zones.py`.

#### `app/db/models.py` — `RacePrediction` (novo)

- **Purpose**: Snapshot latest da predição de prova do Garmin por evento.
- **Interfaces**: `user_id`, `event` (unique com user), `time_s: float | None`, `date: date` (do `calendarDate`), `raw_json`.
- **Reuses**: convenções de `PersonalRecord` (upsert por `(user_id, event)`, `raw_json` preservado).

#### `app/garmin/client.py`

- **Interfaces**: `get_race_predictions() -> dict` — 1 `_call` (snapshot latest; payload plano da sonda).

#### `app/garmin/mappers.py`

- **Interfaces**:
  - `map_personal_records` — fix: `pr_date` = data local de `activityStartDateTimeLocal` (fallback `prStartTimeGmt`; payload real usa `Gmt` — bug atual lê `GMT`).
  - `map_race_predictions(raw: dict | None) -> list[dict]` — `time5K`→`5K`, `time10K`→`10K`, `timeHalfMarathon`→`HALF_MARATHON`, `timeMarathon`→`MARATHON`; evento ausente/inválido fica de fora; `date` do `calendarDate` (fallback: hoje).
- **Reuses**: `_gmt_ms_to_naive_datetime`; postura "filtra o que existe" do records.

#### `app/garmin/upserts.py`

- **Interfaces**: `upsert_race_predictions(db, user_id, rows) -> int` — por `(user_id, event)`, atualiza `time_s`/`date`/`raw_json`, sem delete (espelho do `upsert_records`).

#### `app/garmin/service.py`

- **Interfaces**: `_sync_predictions(db, gateway, job, stats, user_id)` — após `_sync_records`, antes do `_sync_pmc`; tolerante (warning `{tipo: "predictions"}`, sync continua); `stats["predictions"] = len(rows)`; `_initial_stats` ganha `"predictions": 0`.

### Backend — leitura (painel)

#### `app/potential/calc.py` (novo)

- **Purpose**: Toda a matemática do painel como funções puras — pinável em teste, trocável no v2 (média ponderada dos PRs).
- **Interfaces**:
  - `CANONICAL: dict[str, float]` — `{"5K": 5000, "10K": 10000, "HALF_MARATHON": 21097.5, "MARATHON": 42195}` (mesmas distâncias do `RACE_DISTANCES_KM` do script)
  - `riegel_time(anchor_s, anchor_m, target_m, exponent=1.06) -> float`
  - `timeline_points(prs, races, calibration) -> list[dict]` — PR canônico datado (source=`pr`), prova `eventType=race` (source=`prova`, dedup se PR canônico na mesma data), teste de calibração (source=`teste`); vdot = `calculate_vdot`; PR sem data/inválido fica fora (spec)
  - `demonstrated(points) -> float | None` — maior VDOT dos pontos
  - `predictions(garmin, pr_5k_s, current_vdot, prs) -> dict[event, dict]` — `riegel_s` ancorado no PR de 5K (NULL sem âncora), `vdot_s = equivalent_time(current_vdot, d)`, `average_s` das presentes, `garmin_s`/`pr_s`(+`pr_date`)
  - `decay(prs, current_vdot) -> list[dict]` — `real_pace_s`/`ideal_pace_s`/`delta_pct = (ideal-real)/ideal × 100` (negativo = gap)
- **Dependencies**: `vdot/daniels` (puro).

#### `app/potential/service.py` (novo)

- **Purpose**: Montar o payload a partir do banco.
- **Interfaces**: `get_potential(db, days: int, calibration) -> dict` — PRs canônicos; predições por evento; `load` últimos `days` (ORDER BY date DESC LIMIT days, reversed); corridas `(start_time, raw_json)` → pontos VO2max + provas (filtro em Python — 233 atividades, escala pessoal); montagem via `calc`.
- **Reuses**: padrão de query do `activities/service.py`.

#### `app/potential/router.py` (novo)

- **Interfaces**: `GET /api/potential?days=180` — `days: int = Query(180, ge=1, le=365)` (422 fora do intervalo, antes da query); modelos Pydantic inline (`VdotBlock`, `TimelinePoint`, `PredictionRow`, `PmcBlock`, `Vo2maxBlock`, `PotentialOut`); `ZoneConfigError` → 500 "zonas VDOT não configuradas".

### Frontend

#### `frontend/src/lib/api.ts`

- **Interfaces**: tipos espelhando `PotentialOut` + `getPotential(days = 180): Promise<PotentialOut>` (`cache: "no-store"`).

#### `frontend/src/components/potential/PotentialPanel.tsx`

- **Purpose**: Page-shell do painel: fetch, estados loading/error/empty, seções condicionais.
- **Interfaces**: client component; renderiza `VdotTimeline` (+card da lacuna com narrativa §9.5), `PredictionsTable`, `PmcChart` (+cards CTL/ATL/TSB/ACWR do último dia), `Vo2maxTrend` (só se `vo2max != null`), `DecayTable` (só se `decay` não vazio).
- **Reuses**: padrão de estados do `WorkoutDetail`; empty state apontando o sync (padrão `WorkoutsList`).

#### `frontend/src/components/potential/VdotTimeline.tsx`

- **Purpose**: Timeline VDOT com faixa honesta.
- **Interfaces**: Recharts `ScatterChart` — X = data (escala temporal), Y = VDOT; pontos por entrada; `ReferenceLine y=current` (tracejada, "corrente 50,2"); `ReferenceArea y1=current y2=demonstrated` (faixa sombreada); tooltip com label/data/distância/tempo/VDOT.
- **Dependencies**: recharts.

#### `frontend/src/components/potential/PmcChart.tsx`

- **Purpose**: Curva fitness/fadiga.
- **Interfaces**: Recharts `ComposedChart` — `Bar` TSB (semitransparente, atrás) + `Line` CTL + `Line` ATL; `ReferenceLine y=0`; eixos rotulados (padrão a803911).
- **Dependencies**: recharts.

#### `frontend/src/components/potential/Vo2maxTrend.tsx`

- **Purpose**: Linha VO2max com selo "estimativa do relógio" + nota de hierarquia (AD-005).

#### `frontend/src/components/potential/PredictionsTable.tsx` / `DecayTable.tsx`

- **Purpose**: Tabelas HTML (padrão da tabela de consistência): 4 estimativas × 4 distâncias (— quando NULL, nota da média honesta); decay real vs ideal + Δ% com maior gap destacado.

#### `frontend/src/app/potencial/page.tsx`

- Server page renderizando `<PotentialPanel />` (placeholder sai).

---

## Data Models

### `race_predictions` (nova tabela)

```
id, user_id FK users, event VARCHAR (5K|10K|HALF_MARATHON|MARATHON),
time_s FLOAT NULL, date DATE, raw_json JSON
UNIQUE (user_id, event)  — upsert sem delete (snapshot latest)
```

Namespace de `event` distinto dos PRs (`FASTEST_*`): predição ≠ recorde — nunca cruzar as chaves.

### Contrato `GET /api/potential` (valores reais de hoje, ilustrativos)

```json
{
  "vdot": {
    "current": {"vdot": 50.2, "source": "10K em 41:15", "test_date": "2026-10-03"},
    "demonstrated": {"vdot": 51.62, "source": "FASTEST_5K", "date": "2026-04-26"},
    "gap_pct": 97.2,
    "timeline": [
      {"date": "2024-10-05", "vdot": 51.32, "source": "pr", "label": "10K 40:25", "distance_m": 10000, "time_s": 2425},
      {"date": "2026-04-26", "vdot": 51.62, "source": "pr", "label": "5K 19:23", "distance_m": 5000, "time_s": 1163.8},
      {"date": "2026-05-03", "vdot": 50.88, "source": "pr", "label": "Meia 1:30:09", "distance_m": 21097.5, "time_s": 5409.2},
      {"date": "2026-07-05", "vdot": 39.48, "source": "pr", "label": "Maratona 3:52:05", "distance_m": 42195, "time_s": 13925.8},
      {"date": "2026-10-03", "vdot": 50.18, "source": "teste", "label": "10K 41:15", "distance_m": 10012, "time_s": 2475}
    ]
  },
  "predictions": {
    "5K":  {"garmin_s": 1165, "riegel_s": 1163.8, "vdot_s": 1191.9, "average_s": 1173.6, "pr_s": 1163.8, "pr_date": "2026-04-26"},
    "10K": {"garmin_s": 2447, "riegel_s": 2426.5, "vdot_s": 2471.1, "average_s": 2448.2, "pr_s": 2425, "pr_date": "2024-10-05"},
    "HALF_MARATHON": {"garmin_s": 5437, "riegel_s": 5353.8, "vdot_s": 5472.3, "average_s": 5421.0, "pr_s": 5409.2, "pr_date": "2026-05-03"},
    "MARATHON": {"garmin_s": 11989, "riegel_s": 11162.4, "vdot_s": 11401.4, "average_s": 11517.6, "pr_s": 13925.8, "pr_date": "2026-07-05"}
  },
  "pmc": {
    "days": 180,
    "points": [{"date": "2026-04-20", "ctl": 12.3, "atl": 14.1, "tsb": -1.8, "acwr": 1.31}],
    "current": {"date": "2026-10-15", "ctl": 21.0, "atl": 27.2, "tsb": -6.2, "acwr": 1.42}
  },
  "vo2max": {"points": [{"date": "2026-04-22", "value": 54.0}, {"date": "2026-07-05", "value": 56.0}]},
  "decay": [
    {"event": "5K",  "real_pace_s": 232.8, "ideal_pace_s": 238.4, "delta_pct": 2.3},
    {"event": "10K", "real_pace_s": 242.5, "ideal_pace_s": 247.1, "delta_pct": 1.9},
    {"event": "HALF_MARATHON", "real_pace_s": 256.4, "ideal_pace_s": 259.4, "delta_pct": 1.2},
    {"event": "MARATHON", "real_pace_s": 330.0, "ideal_pace_s": 270.2, "delta_pct": -22.1}
  ]
}
```

`pmc=null` sem linhas em `load`; `vo2max=null` sem `vO2MaxValue`; `decay=[]` sem PR canônico; blocos de `predictions` com `null` por estimativa ausente. Pins derivados da forma fechada de Daniels do `calibrate_vdot.py` (a mesma que gerou o 50,2 do teste — o "~53" do plano §9.5 vem da tabela tabulada; a forma fechada é a fonte da verdade do app). A maratona conta a história: Riegel/VDOT otimistas, Garmin moderado, PR 3:52 = gap de execução (−22% no decay) — a média honesta existe para isso.

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| `days` fora de [1, 365] | 422 FastAPI antes da query | UI nunca envia; visível em dev |
| `vdot_zones.json` ausente/inválido | 500 "zonas VDOT não configuradas" (`ZoneConfigError` de `load_calibration`) | Painel falha explícito — sem VDOT corrente não há painel (spec) |
| Passo de predições falha no sync | warning `{tipo: "predictions"}`, sync continua | Coluna Garmin "—" até o próximo sync; resto do painel intacto |
| Sem PRs / sem predições / sem `load` | Blocos `null`/vazios, células "—" | Empty states orientando o sync; sem número inventado |
| API fora do ar | Mensagem inline no painel (padrão workouts) | Navegação segue funcionando |
| Payload de predição sem um evento | Linha do evento não tocada (upsert sem delete) | Estimativa antiga permanece — honesto sobre o que o Garmin mandou |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | -------------------- | ------ | ---------- |
| Mover equações de `calibrate_vdot.py` pode quebrar o CLI validado | `backend/app/vdot/calibrate_vdot.py:58-102` | Fluxo de recalibração da Fase 2 depende do script | Move puro (assinaturas idênticas); script importa do módulo; suite ganha testes das funções (hoje o módulo não tem teste direto) |
| Fixture de PR usa a key errada (`prStartTimeGMT`) — espelha o bug, não a realidade | `backend/tests/helpers.py:274-276` | Testes atuais passariam com o mapper errado | Fixture corrigida para o payload real (`prStartTimeGmt` + `activityStartDateTimeLocal` — sonda no banco 15/10); teste novo pina a data local |
| Recharts 3.x: API pode diferir da 2.x documentada em guias | `frontend/package.json` (^3.10.1) | Charts quebram em runtime | Verificar contra os tipos instalados (`node_modules/recharts/types`) na implementação; componentes pequenos e isolados |
| Next 16 tem breaking changes vs. treinamento | `frontend/AGENTS.md` | Padrões de página incorretos | Seguir os padrões das páginas existentes (server page + client component, `params: Promise`); consultar `node_modules/next/dist/docs/` ao dúvidar |
| `get_race_predictions` exige `display_name` no token | `garminconnect` (`_require_display_name`) | Etapa falha se o token não carregar o nome | Tolerância já projetada: warning `{tipo: "predictions"}` e sync segue |
| Filtro de `vO2MaxValue`/`eventType` via SQL JSON é frágil entre drivers | `activities.raw_json` (coluna JSON, não JSONB) | Query específica de Postgres criaria acoplamento | Filtro em Python nas ~233 linhas (escala pessoal, AD-001); documento o racional no service |
| Sonda de predições consumiu 1 chamada real (15/10) | — | Fora do orçamento de sync (chamada manual, não do job) | Registrado aqui; o job tem teto e intervalo próprios (SYNC-09/03) |
| PRs sem `pr_date` até o próximo sync real | `personal_records.pr_date` (NULL hoje) | Timeline nasce sem os pontos de PR na primeira execução pós-deploy | Self-heal no próximo sync (upsert atualiza campos); UI degrada honesta (só teste de calibração como ponto) |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Renderer dos gráficos do painel | **Recharts** (ScatterChart/ComposedChart/LineChart) | Reservado pelo design workouts-list ("Recharts permanece no stack para os painéis futuros (PMC, sono, timeline)"); aqui não há requisito de largura proporcional — séries temporais são o caso padrão da lib |
| Equações de Daniels | Mover para `vdot/daniels.py`; CLI vira consumidor | Fonte única; o painel não importa script CLI; funções puras ganham testes próprios |
| Calibração vigente | `vdot/calibration.py` lê os campos raiz do mesmo `vdot_zones.json` | Sem arquivo novo; `ZoneConfigError` reaproveitada → mesmo 500 do workouts |
| Snapshot de predições | upsert por `(user_id, event)`, `date` do `calendarDate`, sem histórico | Spec (Out of Scope); a data do snapshot dá frescura sem tabela de histórico |
| Namespace dos eventos de predição | `5K`/`10K`/`HALF_MARATHON`/`MARATHON` (ASCII) | Distinto dos `FASTEST_*` dos PRs — predição nunca vira "recorde"; ASCII na API, acento na exibição (padrão do tipo inferido) |
| Âncora Riegel isolada em função pura | `riegel_time(anchor_s, anchor_m, target_m)` | v2 (média ponderada dos PRs) troca a política da âncora sem tocar o resto — anotado no Out of Scope |
| Filtros JSON em Python, não SQL | `get_potential` carrega corridas e filtra | 233 atividades (escala pessoal); zero acoplamento a sintaxe JSON de driver |
| `days` validado no router | `Query(180, ge=1, le=365)` | 422 antes da query (padrão TRN-06); UI fixa 180 (spec) |
| delta do decay | `(ideal − real)/ideal × 100` | Negativo = real mais lento que o ideal = gap (sinal legível: "quanto falta"); positivo = overperform |

> **AD-008 (novo, STATE.md)**: Recharts é o renderer padrão dos gráficos de série temporal dos painéis; SVG próprio fica reservado para geometrias especiais (ex.: largura proporcional à duração no gráfico de splits). Convenção trans-feature — Saúde/Hoje seguirão.

---

## Test Plan (resumo — vira tasks)

- `test_vdot_daniels.py` — pins: `calculate_vdot(5000, 1163.83) ≈ 53.1`, `equivalent_time(50.2, 42.195)`, inversibilidade.
- `test_potential_calc.py` — Riegel ancorado no 5K; timeline (dedup prova×PR, PR sem data fora, teste de calibração como ponto); demonstrado; predictions com estimativas ausentes; decay com sinal.
- `test_potential_api.py` — TestClient + Postgres: payload completo com seeds; `days` 0/366 → 422; `pmc=null`; `vo2max=null`; 500 sem `vdot_zones.json` (monkeypatch do path).
- `test_garmin_mappers.py` — fixture real de PRs (data local); `map_race_predictions` com payload da sonda + eventos ausentes.
- `test_garmin_upserts.py` — idempotência do upsert de predições; evento ausente não apaga linha.
- `test_garmin_service.py` — `_sync_predictions`: 1 chamada, contador no stats, warning tolerante, ordem records→predictions→pmc.
- UAT real ao final: sync → `/potencial` com os dados do usuário (padrão do workouts-list).
