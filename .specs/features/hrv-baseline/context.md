# HRV Baseline Científico Context

**Gathered:** 2026-10-17
**Spec:** `.specs/features/hrv-baseline/spec.md`
**Status:** Ready for design

---

## Feature Boundary

O bloco de HRV do painel Saúde passa a avaliar HRV no modelo científico (Altini/Plews): gráfico com noites individuais + linha de média móvel de 7 dias + banda móvel por dia da faixa normal (janela móvel de 60 dias, média ± 0,75 DP), status calculado localmente (BALANCED/UNBALANCED pela média 7d vs banda do dia) com os números de contexto visíveis no card, e tabela diária paginada de 7 em 7 dias sobre a janela de exibição de 60 dias. O backfill de saúde sobe para 120 dias para sustentar a banda em toda a janela exibida; sem mudanças no pipeline de sync além disso.

---

## Implementation Decisions

### Fonte do status exibido

- **Status 100% local.** O status de destaque do card é calculado por nós (média 7d do último dia com dado vs faixa normal local); o status cru da Garmin sai da UI do painel Saúde e do payload do summary (AD-009), mas continua persistido na tabela `hrv` e continua usado pelo chip "Contexto do dia" no detalhe do treino.
- Rótulos mantidos em BALANCED / UNBALANCED (inglês, paridade com o relógio, sem tradução inventada).

### Composição visual do gráfico

- **Linha 7d + pontos diários + banda** (padrão Altini): pontos discretos das noites individuais, linha de média móvel de 7 dias por cima, faixa normal como banda ao fundo. A relação noite↔baseline fica visível e explica o status.

### Hierarquia do card (decisão de UAT, 17/10/2026)

- **Destaque do card = média 7d** — é ela que decide BALANCED/UNBALANCED. A última noite desce para a linha de contexto, ao lado dos limites da banda. Ajuste pós-UAT solicitado pelo usuário ("o número que diz se tá balanced merece o destaque").

### Método científico (resultado da pesquisa encomendada pelo usuário)

- Garmin (oficial): status compara média móvel de 7 dias contra uma faixa pessoal (range, ex. 70–98 ms); ~3 semanas para ativar; fórmula não publicada.
- Altini/HRV4Training (método publicado, adotado): faixa normal = média dos últimos 60 dias corridos ± 0,75 × DP amostral (smallest worthwhile change, Plews et al.); linha = média móvel de 7 dias; lacunas preenchidas pela média dos valores disponíveis; "normal é melhor", não "maior é melhor".

### Banda móvel por dia e histórico

- **Usuário vetou a banda plana**: quer a banda deslizando por dia (cada dia exibido com sua própria janela móvel de 60 dias), como a baseline page do HRV4Training.
- Consequência aceita pelo usuário: buscar mais de 60 dias de histórico. Escolha: manter a janela de exibição em 60 dias e subir o backfill de saúde para 120 dias (60 de exibição + 59 de lookback = 119 necessários; 120 como default redondo).
- A base existente (60 dias semeados) só ganha o histórico extra no próximo re-sync completo — esperado e aceitável.
- Threshold por dia: janela móvel com ≥14 valores exibe banda; senão o dia fica sem banda. O mesmo vale para o card, avaliado na janela do último dia com dado.

### Tabela diária

- Colunas: Data (PT-BR), HRV, média 7d — 1 casa decimal; ordem decrescente; apenas dias com dado.
- Paginação client-side de 7 linhas/página sobre a janela de 60 dias, com controles Anterior/Próxima e indicador "atual/total".

### Agent's Discretion

- Como o backend expõe a série de média 7d e a faixa no payload (contrato), regras de lookback para as janelas truncadas, e detalhes visuais da banda/cores — desde que AD-008 (Recharts) e AD-009 (payload espelha render) sejam respeitados.
- Estado "coletando linha de base": texto e forma de exibição no card.

### Declined / Undiscussed Gray Areas → Assumptions

- Threshold de 14 valores por janela móvel — logado na spec.
- Janela de exibição muda de "60 linhas" para "60 dias corridos" — logado na spec.
- Arredondamento (1 casa na exibição, sem arredondamento intermediário) — logado na spec.
- P2 (noites fora da banda com cor diferenciada) e P3 (paginar além da janela de exibição, até 365) — priorizados na spec, sem detalhamento visual discutido.

---

## Specific References

- "Normalmente cada ponto é a média dos últimos 7 dias, onde caso falte um ponto (por falta de captura do dado) ele é preenchido com a média dos últimos 7 dias" — preenchimento de lacunas adotado como comportamento da linha.
- Exemplo real do usuário citado como caso de aceitação: última noite 69 ms, média 7d 76 ms, faixa 70–98 ms → BALANCED.
- Referências visuais: homepage/baseline page do HRV4Training (pontos + linha 7d + banda); gráfico atual do Ritmo usa banda em `RemChart` e linha de referência em `RhrChart` como padrões internos.
- Pesquisa: Garmin HRV Status (garmin.com, webhelp oficial), Marco Altini — "Daily score, baseline and normal range", "Determining your normal range", "What's your normal range for HRV?" (0,75 SD/60 dias confirmado em fonte secundária intervals.icu), Plews et al. Frontiers in Physiology 2014 (SWC).

---

## Deferred Ideas

- Reavaliar o chip "Contexto do dia" (detalhe do treino) para usar o modelo local — feature futura.
- Painel Hoje / readiness usando status local vs faixa (§4.2 do PLANO_PLATAFORMA) — feature futura.
- Coeficiente de variação do HRV e classificação de tendências de Altini (estável / coping well / maladaptation / fadiga acumulada) — Fase 2.
- Nenhuma destas entra no escopo desta feature.
