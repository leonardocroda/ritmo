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

### L-005 - Toda query de leitura filtrada por user_id precisa de um teste que semeie uma linha de outro usuario e afirme que ela nao vaza no payload
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `backend/service-layer` · harmful: 0
- features: health-panel
- evidence: mutant M3: backend/app/health/service.py:56 (backend/service-layer)
- last seen: 2026-10-16T20:21:01Z

### L-006 - Gate de UI (build+lint) so cobre sintaxe/tipos: a discriminacao comportamental de ACs de frontend vem da inspecao spec-anchored + UAT, nunca do gate
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `frontend/ui` · harmful: 0
- features: health-window
- evidence: mutantes M1-M4: .specs/features/health-window/validation.md (Discrimination Sensor) (frontend/ui)
- last seen: 2026-10-17T21:33:15Z

### L-007 - Seed and assert every field the spec enumerates in a payload contract; unseeded fields regress silently.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend/tests/payload` · harmful: 0
- features: ai-evaluation
- evidence: EVAL-02 / backend/tests/test_evaluation_payload.py:139 (backend/tests/payload)
- last seen: 2026-10-18T14:11:32Z

### L-008 - Assert every entry of a spec-enumerated mapping table, not a sample of it.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend/tests/payload` · harmful: 0
- features: ai-evaluation
- evidence: EVAL-02 / backend/app/evaluation/payload.py:23 (backend/tests/payload)
- last seen: 2026-10-18T14:11:32Z

### L-009 - Every rule the spec requires in prompt text needs its own literal marker assertion; a partial marker set is a hole.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend/tests/prompt` · harmful: 0
- features: ai-evaluation
- evidence: EVAL-03 / backend/tests/test_evaluation_prompt.py:11 (backend/tests/prompt)
- last seen: 2026-10-18T14:11:33Z

### L-010 - Pin call counts for spec-mandated single calls; a capture that overwrites cannot detect a second call.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend/tests/service` · harmful: 0
- features: ai-evaluation
- evidence: EVAL-03 / backend/tests/test_evaluation_service.py:115 (backend/tests/service)
- last seen: 2026-10-18T14:11:33Z

### L-011 - Test the accepted side of every boundary: assert each accepted type passes, not only that the rejected type fails.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend/tests/service` · harmful: 0
- features: ai-evaluation
- evidence: EVAL-10 / backend/app/evaluation/service.py:27 (backend/tests/service)
- last seen: 2026-10-18T14:11:34Z

### L-012 - Spec edge cases need an end-to-end assertion at the layer that owns the outcome, not only a unit pin of the producer.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `backend/tests/service` · harmful: 0
- features: ai-evaluation
- evidence: Edge / backend/tests/test_evaluation_nim.py:76 (backend/tests/service)
- last seen: 2026-10-18T14:11:34Z

### L-013 - When the spec is silent on validation precedence, record the chosen order in the design and pin it with a test.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `backend/routes` · harmful: 0
- features: ai-evaluation
- evidence: EVAL-09/12 / backend/app/evaluation/router.py:33 (backend/routes)
- last seen: 2026-10-18T14:11:35Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
