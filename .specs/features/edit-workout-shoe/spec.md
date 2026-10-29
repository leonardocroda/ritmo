# Edit Workout Shoe Specification

## Problem Statement

Currently, the ShoePickerModal only opens automatically when a running activity has NO shoe assigned (shoe === null). There is no way for users to change or remove the shoe of a workout that already has one assigned. Users need to be able to edit the shoe assignment after the fact — whether to correct a mistake, update to the correct shoe, or remove the association entirely.

## Goals

- [ ] Allow users to change the shoe of a workout that already has one assigned
- [ ] Allow users to remove the shoe association (set to null)
- [ ] Reuse existing ShoePickerModal component with minimal changes
- [ ] Maintain consistent UX with current assignment flow

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Bulk edit shoes for multiple activities | Separate feature, different UX |
| Shoe suggestions based on activity type | Already handled by default-by-type in modal |
| Editing shoe metadata (name, brand, km, etc.) | Already exists in Shoes section (PATCH /api/shoes/{id}) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Click target | Badge do tênis no header | UX simples, descoberta natural, não polui a UI | y |
| Modal behavior when editing | Mostrar tênis atual como "selecionado" (ring-2 ring-accent) + botão "Remover tênis" | Reusa ShoePickerModal, UX consistente | y |
| Activity types eligible | running + trail_running (mesmo RUNNING_TYPES do backend) | Consistente com validação existente no backend | y |
| Permission check | Mesmo user_id da atividade (já validado no backend) | Backend já garante isolamento por usuário | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Click shoe badge to change/remove shoe ⭐ MVP

**User Story**: As a runner, I want to click on the shoe badge in the workout detail header so that I can change to a different shoe or remove the shoe assignment.

**Why P1**: Core missing functionality — users cannot correct shoe assignments after initial assignment.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN the user clicks the shoe badge in the workout header AND the activity is running/trail_running THEN the system SHALL open the ShoePickerModal with the current shoe highlighted as selected
2. WHEN the ShoePickerModal opens for editing an existing assignment THEN the system SHALL display the current shoe with a visual indicator (ring-2 ring-accent) and label "Atual"
3. WHEN the user selects a different shoe in the modal THEN the system SHALL call PATCH /api/activities/{activity_id}/shoe with the new shoe_id AND update the badge in the header
4. WHEN the user clicks "Remover tênis" in the modal THEN the system SHALL call PATCH /api/activities/{activity_id}/shoe with shoe_id=null AND remove the badge from the header
5. WHEN the user clicks "Agora não" or clicks outside the modal THEN the system SHALL close the modal without changing the assignment
6. WHILE the modal is open for editing THEN the system SHALL show both active and retired shoes (retired allowed for retroactive assignment)
7. IF the activity is not running/trail_running THEN the system SHALL NOT show the shoe badge as clickable (no modal trigger)
8. IF the API call fails THEN the system SHALL show an error toast AND keep the modal open with previous state

**Independent Test**: Navigate to a running workout that has a shoe assigned → click the shoe badge → modal opens with current shoe highlighted → select different shoe → badge updates to new shoe → click badge again → click "Remover tênis" → badge disappears.

---

### P2: Keyboard accessibility for shoe badge

**User Story**: As a keyboard-only user, I want to activate the shoe badge with Enter/Space so that I can change the shoe without a mouse.

**Why P2**: Accessibility compliance — interactive elements must be keyboard accessible.

**Acceptance Criteria**:

1. WHEN the shoe badge receives focus AND the user presses Enter or Space THEN the system SHALL open the ShoePickerModal (same as click)
2. The shoe badge SHALL have role="button" and tabindex="0" when clickable
3. The shoe badge SHALL have aria-label describing the action (e.g., "Trocar tênis: Nike Pegasus 40")

**Independent Test**: Tab to the shoe badge → press Enter → modal opens → Tab through modal → press Escape → modal closes.

---

## Edge Cases

- IF the activity has no shoe assigned (shoe === null) THEN the existing auto-open behavior on page load remains unchanged (TRN-10)
- IF the user has no shoes registered THEN the modal shows empty state with link to Shoes section (already implemented)
- IF the shoe assigned to the activity was deleted (shouldn't happen due to FK SET NULL) THEN the badge shows null and click opens modal to assign new
- IF network error during shoe change THEN modal stays open, error toast shown, user can retry
- IF the activity is not running/trail_running THEN shoe badge is not shown at all (already handled by isRunning check)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| SHOEEDIT-01 | P1: Click badge to open modal | Specify | Pending |
| SHOEEDIT-02 | P1: Current shoe highlighted in modal | Specify | Pending |
| SHOEEDIT-03 | P1: Select different shoe updates assignment | Specify | Pending |
| SHOEEDIT-04 | P1: Remove shoe (set null) | Specify | Pending |
| SHOEEDIT-05 | P1: Cancel keeps current assignment | Specify | Pending |
| SHOEEDIT-06 | P1: Retired shoes shown for retroactive | Specify | Pending |
| SHOEEDIT-07 | P1: Non-running activities no badge click | Specify | Pending |
| SHOEEDIT-08 | P1: Error handling on API failure | Specify | Pending |
| SHOEEDIT-09 | P2: Keyboard accessibility | Specify | Pending |
| SHOEEDIT-10 | P2: ARIA attributes on badge | Specify | Pending |

**ID format:** `SHOEEDIT-[NUMBER]`

**Coverage:** 10 total, 0 mapped to tasks, 10 unmapped ⚠️

---

## Success Criteria

- [ ] User can change shoe of a workout with existing assignment in < 3 clicks
- [ ] User can remove shoe assignment entirely
- [ ] No regression: auto-open for unassigned runs still works
- [ ] Keyboard navigation works end-to-end
- [ ] API errors don't leave UI in inconsistent state