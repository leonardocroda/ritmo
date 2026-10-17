# HRV Baseline Científico — Design

**Spec**: `.specs/features/hrv-baseline/spec.md` (HRV-01..HRV-15) · **Context**: `context.md` · **Fonte do método**: Altini/HRV4Training (60d ± 0,75 DP — smallest worthwhile change, Plews et al. 2014)

## Context

O bloco HRV atual copia a série do banco com o status cru da Garmin (`backend/app/health/service.py:115-122`) e o gráfico plota as noites cruas sem referência (`frontend/src/components/health/HrvChart.tsx:97-104`). Este design troca o modelo de exibição pelo científico: **linha = média móvel de 7 dias**, **banda móvel por dia = janela de 60 dias, média ± 0,75 × DP amostral**, **status local** (BALANCED/UNBALANCED pela média 7d vs banda do dia). Toda a matemática é backend, em função pura (AD-003: determinística, pinável); o payload espelha o render (AD-009); o gráfico continua Recharts (AD-008).

```
config (backfill 60→120) ──> garmin sync ──> Postgres `hrv` (date, value, status cru — intocado)
                                                        │
                             service._hrv_history ──────┘  (janela de datas: exibição + lookback 59d)
                                                        │
                             calc.hrv_model (puro): avg7 + banda/dia + status
                                                        │
                             router.HrvBlock ──> api.ts ──> HrvChart (banda + linha + noites + card)
                                                        └──> HrvTable (7/página, client-side)
```

## Components

### 1. `backend/app/health/calc.py` — modelo puro (novo)

Réguas do backend, no padrão de `SLEEP_FLOOR_S`/`REM_BAND` (`calc.py:19-22`) — a UI não inventa régua:

```python
HRV_AVG_DAYS = 7            # janela da média móvel
HRV_BASELINE_DAYS = 60      # janela da banda normal
HRV_BASELINE_MIN_VALUES = 14  # mínimo de valores na janela para exibir banda
HRV_BASELINE_SD_FACTOR = 0.75  # smallest worthwhile change
```

`hrv_model(rows, days)` — entrada `[(date, value)]` ASC, saída `{points, current, status}`:

- **Janela de exibição**: `days` dias corridos terminando na última data com dado `L` (primeira = `L−(days−1)`).
- **Por dia corrido `d`**:
  - `avg7` = média dos valores em `[d−6, d]` — **sobre os valores disponíveis** (lacuna de captura não quebra a linha, HRV-02); janela vazia → `None` (dia sem ponto na linha, HRV-03).
  - banda: valores em `[d−59, d]`; `n ≥ 14` → `(média − 0,75×DP, média + 0,75×DP)` com DP **amostral** (`statistics.stdev`, n−1); senão `None` (HRV-04/05).
- **current** = último dia com dado: `{date, value, avg7, band_low, band_high, status}`.
- **status**: `BALANCED` se `low ≤ avg7 ≤ high` (limites inclusos, valores **sem arredondar**); `UNBALANCED` fora; `None` sem banda (HRV-06/08).
- Complexidade O(days×rows) (~7k operações na janela máxima) — sem cleverness: legível e pinável. **Não** reusar `_avg` (`calc.py:46-48`), que arredonda — o modelo compara sem arredondar.

### 2. `backend/app/health/service.py` — query + montagem

- Novo `_hrv_history(db, days)`: `max(date)` do usuário → linhas com `date ≥ L−(days+58)` (exibição `days` + lookback de banda 59), ASC, **filtro `user_id`** (AD-001). Sem linhas → `[]`.
- `_hrv_block(rows, days)` reescrito: `[]` → `None`; senão `calc.hrv_model` + **arredondamento de 1 casa no payload** (`avg7`, `band_low`, `band_high`) — a comparação de status já aconteceu sem arredondar dentro do modelo.
- `hrv_by_date` do dose-resposta **continua** vindo do `_series(db, Hrv, days)` (`service.py:202,212`) — zero mudança no cruzamento sono×HRV (spec: dose-resposta e chip do treino intocados).

### 3. `backend/app/health/router.py` — contrato novo (AD-009)

```python
class HrvPoint(BaseModel):    # dia corrido da janela de exibição
    date: date
    value: float | None      # noite individual (null = sem captura)
    avg7: float | None       # média móvel 7d (null = janela vazia)
    band_low: float | None   # banda do dia (null = <14 valores na janela)
    band_high: float | None

class HrvCurrent(BaseModel):  # último dia com dado
    date: date
    value: float
    avg7: float
    band_low: float | None
    band_high: float | None
    status: str | None        # "BALANCED" | "UNBALANCED" | null (coletando)

class HrvBlock(BaseModel):
    points: list[HrvPoint]    # dias corridos, ASC
    current: HrvCurrent
```

O `status` cru da Garmin **sai do payload** (continua persistido na tabela `hrv` — model intocado).

### 4. `backend/app/core/config.py` — backfill (HRV-15)

`sync_backfill_health_days: 60 → 120` (`config.py:48`). Exibição de 60 dias + lookback de banda de 59 = 119 dias necessários; 120 como default redondo. Vale para todos os tipos de saúde — as leituras são por janela de dias, nenhum leitor muda de comportamento.

**Ops (base existente)**: `_window_start` (`garmin/service.py:129-136`) usa o backfill só sem `sync_state` — os 60 dias extras chegam no próximo sync completo (linhas de `sync_state` dos tipos de saúde limpas). Nota vai no handoff do STATE.md.

### 5. Frontend

**`frontend/src/lib/api.ts`** — espelho dos tipos (linhas 335-338 substituídas).

**`HrvChart.tsx` (rewrite)** — dados: `points` + 2 campos derivados de render (`bandBase = band_low`, `bandSpan = band_high − band_low`, só quando ambos existem):

- **Banda por dia**: 2 `<Area stackId="band">` — base com `fill="transparent"` + span com `fill={HRV_COLOR}` `fillOpacity≈0.12`. `ReferenceArea` não serve (y1/y2 fixos); nulls dividem a área = banda some nos dias sem threshold. Técnica padrão Recharts para banda variável.
- **Linha**: `<Line dataKey="avg7" connectNulls={false}>` (`strokeWidth 1.5`, `dot=false`, cor `#38bdf8`).
- **Noites**: `<Scatter dataKey="value">` círculos `r≈2`; noite fora da banda → cor diferenciada (âmbar `#fbbf24`) via `shape` custom — HRV-13 (P2).
- **Card**: valor da última noite em destaque + badge com status local; status `null` → "coletando linha de base…" (texto muted, no lugar do badge). Linha de contexto: `média 7d 76,0 ms · banda 70,0–98,0 ms` (`formatVdot`).
- **Tooltip**: data completa, HRV (ou "sem captura"), média 7d, banda do dia.
- **Legenda** (padrão `SeriesLegend` do `RemChart.tsx:58-81`): noite / média 7 dias / banda normal.
- Domínio Y: auto (banda e noites participam do domínio).

**`HrvTable.tsx` (novo)** — pontos com `value ≠ null`, ordem desc, **7 linhas/página** (client-side); controles Anterior/Próxima + indicador `atual/total` só quando >7 dias com dado (HRV-12); colunas Data (`20/04/2026`), HRV, média 7d — 1 casa, `tabular-nums`; estilo espelha `PredictionsTable`/`DecayTable` (tabela Tailwind simples). Mount no `HealthPanel.tsx:152-155`: dentro do mesmo card do HRV, abaixo do gráfico.

**Next.js 16.4.0** (`frontend/AGENTS.md`): componentes client-only, nenhuma API nova do framework — seguir os padrões dos componentes existentes; se qualquer task tocar rota/suspense, consultar `node_modules/next/dist/docs/` antes.

### Contrato (payload ilustrativo, `days=60`)

A janela de exibição **termina na última data com dado**, e `current` é exatamente esse dia — `value` numérico garantido; dias sem captura só existem no miolo da série (média 7d preenche, noite é `null`):

```json
"hrv": {
  "points": [
    {"date": "2026-08-19", "value": 71.0, "avg7": 71.0, "band_low": 66.9, "band_high": 87.3},
    {"date": "2026-08-20", "value": null, "avg7": 71.0, "band_low": 66.9, "band_high": 87.3},
    {"date": "2026-10-16", "value": 69.0, "avg7": 76.0, "band_low": 70.4, "band_high": 97.6}
  ],
  "current": {"date": "2026-10-16", "value": 69.0, "avg7": 76.0, "band_low": 70.4, "band_high": 97.6, "status": "BALANCED"}
}
```

(noites fora da banda → pontos com `band_low/band_high` do dia; dias com <14 valores na janela → banda `null`)

## Decisões

1. **Status decide sem arredondar; payload arredonda 1 casa** — o que decide é a matemática, o que aparece é limpo. Testes usam valores não-fronteiriços (a borda inclusiva é testada no puro).
2. **`points` = dias corridos** (value null nas lacunas) — 1 dataset serve gráfico (eixo X) e tabela (filtra `value ≠ null`), espelhando o render (AD-009).
3. **Banda via Areas empilhadas** — única forma Recharts de banda com limites por ponto.
4. **Sem coluna status na tabela** — números bastam; status é crônico (média 7d vs banda) e viveria repetido por linha.
5. **dose-response e chip "Contexto do dia" intocados** — a troca de modelo é exclusiva do bloco HRV da Saúde.
6. **AD-010 (registrar em STATE.md na task de fechamento)**: modelo de avaliação de HRV do Ritmo = Altini (linha: média móvel 7d; referência: banda 60d ± 0,75 DP com threshold 14; status: local BALANCED/UNBALANCED) — fonte de verdade para a Saúde e para o futuro Painel Hoje (§4.2).

## Riscos

- **Areas empilhadas com nulls**: dias sem banda dividem a área — desejado (banda aparece só quando confiável); validar no build/UAT.
- **`days=7`**: exibição curta, banda continua com janela de 60d (query traz 65 dias) — a régua científica não encolhe com a janela de exibição.
- **Primeiro pós-deploy**: até um re-sync completo, os dias mais antigos da janela ficam sem banda (threshold por dia já comunica, omitindo) — aceitável e esperado.
- **Pins existentes** (`tests/test_health_api.py:190-197, 364-369, 509-511`) mudam de forma — atualização prevista na T3.
- **Sync**: 120 dias × 4 tipos diários ≈ 480 chamadas — dentro do teto (`sync_max_calls=1500`, `config.py:50`); primeira sync completa fica mais lenta.

## Reuse

- `RemChart.tsx:110-115` (banda) e `:58-81` (legenda) → padrões visuais da banda/legenda
- `RhrChart.tsx:79-90` → régua sempre vem do payload (UI não calcula)
- `PmcChart.tsx` → ComposedChart multi-série
- `tests/test_health_api.py:76-77` (`_seed_hrv`) → seeding; lição candidata L-005 aplicada como teste de isolamento desde a primeira task de leitura
