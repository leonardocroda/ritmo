# Lista de Treinos + Gráfico de Splits — Design

**Spec**: `.specs/features/workouts-list/spec.md`
**Status**: Draft

---

## Architecture Overview

Leitura pura do banco próprio (AD-002): um novo domínio de leitura `activities/` no backend (router + service + métricas/tipo como funções puras) e telas client-side no Next.js consumindo a API tipada. Classificação de zona VDOT vive no domínio `vdot/` — reutilizada no futuro pelo motor de avaliação (AD-003).

```mermaid
graph TD
    subgraph Frontend
        NAV[Nav no Header] --> LIST[/treinos · WorkoutsList]
        LIST --> DET[/treinos/id · WorkoutDetail]
        DET --> CHART[SplitsChart · SVG próprio]
    end
    LIST -->|GET /api/activities| RT[activities/router]
    DET -->|GET /api/activities/id| RT
    RT --> SVC[activities/service]
    SVC --> DB[(Postgres)]
    SVC --> ZONES[vdot/zones · load+classify]
    SVC --> MET[activities/metrics · consistência]
    SVC --> INF[activities/infer · tipo+estrutura]
    ZONES --> JSON[vdot_zones.json]
```

Fluxo do detalhe: service carrega atividade + voltas → classifica cada pace por zona (função pura) → calcula consistência (função pura) → junta contexto (sono/HRV/RHR do dia) → monta o payload; tipo inferido e estrutura derivam de `intensity_type` + zonas, em tempo de leitura.

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --------- | -------- | ---------- |
| `get_db` / SessionLocal | `backend/app/db/engine.py` | Injeção de sessão nos endpoints (mesmo padrão do sync router) |
| `DEFAULT_USER_ID` | `backend/app/db/models.py` | Escopo de todas as queries (AD-001) |
| Padrão do router Pydantic | `backend/app/garmin/router.py` | Modelos de saída inline + HTTPException 404 |
| `map_splits` (normalização lapDTOs) | `backend/app/garmin/mappers.py` | Extend: `averageRunCadence` + `averageTemperature` (nomes da sonda real) |
| Cliente tipado da API | `frontend/src/lib/api.ts` | Extend: tipos + fetchers de lista/detalhe; `parseError` reutilizado |
| `SyncButton` como padrão de client component | `frontend/src/components/SyncButton.tsx` | Estado loading/error + fetch no mount |
| Cores/clamp/legend do gráfico validado | `garmin_mcp/.opencode/skills/generate-run-summary-image/generate_image.py` | Referência para clamp de pace e legenda (cores mudam para zonas VDOT) |
| `derive_structure` | idem | Port direto para `activities/infer.py` |
| Helpers/factories de teste | `backend/tests/helpers.py`, `fake_garmin.py` | Fixtures de atividades+splits nos testes novos |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| Postgres (tables `activities`, `splits`, `sleep`, `hrv`, `rhr`) | Leitura via SQLAlchemy; nenhuma tabela nova — 2 colunas em `splits` |
| `vdot_zones.json` | Lido por `vdot/zones.py` via `VDOT_ZONES_PATH`; imagem do backend passa a copiar `data/` |
| Router mounting | `app.main` ganha `include_router(activities_router)` |
| Navegação existente | `Header.tsx` ganha `<Nav />` (client, `usePathname`) |

---

## Components

### `app/vdot/zones.py`

- **Purpose**: Carregar zonas VDOT calibradas e classificar pace em zona — a única fonte de verdade de zona.
- **Location**: `backend/app/vdot/zones.py`
- **Interfaces**:
  - `load_zone_config(path: str) -> ZoneConfig` — parse do JSON; lança `ZoneConfigError` se ausente/inválido
  - `ZoneConfig.classify(speed_ms: float | None) -> str | None` — easy/marathon/threshold/interval/repetition pelos cut points de midpoint; `None` se pace inválido
  - `ZoneConfig.meta() -> list[ZoneMeta]` — chave, rótulo, faixa exibível e **cor** (fonte única para o frontend)
- **Dependencies**: `json`, `pathlib`; settings `vdot_zones_path`
- **Reuses**: `backend/data/vdot_zones.json` (calibração existente)

### `app/activities/metrics.py`

- **Purpose**: Métricas de consistência como funções puras sobre voltas classificadas.
- **Location**: `backend/app/activities/metrics.py`
- **Interfaces**:
  - `split_halves(splits) -> tuple[list, list]` — divisão por distância acumulada (≥50% = 1ª metade)
  - `consistency_metrics(splits, distance_m) -> dict | None` — gate ≥8000m e ≥4 voltas; retorna equilíbrio (Δ pace s/km + %), drift cardíaco (Δ bpm), decoupling (%), fade de cadência (Δ spm) quando houver dados
- **Dependencies**: nenhum (puro)
- **Reuses**: convenções numéricas do `pmc.py` (funções puras testáveis)

### `app/activities/infer.py`

- **Purpose**: Tipo inferido + estrutura derivada — funções puras.
- **Location**: `backend/app/activities/infer.py`
- **Interfaces**:
  - `infer_type(raw_json, splits_classificados, distance_m) -> str` — prova/intervalado/limiar/tempo/progressivo/longao/facil na ordem de prioridade do spec
  - `derive_structure(splits) -> str` — port de `derive_structure` (soma passos por intensity_type)
- **Dependencies**: nenhum (puro)
- **Reuses**: lógica de grupos do `_count_run_groups` (generate_image.py) adaptada para zonas

### `app/activities/service.py`

- **Purpose**: Montar os payloads de lista e detalhe a partir do banco.
- **Location**: `backend/app/activities/service.py`
- **Interfaces**:
  - `list_activities(db, activity_type: str, limit: int, offset: int) -> dict` — corridas por padrão; count total; voltas da página em **1 query `IN`** (sem N+1); tipo inferido por item
  - `get_activity_detail(db, activity_id: int, zone_config) -> dict` — atividade + voltas classificadas + consistência + contexto (sono/HRV/RHR da data local) + zonas meta + estrutura
- **Dependencies**: models, `vdot/zones`, `metrics`, `infer`
- **Reuses**: padrão de query do sync service

### `app/activities/router.py`

- **Purpose**: Endpoints de leitura + validação de parâmetros.
- **Location**: `backend/app/activities/router.py`
- **Interfaces**:
  - `GET /api/activities?activity_type=running|all&limit=&offset=` → `ActivityListOut` (422 fora de [1,100]/offset<0)
  - `GET /api/activities/{activity_id}` → `ActivityDetailOut` (404 se inexistente; 500 "zonas VDOT não configuradas" se o arquivo falhar)
- **Dependencies**: `get_db`, `service`, `vdot/zones`
- **Reuses**: padrão do `garmin/router.py`

### `frontend/src/components/Nav.tsx`

- **Purpose**: Navegação dos 4 painéis no header, com painel ativo marcado.
- **Location**: `frontend/src/components/Nav.tsx`
- **Interfaces**: componente client (`usePathname`); items: Hoje `/hoje`, Treinos `/treinos`, Potencial `/potencial`, Saúde `/saude`; ativo = pathname === href ou `pathname.startsWith(href + "/")`
- **Dependencies**: `next/link`, `next/navigation`
- **Reuses**: tokens visuais do `Header.tsx` (border-white/10, text-muted)

### `frontend/src/components/workouts/WorkoutsList.tsx`

- **Purpose**: Lista paginada com filtro corridas/todas e "Carregar mais".
- **Location**: `frontend/src/components/workouts/WorkoutsList.tsx`
- **Interfaces**: client component; estado `{items, total, offset, filter, loading, error}`; reset de offset ao trocar filtro; item = `Link` para `/treinos/{id}` com data, nome, tipo, distância, pace (ou duração), FC, badge "Avaliado"
- **Dependencies**: `lib/api` (`getActivities`), `lib/format`
- **Reuses**: padrão de fetch/estado do `SyncButton`

### `frontend/src/components/workouts/WorkoutDetail.tsx`

- **Purpose**: Página do treino: cabeçalho de métricas, faixa de contexto, gráfico, tabela de consistência, estrutura.
- **Location**: `frontend/src/components/workouts/WorkoutDetail.tsx`
- **Interfaces**: client component `(id: number)`; estados loading/not-found/error/dados; seções renderizadas condicionalmente ("só o que existir")
- **Dependencies**: `lib/api` (`getActivityDetail`), `SplitsChart`, `lib/format`
- **Reuses**: padrão de fetch/estado do `SyncButton`

### `frontend/src/components/workouts/SplitsChart.tsx`

- **Purpose**: Gráfico composto de splits (barras de pace por zona **com largura proporcional à duração da volta** + linha FC + relevo).
- **Location**: `frontend/src/components/workouts/SplitsChart.tsx`
- **Interfaces**: props `{splits, zones}`; renderer React SVG — port direto do layout validado do `generate_image.py`: largura da barra = `duração_da_volta / duração_total` da área útil; pace clampado a [180, 420] s/km com altura `max(altura, 2.5)` (voltas de recuperação ficam no fundo, sem barra negativa); polyline de FC com pontos no **meio de cada barra**; banda de relevo atrás; rótulos de pace por volta (ocultos quando a barra for estreita demais); rótulo do eixo X pelo km acumulado nas marcas proporcionais; tooltip por hover/tap (estado React) com pace real, FC, elevação, duração e zona; legenda de zonas presentes + FC
- **Dependencies**: React apenas — sem Recharts neste componente (decisão abaixo); responsivo via `viewBox`
- **Reuses**: `calculate_chart_dimensions`, `classify_split`, `generate_svg`, `generate_legend` do renderer validado (generate_image.py) — mesma matemática, cores trocadas para zonas VDOT

> **Por que não Recharts neste gráfico**: eixo categórico do Recharts dá slots iguais — largura proporcional (pausa de 30s ≠ tiro de 3km) e linha de FC alinhada ao meio de cada barra exigiriam shapes/ticks/tooltip customizados contra o modelo interno da lib. O renderer validado já resolve exatamente essa matemática. Recharts permanece no stack para os painéis futuros (PMC, sono, timeline).

### `frontend/src/lib/format.ts`

- **Purpose**: Formatadores PT-BR (pace MM:SS, duração H:MM:SS, distância com vírgula, cadência, temperatura).
- **Location**: `frontend/src/lib/format.ts`
- **Interfaces**: `formatPace(s)`, `formatDuration(s)`, `formatKm(m)`, `formatCadence(spm)`, `formatTemp(c)`
- **Dependencies**: nenhum
- **Reuses**: port de `format_pace`/`format_duration` (generate_image.py)

### Páginas e rotas (Next 16)

- `src/app/page.tsx` → `redirect("/treinos")` (server component, `next/navigation`)
- `src/app/treinos/page.tsx` → server page, renderiza `<WorkoutsList />`
- `src/app/treinos/[id]/page.tsx` → server page com `params: Promise<{id: string}>` (`await params`, `PageProps<"/treinos/[id]">`), valida número e renderiza `<WorkoutDetail id={n} />`
- `src/app/hoje/page.tsx`, `src/app/potencial/page.tsx`, `src/app/saude/page.tsx` → placeholders (componente compartilhado `PanelPlaceholder`)
- `Header.tsx` ganha `<Nav />` entre o título e o SyncButton; em 390px a nav vira linha rolável

---

## Data Models

### Contrato `GET /api/activities` (resumo)

```json
{
  "items": [{
    "id": 12, "start_time": "2026-10-14T07:15:02", "activity_type": "running",
    "name": "Londrina - Strides", "distance_m": 8234.0, "duration_s": 2451.0,
    "pace_s": 297.7, "avg_hr": 141, "inferred_type": "intervalado", "evaluated": false
  }],
  "total": 87, "limit": 30, "offset": 0
}
```

`inferred_type`: `prova|intervalado|limiar|tempo|progressivo|longao|facil|null` (ASCII na API; rótulos PT-BR com acento na UI). Não-corrida: `inferred_type=null`, pace `null`.

### Contrato `GET /api/activities/{id}` (resumo)

```json
{
  "activity": { "id": 12, "start_time": "...", "name": "...", "distance_m": 0, "duration_s": 0,
    "pace_s": 0, "avg_hr": 0, "max_hr": 0, "avg_cadence": 0, "elevation_gain_m": 0,
    "aerobic_te": 0, "anaerobic_te": 0, "training_load": 0, "evaluated": false,
    "inferred_type": "intervalado", "structure": "Aquecimento 2,0km + ..." },
  "splits": [{ "idx": 1, "dist_m": 100.0, "duration_s": 20.5, "pace_s": 205.7, "avg_hr": 123,
    "avg_cadence": 155.2, "avg_temperature": 22.0, "elevation_m": 0.0,
    "intensity_type": "ACTIVE", "zone": "repetition", "km_label": "1,6" }],
  "zones": [{ "key": "easy", "label": "Easy", "pace_range": "5:51–4:53/km", "color": "#22c55e" }],
  "consistency": { "balance_delta_s": -5.0, "balance_delta_pct": -1.7,
    "first_half_pace_s": 300.0, "second_half_pace_s": 295.0,
    "first_half_hr": 140.0, "second_half_hr": 146.0, "hr_drift_bpm": 6.0,
    "decoupling_pct": 3.2, "cadence_fade_spm": -2.0 },
  "context": { "sleep": {"duration_s": 21600, "score": 72}, "hrv": {"value": 77.0, "status": "balanced"},
    "rhr": {"value": 44}, "temperature_c": 22.4 }
}
```

`consistency=null` quando <8000m ou <4 voltas; campos de `context` = `null` quando ausentes (UI esconde); `temperature_c` ausente quando nenhuma volta tem temperatura; `cadence_fade_spm` omitido sem cadência suficiente.

### Model change (splits)

```
Split ganha: avg_cadence FLOAT NULL, avg_temperature FLOAT NULL
mapper: averageRunCadence / averageTemperature (sonda real 14/10/2026)
upsert: idempotente por (activity_id, idx) — herdado
```

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| Detalhe inexistente | 404 do backend | "Treino não encontrado" + link de volta à lista |
| `limit`/`offset` inválidos | 422 (validação FastAPI antes da query) | UI nunca envia inválido; erro visível em dev |
| `vdot_zones.json` ausente/inválido | 500 com mensagem "zonas VDOT não configuradas" | Detalhe falha explícito — cor de zona é requisito, não opcional |
| API fora do ar / fetch falha | Mensagem inline na página (lista e detalhe) | Navegação do header continua funcionando |
| Atividade sem splits | Resumo sem gráfico/métricas + nota "sem voltas registradas" | Usuário entende que é falta de dado, não erro |
| Banco vazio | Estado vazio apontando o botão "Puxar do Garmin" | CTA claro, sem tela branca |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | -------------------- | ------ | ---------- |
| `data/` não está na imagem do backend — zonas falhariam 500 no container | `backend/Dockerfile:16` (só `COPY app`) | Detalhe quebra no compose | Task dedicada: `COPY data ./data` + teste de fumaça do endpoint no container |
| N+1 de voltas na lista (tipo inferido precisa dos splits de cada item) | novo `activities/service.py` | Lista lenta com muitas páginas | 1 query `IN (activity_ids da página)` + agrupamento em memória |
| Recharts 3.x pode ter API diferente da 2.x | resolvido — gráfico de splits é SVG próprio; Recharts só entra em painéis futuros | — | — |
| SVG próprio: responsividade e hit-áreas de hover/tap são responsabilidade nossa | novo `SplitsChart.tsx` | Gráfico ruim no celular | `viewBox` responsivo + `preserveAspectRatio`; tooltip por estado React (hover/tap); testado manualmente em 390px (AC da navegação) |
| Voltas antigas sem cadência/temperatura (fora da janela de re-pull) | tabela `splits` existente | Métricas parciais nos treinos antigos | Já coberto pelo princípio "só o que existir" do spec (campos omitidos) |
| Home atual (landing "fase 0") é substituída pelo redirect | `frontend/src/app/page.tsx` | Conteúdo de scaffolding some | Aceito: era placeholder da Fase 0; nav + Treinos assumem a entrada |
| `usePathname` no Header client — hidratação com rewrites/proxy | `docs use-pathname.md` | Mismatch teórico de hidratação | Projeto não usa proxy/rewrites; risco nulo hoje |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| **Renderer do gráfico de splits** | **SVG próprio (port do validado)**, não Recharts | O requisito do usuário é largura proporcional à duração (pausa de 30s ≠ tiro de 3km) e FC alinhada por volta; eixo categórico do Recharts dá slots iguais. O `generate_image.py` validado já tem a matemática exata — portar para React SVG é menos código que lutar contra a lib. Recharts segue no stack para os demais painéis |
| Cores das zonas | Definidas no **backend** (`ZoneConfig.meta()`), frontend só renderiza | Fonte única; TRN-16 (FC ≠ cor de interval) vira teste Python no payload |
| Cor da linha de FC | `#f8fafc` (quase branco) com pontos | Contraste máximo com TODAS as cores de zona no tema escuro (princípio da imagem validada: FC contrasta com o herói); zero colisão com vermelho=interval |
| Zonas por request, sem cache | `load_zone_config` lê o arquivo a cada detalhe | Arquivo ~1KB; recarbiração (Fase 2) vale sem invalidação de cache |
| Tipo inferido em tempo de leitura | Função pura sobre splits+zonas, nunca persistido | Recalibração re-classifica sem re-sync; custo trivial |
| Valores de tipo em ASCII na API | `longao`, `facil` (sem acento) | Evita encoding inconsistente entre camadas; acento fica na camada de exibição |
| Paginação por offset/limit | Sem cursor | Escala pessoal (~200 atividades); simples e testável |
| Fetch client-side (sem SWR/React Query) | `fetch` + estados locais, como o SyncButton | Sem dependência nova; escala pessoal; Next 16 docs: client-side fetching é padrão suportado |

> Nenhuma decisão aqui cria convenção trans-versão além do que AD-001/002/003 já travam — sem novo AD-NNN.
