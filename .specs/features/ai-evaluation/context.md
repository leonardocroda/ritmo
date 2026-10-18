# Avaliar com IA Context

**Gathered:** 2026-10-17
**Spec:** `.specs/features/ai-evaluation/spec.md`
**Status:** Ready for design

---

## Feature Boundary

No detalhe de uma corrida: formulário de intenção (tipo + texto livre) → payload determinístico montado em Python a partir do banco próprio → uma chamada NVIDIA NIM com system prompt derivado de `analyze-garmin-run` → veredito JSON validado e persistido (`model`, `prompt_version`, tokens, payload, veredito) → card no detalhe + badge "Avaliado" na lista.

Fora: seletor de modelo, feed do veredito no Potencial, zonas de FC formais, revisão semanal por IA, story, alertas proativos.

---

## Implementation Decisions

### A — Zonas de FC no payload

- v1 **sem classificação Z1–Z5 formal**: o sync não puxa a config RUNNING do Garmin e a skill veta hardcode de zonas de FC.
- O payload manda FC média por split (e FC média/máx da corrida) + **LTHR de referência configurável por env** (`LTHR_BPM`, default 177 do perfil calibrado).
- O LLM interpreta FC contra o LTHR — papel do LLM segundo AD-003 (números em Python, interpretação no modelo).
- Zonas de FC formais (sync da config RUNNING + time-in-zone) ficam como extensão futura do sync, fora desta feature.

### B — Modelo por avaliação

- Fixo pelo env `NVIDIA_MODEL` (default `z-ai/glm-5.3`), **sem seletor na UI** na v1.
- A coluna `model` continua gravada por avaliação — quando o seletor flash/full existir (Fase 2), é só UI em cima do contrato vigente.

### C — Re-avaliação e histórico

- Reavaliação sempre **explícita** (clique no botão), nunca automática — cache de veredito por design (plano §7).
- Cada avaliação é **linha nova**; nada sobrescrito, nada apagado.
- Detalhe mostra a mais recente como card; as anteriores como entradas resumidas (data, selo, headline).

### D — Alcance do veredito na v1

- Card no detalhe + badge "Avaliado" na lista (flag `evaluated`, já renderizada pela lista).
- Feed do painel Potencial e agregação "últimas 10 avaliações: X no alvo" ficam na **Fase 2** (roadmap §6 já os coloca lá).

### E — Falhas

- Qualquer falha (sem API key, NIM fora, timeout, JSON inválido) → **nada gravado**, `evaluated` inalterado, erro claro em PT-BR no lugar do card.
- **Sem retry automático**: cada tentativa custa tokens; o pedido é explícito.
- JSON da NIM validado contra schema no backend; campos extras são ignorados, obrigatórios ausentes rejeitam a resposta.

### Agent's Discretion

- Pré-preenchimento do seletor de intenção com `inferred_type` (chaves 1:1 com o enum).
- Mapeamento intenção → zona(s) alvo (incl. progressivo e prova sem alvo único).
- Selo visual ✅/⚠️/❌ por veredito.
- POST síncrono, sem job em background.
- Códigos HTTP por tipo de falha.
- Corrida sem splits avalia com payload honesto (bloco de voltas omitido).

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi recusada — o usuário aceitou as 5 recomendações (A–E) no ritmo Quick (17/10/2026, "pode seguir com as soluções sugeridas"). Os defaults de agente estão marcados `n` na tabela de assumptions do spec.

---

## Specific References

- System prompt deriva de `C:\Users\leona\projects\garmin_mcp\.opencode\skills\analyze-garmin-run\SKILL.md` — regras de veredito (§D), modificadores de contexto (§C), hierarquia pace>FC, ajuste por calor, casos de borda — **destilado a ~2k tokens** (plano §9.3: só regras de veredito e formato).
- JSON de veredito: plano §9.2, chaves exatas — `veredito`, `headline`, `execucao_vs_intencao{pct_zona_alvo, principais_desvios}`, `o_que_funcionou`, `corrigir_prox_vez`, `contexto_relevante`, `confianca`.
- Placeholder do texto livre do plano §4.6: "era pra ser 30min a 4:15".
- UI segue AD-009: cabeçalho forte, selo de método visível (modelo + tokens), nada atrás de clique/tooltip.

---

## Deferred Ideas

- Seletor de modelo flash/full por avaliação (Fase 2 — a coluna `model` já suporta)
- Feed do veredito no painel Potencial + "% no alvo por tipo" (Fase 2)
- Zonas de FC formais (sync da config RUNNING + time-in-zone)
- Gerar story com o veredito injetado (Fase 2 — reuso de `generate_image.py`)
- Revisão semanal por IA (Fase 2)
- Alerta "novo teste? recalibrar zonas" no card de avaliação (Fase 2)
