# Design system v0.3 — fundação visual — Especificação

> Materializa a identidade visual v0.3 — aprovada em 22/10/2026, referência canônica em `docs/design/identidade-visual-v0.3.html` (registrada como AD-022) — como fundação de código: tokens de cor/forma, tipografia com assinatura, tema de gráfico compartilhado e tab bar inferior. Re-pela as superfícies existentes sem tocar contratos, dados ou composição; as features que a consomem (Home, retrofit de composição dos painéis) seguem em specs próprias.

## Problem Statement

O frontend é hoje a soma dos defaults da stack: paleta zinc+lime-400 (5 tokens em `globals.css`), Geist (a fonte default de todo app Next), Recharts cru — 11 componentes de gráfico com hex local (`#3f3f46`, `#38bdf8`, `#f87171`, `#a3e635`) — e navegação em pills no header. O resultado é funcional, mas genérico ("cara de dashboard") e sem assinatura visual — e o produto já decidiu migrar de "métricas pra especialista" para "decisão diária pra corredor comum", o que exige uma identidade reconhecível no primeiro olhar. A identidade v0.3 existe e foi aprovada; falta materializá-la como fundação única antes das features que a consomem.

## Goals

- [ ] Paleta v0.3 em tokens únicos mapeados ao tema Tailwind — re-pele 100% das superfícies num único swap
- [ ] Instrument Sans (400–700) via next/font + números tabulares em todo dado exibido
- [ ] Tema de gráfico centralizado ("contexto em neutro, um único destaque lime") aplicado aos 11 gráficos existentes
- [ ] Tab bar inferior: Treinos · Saúde · Performance · Perfil (navegação de polegar, app feel)
- [ ] Zero mudança de comportamento: contratos de API, dados e copy permanecem os mesmos

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| ------- | ------ |
| Home / card-veredito / quick-log de hábitos | Spec própria (supersede AD-011) — esta feature entrega só a fundação que a Home consome |
| Retrofit de composição/copy dos painéis (caption compacto etc.) | O swap de tokens já re-pela visualmente; mudança de composição é por painel, spec própria |
| Cores das zonas VDOT | Mantidas intactas — regra de coexistência v0.3: zonas vivem só em contexto de treino |
| Tema claro | Tema escuro permanente (plano) |
| Logotipo/wordmark definitivo de marca | v0.3 declara-se direção provisória; só o glyph de pulso mínimo entra (P3) |
| Novos estados vazios | CLR-11 e congêneres continuam — herdam a pele nova via tokens |
| Backend / banco | 100% frontend — zero mudança de servidor |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica implicitamente incerto.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Fonte de interface | Instrument Sans 400–700 via `next/font/google` (`display: swap`); Geist Mono permanece para mono | O mock v0.3 aprovado usa Instrument Sans; Geist é exatamente a default que se quer trocar | y (aprovação visual 22/10) |
| Compatibilidade de classes | Tokens atuais (`--background`, `--accent`, `--card`, `--muted`, `--foreground`) continuam existindo como aliases com valores v0.3 | Os 100+ usos de `bg-card`/`text-muted`/`accent` seguem funcionando sem refactor |
| Tab bar começa com 4 itens | Treinos · Saúde · Performance · Perfil — o "Hoje" entra com a spec da Home | Não existe destino `/hoje` ainda; tab fantasma quebraria o princípio "a Home roteia" |
| Perfil na tab bar | `/perfil` vira 4ª tab; o link de nome sai do header (fica wordmark + sync + menu Sair) | Navegação única ao alcance do polegar; o topo vira conteúdo (v0.3 §06) |
| Tema aplicado a TODOS os gráficos agora | Os 11 componentes migram ao módulo central nesta feature | Consistência imediata; mudança é de estilo, não de dado — risco baixo |
| SplitsChart | Mantém cores de zona VDOT; ganha só eixo/caption/tooltip do tema | Regra de coexistência v0.3 + AD-009 |
| Semânticas de saúde | `--good`/`--attention`/`--alert` definidos agora, consumidos pela Home depois | Barato agora; evita reabrir o arquivo na feature da Home |
| Raio | Cartão 16px, controle 12px, pill 999px | v0.3: "uma resposta por pergunta" |
| Tab bar em telas largas | Permanece inferior em qualquer largura, alinhada ao conteúdo (max-w) | App-like consistente; desktop não é o público-alvo do MVP |

**Open questions:** none — as decisões de gosto (fonte, identidade) foram confirmadas pela aprovação do mock v0.3 (22/10/2026); o resto segue os defaults acima, passíveis de veto na confirmação desta spec.

---

## User Stories

### P1: Tokens v0.3 em código ⭐ MVP

**User Story**: Como desenvolvedor, quero a paleta e a forma v0.3 em tokens únicos mapeados ao tema Tailwind, para que toda a plataforma re-pele de uma vez e nenhuma cor viva fora dos tokens.

**Why P1**: O swap de tokens é o maior ganho visual pelo menor custo — toda a superfície existente muda de pele num commit, e é o pré-requisito de tudo o que segue (tema de gráfico, tab bar, Home).

**Acceptance Criteria**:

1. WHEN qualquer superfície do app renderiza THEN the system SHALL usar somente os tokens v0.3 definidos em `globals.css` e mapeados no `@theme inline`: `--night #0B0F12`, `--surface #121815`, `--raised #1B241A`, `--deep #273323`, `--border #354039`, `--border-hover #4A574E`, `--lime #B7F36B`, `--on-lime #182014`, `--text #F5F7F2`, `--muted #A1AAA9` — incluindo o `themeColor` do viewport (`#0B0F12`). <!-- event-driven -->
2. The system SHALL manter os nomes de token existentes (`--background`, `--foreground`, `--accent`, `--muted`, `--card`) como aliases com valores v0.3, sem quebrar nenhum componente existente. <!-- ubiquitous -->
3. The system SHALL expor os tokens semânticos de saúde `--good #B7F36B`, `--attention #E9B44C` e `--alert #EF6757` no tema, prontos para consumo pela Home. <!-- ubiquitous -->
4. WHEN um elemento interativo (botão, pill, link, tab) recebe hover ou focus THEN the system SHALL usar `--border-hover #4A574E` na borda — a borda default `#354039` (contraste 1,8:1) nunca é o único sinal de interatividade. <!-- event-driven -->
5. The system SHALL aplicar a escala de raio v0.3 — cartão 16px, controle 12px, pill 999px — em todos os cartões e controles existentes. <!-- ubiquitous -->
6. The system SHALL concentrar todas as cores de componente nos tokens/módulo de tema — verificação por grep: nenhum hex fora do módulo central em `src/components`. <!-- ubiquitous -->

**Independent Test**: `npm run dev` → todas as telas na paleta nova (fundo `#0B0F12`, cartões `#121815`, accent lime `#B7F36B`); `grep -rE "#[0-9a-fA-F]{6}" src/components` retorna apenas o módulo do tema.

---

### P1: Tipografia com assinatura + números tabulares ⭐ MVP

**User Story**: Como usuário, quero uma fonte com personalidade e números que não dançam ao atualizar, para que o app pareça desenhado de propósito e os valores sejam legíveis em qualquer mudança.

**Why P1**: Geist é a default de todo app Next.js — zero assinatura; e valores numéricos sem tabular-nums pulsam a cada refresh. É o upgrade visual mais barato disponível.

**Acceptance Criteria**:

7. WHEN o app carrega THEN the system SHALL renderizar o texto em Instrument Sans (pesos 400–700, via `next/font/google` com `display: swap`) com stack de fallback de sistema. <!-- event-driven -->
8. The system SHALL manter Geist Mono como fonte mono para valores técnicos/código, sem mudança de uso. <!-- ubiquitous -->
9. WHEN um número de dado é exibido (eixo de gráfico, tabela, valor em destaque) THEN the system SHALL usar números tabulares (`font-variant-numeric: tabular-nums` — utilitário do tema ou classe `tabular-nums`). <!-- event-driven -->
10. IF a fonte remota não carregar (offline/LAN sem internet) THEN the system SHALL cair na stack de fallback sem bloquear a renderização (swap, nunca bloqueio de layout). <!-- unwanted-behavior -->

**Independent Test**: computed style do body = Instrument Sans; tabela de HRV com colunas alinhadas dígito a dígito; devtools offline (sem rede) → app renderiza com fallback.

---

### P1: Tema de gráfico compartilhado ("neutro + um destaque") ⭐ MVP

**User Story**: Como usuário, quero todos os gráficos na mesma linguagem visual, para que a plataforma pareça desenhada de propósito, não colada por feature.

**Why P1**: 11 componentes com hex local é a maior fonte do "cara de dashboard" — Recharts cru é o rosto genérico. O tema central é a assinatura mais repetida da plataforma (AD-008 mantém Recharts como renderer).

**Acceptance Criteria**:

11. The system SHALL centralizar o tema de gráfico — cores de série do conjunto semântico (lime/âmbar/coral/neutro), eixo e linha de base `#354039`, tick 9–10px muted, tooltip como cartão surface raio 12 com borda `#354039` — em um único módulo importável (e.g. `src/lib/chartTheme.ts`). <!-- ubiquitous -->
12. WHEN um gráfico Recharts renderiza THEN the system SHALL desenhar apenas a linha de base horizontal como guia (hairline `#354039`) — sem grid vertical e sem CartesianGrid cheio. <!-- event-driven -->
13. WHERE um gráfico tem ponto ou segmento "hoje/último" destacável THEN the system SHALL destacá-lo em lime, com o resto do contexto em neutro. <!-- optional-feature -->
14. WHEN um gráfico de série única renderiza THEN a série SHALL usar lime como cor de sujeito, com área em gradiente lime→transparente quando o tipo de gráfico suportar área. <!-- event-driven -->
15. The system SHALL aplicar o tema aos 11 componentes de gráfico existentes (Sleep, SleepStages, Rem, Hrv, Rhr, Stress, WeekdayPattern, Pmc, Vo2maxTrend, VdotTimeline, Splits) — zero hex local após a migração. <!-- ubiquitous -->
16. The system SHALL manter as cores das zonas VDOT (verde/azul/laranja/vermelho/roxo) no SplitsChart e superfícies de treino, servidas pelo módulo central com a regra de coexistência documentada (zonas nunca fora de contexto de treino; lime da marca ≠ verde-easy de zona). <!-- ubiquitous -->

**Independent Test**: abrir `/saude` e `/performance` — todos os gráficos com uma única linha de base, ticks 9–10px, tooltip cartão raio 12, séries no conjunto semântico e "hoje"/último ponto em lime onde existe; SplitsChart com as zonas VDOT intactas.

---

### P2: Tab bar inferior (app shell)

**User Story**: Como usuário no celular, quero navegar pelos painéis com o polegar numa tab bar inferior, para que o app pareça app — não site.

**Why P2**: É o sinal nº1 de "isso é um app" num web app mobile-first 390px (v0.3 §06); não bloqueia as P1 (pode entrar no mesmo ciclo de implementação logo após).

**Acceptance Criteria**:

17. WHEN qualquer painel abre THEN the system SHALL exibir uma tab bar inferior fixa com 4 itens (Treinos, Saúde, Performance, Perfil) — ícone line 22px + label 10px, item ativo em lime com pill lime/12% (continuidade do padrão da nav atual). <!-- event-driven -->
18. WHILE uma tab está ativa THEN o item SHALL ter alvo de toque ≥44px e marcação `aria-current="page"` (padrão da `Nav` atual — `activePanel` por `startsWith`). <!-- state-driven -->
19. WHEN a tela tem 390px de largura THEN as 4 tabs SHALL caber sem scroll horizontal. <!-- event-driven -->
20. WHEN `/perfil` é alcançado pela tab bar THEN o header SHALL reter apenas wordmark + sync + menu do usuário (Sair) — o link de nome sai do header. <!-- event-driven -->
21. The system SHALL adicionar 18px de respiro inferior fixo abaixo da tab bar (safe-area em telas que expõem inset). <!-- ubiquitous -->

**Independent Test**: navegar pelos 4 destinos em 390px; ativo com pill lime em cada painel; `/perfil` alcançável pelo polegar; sem scroll horizontal.

---

### P2: Skeletons na linguagem

**User Story**: Como usuário, quero carregamento com skeleton discreto pulsando no neutro, para que até a espera faça parte da identidade.

**Why P2**: Spinners e "Carregando…" texto são o oposto do app feel; o padrão existe no v0.3 e é mecânico de aplicar nos pontos de loading existentes.

**Acceptance Criteria**:

22. WHEN um painel carrega dados THEN the system SHALL exibir skeleton na linguagem v0.3 (blocos neutros pulsando ~1,6s, sem spinner) no lugar do texto de carregamento atual. <!-- event-driven -->
23. IF o carregamento falha THEN o estado de erro existente SHALL permanecer inalterado — o skeleton não muda o contrato de erro dos painéis. <!-- unwanted-behavior -->

**Independent Test**: throttling de rede no devtools → painéis mostram skeleton pulsando; matar a API → mensagem de erro atual intacta.

---

### P3: Wordmark + pulso

**User Story**: Como usuário, quero o wordmark "ritmo" com o pulso de HRV, para que a marca comece a ficar reconhecível até antes do logotipo definitivo.

**Why P3**: Toque mínimo de marca com custo ~zero; o logotipo definitivo segue fora de escopo.

**Acceptance Criteria**:

24. WHEN o header renderiza THEN o wordmark SHALL ser "ritmo" em lowercase com o glyph de pulso lime ao lado. <!-- event-driven -->
25. The system SHALL usar o pulso como favicon (metadata icon) enquanto não há logotipo definitivo. <!-- ubiquitous -->

**Independent Test**: header com "ritmo" + pulso; favicon do browser = pulso.

---

## Edge Cases

- IF a fonte do Google Fonts está indisponível (offline/LAN sem internet) THEN a stack de fallback renderiza — nenhum bloqueio (`display: swap`, DSN-10).
- IF o usuário está num painel profundo (ex.: `/treinos/123`) THEN a tab ativa continua Treinos (resolução `startsWith` da `activePanel` atual).
- IF o viewport é mais largo que 390px THEN a tab bar permanece inferior, alinhada ao conteúdo — o shell não vira header nav em desktop.
- IF um gráfico não tem dados THEN o estado vazio do bloco permanece (CLR-11/HLT-19) — o tema não inventa série.
- WHEN um gráfico é legitimamente multi-série (PMC: CTL/ATL/TSB; fases do sono) THEN cada série recebe cor do conjunto semântico central — o mapeamento por gráfico é definido no design, nunca hex local de volta.

## Varredura de dimensões implícitas (Large — gate completo)

| Dimensão | Resolução |
| -------- | --------- |
| Input validation & bounds | N/A — feature visual, nenhum input novo |
| Failure / partial-failure | Fonte offline → fallback swap (DSN-10); erro de dados preservado (DSN-23) |
| Idempotency / retry / duplicatas | N/A — sem escrita de dado |
| Auth boundaries & rate limits | N/A — rotas e sessão intocadas (tab bar navega nas mesmas URLs existentes) |
| Concurrency / ordering | N/A — sem estado compartilhado novo |
| Data lifecycle / expiry | N/A — nenhum dado novo |
| Observability | N/A — feature visual; build/lint são o gate |
| External-dependency failure | Google Fonts offline → stack de fallback com swap (DSN-10) |
| State-transition integrity | Estados loading→ready→error/vazio preservados (DSN-22/23 + Edge Cases) |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| DSN-01 | P1: Tokens v0.3 em código | Design | Pending |
| DSN-02 | P1: Tokens v0.3 em código | Design | Pending |
| DSN-03 | P1: Tokens v0.3 em código | Design | Pending |
| DSN-04 | P1: Tokens v0.3 em código | Design | Pending |
| DSN-05 | P1: Tokens v0.3 em código | Design | Pending |
| DSN-06 | P1: Tokens v0.3 em código | Design | Pending |
| DSN-07 | P1: Tipografia com assinatura | Design | Pending |
| DSN-08 | P1: Tipografia com assinatura | Design | Pending |
| DSN-09 | P1: Tipografia com assinatura | Design | Pending |
| DSN-10 | P1: Tipografia com assinatura | Design | Pending |
| DSN-11 | P1: Tema de gráfico compartilhado | Design | Pending |
| DSN-12 | P1: Tema de gráfico compartilhado | Design | Pending |
| DSN-13 | P1: Tema de gráfico compartilhado | Design | Pending |
| DSN-14 | P1: Tema de gráfico compartilhado | Design | Pending |
| DSN-15 | P1: Tema de gráfico compartilhado | Design | Pending |
| DSN-16 | P1: Tema de gráfico compartilhado | Design | Pending |
| DSN-17 | P2: Tab bar inferior | Design | Pending |
| DSN-18 | P2: Tab bar inferior | Design | Pending |
| DSN-19 | P2: Tab bar inferior | Design | Pending |
| DSN-20 | P2: Tab bar inferior | Design | Pending |
| DSN-21 | P2: Tab bar inferior | Design | Pending |
| DSN-22 | P2: Skeletons na linguagem | Design | Pending |
| DSN-23 | P2: Skeletons na linguagem | Design | Pending |
| DSN-24 | P3: Wordmark + pulso | - | Pending |
| DSN-25 | P3: Wordmark + pulso | - | Pending |

**Coverage:** 25 total, 25 mapped to stories, 0 unmapped ✅

---

## Success Criteria

How we know the feature is successful:

- [ ] 100% das superfícies na paleta v0.3 — zero resquício zinc/lime-400; nenhum sky-400/red-400 hardcoded nos gráficos
- [ ] `grep` de hex em `src/components` retorna apenas o módulo do tema (zonas VDOT incluídas lá)
- [ ] Os 11 gráficos na mesma linguagem: linha de base hairline única, ticks 9–10px, tooltip cartão raio 12, "hoje" em lime onde existe
- [ ] Tab bar inferior com Treinos · Saúde · Performance · Perfil funcionando em 390px, sem scroll horizontal, `/perfil` ao alcance do polegar
- [ ] `npm run build` + `npm run lint` verdes; suite do backend intocada (zero mudança de servidor)
- [ ] UAT visual em 390px contra `docs/design/identidade-visual-v0.3.html` — o app vivo conversa com o mock aprovado
