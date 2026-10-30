# Running dynamics por tênis — Design

**Spec**: `.specs/features/tenis-running-dynamics/spec.md`
**Context**: `.specs/features/tenis-running-dynamics/context.md`
**Status**: Draft

---

## Architecture Overview

Quatro frentes independentes sobre o mesmo modelo de dados: (1) migração da `Split` com 4 colunas nullable de running dynamics, (2) enriquecimento do `map_splits` para extrair GCT/passada/oscilação/ratio do `lapDTO`, (3) método no client Garmin para typed splits de uma atividade (backfill sob demanda, sem re-pull de listagens), (4) exposição dos 4 campos no `GET /api/activities/{id}` detail. Sem UI nesta entrega.

```mermaid
graph TD
    subgraph "Runtime - leitura do banco"
        U[Usuário] -->|GET /api/activities/{id}| AR[activities/router]
        AR --> AS[activities/service - get_activity_detail]
        AS -->|SplitOut com 4 campos RD| FE[Frontend detail]
    end
    subgraph "Backfill por atividade (CLI, sob demanda)"
        CLI[python -m app.strava.backfill-activity\n--activity-id X --user-id 1] --> SC[app.strava.client\ntyped_splits(activity_id)]
        SC --> MP[app.garmin.mappers.map_splits\nenriquece com GCT/passada/oscilação/ratio]
        MP --> SS[Split upsert por activity_id + idx]
        SS --> PG[("Postgres: splits.gct_ms,\nstride_cm, vert_osc_cm, vert_ratio")]
    end
    subgraph "Garmin Connect (1 chamada por atividade)"
        SC -->|connectapi / get_activity_splits| GC[(Garmin API)]
    end
```

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --------- | -------- | ---------- |
| Modelo `Split` | `app/db/models.py:98` | Adicionar 4 colunas nullable: `ground_contact_time_ms` (Integer), `stride_length_cm` (Float), `vertical_oscillation_cm` (Float), `vertical_ratio` (Float). Manter `uq_split_activity_idx`. |
| Migração idempotente | `app/db/engine.py::_migrate_schema` | Estender com bloco condicional `_migrate_splits_running_dynamics()` (sem early-return bloqueante — lição do tenis T1). |
| Mapper de splits | `app/garmin/mappers.py:map_splits` | Adicionar extração de `groundContactTime`, `strideLength`, `verticalOscillation`, `verticalRatio` do lapDTO → chaves `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio`. Ausente = None. |
| Client Garmin | `app/garmin/client.py` | Adicionar método `get_activity_splits_typed(activity_id)` que retorna lapDTOs completos via `connectapi`, contando chamada no orçamento (`_call`), com backoff (2,4,8). |
| Backfill CLI | `app/garmin/import_tokens.py` | Padrão CLI (argparse + `SessionLocal()` + exceção de domínio + `sys.exit(1)`). Novo comando `backfill-activity` no módulo strava ou flag. |
| Router de atividades | `app/activities/router.py` | `SplitOut` ganha 4 campos opcionais; `get_activity_detail` já monta splits — só passar os novos campos. |
| Testes | `conftest.py`, `test_*.py` | Matriz happy + edge (métrica ausente, lapDTO vazio, atividade inexistente, idempotência). |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| Garmin Connect | `connectapi` genérico (mesmo padrão de `get_heart_rate_zones`) para typed splits de uma atividade; 1 chamada contada no orçamento. |
| Postgres | Tabela `splits` + 4 colunas nullable; upsert por `(activity_id, idx)`. |
| API existente | `GET /api/activities/{id}` detail expõe `SplitOut` com os 4 campos (null quando ausente). |
| Frontend | Nada a mudar nesta entrega (sem UI). Campos disponíveis para consumo futuro de A e C. |

---

## Components

### Backend — Migração da Split (4 colunas nullable)

- **Purpose**: Adicionar colunas de running dynamics à `Split` sem quebrar esquema existente.
- **Location**: `app/db/models.py` + `app/db/engine.py`
- **Interfaces**:
  - `Split.ground_contact_time_ms: int | None` (Integer, nullable)
  - `Split.stride_length_cm: float | None` (Float, nullable)
  - `Split.vertical_oscillation_cm: float | None` (Float, nullable)
  - `Split.vertical_ratio: float | None` (Float, nullable)
  - `_migrate_schema()` refatorado: `_migrate_splits_running_dynamics()` condicional à existência das colunas (`ALTER TABLE splits ADD COLUMN ...` se não existir), idempotente em re-run.
- **Dependencies**: nenhuma nova
- **Reuses**: padrão de migração do tenis (T1); espírito AD-019 (idempotente, zero deps)

### Backend — Mapper enriquecido de splits

- **Purpose**: Extrair running dynamics do `lapDTO` do Garmin.
- **Location**: `app/garmin/mappers.py` (função `map_splits`)
- **Interfaces**:
  - Cada linha de split retorna chaves adicionais: `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio`.
  - `groundContactTime` → `gct_ms` (int | None); `strideLength` → `stride_cm` (float | None); `verticalOscillation` → `vert_osc_cm` (float | None); `verticalRatio` → `vert_ratio` (float | None).
  - Campo ausente → None (não falhar). `lapDTO` None/vazio → `[]` (mesmo comportamento atual).
- **Dependencies**: nenhuma
- **Reuses**: estilo de mappers puros de `app/garmin/mappers.py` (100% testável com fixtures)

### Backend — Método typed splits no client Garmin

- **Purpose**: Buscar lapDTOs completos de uma atividade específica para backfill sob demanda.
- **Location**: `app/garmin/client.py` (método novo na `GarminGateway`)
- **Interfaces**:
  - `get_activity_splits_typed(activity_id: int) -> dict | None` — retorna o payload completo de `get_activity_splits` (com `lapDTOs` incluindo running dynamics) via `connectapi`/`get_activity_splits`.
  - Conta 1 chamada no orçamento (`_call`), backoff (2,4,8) em 429/5xx.
  - Atividade sem splits → lista vazia ou None sem erro.
- **Dependencies**: `httpx`, `garminconnect`, `_call` (orçamento)
- **Reuses**: padrão `_call` de `GarminGateway`; seam injetável para teste

### Backend — Backfill por atividade sob demanda (CLI)

- **Purpose**: Enriquecer splits existentes com running dynamics, um por um, sem re-pull de listagens.
- **Location**: `app/strava/` ou novo módulo `app/strava/backfill_activity.py` (decisão de agent: CLI separada ou flag do backfill existente)
- **Interfaces**:
  - CLI `python -m app.strava.backfill_activity --activity-id X --user-id 1 [--yes]`
  - Busca typed splits do Garmin, faz upsert nas linhas de `Split` por `(activity_id, idx)` preenchendo as 4 colunas, commit único no fim.
  - Idempotente: re-run não duplica.
  - Atividade inexistente → erro claro, sem gravação.
  - Apenas `running`/`trail_running` (ou pula silenciosamente outras modalidades).
- **Dependencies**: `app.shoes` (modelo Split), `app.garmin.client` (typed splits), `SessionLocal`
- **Reuses**: padrão CLI de `app/garmin/import_tokens.py`

### Backend — Exposição no detail da atividade

- **Purpose**: Disponibilizar running dynamics no `GET /api/activities/{id}`.
- **Location**: `app/activities/router.py` + `app/activities/service.py`
- **Interfaces**:
  - `SplitOut` ganha `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio` (todos `int | None` / `float | None`).
  - `get_activity_detail` passa os novos campos de cada split para o detail.
  - Sem dado → campos null (split não omitido).
- **Dependencies**: `Split` model (novas colunas)
- **Reuses**: padrão de `ActivityDetailOut` existente

---

## Data Models

### `Split` (SQLAlchemy → Postgres `splits`)

Colunas existentes mantidas + 4 novas:

| Coluna | Tipo | Nullable | Nota |
| ------ | ---- | -------- | ---- |
| `ground_contact_time_ms` | Integer | Sim | GCT da volta (ms) |
| `stride_length_cm` | Float | Sim | Comprimento de passada (cm) |
| `vertical_oscillation_cm` | Float | Sim | Oscilação vertical (cm) |
| `vertical_ratio` | Float | Sim | Ratio vertical |

`__table_args__` mantém `UniqueConstraint("activity_id", "idx", name="uq_split_activity_idx")`.

### Payloads (pydantic ↔ TS)

`SplitOut`: campos existentes + `gct_ms: int | None`, `stride_cm: float | None`, `vert_osc_cm: float | None`, `vert_ratio: float | None`.

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| Sem sessão (401) | `require_session` por include do router | Redirect para `/login` |
| Atividade inexistente no backfill | Erro claro do CLI, sem gravação | Nenhum split alterado |
| Métrica ausente no lapDTO | Campo = None (não falha) | Split continua com dados parciais |
| lapDTO vazio/None | `map_splits` retorna `[]` | Sem splits, sem warning |
| Garmin 429/5xx em typed splits | Backoff (2,4,8), 3 tentativas, depois erro de domínio | Re-executar o CLI retoma (idempotente) |
| Atividade não é running/trail_running | Pula silenciosamente (ou não enriquece) | Nenhum efeito colateral |
| Commit único no backfill | Tudo-ou-nada; abort = estado consistente | Sem gravação parcial |

---

## Risks & Concerns

| Concern | Location | Impact | Mitigation |
| ------- | -------- | ------ | ---------- |
| `_migrate_schema` early-return bloqueia migração nova | `app/db/engine.py` (lição tenis T1) | Bloqueia em bases já migradas | Refatorar em bloco condicional independente `_migrate_splits_running_dynamics()` |
| Colunas NULL vs zero inventado | `map_splits` + `SplitOut` | Falsa precisão na análise A/C | Campo ausente = None; nunca 0 ou default |
| N+1 se backfill processar muitas atividades | CLI backfill-activity | Uma chamada Garmin por atividade | Backfill é sob demanda (um por one), não em lote automático |
| `verticalRatio` pode ser percentual (0-100) ou ratio (0-1) | Mapper | Interpretação inconsistente | Aterrissar contra payload real do garmin_mcp do usuário; documentar unidade |
| Frontend sem suite JS | `frontend/` | Sem teste automatizado de UI | Sem UI nesta entrega; campos expostos para consumo futuro |

---

## Tech Decisions

| Decision | Choice | Rationale |
| -------- | ------ | ---------- |
| 4 colunas nullable na `Split` | `ground_contact_time_ms`, `stride_length_cm`, `vertical_oscillation_cm`, `vertical_ratio` | Todas as 4 quando existirem (decidido pelo usuário); nullable = "sem dado não é zero" |
| Migração condicional por bloco | `_migrate_splits_running_dynamics()` | Evita early-return do `users` bloquear a emenda (lição tenis T1) |
| Typed splits via `connectapi` | `get_activity_splits_typed` na `GarminGateway` | Reusa `_call` (orçamento + backoff); 1 chamada contada por atividade |
| Backfill sob demanda | CLI separado, um activity_id por execução | Sem re-pull de listagens (contexto tenis); idempotente por upsert `(activity_id, idx)` |
| Commit único no backfill | Tudo-ou-nada | Abort = estado consistente; idempotência natural da re-execução |
| Sem UI nesta Delivery | Apenas endpoint + dados | UI fica para features A/C consumirem; não há demanda de UI no escopo B |

> Nenhuma Tech Decision aqui é project-level: o log `## Decisions` de `.specs/STATE.md` permanece inalterado para decisões de arquitetura global.
