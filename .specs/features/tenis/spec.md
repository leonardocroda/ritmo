# Tênis no Ritmo (quilometragem + atribuição) — Specification

## Problem Statement

Rodízio real de 6 tênis, dois perto do fim da vida (Kayano ~788/1000 km,
Corre 3 ~623/1000 km). O uso sempre foi registrado no Strava — o gear do
Garmin Connect está stale (corrida de 27/10/2026 sem tênis associado). O
Ritmo não tem estrutura para tênis: sem ela não existe quilometragem
confiável, alerta de vida útil, nem a análise comparativa planejada para o
futuro. A análise foi deliberadamente movida para outra feature: esta entrega
é o dado — histórico importado do Strava e atribuição contínua no Ritmo.

## Goals

- [ ] Quilometragem por tênis derivada de dados (`initial_km` + soma das
      atividades associadas), nunca contador solto — reatribuição retroativa
      recalcula sozinha
- [ ] Histórico importado do Strava via backfill one-shot: após a execução a
      fonte externa se aposenta; tênis futuro nasce por cadastro manual
- [ ] Ciclo de vida completo na UI sem depender do Strava: criar, editar,
      aposentar
- [ ] Dado novo sempre com tênis: modal de atribuição ao abrir corrida sem
      tênis

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| Análise comparativa entre tênis (perfil por tipo de treino, comparação pareada, EF, GCT ajustado por ritmo) | Feature futura separada; depende de dado limpo e da captura de running dynamics |
| Captura de running dynamics (typed splits: GCT/passada/oscilação) | Pré-requisito da análise futura, não da quilometragem |
| Alerta de aposentadoria por degradação (baseline multi-sinal) | Depende da análise futura |
| Sync contínuo do Strava ou qualquer integração viva | Decisão do usuário: backfill one-shot aposenta a fonte |
| Import de gear do Garmin Connect | Gear stale; fonte de verdade do uso é o Strava |
| Exclusão de tênis (DELETE) | Aposentadoria cobre o caso sem quebrar histórico e FKs |
| Notificação ativa de vida útil (badge na Home) | A barra com marcos 75/90% na gestão cobre o MVP; notificação é análise futura |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Fonte de verdade do histórico | Strava; gear do Garmin não é importado | Gear do Garmin está stale; o uso sempre foi registrado no Strava | y |
| Escopo do backfill | One-shot via CLI; sem sync contínuo; token não persistido no banco | Decisão do usuário: após o backfill a fonte externa se aposenta; tênis futuro vem por cadastro manual | y |
| Cálculo da km acumulada | Derivada: `initial_km + Σ distance_m` das atividades associadas | Reatribuição retroativa recalcula sozinha; contador armazenado causa drift | y |
| Ciclo de vida sem exclusão | `status` ativo↔aposentado via PATCH; sem rota de DELETE | Preserva histórico e integridade referencial | y |
| Ordem de entrega | Backend → backfill Strava → UI de gestão → modal de atribuição | Ordem decidida pelo usuário; análise só depois, em outra feature | y |
| Onde a gestão de tênis vive na navegação | Seção dentro de Treinos | Tênis é equipamento de treino; Perfil já concentra configuração (zonas de FC) | y |
| Decomposição histórica na mesma execução do backfill | Sim: mesma tacada, mesmo matching; P2 é separável | Destrava o baseline histórico da análise futura com custo marginal; checksum valida os dois | y |
| Vida útil sugerida na criação manual | `max_km = 800`, editável | Convenção da indústria (500–800 km), evidência científica fraca — por isso editável e informativo | y |
| Modal pergunta em corrida de esteira | Sim, pergunta normalmente | Tênis é tênis; esteira só será isolada na análise futura (pace/elevação) | y |
| Reativação de tênis aposentado | Permitida via edição (transição livre de status) | Sem máquina de estados formal; menor complexidade | y |
| Associação restrita a corridas | Só `running`/`trail_running` recebem `shoe_id` | Yoga/força não usam tênis; validação por `RUNNING_TYPES` | y |

**Open questions:** none — todas as ambiguidades foram resolvidas ou registradas como assumptions acima; as marcadas "n — confirmar" serão confirmadas antes do Design.

---

## User Stories

### P1: Tênis no backend (CRUD + km derivável) ⭐ MVP

**User Story**: Como corredor, quero cadastrar e gerenciar tênis pela API,
com a quilometragem derivada das minhas corridas, para não depender do
Strava a partir de agora.

**Why P1**: Fundação de tudo — o backfill (P1-2), a UI (P1-3) e o modal
(P1-4) escrevem nesta estrutura.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o usuário cria um tênis via `POST /api/shoes` com nome válido THEN o sistema SHALL persistir o tênis com status "ativo" e devolver id e km derivada igual a `initial_km` informado (0 quando ausente).
2. WHEN o usuário lista via `GET /api/shoes` THEN o sistema SHALL devolver cada tênis com km derivada igual a `initial_km + Σ distance_m` das atividades associadas, percentual da vida útil quando `max_km` existe, data do último uso e contagem de corridas.
3. WHEN o usuário edita um tênis via `PATCH /api/shoes/{id}` THEN o sistema SHALL persistir os campos enviados, inclusive a transição de status entre ativo e aposentado.
4. IF a requisição omite o nome, envia `initial_km` negativo ou status fora de {ativo, aposentado} THEN o sistema SHALL responder 422 sem gravar nada.
5. IF um usuário solicita ou edita tênis de outro usuário THEN o sistema SHALL responder 404.
6. The system SHALL oferecer apenas criação, listagem e edição de tênis — nenhuma rota de exclusão.

**Independent Test**: criar tênis via curl, associar uma atividade, listar e conferir a km derivada.

---

### P1: Backfill one-shot do Strava ⭐ MVP

**User Story**: Como corredor que sempre registrou tênis no Strava, quero
trazer esse histórico para o Ritmo numa única execução, para a partir de
agora acumular tudo no Ritmo.

**Why P1**: O dado histórico é o valor imediato da feature (a quilometragem
atual dos 6 tênis). Sem ele, o cadastro manual começa do zero.

**Acceptance Criteria**:

1. WHEN o script de backfill roda com credenciais válidas THEN o sistema SHALL criar ou atualizar cada tênis do Strava via upsert por `strava_gear_id`, gravando nome, marca e modelo, e `initial_km` de modo que a km derivada iguale a distância acumulada reportada pelo Strava na data da execução.
2. WHEN o script roda uma segunda vez THEN o sistema SHALL deixar o estado idêntico: nenhum tênis ou associação duplicada.
3. IF a API do Strava responde 429 ou 5xx THEN o script SHALL aplicar backoff exponencial, repetir a chamada até 3 vezes e, se persistir, abortar com relatório do que foi concluído.
4. IF o token Strava é inválido ou expira durante a execução THEN o script SHALL abortar com estado consistente — nenhum tênis parcialmente importado — e mensagem que explique a renovação.
5. The system SHALL manter tokens do Strava fora do banco de dados — credenciais vêm de env vars e o token vive apenas na memória do script.
6. WHEN o backfill conclui THEN o script SHALL imprimir relatório com tênis criados e atualizados, km importada por tênis, corridas casadas, corridas sem match, corridas sem gear_id e o checksum por tênis.

**Independent Test**: rodar o script contra a conta real, conferir os 6 tênis no banco com a km do Strava, rodar de novo e conferir que nada mudou.

---

### P1: Gestão de tênis na UI ⭐ MVP

**User Story**: Como corredor, quero ver e gerenciar meus tênis na UI, com
barra de vida útil, para saber a qualquer momento qual tênis está perto do
fim.

**Why P1**: Sem UI o ciclo de vida (cadastrar tênis novo, aposentar velho)
depende de curl — a feature não fecha o ciclo sem ela.

**Acceptance Criteria**:

1. WHEN o usuário abre a gestão de tênis THEN a UI SHALL exibir cada tênis com nome, marca/modelo, km atual versus `max_km` em barra de vida útil com marcos em 75% e 90%, status, último uso e contagem de corridas.
2. WHEN o usuário cria ou edita um tênis THEN a UI SHALL oferecer nome, marca, modelo, data de aquisição, km inicial, vida útil estimada e status, sugerindo `max_km = 800` na criação manual.
3. WHEN o usuário aposenta um tênis THEN a UI SHALL pedir confirmação explícita e, após confirmar, manter o tênis listável com a km derivada intacta e fora das sugestões de novas atribuições.
4. WHEN não existe nenhum tênis cadastrado THEN a UI SHALL exibir estado vazio com atalho para o cadastro manual.

**Independent Test**: abrir a gestão, editar o nome de um tênis importado, aposentar outro e conferir a barra de vida.

---

### P1: Modal de atribuição por atividade ⭐ MVP

**User Story**: Como corredor, quero ser lembrado de marcar o tênis quando
abro uma corrida sem tênis, para o dado novo nunca ficar incompleto.

**Why P1**: O dado novo é o que sustenta a análise futura; sem o gatilho, o
hábito de registrar migra pro limbo.

**Acceptance Criteria**:

1. WHEN o usuário abre o detalhe de uma corrida (`running`/`trail_running`) sem tênis THEN a UI SHALL perguntar qual tênis foi usado, no máximo uma vez por visita à tela.
2. WHEN o modal é exibido THEN a UI SHALL ordenar as sugestões pelo padrão do tipo de treino inferido e, sem padrão definido, pelo último tênis usado, permitindo confirmação em um toque.
3. WHEN o usuário marca um tênis como padrão para um tipo de treino THEN a UI SHALL priorizar esse tênis nas próximas sugestões do mesmo tipo.
4. IF o usuário dispensa o modal THEN a atividade SHALL permanecer sem tênis e o modal não reabrir na mesma visita.
5. WHEN o usuário escolhe um tênis THEN o sistema SHALL associar via `PATCH /api/activities/{id}/shoe`, validando que o tênis pertence ao usuário da sessão — caso contrário 404.
6. IF a atividade não é `running` nem `trail_running` THEN o sistema SHALL responder 422 e não gravar `shoe_id`.

**Independent Test**: abrir uma corrida sem tênis, confirmar a sugestão, reabrir o detalhe e não ver o modal de novo.

---

### P2: Decomposição histórica (associação tênis↔treino)

**User Story**: Como corredor, quero que o backfill também reconstrua qual
treino usou cada tênis, para a análise futura ter baseline histórico.

**Why P2**: É o extra sobre o núcleo (snapshot). Confirmado: roda na mesma
execução do backfill — o núcleo não depende dela, e permanece separável para
proteger o delivery se o matching precisar de ajuste fino.

**Acceptance Criteria**:

1. WHEN uma corrida do Strava com `gear_id` casa com uma atividade do Ritmo pelo `external_id` (padrão `garmin_push_<activityId>`) THEN o script SHALL associar o tênis retroativamente e ajustar `initial_km` preservando a km total do tênis.
2. WHEN o `external_id` está ausente THEN o script SHALL casar por fallback: distância com tolerância de 2%, moving_time com tolerância de 2% e mesmo dia wall-clock com janela de 5 minutos.
3. IF o casamento é ambíguo — mais de uma corrida candidata com os mesmos critérios THEN o script SHALL deixar a atividade sem tênis e listá-la no relatório.
4. IF a corrida do Strava não tem `gear_id` THEN o script SHALL deixá-la sem tênis e reportá-la como km não alocada.
5. WHEN a decomposição conclui THEN o relatório SHALL apresentar o checksum por tênis: `initial_km + km das corridas casadas + km não alocada` igual à distância total do Strava.

**Independent Test**: rodar o backfill, abrir a gestão de tênis e conferir contagem de corridas e último uso preenchidos para cada tênis.

---

### P3: Higiene do dado (badge de cobertura)

**User Story**: Como corredor, quero ver o percentual de corridas com tênis
nos últimos 30 dias, para saber se estou mantendo o hábito.

**Why P3**: Útil, mas não muda o resultado sem hábito formado.

**Acceptance Criteria**:

1. WHEN o usuário consulta a gestão de tênis THEN a UI SHALL exibir o percentual de corridas com tênis associado nos últimos 30 dias.

---

## Edge Cases

Edge cases are usually unwanted-behavior (IF/THEN) or boundary (WHEN) criteria:

- WHEN o Strava retorna atividades de outras modalidades (Hike, Walk) THEN o script SHALL ignorá-las — filtra `type == "Run"`.
- WHEN o Strava reporta tênis com distância 0 THEN o sistema SHALL importá-lo normalmente com km derivada 0.
- WHEN a corrida é de esteira (sem splits) THEN o modal de atribuição SHALL perguntar normalmente — tênis é tênis.
- IF duas corridas do mesmo dia têm distância e duração idênticas THEN o fallback SHALL considerá-las ambíguas e não casar nenhuma (P2 AC3).
- IF o `strava_gear_id` já existe no Ritmo THEN o backfill SHALL atualizar o tênis existente em vez de criar outro (upsert, AC de idempotência).

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------- |
| TEN-01 | P1: Backend (criação) | Design | Pending |
| TEN-02 | P1: Backend (km derivada na listagem) | Design | Pending |
| TEN-03 | P1: Backend (edição/status) | Design | Pending |
| TEN-04 | P1: Backend (validação 422) | Design | Pending |
| TEN-05 | P1: Backend (isolamento 404) | Design | Pending |
| TEN-06 | P1: Backend (sem exclusão) | Design | Pending |
| TEN-07 | P1: Backfill (upsert + snapshot) | Design | Pending |
| TEN-08 | P1: Backfill (idempotência) | Design | Pending |
| TEN-09 | P1: Backfill (429/5xx backoff) | Design | Pending |
| TEN-10 | P1: Backfill (token inválido/expirado) | Design | Pending |
| TEN-11 | P1: Backfill (token fora do banco) | Design | Pending |
| TEN-12 | P1: Backfill (relatório final) | Design | Pending |
| TEN-13 | P1: UI (lista + barra de vida) | Design | Pending |
| TEN-14 | P1: UI (criar/editar, default 800) | Design | Pending |
| TEN-15 | P1: UI (aposentar com confirmação) | Design | Pending |
| TEN-16 | P1: UI (estado vazio) | Design | Pending |
| TEN-17 | P1: Modal (gatilho na abertura) | Design | Pending |
| TEN-18 | P1: Modal (sugestões ordenadas) | Design | Pending |
| TEN-19 | P1: Modal (padrão por tipo) | Design | Pending |
| TEN-20 | P1: Modal (dispensa/snooze) | Design | Pending |
| TEN-21 | P1: Modal (associação + posse) | Design | Pending |
| TEN-22 | P1: Modal (tipo de atividade 422) | Design | Pending |
| TEN-23 | P2: Decomposição (external_id) | Design | Pending |
| TEN-24 | P2: Decomposição (fallback) | Design | Pending |
| TEN-25 | P2: Decomposição (ambiguidade) | Design | Pending |
| TEN-26 | P2: Decomposição (sem gear_id) | Design | Pending |
| TEN-27 | P2: Decomposição (checksum) | Design | Pending |
| TEN-28 | P3: Higiene (badge 30 dias) | - | Pending |

**ID format:** `TEN-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 28 total, 0 mapped to tasks (fase Tasks pendente), 0 unmapped

---

## Success Criteria

How we know the feature is successful:

- [ ] Km derivada de cada tênis importado igual à distância do Strava (checksum ±0,1 km)
- [ ] Re-executar o backfill não altera o estado do banco (idempotente)
- [ ] Usuário cadastra, edita e aposenta tênis pela UI sem tocar no Strava
- [ ] Nenhuma atividade não-corrida recebe tênis
- [ ] ≥ 90% das corridas dos últimos 30 dias com tênis associado (medido 30 dias após o modal entrar em uso)
