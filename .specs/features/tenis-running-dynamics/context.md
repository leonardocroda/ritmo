# Running dynamics por tênis — Context

**Gathered:** 29/10/2026 (conversa de planejamento, feature tenis expandida)
**Spec:** `.specs/features/tenis-running-dynamics/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Running dynamics por volta (GCT, passada, oscilação vertical, ratio vertical) como dado de fundação para a análise comparativa entre tênis (A) e alerta de degradação (C). Colunas na `Split`, mapper do Garmin, método no client e backfill por atividade sob demanda. Sem UI nesta entrega; sem sync contínuo.

---

## Implementation Decisions

### Métricas por volta (decidido pelo usuário — Guided)

- Capturar todas as 4 métricas quando existirem no payload do Garmin: `ground_contact_time_ms`, `stride_length_cm`, `vertical_oscillation_cm`, `vertical_ratio` (mapeadas no mapper como `gct_ms`, `stride_cm`, `vert_osc_cm`, `vert_ratio`).
- O Forerunner 255 grava as 4 via punho (confirmado no context.md do tenis, atividade 24867446401).

### Volta sem dado (decidido pelo usuário — Guided)

- Coluna = NULL quando a métrica não vier no `lapDTO`; nunca preencher 0 ou default inventado.
- "Sem dado não é zero" — evita falsa precisão na análise futura.

### Fonte e backfill (assumptions do spec)

- Fonte: Garmin Connect typed splits / lapDTO (Strava não expõe running dynamics por volta de forma confiável).
- Backfill por atividade, sob demanda (CLI), um por um; sem re-pull das listagens de atividades.
- Enriquece splits já existentes no Ritmo (por `activity_id` + `idx`); não rebaixar atividades do zero.

---

## Agent's Discretion

- Nomes exatos das chaves no JSON de retorno do client (garantir consistência com o mapper).
- Detalhes de erro do CLI (mensagem, verbosidade).
- Se o backfill por atividade é um comando separado do CLI de tênis ou uma flag do mesmo.

---

## Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi recusada. As duas áreas cinzentas (métricas e tratamento de ausência) foram resolvidas pelo usuário nesta conversa (aceitou as recomendadas) e estão registradas nas Assumptions do spec com `Confirmed? = y`.

---

## Specific References

- Context.md do feature tenis (Deferred Ideas): "adicionar `get_activity_typed_splits` ao `client.py`, colunas `gct_ms`/`stride_cm`/`vert_osc_cm`/`vert_ratio` na `Split`, backfill por atividade sem re-pull das listagens."
- lapDTO real do garmin_mcp do usuário (mesma lib garminconnect==0.3.2): `groundContactTime`, `strideLength`, `verticalOscillation`, `verticalRatio` existem nos lapDTOs; `map_splits` atual não captura esses campos.
- Padrão de retry/backoff do `app/garmin/client.py::_call` (2/4/8 s, conta no orçamento).

---

## Deferred Ideas

- Feature A (análise comparativa entre tênis): depende deste dado limpo.
- Feature C (alerta de degradação): depende de A.
- UI de running dynamics (tela, gráfico): sem demanda nesta entrega.
