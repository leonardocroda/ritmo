# STATE

## Decisions

(vazio — nenhuma decisão project-level registrada aqui. Nota: o log de ADs de
arquitetura do projeto vive em `docs-site/docs/arquitetura/decisoes.md`
(AD-001..025); este arquivo segue contagem própria do workflow .specs.

## Handoff

- **Feature**: tenis (`.specs/features/tenis/`)
- **Phase / Task**: **COMPLETA** — Batch 1 (T1-T6 backend) + Batch 2 (T7-T11 frontend+docs) concluídos
- **Completed**: 
  - T1: Modelo + migração (7 testes, commit 4596643)
  - T2: CRUD + km derivada (18 testes, 68bacff)
  - T3: Associação + detail shoe (26 testes, 533f65f)
  - T4: Cliente Strava httpx + backoff (11 testes, 82bc30c)
  - T5: Matching Strava↔Garmin (18 testes, 90e140b)
  - T6: CLI backfill one-shot + checksum (12 testes, 47fcbb3)
  - T7: Seção Tênis Treinos + api.ts (build OK, 5315724)
  - T8: Aposentar + badge higiene + backend field (5 testes novos, 7c68fdb)
  - T9: Modal ShoePicker (da0ac4b)
  - T10: Gatilho no WorkoutDetail (c9d6562)
  - T11: Docs-site tenis.md + banco-de-dados.md + nav (539b671)
- **In-progress**: none
- **Next step**: Verifier roda automaticamente (spec-anchored + discrimination sensor)
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main
- **Total**: 17 commits (11 tenis + 6 running-dynamics), 143 testes backend (tenis) + 25 running-dynamics, frontend build OK, docs build OK

---

## Novas features em spec (aguardam Design → Tasks → Execute)

- **tenis-running-dynamics** (B): **COMPLETA** — 6 commits (b9fef78 → 43ded93), 25 testes, 15/15 TRDs Verified, 0 regressão no tenis. Colunas Split + mapper + client typed splits + backfill CLI + SplitOut.
- **tenis-analise-comparativa** (A): **PRÓXIMA** — spec.md + context.md criados e validados (0 erros). Decisões travadas: par válido = distância ±5% e pace ±5% (data livre); confiança sempre exibida (baixo <3 / médio 3–5 / alto >5). Dependência: B (concluída).
- **tenis-alerta-degradacao** (C): spec.md + context.md criados e validados (0 erros). Decisões travadas: baseline ~100 km vs ~50 km, ritmo-pareado, gate de mix de tipos; sinais ΔGCT/Δoscilação/Δcadência/ΔEF/ΔHR drift/Δ feel-RPE ("sinais, não veredito"). Dependência: A + B.

Ordem de execução acordada com o usuário: **B → A → C**. D (sync contínuo Strava) não entra. E (badge vida útil na Home) espera.
