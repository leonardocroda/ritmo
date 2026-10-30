# Análise comparativa entre tênis — Design

**Spec**: `.specs/features/tenis-analise-comparativa/spec.md`
**Context**: `.specs/features/tenis-analise-comparativa/context.md`
**Status**: Draft

---

## Architecture Overview

Três frentes independentes sobre o mesmo modelo de dados (100% leitura do banco, AD-002, zero Garmin em tempo de análise): (1) domínio novo `app/tenis_analysis` com funções puras de perfil, comparação pareada, nível de confiança, running dynamics ajustados, EF, HR drift e janela fresco vs fadiga; (2) endpoints de leitura no router existente de atividades ou novo router `/api/tenis/analysis`; (3) sem UI nesta entrega (campos expostos para consumo futuro).

```mermaid
graph TD
    subgraph "Banco do Ritmo (leitura)"
        ACT[activities + shoe_id] --> TA[tenis_analysis]
        SPL[splits com running dynamics (B)] --> TA
        SHO[shoes (km derivada)] --> TA
    end
    subgraph "Domínio de análise (funções puras)"
        TA --> PERF[perfil por tipo x banda de pace]
        TA --> PAIR[comparacao pareada matched runs]
        TA --> CONF[nivel de confiança baixo/medio/alto]
        TA --> RD[running dynamics ajustados por ritmo]
        TA --> EF[EF velocidade/FC]
        TA --> DRIFT[HR drift]
        TA --> WINDOW[janela fresco vs fadiga]
    end
    subgraph "API de leitura"
        TA --> EP[GET /api/tenis/analysis/{shoe_id} e comparação]
        EP --> FE[Frontend futuro (sem UI nesta entrega)]
    end
```

O domain depende de **B** (colunas running dynamics na `Split`) e do **tenis** (km derivada, `shoe_id`).

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --------- | -------- | ---------- |
| Modelo `Activity` + `shoe_id` | `app/db/models.py` | Filtrar atividades por `shoe_id` e `activity_type in RUNNING_TYPES` |
| Modelo `Split` (colunas RD de B) | `app/db/models.py` | Ler `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio` + `avg_hr`, `pace_s`, `dist_m`, `duration_s` |
| `RUNNING_TYPES` | `app/garmin/mappers.py:16` | `{"running", "trail_running"}` — só corridas entram na análise |
| `consistency_metrics` / `derive_structure` | `app/activities/service.py` | Reuso de lógica de classificação se necessário |
| ZoneConfig (VDOT) | `app/vdot/zones.py` | Para definir bandas de pace por tipo de treino (mesmo arquivo do perfil Performance) |
| `_pace_s`, `_km_label` | `app/activities/service.py` | Helpers existentes para pace e rótulo de km |
| Testes | `conftest.py` | Matriz happy + edge (sem dados, confiança baixa, pares insuficientes) |

### Integration Points

| System | Integration Method |
| ------ | ------------------ |
| Postgres | Leitura de `activities`, `splits`, `shoes` — filtro por `user_id` (user-scope) |
| API existente | Novo router `/api/tenis/analysis` ou extensão do router de atividades |
| Frontend | Nada nesta entrega (sem UI); payload JSON pronto para consumo futuro |

---

## Components

### Backend — Domínio `app/tenis_analysis/` (funções puras)

- **Purpose**: Cálculo puro de perfil, comparação pareada, nível de confiança e métricas derivadas.
- **Location**: `app/tenis_analysis/__init__.py`, `app/tenis_analysis/profile.py`, `app/tenis_analysis/comparison.py`, `app/tenis_analysis/metrics.py`
- **Interfaces** (funções puras, recebem rows do banco, não fazem queries diretas — testáveis com fixtures):
  - `build_shoe_profile(runs: list[dict]) -> dict` — agrupa por tipo × banda de pace, retorna médias + contagem
  - `build_matched_pairs(runs_a: list[dict], runs_b: list[dict]) -> list[dict]` — pares distância ±5% e pace ±5%, data livre
  - `confidence_level(n_pairs: int) -> str` — <3 = "baixo", 3–5 = "médio", >5 = "alto"
  - `running_dynamics_adjusted(runs_with_rd: list[dict]) -> dict | None` — resíduo de regressão linear de GCT/passada/oscilação vs pace (por tipo); None sem dado
  - `ef_factor(runs: list[dict]) -> dict | None` — velocidade / FC média; null sem FC
  - `hr_drift(runs: list[dict]) -> dict | None` — FC 2ª metade − 1ª metade, só se pace estável (AD-005)
  - `fresh_vs_fatigue(runs: list[dict]) -> dict | None` — primeiros ~30% vs últimos ~30% da distância

### Backend — Endpoints de leitura

- **Purpose**: Expor a análise via API para consumo futuro.
- **Location**: novo router `app/tenis_analysis/router.py` (ou extensão de `app/activities/router.py`)
- **Interfaces**:
  - `GET /api/tenis/analysis/shoes` — perfil de todos os tênis do usuário
  - `GET /api/tenis/analysis/shoes/{shoe_id}` — perfil detalhado de um tênis
  - `GET /api/tenis/analysis/compare?shoe_a=X&shoe_b=Y` — comparação pareada com nível de confiança
- **Dependencies**: `app.tenis_analysis.*` (regras), `require_session`, `get_db`
- **Reuses**: padrão de router do projeto; isolamento por `user.id`

---

## Data Models

Não há novas tabelas — leitura pura de `activities`, `splits`, `shoes`.

### Payload de entrada (run row)

Cada corrida usada na análise traz (do banco):
- `id`, `distance_m`, `duration_s`, `pace_s`, `avg_hr`, `max_hr`, `avg_cadence`, `inferred_type`, `start_time`, `shoe_id`
- Running dynamics (de B, nullable): `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio`
- Splits com FC para HR drift e fresh vs fadiga

### Payloads de saída

`ShoeProfile`: `{shoe_id, name, total_runs, total_km, profile_by_type_band: [...]}`
`MatchedPair`: `{shoe_a, shoe_b, distance, pace_a, pace_b, delta_pace, fc_a, fc_b, delta_fc}`
`ComparisonResult`: `{pairs: [...], confidence: "baixo|medio|alto", n_pairs}`

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| -------------- | -------- | ----------- |
| Sem sessão (401) | `require_session` | Redirect para `/login` |
| Tênis inexistente ou de outro usuário | 404 | Mensagem padrão |
| Sem dados suficientes | Retorno vazio + confiança "baixa" | Não erro; honestidade do dado |
| Sem running dynamics (B não populado) | Blocos de RD omitidos, não erro | Análise segue com o que existe |
| Sem FC para EF/HR drift | Campo null | Omitido do bloco respectivo |
| Pace não estável para HR drift | Drift omitido para aquela corrida | Conforme AD-005 |

---

## Risks & Concerns

| Concern | Location | Impact | Mitigation |
| ------- | -------- | ------ | ---------- |
| Confounding de seleção (pace bruto agregado) | `profile.py` | Análise inválida | Fatiar obrigatoriamente por tipo × banda; nunca expor agregado bruto |
| Few pairs (baixa confiança) | `comparison.py` | Falsas conclusões | Nível de confiança sempre exibido; usuário decide |
| Sem dados de running dynamics de B | `metrics.py` | Blocos RD ausentes | Omitido, não erro; análise segue com EF/drift/janela |
| Regressão sobre dados existentes | Queries de leitura | Nenhuma gravação | Apenas SELECT — zero risco de corrupção |

---

## Tech Decisions

| Decision | Choice | Rationale |
| -------- | ------ | ---------- |
| Nenhuma tabela nova | Leitura pura de `activities`/`splits`/`shoes` | Zero migração, zero risco de schema; dados já existem de B + tenis |
| Funções puras injetadas com rows | `app/tenis_analysis/` recebe listas de dict | 100% testável sem banco; fácil de unit testar com fixtures |
| Endpoints de leitura somente | GET apenas | Análise sob demanda, reprodutível; nenhuma escrita |
| Data livre para pares | Não há critério de proximidade de datas | Decidido pelo usuário (Guided) |
| Confiança sempre exibida | <3 / 3–5 / >5 pares | Decidido pelo usuário (Opção C) |
| Sem UI nesta entrega | Apenas JSON via endpoint | UI fica para consumo futuro; não há demanda no escopo A |

> Nenhuma Tech Decision é project-level; o log `## Decisions` de `.specs/STATE.md` permanece inalterado.
