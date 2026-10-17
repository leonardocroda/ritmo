# Janela de tempo do Painel Saúde — Especificação

> Promoção do item "Seleção de janela na UI" (Out of Scope do health-panel) a feature: seletor fixo de janelas 7d · 30d · 42d · 60d · 90d aplicado a todas as seções do `/saude`, sobre o contrato `days` que o backend já entrega (HLT-02/03)

## Problem Statement

O painel Saúde fixa 60 dias na UI (`HealthPanel` chama `getHealthSummary()` sem expor a janela), mas o contrato já aceita `days` 7–365. O usuário quer inspecionar escalas diferentes: a semana aguda (7d — ATL/WHOOP W), o mês (30d), a janela de fitness do TrainingPeaks (42d — constante do CTL/Coggan), o default atual ancorado na banda de HRV (60d — AD-010) e uma visão longa (90d — padrão de dashboards de saúde). Hoje isso exige chamada manual à API — a UI precisa do controle.

## Goals

- [ ] Grupo fixo de botões 7d, 30d, 42d, 60d e 90d no `/saude`, ativa destacada, default 60d
- [ ] Troca de janela refaz a busca e re-renderiza **todas** as seções com os dados da nova janela
- [ ] Derivados da janela recalculam honestamente (baseline RHR, média de estresse, % abaixo do piso, dose-resposta, yoga/semanas) — nenhum número da janela antiga permanece

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| -------- | ------ |
| Janela livre (input de dias arbitrário) | Conjunto fixo por decisão do usuário (17/10/2026); os 5 botões cobrem as âncoras pesquisadas |
| Mudar a matemática da banda de HRV | AD-010: banda = janela móvel de 60 dias (ciência Altini, não exibição) — a janela exibida não mexe na régua |
| Recalcular CTL/ATL/TSB/ACWR por janela | CLR-06: valores pré-computados no sync (EMA 42/7 fixa); a janela só muda quantos dias da curva aparecem |
| Seletor de janela em outros painéis | Potencial/Treinos/Hoje não têm série multi-janela; escopo é o `/saude` |
| Backend | Contrato `days` 7–365 já validado (HLT-02/03); zero mudança de servidor |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Conjunto de botões | 7d · 30d · 42d · 60d · 90d (ordem crescente) | Âncoras: semana aguda (ATL, WHOOP W, média 7d Garmin), mês (WHOOP M/Health Report), fitness (CTL 42d — TrainingPeaks/Coggan, ~6 semanas de adaptação), default atual + banda HRV (Altini 60d), visão longa (padrão 90d em dashboards Oura/WHOOP) | y |
| Janela padrão | 60d | Preserva o comportamento atual e conversa com a banda de HRV (AD-010) | y |
| Comportamento durante a nova busca | Dados anteriores continuam visíveis + indicador "atualizando…" | Full-panel flash a cada clique é hostil; padrão de resposta velha descartada por seq (WorkoutsList) | n |
| Falha na troca com dados na tela | Mantém dados anteriores + erro inline junto ao filtro | Perder o painel inteiro por um erro de refetch seria pior que a troca; a UI nunca fica branca | n |
| Seletor visível | Somente com painel pronto (estado ready) | Sem dados não há o que janelar; loading/erro/vazio seguem os fluxos existentes | n |
| Rótulo do botão | `7d`..`90d` (número + sufixo) | Compacto em 390px; 42d é o número que o mercado associa ao CTL, não "6s" | n |
| Paginação da tabela de HRV na troca | Reseta para a primeira página (`key` pela janela) | Página 3 de 60d pode não existir em 7d — remount é o reset mais simples | n |

**Open questions:** none — as duas decisões de gosto (conjunto e default) foram confirmadas com o usuário (17/10/2026); o resto segue os defaults acima.

---

## User Stories

### P1: Seletor de janela do painel ⭐ MVP

**User Story**: Como corredor, quero trocar a janela de tempo do painel Saúde (7d, 30d, 42d, 60d, 90d), para inspecionar a semana aguda, o mês, o bloco de fitness e a visão longa sem sair da tela.

**Why P1**: A janela fixa de 60d esconde as escalas que importam: 7d mostra o impacto agudo, 42d é a janela de fitness que o TrainingPeaks consagra — o dado já está no contrato, falta o controle.

**Acceptance Criteria**:

1. WHEN o painel está pronto THEN a UI SHALL exibir o grupo fixo de botões `7d`, `30d`, `42d`, `60d`, `90d` com a janela ativa destacada — `60d` no primeiro carregamento. <!-- event-driven -->
2. WHEN o usuário clica um botão de janela THEN a UI SHALL buscar `/api/health/summary?days=N` e re-renderizar todas as seções (sono, carga, recuperação, dose-resposta, equilíbrio) com os dados da nova janela. <!-- event-driven -->
3. WHEN a janela muda THEN os derivados de janela SHALL refletir a nova janela: baseline do RHR, média de estresse, % de noites abaixo do piso, buckets do dose-resposta e sessões/média de yoga — nenhum número da janela anterior permanece. <!-- event-driven -->
4. WHILE a busca da nova janela está em curso THEN a UI SHALL manter os dados da janela anterior visíveis com um indicador de atualização. <!-- state-driven -->
5. IF o usuário troca de janela enquanto uma busca anterior ainda está em curso THEN a UI SHALL descartar as respostas velhas e aplicar somente a resposta do último clique. <!-- unwanted-behavior -->
6. IF a busca da nova janela falha THEN a UI SHALL manter os dados anteriores visíveis e exibir a mensagem de erro inline junto ao filtro, sem quebrar a navegação. <!-- unwanted-behavior -->
7. WHEN a janela muda THEN a paginação da tabela de HRV SHALL resetar para a primeira página. <!-- event-driven -->
8. WHEN a janela muda THEN o subtítulo da seção Carga de treino SHALL refletir a janela ativa ("A curva de N dias…" — nunca o 60 fixo). <!-- event-driven -->
9. The system SHALL exibir CTL/ATL/TSB/ACWR exatamente como pré-computados no sync — a janela muda quantos dias da curva aparecem, nunca os valores (CLR-06). <!-- ubiquitous -->
10. The system SHALL manter a banda normal de HRV calculada sobre a janela de baseline de 60 dias (AD-010) em qualquer janela exibida. <!-- ubiquitous -->

**Independent Test**: Abrir `/saude` → `60d` ativo; clicar `7d` → todas as séries com ~7 pontos, dose-resposta reduzido, "—" onde vazio; clicar `90d` → séries longas; voltar a `60d`. Cliques rápidos encadeados não deixam dados de janela errada na tela.

---

### P2: Estados honestos nas janelas curtas ⭐ MVP

**User Story**: Como corredor, quero que janelas curtas mostrem o que existe sem inventar número, para confiar no painel em qualquer janela.

**Why P2**: A janela de 7d naturalmente esvazia derivados (dose-resposta pode ficar sem bucket, weekday com 1 noite/dia) — o painel já tem o vocabulário de estado vazio; a spec prende o comportamento.

**Acceptance Criteria**:

1. WHEN a janela exibida deixa um bucket do dose-resposta sem noites THEN a UI SHALL exibir "—" nas médias daquele bucket (padrão HLT-22 — nenhum número inventado). <!-- event-driven -->
2. WHEN o histórico é menor que a janela pedida THEN as séries SHALL exibir tudo que existe (janela pedida, não inventada — edge do health-panel). <!-- event-driven -->
3. WHEN o painel renderiza em 390px THEN o grupo de botões SHALL permanecer legível em uma linha, sem scroll horizontal (padrão dos painéis anteriores). <!-- event-driven -->

**Independent Test**: `7d` com dados reais → buckets "—" quando vazios; `90d` com 62 noites de histórico → série com as noites existentes; viewport 390px sem scroll horizontal.

---

## Edge Cases

- IF a troca de janela acontece em sequência rápida (respostas fora de ordem) THEN só a última resposta aplica (seq — padrão WorkoutsList); a resposta da janela anterior é descartada.
- IF a falha ocorre na **primeira** carga (sem dados anteriores) THEN o fluxo de erro existente se mantém (mensagem inline no lugar do painel).
- IF a janela 7d reduz a tabela de HRV a ≤7 noites THEN a paginação some sozinha (`totalPages <= 1`) — reset via key já cobre a volta.
- IF o bloco é `null` na nova janela (ex.: estresse sem `avg`) THEN o estado vazio próprio do bloco aparece — a troca não inventa dado onde não há.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| HWF-01 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-02 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-03 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-04 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-05 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-06 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-07 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-08 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-09 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-10 | P1: Seletor de janela do painel | Execute | Verified |
| HWF-11 | P2: Estados honestos nas janelas curtas | Execute | Verified |
| HWF-12 | P2: Estados honestos nas janelas curtas | Execute | Verified |
| HWF-13 | P2: Estados honestos nas janelas curtas | Execute | Verified |

**Coverage:** 13 total, 13 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] `/saude` abre com `60d` ativo; cada botão troca todas as seções com os dados da janela escolhida (derivados acompanham: baseline RHR e média de estresse mudam entre janelas)
- [ ] Troca não pisca o painel: dados antigos ficam visíveis com "atualizando…" até a resposta nova chegar; cliques rápidos nunca deixam janela errada na tela
- [ ] `7d` mostra os vazios com honestidade ("—" nos buckets sem noite), `42d` exibe a curva de fitness, `90d` mostra o histórico existente
- [ ] `npm run build` + `npm run lint` verdes; suite do backend intocada (zero mudança de servidor)
- [ ] UAT em 390px: seletor em uma linha, sem scroll horizontal
