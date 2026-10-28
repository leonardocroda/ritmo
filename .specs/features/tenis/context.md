# Tênis no Ritmo — Context

**Gathered:** 27/10/2026 (conversa de planejamento + pesquisa)
**Spec:** `.specs/features/tenis/spec.md`
**Status:** Ready for design (após confirmação da spec)

---

## Feature Boundary

Quilometragem confiável de tênis no Ritmo com ciclo de vida completo:
estrutura no backend (CRUD + km derivada), backfill one-shot do histórico do
Strava, gestão na UI e modal de atribuição pós-atividade. A análise
comparativa entre tênis (pace, GCT, passada) é outra feature, futura, e
depende deste dado limpo. O usuário nunca integrou com o Strava antes.

---

## Implementation Decisions

### Fonte de dados (decidido pelo usuário)

- Fonte de verdade do uso histórico é o **Strava**. O gear do Garmin Connect
  está stale e **não será importado**.
- O backfill do Strava é **one-shot e aposenta a fonte**: sem sync contínuo,
  sem agendamento, sem persistência de tokens. Tênis futuro = cadastro manual
  na UI.
- Primeiro usuário da integração: "nunca integrei com o Strava, não sei por
  onde começar" — o plano precisa do caminho completo (criar app pessoal em
  `strava.com/settings/api`, escopos `profile:read_all` + `activity:read_all`,
  OAuth manual uma vez, script CLI no padrão do `import_tokens.py`).

### Núcleo vs extra (decidido pelo usuário)

- **Núcleo do backfill**: trazer o histórico dos tênis (nome/marca/km). 
- **Extra**: associação tênis↔treino (qual corrida usou cada tênis). O
  usuário classificou como extra; ficou como P2 da spec, com recomendação do
  agente de fazer na mesma tacada (mesmo matching, mesmo relatório, e
  destrava o baseline histórico da análise futura — "quando era novo").

### Associação atividade Strava ↔ atividade Garmin

- O Strava importa as corridas do Garmin Connect automaticamente; a mesma
  corrida existe nos dois com IDs distintos.
- Ponte: `external_id` do Strava no padrão `garmin_push_<activityId>` →
  extrai o `garmin_id`, a chave natural de dedup que o Ritmo já usa
  (SYNC-11).
- Fallback (sem `external_id`): distância ±2%, moving_time ±2%, mesmo dia
  wall-clock ±5 min. Ambíguo = não casa, reporta. **Nunca inventar
  associação** — corrida Strava sem `gear_id` fica sem tênis.
- Nota de fuso: `start_time` no Ritmo é wall clock local (decisão travada da
  spec de sync), `start_date` do Strava é ISO GMT — por isso o fallback usa
  distância+duração, não horário.

### Quilometragem (decidido pelo usuário + refinamento do agente)

- Km acumulada é sempre **derivada**: `initial_km + Σ distance_m` das
  atividades associadas. Nunca contador solto armazenado.
- Com a decomposição (P2), `initial_km = km_strava_total − Σ(casadas)` —
  absorve o que não foi decomponível (km anterior ao Strava, corridas fora
  da janela de sync do Ritmo, corridas sem gear). O invariante é a km total
  por tênis; o relatório valida com checksum.

### Ciclo de vida

- Sem exclusão; só `status` ativo↔aposentado via PATCH. Reativação é edição
  comum (sem máquina de estados).
- Vida útil (`max_km`) é conveniência visual (barra com marcos 75/90%),
  default 800 na criação manual, editável. A faixa 500–800 km é convenção da
  indústria com evidência científica fraca — copy não vende como verdade.

### Modal de atribuição (decidido pelo usuário)

- Abre ao abrir detalhe de corrida sem tênis — garante que não esquecemos de
  selecionar o modelo. Uma vez por visita; dispensar não marca a atividade.
- Sugestões: padrão por tipo de treino (`infer_type` existe no backend),
  depois último usado; confirmação em um toque; aposentados acessíveis para
  atribuição retroativa.

### Ordem de entrega (decidido pelo usuário)

1. Estrutura no backend (possibilita puxar do Strava)
2. Backfill do histórico do Strava
3. Evolução do cadastro/edição no frontend
4. Pop-up de atribuição
5. (Outra feature) Análise dos dados

---

## Agent's Discretion

- Layout e copy da gestão de tênis (dentro do sistema de design v0.3).
- Mensagens de erro e relatório do script CLI.
- Detalhes do matching fallback (tolerâncias exatas ficam na spec; ajustes
  finos são do Design/Tasks).
- Nome/ícone da seção na UI.

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi recusada. As não discutidas estão registradas na tabela de
Assumptions da spec: onde a gestão vive na navegação (default: Treinos),
decomposição na mesma tacada, esteira no modal, reativação, default 800 km.

---

## Specific References

- Fluxo real dos dados: Garmin Connect → (auto-export) → Strava;
  `external_id = garmin_push_<activityId>` como ponte para o `garmin_id`.
- Strava API v3: `shoes` no `DetailedAthlete` (`GET /athlete`),
  `gear_id` por atividade (`GET /athlete/activities`, `per_page=200`);
  rate limit 100/15 min, 1000/dia; backoff em 429.
- Forerunner 255 grava running dynamics de punho — confirmado na atividade
  24867446401 (GCT 243 ms, passada 120,9 cm, oscilação 9,2 cm) e por split
  em typed splits (`groundContactTime`, `strideLength`,
  `verticalOscillation`, `verticalRatio`, segmentos
  `INTERVAL_WARMUP`/`RWD_RUN`/`RWD_WALK`/`RWD_STAND`). Relevante só para a
  feature futura de análise.
- Rodízio atual real: Adizero SL 2 (293 km), Drive RC (182 km), Grafeno 3
  (235 km), Corre 3 (623 km), Trabuco Terra 2 (22 km, trail), Kayano 30
  (789 km) — números do gear do Garmin, aproximados vs Strava.
- Pesquisa que fundamenta o futuro escopo de análise: Hoogkamer 2018
  (respostas individuais −2,6% a +11%), Van Hooren 2024 (GCT só comparável
  a ritmo pareado), Kong 2009 (degradação muda biomecânica pouco),
  Cornwall 2017 (corredor não percebe degradação), Malisoux (rodízio de 2+
  tênis, −39% lesão), metodologia Run-It (matched runs, fresh vs fatigue,
  comparação por propósito).

---

## Deferred Ideas

- **Feature futura "Análise de tênis"** (já discutida em profundidade):
  - Captura de running dynamics: adicionar `get_activity_typed_splits` ao
    `client.py`, colunas `gct_ms`/`stride_cm`/`vert_osc_cm`/`vert_ratio` na
    `Split`, backfill por atividade sem re-pull das listagens.
  - Perfil por tênis fatiado por tipo de treino e banda de pace (nunca pace
    bruto agregado — confounding de seleção: Adizero → tiro, Kayano →
    rodagem).
  - Comparação pareada (matched runs) com gates de confiança (≥3–5 pares);
    EF (velocidade/FC); GCT/passada ajustados por ritmo via resíduo de
    regressão; HR drift; janela fresco vs fadiga.
  - Alerta de aposentadoria multi-sinal: baseline primeiros ~100 km vs
    últimos ~50 km, sempre ritmo-pareado, gate de mix de tipos; sinais
    ΔGCT/Δoscilação/Δcadência/ΔEF/ΔHR drift/Δ feel-RPE; "sinais, não
    veredito".
  - Teste A/B guiado back-to-back (mesma rota, dois tênis alternados).
- Sync contínuo do Strava, se um dia fizer sentido (hoje: aposentado).
- Notificação ativa de vida útil (badge na Home).
