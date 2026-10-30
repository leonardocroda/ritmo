# Análise comparativa entre tênis — Context

**Gathered:** 29/10/2026 (conversa de planejamento, feature tenis expandida)
**Spec:** `.specs/features/tenis-analise-comparativa/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Análise comparativa entre tênis com dados já no banco (quilometragem de tenis + running dynamics de tenis-running-dynamics). Perfil por tipo de treino × banda de pace, comparação pareada, nível de confiança, running dynamics ajustados por ritmo, EF, HR drift, janela fresco vs fadiga. Cálculo puro via endpoint, sem UI obrigatória. Pré-requisito para C (alerta de degradação).

---

## Implementation Decisions

### Critério de par válido (decidido pelo usuário — Guided)

- Distância dentro de ±5% E pace médio dentro de ±5%.
- Data livre: não é critério de proximidade (corridas em dias diferentes podem formar par).

### Gate de confiança (decidido pelo usuário — Guided, Opção C)

- Exibir sempre com qualquer quantidade de pares.
- Nível: <3 pares = baixo; 3–5 pares = médio; >5 pares = alto.
- Sem gate mínimo rígido para mostrar resultados.

### Confounding de seleção (assumption do spec)

- Fatiar por tipo de treino inferido + banda de pace; nunca pace bruto agregado.
- Adizero → tiro, Kayano → rodagem; agregado bruto invalida comparação.

### Fonte e execução (assumptions do spec)

- 100% leitura do banco próprio (AD-002), zero Garmin em tempo de análise.
- Depende de tenis-running-dynamics para as colunas GCT/passada/oscilação.
- Cálculo puro, endpoint de leitura, reprodutível.

---

## Agent's Discretion

- Faixas exatas de banda de pace (ex.: fácil 5:30–6:30/km) — podem ser ajustadas no design.
- Limiar de "pace estável" para HR drift (Δ pace entre metades) — definir no design.
- Formato exato do payload JSON de resposta do endpoint.

---

## Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi recusada. As duas áreas cinzentas (critério de par e gate de confiança) foram resolvidas pelo usuário nesta conversa e estão registradas nas Assumptions do spec com `Confirmed? = y`.

---

## Specific References

- context.md do feature tenis (Deferred Ideas): "Perfil por tênis fatiado por tipo de treino e banda de pace (nunca pace bruto agregado — confounding de seleção)"; "Comparação pareada (matched runs) com gates de confiança (≥3–5 pares)"; "EF (velocidade/FC); GCT/passada ajustados por ritmo via resíduo de regressão; HR drift; janela fresco vs fadiga".
- Pesquisa do tenis (context.md): Hoogkamer 2018 (respostas individuais −2,6% a +11%), Van Hooren 2024 (GCT só comparável a ritmo pareado), Malisoux (rodízio de 2+ tênis, −39% lesão), metodologia Run-It (matched runs, fresh vs fatigue, comparação por propósito).
- AD-005 do tenis: drift só se interpreta a ritmo constante.
- Regras do tenis-running-dynamics: colunas NULL quando ausente, nunca zero inventado.

---

## Deferred Ideas

- Feature C (alerta de degradação por tênis): depende de A.
- UI de comparação de tênis (tela, gráfico lado a lado): sem demanda nesta entrega.
- Teste A/B guiado back-to-back (mesma rota, dois tênis alternados): ideia futura, requer UI e fluxo guiado.
