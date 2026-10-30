# Análise de tênis — UI frontend Specification

## Problem Statement

O backend já expõe análise comparativa e alerta de degradação por tênis, mas o usuário não consegue visualizar esses dados. A comparação pareada e os sinais de degradação permanecem invisíveis no frontend, impedindo decisões baseadas em dados.

## Goals

- [ ] Exibir perfil por tênis fatiado por tipo de treino × banda de pace
- [ ] Permitir comparação pareada entre dois tênis com confiança e tabela de pares
- [ ] Exibir métricas derivadas e sinais de degradação por tênis
- [ ] Manter padrão PanelState e tema escuro

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Re-criar gestão de tênis (cadastro, editar, aposentar) | Já existe em ShoesSection |
| Gráficos avançados com canvas/SVG custom | MVP texto/tabela; gráficos opcionais futuro |
| Persistência de favoritos/comparações | Não solicitado |
| Exportação de relatório | Fora do escopo MVP |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Localização da UI | Seção abaixo de ShoesSection na página Equipamentos | Página já dedicada a tênis e acessível ao usuário | y |
| Tipos de dados | Endpoints backend retornam estruturas conforme spec A e C | Backend já validado, apenas consumo | y |
| Formatação de pace/km | Reusar lib/format existente | Consistência com app | y |
| Autenticação | Herda do layout App Router existente | Não criar nova lógica de auth | y |

**Open questions:** none

---

## User Stories

### P1: Perfil por tênis com tipo × banda ⭐ MVP

**User Story**: Como corredor, quero ver o perfil de cada tênis com agrupamento por tipo de treino e banda de pace, para entender onde cada tênis performou melhor.

**Why P1**: É a porta de entrada para análise.

**Acceptance Criteria** (EARS):

1. WHEN o usuário abre a página Equipamentos THEN o sistema SHALL exibir lista de tênis com nome, status e cartões de perfil resumido.
2. WHEN um tênis é selecionado THEN o sistema SHALL exibir total de corridas, km total e grupos tipo × banda com pace médio e FC média.
3. IF não houver dados de análise para um tênis THEN o sistema SHALL exibir mensagem de dados insuficientes.

**Independent Test**: abrir página com tênis com dados e confirmar cartões de perfil.

---

### P1: Comparação pareada entre dois tênis ⭐ MVP

**User Story**: Como corredor, quero comparar dois tênis em corridas equivalentes para ver diferenças em pace e FC.

**Why P1**: Núcleo da análise.

**Acceptance Criteria** (EARS):

1. WHEN o usuário seleciona dois tênis THEN o sistema SHALL chamar GET /api/tenis/analysis/compare e exibir número de pares, nível de confiança e tabela.
2. WHEN a comparação tem pares THEN o sistema SHALL exibir para cada par distância, pace A, pace B, Δ pace, FC A, FC B, Δ FC.
3. IF houver menos de 3 pares THEN o sistema SHALL exibir confiança "baixo"; 3-5 "médio"; >5 "alto".
4. IF não houver pares válidos THEN o sistema SHALL exibir estado vazio explicativo.

**Independent Test**: selecionar dois tênis com pares e verificar tabela e confiança.

---

### P1: Detalhe de tênis com métricas derivadas ⭐ MVP

**User Story**: Como corredor, quero ver métricas derivadas do tênis quando disponíveis.

**Why P1**: Complementa o perfil.

**Acceptance Criteria** (EARS):

1. WHEN o usuário abre detalhe de tênis THEN o sistema SHALL fazer GET /api/tenis/analysis/shoes/{id} e exibir blocos de running dynamics ajustados, EF, HR drift e janela fresco vs fadiga SE presentes.
2. WHILE dados faltam para um bloco THEN o sistema SHALL omitir o bloco, sem exibir zero.
3. The system SHALL formatar valores usando lib/format.

**Independent Test**: tênis com e sem dados, confirmar presença/ausência de blocos.

---

### P2: Alerta de degradação por tênis

**User Story**: Como corredor, quero visualizar sinais de degradação por tênis para decidir momento de rodízio.

**Why P2**: Valor agregado de análise.

**Acceptance Criteria** (EARS):

1. WHEN o usuário consulta degradação de um tênis com ≥150 km THEN o sistema SHALL exibir baseline (primeiros ~100 km vs últimos ~50 km) e lista de sinais com inicial/final/delta/direção.
2. IF o tênis tem <150 km THEN o sistema SHALL exibir aviso de dados insuficientes e ocultar sinais.
3. IF um sinal não tem dado THEN o sistema SHALL omitir o sinal.
4. The system SHALL NUNCA exibir veredicto de aposentadoria, apenas sinais e confiança.

**Independent Test**: tênis com 200 km, verificar baseline e sinais; tênis com 100 km, verificar aviso.

---

## Edge Cases

- IF erro de API THEN o sistema SHALL exibir mensagem amigável sem quebrar layout.
- WHEN usuário trocar seleção rapidamente THEN a UI SHALL cancelar/ignorar resposta antiga (stale request guard).
- IF nome do tênis é vazio THEN exibir fallback "Tênis sem nome".

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| TUI-01 | P1: Perfil | Design | Verified |
| TUI-02 | P1: Perfil | Design | Verified |
| TUI-03 | P1: Perfil | Design | Verified |
| TUI-04 | P1: Comparação | Design | Verified |
| TUI-05 | P1: Comparação | Design | Verified |
| TUI-06 | P1: Comparação | Design | Verified |
| TUI-07 | P1: Detalhe | Design | Verified |
| TUI-08 | P1: Detalhe | Design | Verified |
| TUI-09 | P2: Degradação | Design | Verified |
| TUI-10 | P2: Degradação | Design | Verified |
| TUI-11 | P2: Degradação | Design | Verified |
| TUI-12 | P2: Degradação | Design | Verified |
| TUI-13 | Edge Cases | Design | Verified |

**ID format:** `TUI-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 13 total, 13 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Perfil por tênis exibido com grupos tipo × banda
- [ ] Comparação pareada exibe confiança e tabela de pares
- [ ] Detalhe de tênis exibe métricas derivadas omitindo blocos vazios
- [ ] Degradação exibe baseline e sinais, com aviso de dados insuficientes
- [ ] Sem veredicto de aposentadoria

