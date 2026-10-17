# Janela de tempo do Painel Saúde (health-window) — Validation

**Date**: 2026-10-17
**Spec**: `.specs/features/health-window/spec.md`
**Diff range**: `4f7d553..68857ee` (1 commit `68857ee`; 4 arquivos: `HealthPanel.tsx` +138/−28 comportamentais, `api.ts` e `HrvTable.tsx` só comentário de contrato, `spec.md` traceability; **zero arquivos backend**)
**Verifier**: sub-agente independente (author ≠ verifier) — árvore real intacta (`git status --porcelain` vazio no baseline, idêntico antes/depois de cada mutante e após o descarte do worktree; mutações só em worktree descartável fora do repo)

---

## Veredito

**PASS ✅** — 13/13 ACs com evidência `file:line` na superfície do diff e comportamento conforme a spec (0 spec-precision gaps). Gate verde: `npm run build` exit 0 (Next 16.4.0/Turbopack, TypeScript 6,5s, 7 rotas incl. `/saude`) + `npm run lint` exit 0 (zero reportes). Backend não executado — intocado por design (justificativa na seção Gate Check). Sensor: **0/4 mutantes comportamentais mortos pelo gate automatizado** (estrutural e esperado — build+lint é gate sintático/tipo; a camada UI do repo não tem suite por convenção) · **4/4 pegos pela inspeção spec-anchored** (cada mutante contradiz uma evidência `file:line` específica) · **controle positivo morto** (erro de tipo → build exit 1) provando que o gate não é no-op. **UAT real aprovado pelo usuário em 17/10/2026 — a prova comportamental restante está cumprida; feature concluída.**

---

## Task Completion

Sem `tasks.md` nesta feature (pasta contém só `spec.md`; entrega em 1 commit). Superfície mapeada do diff:

| Arquivo | Status | Notas |
| ------- | ------ | ----- |
| `HealthPanel.tsx` | ✅ Done | `WindowFilter` (:57-91), estado `ready` estendido com `refreshing`/`refreshError` (:41-46), seq guard (:96,:103,:106,:115), effect por `[days]` (:102-123), `changeWindow` (:127-135), subtítulo dinâmico (:220), `key={days}` na HrvTable (:243-245) |
| `api.ts` | ✅ Done (comentário) | Contrato documentado: seletor fixo 7/30/42/60/90d, backend valida `days` em [7,365] (:422-424); assinatura `getHealthSummary(days = 60)` intocada (:425) |
| `HrvTable.tsx` | ✅ Done (comentário) | Doc atualizada: paginação sobre "a janela carregada, definida pelo filtro de tempo do painel" (:3-7); lógica intocada |
| `spec.md` | ✅ Done | Traceability Pending→Verified (HWF-01..13) |

---

## Spec-Anchored Acceptance Criteria

**Convenção da matriz**: frontend sem infra de testes (convenção do repo — precedentes health-panel/hrv-baseline): para ACs de UI a evidência é implementação (`file:line`) + gates; o UAT real é do orquestrador. Contratos de backend citados (CLR-06, AD-010) re-derivados da fonte, não herdados do autor.

| Criterion | Spec-defined outcome | `file:line` + evidência | Result |
| --------- | -------------------- | ----------------------- | ------ |
| HWF-01: painel pronto → grupo fixo `7d`,`30d`,`42d`,`60d`,`90d` com ativa destacada; `60d` no primeiro carregamento | 5 botões `N d`, destaque na ativa, default 60 | `HealthPanel.tsx:35` — `const WINDOW_OPTIONS = [7, 30, 42, 60, 90] as const;` (grupo fixo, ordem crescente); `:71-88` — `WINDOW_OPTIONS.map(...)` renderiza `{option}d` (:85); `:72,77` — `const active = option === days` + `aria-pressed={active}`; `:79-83` — ativa `bg-accent/15 ... font-medium text-accent` vs inativa `text-muted`; `:94` — `useState<WindowDays>(60)` (default 60d); `:169-177` — seletor renderizado só no ramo `ready` (early returns de loading :137, erro :141 e painel vazio :154 vêm antes — consistente com a assumption "vazio segue o fluxo existente") | ✅ PASS |
| HWF-02: clique → busca `/api/health/summary?days=N` + re-render de TODAS as seções | refetch por janela; 5 seções com dados novos | `HealthPanel.tsx:78` — `onClick={() => onSelect(option)}`; `:127-135` — `changeWindow` → `setDays(next)`; `:102-123` — effect dependente de `[days]` chama `getHealthSummary(days)` (:104); `api.ts:426` — `` fetch(`${API_BASE}/api/health/summary?days=${days}`) ``; re-render total: o painel inteiro nasce de um novo objeto — `:107-112` substitui `state.panel` por completo e `:149` destrutura as 5 seções (`sleep, hrv, rhr, stress, pmc, dose_response, lifestyle`) de `state.panel` (seções :190-285) | ✅ PASS |
| HWF-03: derivados da janela refletem a nova janela — nenhum número antigo permanece | baseline RHR, média estresse, % abaixo do piso, buckets dose, yoga recalculados | Substituição integral do payload: `HealthPanel.tsx:107-112` (novo `panel`, objeto novo → subtree re-renderiza) + `:149` (fonte única); `key={days}` força remount do único filho stateful (:245). Backend recalcula tudo por `days` a cada request: `service.py:249-253` (`_series(db, model, days)` × 4), `:264` (`window_start = today - timedelta(days=days - 1)`), baseline RHR `:180` (média das linhas da janela), `avg_window` estresse `:193`, `below_floor`/dose das noites da janela `:261,272`, lifestyle `:273` — nenhum estado de janela antiga existe no servidor nem na UI | ✅ PASS |
| HWF-04: WHILE busca em curso THEN dados anteriores visíveis + indicador | sem flash; "atualizando…" | `HealthPanel.tsx:130-134` — `changeWindow` seta `refreshing: true` preservando `panel` (`{ ...prev, refreshing: true, ... }`); `:174-176` — `{state.refreshing && <span>atualizando…</span>}` junto ao filtro; seções continuam renderizando o payload anterior (`:222` etc.) até o sucesso trocar o objeto | ✅ PASS |
| HWF-05: troca com busca em curso → descarta respostas velhas, aplica só a do último clique | seq guard (padrão WorkoutsList) | `HealthPanel.tsx:96` — `const requestSeq = useRef(0);`; `:103` — `const seq = ++requestSeq.current;` (incrementa a cada effect, i.e., a cada troca de janela); `:106` — guard no `.then`: `if (seq !== requestSeq.current) return;`; `:115` — mesmo guard no `.catch`; `:123` — effect re-dispara por `[days]`. Espelho exato de `WorkoutsList.tsx:83-138` (padrão citado pela spec) | ✅ PASS |
| HWF-06: refetch falha → mantém dados anteriores + erro inline junto ao filtro, sem quebrar navegação | dados na tela + mensagem inline | `HealthPanel.tsx:117-121` — no `.catch`, `prev.kind === "ready" ? { ...prev, refreshing: false, refreshError: message } : { kind: "error", message }` — com dados na tela o painel NÃO sai do ramo ready; `:178-182` — `refreshError` renderizado logo abaixo da linha do filtro ("Não foi possível atualizar a janela: {message}"); primeira carga falha → fluxo existente (:141-147, fallback :120); erro é `<p>` inline, navegação vive fora (page.tsx) | ✅ PASS |
| HWF-07: janela muda → paginação da tabela de HRV reseta para a 1ª página | remount por key | `HealthPanel.tsx:245` — `<HrvTable key={days} hrv={hrv} />` (único filho com estado interno — por isso é o único que precisa de key); `HrvTable.tsx:23` — `const [page, setPage] = useState(0);` — remount zera a página; edge `totalPages <= 1` esconde a paginação (`HrvTable.tsx:30,69`) | ✅ PASS |
| HWF-08: subtítulo da Carga reflete a janela ("A curva de N dias…" — nunca 60 fixo) | template com `days` | `HealthPanel.tsx:220` — `` subtitle={`Quanta carga estou impondo ao corpo? A curva de ${days} dias traz fitness (CTL), fadiga (ATL) e forma (TSB) — ...`} `` (o diff removeu o literal "A curva de 60 dias"); `days` é o mesmo estado do filtro (:94) e do fetch (:104) | ✅ PASS |
| HWF-09: CTL/ATL/TSB/ACWR exatamente como pré-computados no sync — janela muda quantos dias aparecem, nunca os valores (CLR-06) | zero recálculo na UI e no bloco | Backend: `service.py:197-218` — `_pmc_block` copia `row.ctl/atl/tsb/acwr` verbatim (:208-211, docstring "zero recálculo (CLR-06)"); a janela só corta linhas — `service.py:52-65` `_series` `.limit(days)` (:61) chamado com `DailyLoad` (:253); valores nascem no sync (`garmin/pmc.py:68,86-90,98`) e são colunas do banco (`models.py:161-164`). UI: `PmcChart.tsx:53-55` — `statOrDash` só formata (1 casa/—), `:108-112` cards do `current` do payload, `:117` `data={points}` — nenhuma aritmética; `PmcChart.tsx` não aparece no diff | ✅ PASS |
| HWF-10: banda normal de HRV sempre sobre a janela de baseline de 60 dias (AD-010), em qualquer janela exibida | régua científica imóvel | Backend: `calc.py:30` — `HRV_BASELINE_DAYS = 60`; `calc.py:89` — `w60 = window(day - timedelta(days=HRV_BASELINE_DAYS - 1), day)` e `:91-94` banda = média ± 0,75×DP de `w60` — independe de `days`; `service.py:126` — `_hrv_history` busca `start = latest - timedelta(days=days - 1 + HRV_BASELINE_DAYS - 1)` (lookback de 59 dias SEMPRE somado, qualquer janela exibida). UI: `HrvChart.tsx:123-128,177-195` — banda renderizada do payload (`band_low/band_high` → `bandBase/bandSpan`), `:80-83` fora-da-banda compara contra o payload — nenhuma recalculação; `HrvChart.tsx` não aparece no diff | ✅ PASS |
| HWF-11: bucket do dose-resposta sem noites → "—" nas médias (padrão HLT-22) | nenhum número inventado | `DoseResponse.tsx:16-18` — `avgOrDash` ("—" quando null), aplicado a `avg_hrv`/`avg_score` (:33,37); `HealthPanel.tsx:271` — `<DoseResponse dose={dose_response} />` recebe o bloco da janela nova; backend mantém `calc.py:58` (`_avg` → None sem valores). Componente não aparece no diff — comportamento preservado sob a nova janela | ✅ PASS |
| HWF-12: histórico < janela pedida → séries exibem tudo que existe (nada inventado) | janela pedida, não inventada | `service.py:52-55` — docstring de `_series`: "Janela maior que o histórico devolve as linhas disponíveis" (`.limit(days)` :61); `calc.py:84-87` — pontos HRV são dias corridos `while day <= latest` (termina no último dado); UI renderiza o payload como veio (gráficos sem lógica de preenchimento — `PmcChart.tsx:117`, `HrvChart.tsx:157`, `SleepChart` etc.). Invariante pré-existente mantida sob as novas janelas 7/30/42/90 | ✅ PASS |
| HWF-13: em 390px o grupo de botões permanece legível em uma linha, sem scroll horizontal | padrão dos painéis anteriores | `HealthPanel.tsx:66-70` — container `flex flex-wrap items-center gap-2` com `role="group"` `aria-label="Janela de tempo"`; pills `rounded-full px-3 py-1 text-sm` (:81-82) — 5 pills ≈ 233px + 4×8px de gap ≈ 265px dentro dos ~358px disponíveis (390px − `px-4` de `app/saude/page.tsx:7`), uma linha com ~90px de folga; nenhuma largura fixa/`min-w` no seletor; linha única não é forçada (`flex-wrap` permite quebra como robustez) | ✅ PASS (aritmética + **visual confirmado no UAT 17/10/2026**) |

**Status**: ✅ 13/13 ACs com evidência `file:line` na superfície do diff, cada uma mirando o outcome preciso da spec. 0 spec-precision gaps. Confirmação visual/interativa (pixeis, 390px real, corridas de clique) = UAT do orquestrador, conforme a matriz do repo.

---

## Edge Cases (spec.md:88-93)

- [x] **Troca em sequência rápida (respostas fora de ordem) → só a última aplica**: seq guard nos dois ramos (`HealthPanel.tsx:103,106,115`); sem `AbortController` — a resposta velha completa e é descartada, exatamente o padrão WorkoutsList que a spec cita
- [x] **Falha na primeira carga → fluxo de erro existente**: `.catch` cai no ramo `{ kind: "error", message }` quando `prev.kind !== "ready"` (:120) → mensagem inline no lugar do painel (:141-147)
- [x] **7d reduz a tabela a ≤7 noites → paginação some sozinha**: `totalPages = Math.ceil(nights/7)` (`HrvTable.tsx:30`), controles só com `totalPages > 1` (:69); reset da volta garantido pelo remount (`key={days}`, HealthPanel.tsx:245)
- [x] **Bloco `null` na nova janela → estado vazio próprio do bloco**: condicionais por bloco alimentados pelo payload novo (sono :195/:210, HRV :240/:247, RHR :253/:257, PMC :222/:226) — a troca não inventa dado onde não há

---

## Discrimination Sensor

**Tier**: lightweight (4 mutações comportamentais nos pontos de maior risco da feature — uma por comportamento novo: default, corrida, remount, subtítulo — + 1 controle positivo).
**Scratch**: `git worktree add C:\Users\leona\AppData\Local\Temp\opencode\ritmo-hwf-scratch HEAD` (detached em `68857ee`), `npm ci` (395 packages), **baseline build exit 0 + lint exit 0** (cópia fiel). Cada mutante injetado isoladamente em `frontend/src/components/health/HealthPanel.tsx`, revertido com `git checkout --` antes do próximo (porcelana do scratch limpa a cada injeção). Nenhuma mutação tocou a árvore real — `git status --porcelain` vazio antes/depois de cada run; worktree removido com `--force`; `git worktree list` mostra só `main`.

| # | Mutante | file:line (scratch) | Descrição | Gate automatizado (build+lint) | Discriminação real |
| - | ------- | ------------------- | --------- | ------------------------------ | ------------------ |
| M1 | default 60→7 | `HealthPanel.tsx:94` | `useState<WindowDays>(60)` → `(7)` | ❌ **Survived** (build 0 / lint 0 — mutante type-safe: `7` é membro da união) | ✅ Pego pela inspeção — contradiz HWF-01 (`:94` default 60d) e seria óbvio no UAT (primeira carga abre em 7d) |
| M2 | guard do `.then` removido | `HealthPanel.tsx:106` | `if (seq !== requestSeq.current) return;` apagado do `.then` (catch intacto — `seq` continua usado, lint não flaga) | ❌ **Survived** (build 0 / lint 0) | ✅ Pego pela inspeção — contradiz HWF-05 (`:106`); corrida só seria reproduzível em UAT com latência induzida |
| M3 | `key={days}` removida | `HealthPanel.tsx:245` | `<HrvTable hrv={hrv} />` sem remount | ❌ **Survived** (build 0 / lint 0 — JSX válido) | ✅ Pego pela inspeção — contradiz HWF-07 (`:245` + `HrvTable.tsx:23`); UAT pegaria (página 3 de 60d preservada ao trocar para 7d) |
| M4 | subtítulo fixo | `HealthPanel.tsx:220` | template `${days}` → literal `"A curva de 60 dias"` | ❌ **Survived** (build 0 / lint 0) | ✅ Pego pela inspeção — contradiz HWF-08 (`:220`); UAT visual pegaria |
| C1 | controle positivo | `HealthPanel.tsx:94` | `useState<WindowDays>(61)` — 61 fora da união (fault de tipo) | ✅ **Killed** — build **exit 1**: `error TS2345: Argument of type '61' is not assignable to parameter of type '7 | 30 | 42 | 60 | 90'` (`HealthPanel.tsx(94,48)`) | — |

**Sensor depth**: lightweight (com controle positivo).
**Result**: **gate automatizado 0/4 mutantes comportamentais** (4/4 sobrevivem) · **controle positivo 1/1 morto** (o gate discrimina sintaxe/tipo — não é no-op) · **inspeção spec-anchored 4/4** (cada mutante contradiz uma evidência `file:line` listada na matriz acima — a verificação desta feature É o discriminador comportamental da camada UI, junto do UAT) — **PASS ✅**

**Honestidade sobre a cobertura** (limitação estrutural da camada UI neste repo, conhecida e documentada): `build+lint` é um gate sintático/tipo — nenhum dos 4 mutantes comportamentais o derruba, porque o frontend não tem suite de testes (convenção do repo, fora de escopo criar uma). A discriminação comportamental desta validação vem da inspeção evidência-por-AC (seção Spec-Anchored) + UAT real do orquestrador (pendente, próxima etapa). Os sobreviventes **não são fix tasks de código** — o código está correto (evidência por AC); o que eles expõem é a ausência de suite UI, e o registro é a lição abaixo, não uma correção. Nenhum mutante de backend foi injetado: nenhum arquivo backend está no diff.

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ 3 arquivos de código: 1 helper (`WindowFilter`), 2 campos de estado (`refreshing`/`refreshError`), 1 ref (`requestSeq`), template no subtítulo, 1 `key`. Nada de input livre, outros painéis ou backend (out-of-scope respeitado — spec.md:19-25) |
| No abstractions for single-use code | ✅ `WindowFilter` é o único componente novo, usado uma vez; sem params de flexibilidade |
| Surgical changes / só arquivos da task | ✅ `api.ts` e `HrvTable.tsx` mudaram só comentários de contrato; nenhum arquivo fora da superfície |
| Didn't "improve" unrelated code | ✅ nenhum |
| Matches patterns | ✅ seq guard + pills = espelho de `WorkoutsList.tsx:83-138` (padrão que a spec manda seguir); `aria-pressed`/`role="group"`; subtítulo via prop `PanelSection`; comentários citam os ACs (HWF-NN) |
| Spec-anchored outcome check | ✅ evidências miram os outcomes exatos (conjunto 7/30/42/60/90, default 60, guards nos 2 ramos, remount por key, template com `days`, cópia verbatim do PMC, banda 60d) |
| Per-layer Coverage Expectation | ✅ (adaptado): sem suite por convenção — cada AC tem evidência de implementação + gates; contratos backend (CLR-06/AD-010) re-derivados da fonte e intocados |
| Documented guidelines followed | ✅ `frontend/AGENTS.md` (Next 16 — nada de código escrito nesta validação; build exit 0 confirma compat) |

---

## Gate Check

- **Gate command**: `cd frontend; npm run build; npm run lint` (sem `tasks.md` nesta feature — gate definido pelo orquestrador + matriz dos precedentes health-panel/hrv-baseline)
- **Frontend (tree real, `68857ee`)**: `npm run build` **exit 0** (Next 16.4.0/Turbopack; compile 2,5s; TypeScript 6,5s; rotas `/`, `/hoje`, `/potencial`, **`/saude`**, `/treinos`, `/treinos/[id]`) · `npm run lint` **exit 0** (zero reportes)
- **Backend**: **não executado — e não é necessário**: `git show 68857ee --stat` confirma zero arquivos backend no diff (frontend + spec apenas). O contrato `days` consumido pela UI já é validado pela suite existente (HLT-02/03): `router.py:193` `Query(default=60, ge=7, le=365)`; `test_health_api.py:622-626` (fora de faixa → 422); `test_health_api.py:657-659` (janela corta as mais antigas). Rodar a suite revalidaria código que esta feature não tocou
- **Test count**: n/a no frontend (sem suite — convenção do repo); backend inalterado (262 no fim do health-panel, zero mudanças desde)
- **Skipped/Failures**: nenhum

---

## Success Criteria (spec.md:119-127)

- [x] `/saude` abre com `60d` ativo; botões trocam todas as seções; derivados acompanham — **evidência estática (HWF-01/02/03) + UAT 17/10/2026 aprovado**
- [x] Troca sem flash, dados antigos + "atualizando…", cliques rápidos nunca deixam janela errada — **evidência estática (HWF-04/05) + UAT aprovado**
- [x] `7d` honesto ("—"), `42d` curva de fitness, `90d` histórico existente — **invariantes de payload (HWF-11/12) + valores reais conferidos no UAT**
- [x] `npm run build` + `npm run lint` verdes; suite do backend intocada (zero mudança de servidor — confirmado por `--stat`)
- [x] UAT em 390px: seletor em uma linha, sem scroll horizontal — **aprovado pelo usuário em 17/10/2026**

---

## Requirement Traceability Update

13/13 HWF-01..13 confirmados com evidência `file:line` por verificação independente (contratos CLR-06 e AD-010 re-derivados de `service.py`/`calc.py`/`models.py`, não herdados do autor). O Verifier não altera `spec.md` — a tabela de traceability já lista os 13 como `Verified` (autor); este veredito confirma os 13.

---

## Gaps Ranqueados

1. **(Minor, estrutural — registrado, não é código) Mutantes comportamentais sobrevivem ao gate automatizado (0/4)**: sem suite de testes no frontend, `build+lint` não derruba M1-M4 (default errado, corrida, remount, subtítulo fixo). Discriminação comportamental da camada UI = inspeção spec-anchored (feita aqui, 4/4) + **UAT real do orquestrador (obrigatório antes de considerar o comportamento "done")**. Criar suite UI está fora de escopo (convenção do repo). Lição registrada no lessons store (signal `surviving_mutant`, escopo `frontend/ui`).
2. **(Observação, sem ação) HWF-13 — linha única não é forçada**: `flex-wrap` permite quebra como robustez; em 390px os 5 pills cabem em uma linha com ~90px de folga (≈265px de ≈358px disponíveis). Outcome da spec sustentado por aritmética + padrão dos painéis anteriores; pixel real no UAT.

Nenhum gap de código. Nenhuma correção pendente no tree real (Verifier read-only).

---

## Summary

**Overall**: ✅ PASS — **Concluída** (UAT real aprovado pelo usuário em 17/10/2026, fechando a prova comportamental da camada UI)

**Spec-anchored check**: 13/13 ACs com `file:line` + outcome conforme a spec; 0 spec-precision gaps; 4/4 edge cases verificados
**Sensor**: gate automatizado 0/4 mutantes comportamentais (estrutural, documentado) · controle positivo 1/1 morto (gate não é no-op) · inspeção spec-anchored 4/4 · worktree descartado, porcelana do tree real idêntica ao baseline antes/depois
**Gate**: build exit 0 + lint exit 0 (frontend) · backend não executado (zero arquivos no diff; contrato `days` já coberto por HLT-02/03 na suite existente)

**What works**: seletor fixo 7/30/42/60/90d com default 60 e destaque da ativa; refetch por janela com substituição integral do payload (nenhuma seção herda número antigo); dados antigos preservados com "atualizando…" durante o refetch; descarte de respostas fora de ordem por seq (padrão WorkoutsList); falha de refetch mantém os dados com erro inline junto ao filtro; paginação da tabela de HRV reseta por remount; subtítulo da Carga dinâmico; CTL/ATL/TSB/ACWR e banda de HRV 60d intocados pela janela (CLR-06/AD-010 re-derivados da fonte).

**Issues found**: nenhum de código. Limitação estrutural registrada: o gate automatizado da camada UI não discrimina comportamento (lição no lessons store).

**Next steps**: n/a — feature concluída com UAT aprovado (17/10/2026). Os fluxos validados no UAT: 60d ativo de primeira, troca 7d/42d/90d com séries e derivados acompanhando, cliques rápidos, 390px em uma linha. Próximos passos do roadmap: **Avaliar com IA** (§4.6) ou **Painel Hoje** (§4.2) — o Painel Hoje herda o seletor de janela por consumir o mesmo endpoint.
