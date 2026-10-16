# Painel Saúde — Context

**Gathered:** 16/10/2026
**Spec:** `.specs/features/health-panel/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Painel `/saude` (§4.5 + composição v1 de §9.1): responde "meu corpo está absorvendo o treino?" com sono (duração vs piso 7h + score + REM% + regularidade deitar/acordar + padrão por dia da semana), linhas HRV/RHR, dose-resposta sono→HRV/score (noites <6h vs ≥6h45) e equilíbrio de vida (força 2×/semana, yoga, estresse médio). Endpoint de leitura único (`GET /api/health/summary` — o `/api/health` exato já é o health check de infra), zero chamadas Garmin (AD-002) — todos os dados já sincronizados.

---

## Implementation Decisions

### NEAT/passos (decisão: CORTADO da v1 — dado essencial, feature futura própria)

- **Não entra na v1**: não existe tabela nem etapa de sync de passos; incluir custaria +1 chamada de sync + tabela + mapper para um número que hoje não alimenta regra nenhuma.
- **Registro de importância (pedido explícito do usuário 16/10/2026)**: passos/NEAT é dado **importantíssimo para avaliar a saúde geral** — "passos/NEAT nos dias de escritório" era item do §4.5. Não é corte por irrelevância; é adiamento por custo de infra.
- **Caminho futuro**: feature própria "sync de passos" (+1 chamada sequencial, tabela `steps`, mapper, backfill) que o painel Hoje também consumirá (NEAT no card de readiness). Anotada em Out of Scope da spec e em Deferred Ideas abaixo.

### Estresse médio (decisão: INCLUIR)

- Linha simples (média diária) + média da janela no bloco de equilíbrio de vida — fecha o §4.5 sem correlações avançadas.
- Body Battery fica fora da v1 do Saúde (insumo do card de readiness do painel Hoje, §4.2).

### Dose-resposta (decisão: 2 buckets literais + faixa neutra)

- Buckets `<6h` vs `≥6h45` (fiel ao §4.5); a faixa 6h–6h45 fica FORA da comparação e aparece como nota com N noites ("faixa neutra").
- HRV/score cruzados da **mesma noite** (a HRV do Garmin é medida durante o sono, mesma data da linha de sono). A correlação "sono × HRV do dia seguinte × FC do treino" do §4.5 segue cortada (§9.1: "correlações avançadas").
- Dados reais que motivam o painel (banco 16/10/2026): `<6h` → HRV 69,5 / score 60,2; `≥6h45` → HRV 81,3 / score 80,2; neutra: 18 noites.

### Streak de força (decisão: semana ISO)

- Semana ISO com ≥2 sessões de `strength_training` (typeKey exato, das `activities`).
- Exibição: streak atual (semanas completas consecutivas com ≥2, terminando na última semana completa), semanas atingidas na janela (`x/y`) e semana corrente em andamento separada (parcial, não quebra a streak).

---

## Agent's Discretion

- Janela única `days` (default 60, limites 7–365, 422 fora) aplicada a todas as séries e derivados; UI fixa 60.
- Piso de sono (7h) e banda ideal de REM% (21–31%) como constantes do payload (fonte única no backend).
- RHR baseline = média da janela, linha de referência no gráfico.
- Padrão semanal usa o weekday da data de acordar (convenção já existente no sync).
- Yoga no checklist: sessões na janela + média/semana ("mantém como está", §4.5).
- Estutura exata dos gráficos (barras vs linhas, composição Recharts) fica para o design — AD-008 (Recharts é o renderer padrão).

## Declined / Undiscussed Gray Areas → Assumptions

- Sleep debt acumulado no mês (citado no §4.5): cortado — §9.1 não o inclui na composição v1; o % de noites <7h carrega o recado. Registrado no Out of Scope.
- Todos os itens de "Agent's Discretion" acima entram como premissas na spec (tabela Assumptions).

---

## Specific References

- "Esse dado é importantíssimo para avaliar a saúde geral" — sobre passos/NEAT (16/10/2026): registrar a importância onde o projeto futuro o encontre (Out of Scope + Deferred Ideas + handoff do STATE.md).
- Perfil do plano (§1): sono médio 6h17, 83% das noites <7h, REM 14% vs ideal 21–31% — os pins do banco batem (84% <7h, REM 14,2%).

## Deferred Ideas

- **Sync de passos (NEAT)** — feature própria futura: +1 chamada de sync, tabela `steps(dia, total)`, mapper, backfill; consumida pelo checklist do Saúde e pelo card de readiness do Hoje. **Dado importantíssimo para avaliar a saúde geral** (decisão do usuário 16/10/2026 de não incluí-lo na v1 por custo de infra, não por irrelevância).
- Body Battery no Saúde (reavaliar após o painel Hoje existir).
- Correlações avançadas sono × HRV do dia seguinte × FC do treino (§9.1 — Fase 2).
