# Story 3.4: Flag Duplicate Business Number

Status: completed

Depends on: Story 3.1, Story 3.2, Story 3.3

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a system,
I want to flag duplicate Taiwan business numbers during customer creation,
so that we do not create conflicting customer masters.

## Acceptance Criteria

1. Given a customer with the same Taiwan business number already exists, when I attempt to create a new customer with that business number, then the system shows a clear duplicate warning that includes the existing customer name.
2. Given a duplicate is detected, when the warning is shown, then the normal create flow is blocked until I cancel or choose the existing record instead.
3. Given duplicate checks can race under concurrent requests, when persistence occurs, then a unique database constraint still enforces the invariant even if the optimistic duplicate pre-check misses.
4. Given the duplicate error reaches the API or UI, when it is surfaced, then it uses a stable error contract that can link the user back to the existing customer record.
5. Given concurrent requests attempt to create customers with the same business number, when the second request fails at the database constraint instead of the optimistic pre-check, then the returned duplicate error mirrors the optimistic duplicate response shape.

## Tasks / Subtasks

- [ ] Task 1: Add normalized duplicate detection to the customer service layer (AC: 1, 2, 4)
  - [ ] Reuse Story 3.2 normalization rules so duplicate checks compare canonical business-number values.
  - [ ] Add a domain error such as `DuplicateCustomerBusinessNumberError` in the customer service layer.
  - [ ] Query for an existing customer before insert and return enough metadata to guide the user to the right record.
- [ ] Task 2: Enforce the invariant in persistence (AC: 3)
  - [ ] Add or confirm a composite unique constraint on `(tenant_id, normalized_business_number)` and the supporting index needed for tenant-safe duplicate checks.
  - [ ] Map database-level uniqueness violations to the same domain/API error used by the optimistic duplicate pre-check.
  - [ ] Catch `IntegrityError`, query the conflicting customer row by `(tenant_id, normalized_business_number)`, and populate the same duplicate metadata returned by the optimistic pre-check.
  - [ ] Ensure concurrent create requests fail safely without creating two customer rows for one business number.
- [ ] Task 3: Wire duplicate feedback into create flows (AC: 1, 2, 4)
  - [ ] Extend `backend/domains/customers/routes.py` to return a stable 409-style duplicate response contract.
  - [ ] Update the create form UI to show the existing customer name and a clear action to open that record.
  - [ ] Reuse the browse/detail flow from Story 3.1 instead of inventing a second duplicate-resolution screen.
- [ ] Task 4: Add duplicate-handling tests (AC: 1, 2, 3, 4, 5)
  - [ ] Add backend tests for exact-duplicate detection, concurrent insert safety, identical 409 payload shape between optimistic and race-fallback paths, and API error payload shape.
  - [ ] Add frontend tests for duplicate-warning rendering and navigation to the existing customer record.

## Dev Notes

### Story Context

- The earlier epic wording allowed "cancel or proceed after acknowledgment," but that produces bad master data and conflicts with the goal of keeping one canonical customer record per business number.
- Story 3.3 establishes the basic create flow; this story hardens that flow against duplicate master records.
- Story 3.5 must reuse this duplicate behavior when a user edits an existing customer's business number.

### Dependency Sequencing

- Implement Stories 3.2 and 3.3 first.
- Implement Story 3.1 before this story so the duplicate warning can send the user to a real browse/detail destination.
- Story 3.5 should depend on this story because business-number edits must reuse the same duplicate contract.

### Scope Guardrails

- Do not implement fuzzy duplicate matching by name, phone, or address in this story. This story is about exact canonical business-number duplicates only.
- Do not allow a "force create anyway" path. The whole point of the story is to prevent conflicting masters.
- Do not replace the database constraint with a UI-only warning. The persistence invariant must remain authoritative.

### Technical Requirements

- Use the same canonicalized business-number value for the service pre-check, database unique constraint, and UI payloads.
- Follow the architecture's request-scoped tenant context pattern, including `SET LOCAL app.tenant_id` or the repo's equivalent helper, before duplicate queries or inserts run.
- Return HTTP `409 Conflict` with a stable duplicate response shape that includes an error code plus at least the existing customer ID, existing customer name, and the normalized business number.
- Surface duplicates consistently from both optimistic service checks and database race-condition fallbacks.
- Keep the duplicate logic in the customer service layer rather than duplicating it across routes or form components.

### Testing Requirements

- Mandatory backend coverage:
  - duplicate pre-check hit
  - non-duplicate create still succeeds
  - concurrent insert race maps to the same domain error
  - concurrent insert race returns the same 409 payload shape as the optimistic duplicate path
  - API duplicate response shape is stable
- Frontend coverage should verify the warning content and the action that opens the existing record.

### Project Structure Notes

- Extend the customer domain files created by Story 3.3 rather than creating a second duplicate-check module outside `backend/domains/customers/`.
- Reuse the API helper and browse/detail UI from Stories 3.1 and 3.3.
- If a unique constraint is not already present from Story 3.3, add it in a targeted migration rather than silently relying on application code.

### Risks / Open Questions

- Existing historical/legacy data may contain true duplicate business numbers if prior systems were lax. If that is discovered during migration work, the reconciliation plan belongs to data migration, not this online create-flow story.
- Duplicate prevention by business number does not solve customers with no business number or future customer-type expansion. Those are different stories.

### References

- `_bmad-output/epics.md` — Story 3.4 acceptance criteria and adjacent search/update stories.
- `_bmad-output/planning-artifacts/prd.md` — FR19 duplicate rule and Journey 4 customer lookup flow.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — customer get/update contracts and domain structure.
- `research/ui-ux/02-wireframes/01-customer-management.md` — browse/detail actions that make duplicate resolution user-friendly.
- `backend/common/database.py` — persistence and transaction pattern that duplicate handling must respect.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/6f0af2c8-127f-429b-8f9b-f9f78e0f0e40`

### Completion Notes List

- Story tightened the stale epic wording so duplicate creation is blocked rather than acknowledged and allowed.
- Duplicate handling now explicitly spans service logic, database invariants, and user-visible recovery back to the existing record.
- The story was sequenced after browse/detail work so duplicate warnings can point to a usable destination.

### File List

- `backend/domains/customers/service.py`
- `backend/domains/customers/routes.py`
- `backend/domains/customers/schemas.py`
- `backend/common/errors.py`
- `backend/tests/domains/customers/test_duplicate_detection.py`
- `backend/tests/api/test_create_customer.py`
- `migrations/versions/*_enforce_customer_business_number_uniqueness.py`
- `src/lib/api/customers.ts`
- `src/components/customers/CustomerForm.tsx`
- `src/components/customers/DuplicateCustomerWarning.tsx`
- `src/pages/customers/CreateCustomerPage.tsx`
- `src/pages/customers/CustomerListPage.tsx`
- `src/tests/customers/CreateCustomerPage.test.tsx`