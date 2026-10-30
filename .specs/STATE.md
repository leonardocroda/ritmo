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
- **Total**: 23 commits (11 tenis + 6 running-dynamics + 6 analise-comparativa + ... mais degradação), 143 testes backend (tenis) + 25 running-dynamics + 32 analise-comparativa + 14 degradacao, frontend build OK, docs build OK

---

## Novas features em spec (aguardam Design → Tasks → Execute)

- **tenis-running-dynamics** (B): **COMPLETA** — 6 commits (b9fef78 → 43ded93), 25 testes, 15/15 TRDs Verified, 0 regressão no tenis. Colunas Split + mapper + client typed splits + backfill CLI + SplitOut.
- **tenis-analise-comparativa** (A): **COMPLETA** — 6 commits (d86ef38 → dfe9c13), 32 testes (6 profile + 6 comparison + 10 metrics + 7 api), 17/17 TRD Verified, 0 regressão nos domínios existentes. Domínio profile/comparison/metrics + router /api/tenis/analysis.
- **tenis-alerta-degradacao** (C): **COMPLETA** — 2 commits (3cf7b04 → 9adcf92), 14 testes (9 domínio + 5 api), 15/15 TDE Verified, 0 regressão nos domínios existentes. Router /api/tenis/degradation/{id}.
- **tenis-ui-analysis** (UI): **COMPLETA** — 5 commits (253cc7d → c3cb9b6), API client + ShoesAnalysisSection + integração em Equipamentos. 13/13 TUI Verified.

Ordem de execução acordada com o usuário: **B → A → C**. D (sync contínuo Strava) não entra. E (badge vida útil na Home) espera.
