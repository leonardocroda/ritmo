# Alerta de degradação por tênis — Context

**Gathered:** 29/10/2026 (conversa de planejamento, feature tenis expandida)
**Spec:** `.specs/features/tenis-alerta-degradacao/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Sinais de degradação por tênis com dados já no banco (tenis + tenis-running-dynamics + tenis-analise-comparativa). Baseline primeiros ~100 km vs últimos ~50 km, ritmo-pareado, gate de mix de tipos. Sinais: ΔGCT, Δoscilação, Δcadência, ΔEF, ΔHR drift, Δ feel-RPE. Resultado = "sinais, não veredito". Pré-requisito: depende de A e B. Sem UI, sem notificação ativa (E fica para depois).

---

## Implementation Decisions

### Janela de baseline (decidido pelo usuário — Guided, recomendada)

- Primeiros ~100 km vs últimos ~50 km de cada tênis, por distância acumulada (km derivada), não por data.
- Ritmo-pareado: comparar apenas dentro de mesma banda de pace + tipo de treino.
- Gate de mix de tipos: não comparar tiro com rodagem; grupo sem pares válidos é omitido.
- Menos de ~150 km totais → "dados insuficientes".

### Sinais de degradação (decidido pelo usuário — Guided, recomendada)

- ΔGCT (ms), Δoscilação vertical (cm), Δcadência (spm), ΔEF (velocidade/FC), ΔHR drift (bpm), Δ feel-RPE.
- Cada sinal quando houver dado; ausente = omitido, nunca zero.
- Resultado = lista de sinais + confiança (baixo/médio/alto, mesma convenção de A).
- "Sinais, não veredito": nunca "aposentar" ou "continue" automático.

### Fonte e execução (assumptions do spec)

- 100% leitura do banco próprio (AD-002), zero Garmin em tempo de análise.
- Depende de tenis-running-dynamics (colunas GCT/passada/oscilação) e tenis-analise-comparativa (perfil, confiança, EF, HR drift).
- Cálculo puro, endpoint de leitura, reprodutível.

---

## Agent's Discretion

- Limiares exatos de relevância por sinal (defaults razoáveis, configuráveis).
- Formato exato do payload JSON de resposta do endpoint.
- Como o nível de confiança agrega múltiplos sinais (mínimo / médio / pior).

---

## Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi recusada. As duas áreas cinzentas (janela de baseline e sinais) foram resolvidas pelo usuário nesta conversa (aceitou as recomendadas) e estão registradas nas Assumptions do spec com `Confirmed? = y`.

---

## Specific References

- context.md do feature tenis (Deferred Ideas): "Alerta de aposentadoria multi-sinal: baseline primeiros ~100 km vs últimos ~50 km, sempre ritmo-pareado, gate de mix de tipos; sinais ΔGCT/Δoscilação/Δcadência/ΔEF/ΔHR drift/Δ feel-RPE; 'sinais, não veredito'".
- Pesquisa do tenis (context.md): Cornwall 2017 (corredor não percebe degradação), Malisoux (rodízio de 2+ tênis, −39% lesão), Van Hooren 2024 (GCT só comparável a ritmo pareado).
- AD-005 do tenis: drift só se interpreta a ritmo constante.
- Regras do tenis-running-dynamics: colunas NULL quando ausente, nunca zero inventado.
- Convenção de confiança de tenis-analise-comparativa: <3 = baixo, 3–5 = médio, >5 = alto.

---

## Deferred Ideas

- Notificação ativa de vida útil (badge na Home) — Feature E do tenis, aguarda decisão futura.
- UI de alerta de degradação (tela, card): sem demanda nesta entrega.
- Recomendação automática de aposentadoria: "sinais, não veredito" — decisão do corredor.
