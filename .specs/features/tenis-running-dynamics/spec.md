# Running dynamics por tênis (typed splits) — Specification

## Problem Statement

O Ritmo já guarda splits de cada corrida (distância, duração, pace, FC, cadência), mas não guarda **running dynamics** por volta: tempo de contato com o chão (GCT), comprimento de passada, oscilação vertical e ratio vertical. Esses dados existem no `lapDTO` do Garmin (Forerunner 255 grava via punho, confirmado na atividade 24867446401) e são o **pré-requisito** da análise comparativa entre tênis (A) e do alerta de degradação (C) — sem eles, não há como comparar se um tênis muda a biomecânica do corredor.

## Goals

- [ ] Colunas `ground_contact_time_ms`, `stride_length_cm`, `vertical_oscillation_cm`, `vertical_ratio` na tabela `Split`, todas nullable (volta sem dado = NULL, nunca zero inventado)
- [ ] Método no client Garmin para ler typed splits de uma atividade (sem re-pull das listagens)
- [ ] Backfill por atividade sob demanda: enriquecer splits existentes com running dynamics, um por um, sem duplicar
- [ ] Expor os campos no `GET /api/activities/{id}` detail (SplitOut) para consumo futuro de A e C

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Análise comparativa entre tênis (perfil por tipo de treino, comparação pareada, EF, GCT ajustado por ritmo) | Feature A, depende deste dado limpo |
| Alerta de aposentadoria por degradação (baseline multi-sinal) | Feature C, depende de A |
| UI de running dynamics (tela, gráfico, comparação visual) | Sem demanda de UI nesta entrega; dado de fundação |
| Sync contínuo do Strava / Garmin com running dynamics automático | Backfill sob demanda, decisão do usuário |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Métricas capturadas por volta | Todas as 4 quando existirem no payload (GCT, passada, oscilação, ratio) | Forerunner 255 grava as 4 via punho; capturar o que vier | y (usuário aceitou recomendada) |
| Volta sem dado de running dynamics | Coluna NULL; bloco omitido na análise; nunca inventar zero | "Sem dado não é zero" — evita falsa precisão | y (usuário aceitou recomendada) |
| Fonte dos dados | Garmin Connect (typed splits / lapDTO), não Strava | Strava não expõe running dynamics por volta de forma confiável | y |
| Backfill | Por atividade, sob demanda (CLI), um por um; sem re-pull das listagens de atividades | Contexto deferred ideas: "backfill por atividade sem re-pull das listagens" | y |
| População de splits existentes | Enriquecer splits já gravados no Ritmo; não rebaixar atividades do zero | Os splits já existem com `activity_id` + `idx` | y |

**Open questions:** none — todas resolvidas acima.

---

## User Stories

### P1: Colunas de running dynamics na Split ⭐ MVP

**User Story**: Como desenvolvedor da plataforma, quero que a tabela `Split` armazene GCT, passada, oscilação vertical e ratio vertical por volta, para que A e C tenham dado de biomecânica para comparar tênis.

**Why P1**: Fundação de tudo — sem essas colunas, nem A nem C existem.

**Acceptance Criteria** (EARS):

1. WHEN o esquema do banco é (re)criado THEN a tabela `splits` SHALL ter colunas `ground_contact_time_ms` (Integer, nullable), `stride_length_cm` (Float, nullable), `vertical_oscillation_cm` (Float, nullable), `vertical_ratio` (Float, nullable), além das existentes.
2. IF uma volta do Garmin não traz alguma das 4 métricas THEN o valor correspondente SHALL ser NULL (não 0, não default inventado).
3. The system SHALL manter o `UniqueConstraint("activity_id", "idx", name="uq_split_activity_idx")` intacto.

**Independent Test**: rodar migração em banco vazio e conferir as 4 colunas presentes e nullable; inserir split com métricas ausentes e confirmar NULL.

---

### P1: Mapper captura typed splits do Garmin ⭐ MVP

**User Story**: Como desenvolvedor, quero que o mapper de splits extraia ground_contact_time, stride_length, vertical_oscillation e vertical_ratio do `lapDTO` do Garmin, para popular as novas colunas.

**Why P1**: Sem extração no mapper, as colunas ficam vazias.

**Acceptance Criteria** (EARS):

1. WHEN `map_splits` recebe um `lapDTO` com `groundContactTime`, `strideLength`, `verticalOscillation`, `verticalRatio` THEN o dicionário retornado SHALL conter as chaves `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio` com os valores respectivos.
2. IF um dos campos estiver ausente no `lapDTO` THEN a chave correspondente SHALL ser None (não falhar).
3. IF o `lapDTO` for None ou vazio THEN `map_splits` SHALL retornar `[]` sem warning (mesmo comportamento de splits comuns).

**Independent Test**: chamar `map_splits` com fixture de lapDTO contendo as 4 métricas e conferir as chaves; chamar com lapDTO sem as métricas e conferir None.

---

### P1: Método no client Garmin para typed splits de uma atividade ⭐ MVP

**User Story**: Como desenvolvedor, quero um método no client Garmin que busque os typed splits (lapDTOs completos) de uma atividade específica, para enriquecer splits já existentes no Ritmo.

**Why P1**: É o ponto de entrada do backfill por atividade.

**Acceptance Criteria** (EARS):

1. WHEN o client Garmin é chamado para typed splits de um `activity_id` THEN ele SHALL retornar os `lapDTOs` completos da atividade (incluindo running dynamics) via `connectapi` / `get_activity_splits`.
2. IF a atividade não tem splits THEN o método SHALL retornar lista vazia ou None sem erro.
3. The system SHALL contar cada chamada no orçamento de chamadas do Garmin (mesmo padrão de `_call` com backoff).

**Independent Test**: injetar httpx MockTransport com lapDTOs e conferir retorno; testar ausência de splits.

---

### P2: Backfill por atividade (enriquecimento sob demanda) ⭐ MVP

**User Story**: Como corredor, quero enriquecer os splits de uma corrida já sincronizada com running dynamics, um por um, sem baixar tudo de novo.

**Why P2**: Útil para popular dado histórico de corridas já no banco sem re-pull das listagens.

**Acceptance Criteria** (EARS):

1. WHEN o backfill por atividade roda para um `activity_id` THEN ele SHALL buscar os typed splits do Garmin, fazer upsert nas linhas de `Split` correspondentes (por `activity_id` + `idx`) preenchendo as 4 colunas de running dynamics, e commitar.
2. WHEN o backfill roda duas vezes para a mesma atividade THEN o estado SHALL ficar idêntico (idempotente, sem duplicar splits).
3. IF a atividade não existe no Ritmo THEN o script SHALL abortar com erro claro (atividade não encontrada) e não gravar nada.
4. The system SHALL enriquecer apenas splits de atividades `running`/`trail_running` (ou pular silenciosamente outras modalidades).

**Independent Test**: rodar backfill contra uma atividade real com splits, conferir colunas preenchidas; rodar de novo e confirmar sem duplicatas.

---

### P2: Expor running dynamics no detail da atividade ⭐

**User Story**: Como corredor, quero ver GCT, passada, oscilação e ratio por volta no detalhe da corrida, para conferir o dado capturado.

**Why P2**: Validação visual do dado antes de A e C consumirem.

**Acceptance Criteria** (EARS):

1. WHEN `GET /api/activities/{id}` retorna o detail de uma corrida THEN cada split SHALL incluir `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio` (null quando não houver dado).
2. IF não houver running dynamics para nenhum split THEN os campos SHALL vir null (não omitir o split).

**Independent Test**: chamar GET detail de uma corrida com splits enriquecidos e conferir os campos nos splits.

---

## Edge Cases

- WHEN o Garmin retorna typed splits com distância 0 (esteira sem GPS) THEN as métricas de running dynamics SHALL ainda ser capturadas (GCT/passada não dependem de GPS).
- WHEN duas atividades têm o mesmo `activity_id` no Garmin (raro) THEN o upsert por `activity_id` + `idx` atualiza em vez de duplicar.
- IF o token Garmin expira durante o backfill por atividade THEN o script SHALL abortar com estado consistente (split parcial não gravado) e mensagem de renovação.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TRD-01 | P1: Colunas na Split | Implementing | Verified |
| TRD-02 | P1: Volta sem dado = NULL | Design | Pending |
| TRD-03 | P1: Unique constraint intacto | Implementing | Verified |
| TRD-04 | P1: Mapper extrai 4 métricas | Implementing | Verified |
| TRD-05 | P1: Campo ausente -> None | Implementing | Verified |
| TRD-06 | P1: lapDTO vazio -> [] | Implementing | Verified |
| TRD-07 | P1: Método client typed splits | Implementing | Verified |
| TRD-08 | P1: Sem splits -> vazio/sem erro | Implementing | Verified |
| TRD-09 | P1: Chamada contada no orçamento | Implementing | Verified |
| TRD-10 | P2: Backfill por atividade upsert | Implementing | Verified |
| TRD-11 | P2: Idempotência (re-run) | Implementing | Verified |
| TRD-12 | P2: Atividade inexistente -> erro | Implementing | Verified |
| TRD-13 | P2: Apenas running/trail_running | Implementing | Verified |
| TRD-14 | P2: SplitOut expõe 4 campos | Design | Pending |
| TRD-15 | P2: Sem dado -> null nos campos | Design | Pending |

**ID format:** `TRD-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 15 total, 0 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Tabela `splits` com as 4 colunas nullable, migração idempotente
- [ ] Mapper extrai GCT/passada/oscilação/ratio do lapDTO, ausente = None
- [ ] Client Garmin tem método de typed splits por atividade, conta chamada no orçamento
- [ ] Backfill por atividade enriquece splits existentes, idempotente, não duplica
- [ ] `GET /api/activities/{id}` detail expõe os 4 campos por split (null quando ausente)
