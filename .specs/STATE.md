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
- **Branch**: master
- **Total**: 11 commits, 143 testes backend, frontend build OK, docs build OK
