# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - Pin spec-defined error messages with their literal string, not with the constant the implementation interpolates to build the message
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/tests` · harmful: 0
- features: postgres-infra
- evidence: backend/tests/test_infra.py:61 (mutant M2) (backend/tests)
- last seen: 2026-10-14T15:15:00Z

### L-002 - Success Criteria com numeros de orcamento (chamadas, tempo, contagens) devem ser tetos mensuraveis sem '~' - estimativas aproximadas nao sao falsificaveis e forcam julgamento interpretativo na validacao
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `specs` · harmful: 0
- features: garmin-sync
- evidence: .specs/features/garmin-sync/spec.md:223 (specs)
- last seen: 2026-10-15T00:38:48Z

### L-003 - Edge case que alarga um AC precisa ser reconciliado com o qualificador do AC no design — se o AC restringe (ex.: 'PRs datados'), o extra do edge case nasce sem implementação e sem teste
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: potential-panel
- evidence: spec.md:201 vs AC POT-07 (spec.md:106) (spec)
- last seen: 2026-10-16T10:07:26Z

### L-004 - Pine no AC o formato de campos exibidos derivados (labels, narrativas) — sem formato definido, o teste acaba afirmando a escolha da implementação, não um requisito
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `spec` · harmful: 0
- features: potential-panel
- evidence: AC POT-08 (label do ponto teste) / design payload ilustrativo (spec)
- last seen: 2026-10-16T10:07:27Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
