# Painel Clareza (panel-clarity) Context

**Gathered:** 2026-10-16
**Spec:** `.specs/features/panel-clarity/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Rework de arquitetura de informação dos painéis **Potencial** e **Saúde**. Treinos fica de fora (avaliado OK pelo usuário); Hoje herda o padrão quando existir. Entregas:

1. PMC (CTL/ATL/TSB/ACWR) sai inteiro do Potencial e vira seção própria "Carga de treino" na Saúde
2. Cabeçalho forte e numerado em cada seção, com subtítulo explicativo sempre visível ("o que é / por que importa") e selo de fonte/método (VDOT·Daniels, estimativa do relógio, Riegel, Garmin)
3. Potencial reorganizado em 3 blocos narrativos
4. Contrato acompanhando a mudança de casa do PMC (`pmc` sai de `/api/potential`, entra em `/api/health/summary`)

**Nenhum número ou cálculo novo** — os valores continuam exatamente os que o backend já produz; muda a apresentação, a organização e a casa do bloco pmc.

---

## Implementation Decisions

### A. Casa do PMC — seção própria "Carga de treino" na Saúde

- PMC sai inteiro do Potencial (gráfico + destaques do último dia + legenda)
- Na Saúde, vira seção própria na posição 2, entre Sono e Recuperação — fio condutor: **Sono → Carga (quanto imponho) → Recuperação (como respondo) → Dose-resposta (custo de dormir mal) → Equilíbrio**
- Recuperação fica leve (só HRV + RHR); cada seção mantém identidade única
- Alternativa recusada (dentro de Recuperação): misturaria entrada (carga imposta) com resposta (HRV/RHR) e recriaria a confusão de fronteiras que a feature mata

### B. Padrão de explicação — subtítulo sempre visível + selo de fonte

- Toda seção dos dois painéis: subtítulo de 1–2 linhas SEMPRE visível cobrindo "o que é / por que importa" — zero cliques
- Selo textual discreto ao lado do título quando a fonte/método importa distinguir (VDOT·Daniels, estimativa do relógio, Riegel, Garmin)
- Alternativas recusadas: tooltip (ruim no toque, painel é mobile-first 390px) e recolhível (contexto escondido atrás de clique, risco de nunca ser aberto)
- Copy estática em PT-BR dentro dos componentes — sem i18n, sem glossário global

### C. Potencial — 3 blocos narrativos

Ordem fixa, respondendo à pergunta do painel ("qual meu máximo e a que distância dele estou?"):

1. **Onde estou** — lacuna (GapCard explicado) + timeline VDOT (conceito VDOT + faixa honesta AD-004)
2. **O que isso prevê** — previsões vs PRs com legenda por método (Garmin / Riegel / VDOT / média honesta) + decaimento por distância
3. **O que o relógio estima** — VO2max com selo "estimativa" + hierarquia provas > algoritmo (AD-005)

### D. Fronteiras da Saúde — cabeçalho forte, sem container aninhado

- Cada seção: índice numerado (1–5) + título maior + pergunta que responde + espaçamento entre seções claramente maior que entre gráficos internos
- Gráficos continuam como cards individuais dentro da seção — sem card envolvendo card (pesado em 390px)
- Alternativa recusada: accordion (esconde conteúdo atrás de clique)

### Agent's Discretion

- Redação exata dos subtítulos e da linha-guia (a spec pina QUE a explicação existe e o que cobre; o texto é PT-BR e fica a cargo do design/implementação)
- Tratamento visual do selo de fonte (pill, cor, tipografia) — dentro do tema escuro existente
- Posicionamento fino do índice e da linha-guia dentro do cabeçalho

### Declined / Undiscussed Gray Areas → Assumptions

- **Mecânica do contrato na migração do PMC** (bloco `pmc` idêntico sai de `PotentialOut`, entra em `HealthSummaryOut` como `pmc | null`; `/api/potential` perde o query param `days`) — consequência estrutural da escolha A, decidida pelo agente; racional registrado como premissa no spec
- **Janela da PMC na Saúde** (segue o `days` único da Saúde, default 60) — premissa do agente, registrado no spec
- **Linha-guia no topo dos painéis** (fio condutor em 1 frase) — default do agente para responder "como as infos se conectam"; spec pina como P2

---

## Specific References

- "não sei onde é vdot (jack daniels) onde é vo2max do garmin, onde é riesel" → legenda por método + selo de fonte são o coração da solução
- "o gráfico de carga fala do histórico, não do potencial" → PMC fora do Potencial
- "não está muito fácil identificar onde começa uma coisa e termina outra" (Saúde) → cabeçalho forte numerado
- "queria algo que me explicasse o que é cada info, como é útil e porque eu deveria levar em conta" → subtítulo sempre visível
- Copy-guia sugerida (discreção do design): Sono "durmo o suficiente pra absorver o treino?"; Carga "quanta carga estou impondo ao corpo?"; Recuperação "como o corpo está respondendo?"; Dose-resposta "o que dormir mal me custa?"; Equilíbrio "a base fora da corrida sustenta o treino?"

## Deferred Ideas

- Painel Hoje herda o padrão (cabeçalho forte + subtítulo + linha-guia) quando for construído — não implementar aqui
- Explicação recolhível "saiba mais" por seção — evolução futura se o subtítulo fixo ficar raso
- Glossário global/centralizado — fora de escopo; explicações moram no contexto de cada seção
- Correlações avançadas (sono × HRV do dia seguinte × FC do treino) — continua cortado (Fase 2, §9.1)
- Passos/NEAT — feature própria futura (Deferred Ideas do health-panel)
