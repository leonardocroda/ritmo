# Painel Clareza (panel-clarity) — Design

**Spec**: `.specs/features/panel-clarity/spec.md`
**Status**: Draft

---

## Architecture Overview

Dois lados, ambos dentro dos padrões existentes — zero schema novo, zero cálculo novo:

1. **Contrato (backend)**: o bloco `pmc` muda de domínio. A montagem `_pmc_block` sai de `potential/service.py` e vira `_pmc_block(rows, days)` em `health/service.py` — a janela (DESC + limit + reverse) já é o helper `_series` do health; `PotentialOut` perde `pmc` e o router perde o query param `days` (era exclusivo da PMC); `HealthSummaryOut` ganha `pmc: PmcBlock | None` seguindo o `days` único da Saúde (7–365, default 60). Os modelos `PmcPoint`/`PmcBlock` migram de router.

2. **Apresentação (frontend)**: novo componente compartilhado `PanelSection` (cabeçalho forte: índice opcional, título, subtítulo sempre visível, selo opcional — AD-009) + linha-guia por painel. `HealthPanel` recomposta em 5 seções numeradas (Sono → Carga de treino → Recuperação → Dose-resposta → Equilíbrio de vida) com `PmcChart` migrado para `components/health/`; `PotentialPanel` recomposta em 3 blocos narrativos (Onde estou → O que isso prevê → O que o relógio estima) com legenda por método de previsão.

```mermaid
graph TD
    subgraph Backend — contratos
        HRT[health/router GET /api/health/summary] --> HSV[health/service.get_health]
        HSV --> HSER[_series db, model, days]
        HSV --> PMCB[_pmc_block rows, days · montagem movida]
        HSER -->|DailyLoad| PMCB
        PRT[potential/router GET /api/potential] --> PSV[potential/service.get_potential<br/>sem days, sem pmc]
    end
    PMCB --> DB[(Postgres · load 182d — valores intocados)]
    PSV --> DB
    HRT --> FEH[frontend /saude · HealthPanel]
    PRT --> FEP[frontend /potencial · PotentialPanel]
    FEH --> PS[PanelSection 1..5 + linha-guia]
    FEP --> PS2[PanelSection × 3 + linha-guia]
    PS --> PMC[PmcChart · health/]
    PS2 --> GAP[GapCard + VdotTimeline]
    PS2 --> PT[PredictionsTable + legenda por método]
    PS2 --> DCT[DecayTable explicado]
    PS2 --> V2T[Vo2maxTrend · selo + hierarquia]
```

**Abordagens consideradas** — (a) `_pmc_block` movido para o health reusando `_series` + `PanelSection` compartilhado — **escolhida**; (b) domínio compartilhado `app/load/` — descartada: um consumidor hoje e o Hoje consumirá a health summary (o `current` que o card de readiness precisa já vem no bloco); (c) health importando de potential — descartada: acoplamento painel-a-painel, e manteria o load semanticamente preso ao potencial. Frontend: (a) `PanelSection` único — **escolhida**; (b) Section por painel — descartada: divergência silenciosa do padrão que é a entrega da feature.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| ---------- | -------- | ---------- |
| `_series(db, model, days)` | `backend/app/health/service.py:49` | Fonte das linhas de `DailyLoad` da PMC (janela idêntica à que `_pmc_block` fazia na mão) |
| Montagem `_pmc_block` (entry/current) | `backend/app/potential/service.py:39-71` | **Move** (não copia): vira `_pmc_block(rows, days)` no health; a query manual morre (é o `_series`) |
| `PmcChart` completo | `frontend/src/components/potential/PmcChart.tsx` | **Move puro** para `components/health/` — gráfico, cards CTL/ATL/TSB/ACWR e legenda intocados (AD-008) |
| Padrão página-composição (fetch 1 round-trip + loading/error/empty) | `PotentialPanel.tsx`, `HealthPanel.tsx` | Preservado; só a composição interna muda |
| Notas sempre-visíveis já existentes | `Vo2maxTrend.tsx` (selo + hierarquia AD-005), `PredictionsTable.tsx` (nota média honesta), `DecayTable.tsx` (nota do sinal) | Base da copy — evoluem para legendas/cabeçalhos completos |
| Badge pill de estimativa | `Vo2maxTrend.tsx:57` | Padrão visual do selo de fonte no `PanelSection` |
| `formatVdot`/`formatDuration`/`formatPace` | `frontend/src/lib/format.ts` | Reuso direto (nenhum formatador novo) |
| Cliente tipado + `parseError` | `frontend/src/lib/api.ts` | Edit: `PmcPoint`/`PmcBlock` migram de seção; `HealthSummaryOut.pmc`; `PotentialOut` sem `pmc`; `getPotential()` sem param |
| Fixtures/seeds de `DailyLoad` | `backend/tests/test_potential_api.py` | Testes de PMC **migram** para `test_health_api.py` (nenhum assert perdido) |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| `/api/health/summary` | Ganha `pmc: PmcBlock \| None` — mesmo `days` único (7–365, default 60; UI fixa 60) |
| `/api/potential` | Perde `pmc` e o query param `days`; `?days=90` vira query não declarada (ignorada, 200) — CLR-04 |
| Postgres | **Zero mudança de schema** — `DailyLoad` continua a fonte; valores seguem as linhas do sync (CLR-06) |
| Painel Hoje (futuro) | Consumirá `pmc.current` da própria health summary — sem endpoint novo |

---

## Components

### Backend — contrato

#### `app/health/service.py`

- **Purpose**: Montar o bloco `pmc` da Saúde.
- **Interfaces**:
  - `_pmc_block(rows: list[DailyLoad], days: int) -> dict | None` — montagem movida de `potential/service.py:39-71` (dict `entry`, `points` ASC, `current` = última linha); sem linhas → `None` (CLR-02). A query DESC+limit+reverse é substituída pelo `_series`.
  - `get_health(db, days, tz)` — ganha `"pmc": _pmc_block(_series(db, DailyLoad, days), days)` entre `stress` e `dose_response`; importa `DailyLoad`.
- **Dependencies**: `app.db.models.DailyLoad`.
- **Reuses**: `_series` (janela), montagem existente (move puro).

#### `app/health/router.py`

- **Interfaces**: `PmcPoint`, `PmcBlock` movidos de `potential/router.py:61-72`; `HealthSummaryOut` ganha `pmc: PmcBlock | None` (entre `stress` e `dose_response`). Docstring cita CLR-01/02.
- **Reuses**: padrão de modelos inline (inalterado).

#### `app/potential/service.py`

- **Interfaces**: remove `_pmc_block` e o import de `DailyLoad`; `get_potential(db, calibration)` — **sem** `days`; payload sem `pmc` (CLR-03). Nenhum outro bloco muda.
- **Reuses**: tudo existente.

#### `app/potential/router.py`

- **Interfaces**: remove `PmcPoint`/`PmcBlock`, o campo `pmc` de `PotentialOut` e o query param `days` — `get_potential(db: Session)` (CLR-03/04). 500 de calibração preservado (fora de escopo).

### Frontend

#### `frontend/src/components/PanelSection.tsx` (novo)

- **Purpose**: Cabeçalho forte de seção — a unidade de clareza trans-painel (AD-009).
- **Interfaces**: `{ index?: number; title: string; subtitle: string; badge?: string; children: ReactNode }` — `index` renderiza numeral discreto (Saúde 1–5; Potencial sem índice), `badge` renderiza pill (padrão `Vo2maxTrend`), `subtitle` sempre visível (1–2 linhas, `text-muted`); espaçamento externo entre seções claramente maior que o interno (`mt-8+` vs `space-y-3`); **sem** card wrapper (context.md D).
- **Dependencies**: nenhuma (componente puro de layout).
- **Reuses**: classes do tema (border-white/10, bg-card, text-muted).

#### `frontend/src/components/health/HealthPanel.tsx` (recomposição)

- **Interfaces**: linha-guia no topo (CLR-26) + 5 `PanelSection` numerados: 1 Sono, 2 Carga de treino (`PmcChart` | estado vazio), 3 Recuperação, 4 Dose-resposta, 5 Equilíbrio de vida. Empty geral: `sleep && hrv && rhr && stress && pmc` todos null (CLR-11).
- **Reuses**: todos os componentes de gráfico existentes intocados; `BlockEmpty` existente.

#### `frontend/src/components/health/PmcChart.tsx` (move de `potential/`)

- **Move puro** — nenhum gráfico novo (AD-008). Header comment atualizado: POT-23/24 (histórico) → CLR-07/08/10 (vigentes).

#### `frontend/src/components/potential/PotentialPanel.tsx` (recomposição)

- **Interfaces**: linha-guia no topo (CLR-27) + 3 `PanelSection`: "Onde estou" (GapCard + VdotTimeline; subtítulo define VDOT/corrente/demonstrado/lacuna — CLR-18), "O que isso prevê" (PredictionsTable + DecayTable quando não vazio; vo2max não entra aqui), "O que o relógio estima" (Vo2maxTrend — bloco inteiro ausente quando `vo2max === null`, CLR-22). Empty check recalculado: `timeline.length <= 1 && vo2max === null && decay.length === 0` (CLR-23).
- **Reuses**: GapCard (narrativa mantida, label do gap esclarecido: "do potencial demonstrado que o teste atual valida"), todos os componentes existentes.

#### `frontend/src/components/potential/PredictionsTable.tsx`

- **Interfaces**: legenda por método sob a tabela (CLR-19) — 4 entradas de 1 linha: **Garmin** (preditor do Garmin Connect, puxado no sync), **Riegel** (extrapolação T2 = T1 × (D2/D1)^1,06 ancorada no PR de 5K), **VDOT** (equivalência de Daniels do teste corrente), **Média honesta** (média das presentes na distância).
- **Reuses**: nota existente da média honesta vira uma das entradas.

#### `frontend/src/components/potential/DecayTable.tsx`

- **Interfaces**: explicação sempre visível do que compara (pace real dos PRs vs ideal da equivalência VDOT corrente) e do sinal (negativo = gap de execução) — CLR-20; evolui a nota atual, mesmo padrão visual.

#### `frontend/src/lib/api.ts`

- **Interfaces**: `PmcPoint`/`PmcBlock` migram para a seção "Painel Saúde"; `HealthSummaryOut.pmc: PmcBlock | null`; `PotentialOut` sem `pmc`; `getPotential(): Promise<PotentialOut>` — sem param (o cliente atual manda `?days=180`; param morto deixa de ser enviado — higiene na mesma task do contrato).

### Copy (estática, PT-BR, inline)

- **Cabeçalhos de seção/bloco**: no painel (HealthPanel/PotentialPanel) — estrutura e copy juntas.
- **Legendas que explicam o próprio componente** (métodos da tabela, decaimento, hierarquia do VO2max): dentro do componente — viajam com ele.
- Réguas citadas vêm do payload (`floor_s`, `rem_band`); nenhum valor pessoal hardcodado — a copy fala de método, nunca de número do usuário (premissa do spec).

---

## Data Models

**Zero mudança de schema.** Contratos após a migração:

```jsonc
// GET /api/potential — sem pmc, sem days
{ "vdot": {...}, "predictions": {...}, "vo2max": {...} | null, "decay": [...] }

// GET /api/health/summary?days=60 — pmc entra com a janela única
{
  "sleep": {...} | null, "hrv": {...} | null, "rhr": {...} | null,
  "stress": {...} | null,
  "pmc": { "days": 60, "points": [{"date": "...", "ctl": 21.0, "atl": 27.2, "tsb": -6.2, "acwr": 1.42}], "current": {...} } | null,
  "dose_response": {...}, "lifestyle": {...}
}
```

Valores ilustrativos reais de hoje (CTL 21,0 · ATL 27,2 · TSB −6,2 · ACWR 1,42 em 15/10) — os pins dos testes migram com eles.

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| Sem linhas em `load` | `pmc=null`; seção Carga com estado vazio orientando o sync (CLR-09) | "A curva nasce no primeiro sync" — sem tela quebrada |
| `days` fora de [7, 365] na saúde | 422 antes da query (HLT-03 inalterado — pmc segue a janela única) | — |
| `?days=90` no potencial (param morto) | Ignorado — query não declarada (CLR-04) | 200 normal |
| `vdot_zones.json` ausente | 500 **só** no `/api/potential` (inalterado); Saúde imune — é o motivo da migração | Saúde nunca quebra por calibração |
| ACWR null no último dia | "—" (janela 28d incompleta — honestidade SYNC-24, CLR-10) | Sem número inventado |
| API fora do ar | Mensagem inline nos painéis (padrão existente) | Navegação segue |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | -------------------- | ------ | ---------- |
| Migração de testes pode perder asserts (pmc em `test_potential_api.py:184-214, 318-379`) | `backend/tests/` | Cobertura silenciosamente menor | Task dedicada à migração com checklist 1:1 (janela `days`, `current`, `null` sem load, janela > histórico, payload completo); contagem de testes não pode cair (Success Criteria) |
| Cliente `getPotential(days=180)` envia param que virará morto | `frontend/src/lib/api.ts:300` | Query suja + tipo com campo inexistente | Mesma task do contrato atualiza o cliente (tipo + assinatura) — backend e frontend mudam juntos no compose |
| Empty state geral da Saúde esquecer o `pmc` | `HealthPanel.tsx:83` | Painel "vazio" ocultando a seção Carga com dados | CLR-11 + verificação na task: conta só com `load` → seção Carga renderiza |
| ACs do potential-panel superseded (POT-11/12/15/16 — days e pmc) | `.specs/features/potential-panel/spec.md` | Confusão de "qual AC vale?" | panel-clarity governa (spec + ACs CLR); histórico do potential-panel permanece como evidência passada; comments dos arquivos migrados citam CLR |
| Next 16 tem breaking changes vs. treinamento | `frontend/AGENTS.md` | Padrões incorretos | Só client components existentes mudam — nenhum API novo do Next; consultar `node_modules/next/dist/docs/` ao dúvidar |
| Copy estática pode envelhecer | componentes | Explicação defasada | Copy fala de método/conceito (estável), não de números pessoais; réguas vêm do payload |
| Janela PMC 180→60 é mudança visível | UI | Usuário perde o arco de 6 meses | Decisão do usuário (spec premissa 2) — CTL/ATL/TSB do último dia e a leitura "estou absorvendo?" permanecem |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Casa da computação do PMC | `health/service.py` reusando `_series` | Padrão de janela idêntico já existe lá; payload espelha render (AD-009); Hoje consumirá a health summary |
| Janela da PMC na Saúde | `days` único (7–365, default 60; UI fixa 60) | Usuário confirmou; contrato de janela única do health-panel preservado |
| `PmcChart` | Move `potential/` → `health/` (move puro) | Único consumidor é a Saúde; caminho espelha o dono; zero risco Recharts |
| Cabeçalho de seção | `PanelSection` compartilhado (`index?`, `title`, `subtitle`, `badge?`) | Consistência trans-painel é a entrega; Hoje herda (AD-009) |
| Índice numérico | Só na Saúde (1–5) | Numeração marca o passo a passo do fio condutor; Potencial é narrativa curta de 3 blocos — `index` fica opcional |
| Copy | Estática PT-BR inline (painéis = estrutura; componentes = legendas próprias) | Sem i18n/CMS (context.md B); legenda viaja com o componente que explica |
| `?days` morto no potencial | Ignorado (sem validação nova) | FastAPI descarta query não declarada; CLR-04 pina 200 |
| Supersessão de ACs do potential-panel | CLR governa; histórico intacto | Specs antigas são evidência do que foi entregue; o painel mudou de composição por decisão do usuário |

> **AD-009 (novo, STATE.md)**: Padrão de clareza dos painéis — toda seção de painel tem cabeçalho forte com subtítulo explicativo sempre visível ("o que é / por que importa") e selo de fonte/método quando aplica; o payload de cada endpoint espelha exatamente o que o painel correspondente renderiza. Convenção trans-feature — Hoje e futuros painéis seguem.

---

## Test Plan (resumo — vira tasks)

- `test_health_api.py` — pmc com seeds de `DailyLoad`: `days` refletindo a janela pedida, `points` ASC pinados, `current` = última linha, `pmc=null` sem load, janela > histórico devolve o que existe, payload completo com `pmc` entre `stress` e `dose_response` (CLR-01/02/05/06).
- `test_potential_api.py` — payload sem `pmc`; `?days=90` → 200 sem efeito no payload (CLR-03/04); asserts de PMC removidos **contra** os migrados (checklist 1:1 da task).
- Suite inteira verde no Postgres do compose (hoje 262 testes — contagem não cai).
- UAT real 390px: 5 seções numeradas distinguíveis, PMC na posição 2 com os mesmos valores, Potencial em 3 blocos sem PMC, legenda por método e linha-guia visíveis, zero scroll horizontal (CLR-12..15, 17..25).
