# Story 3.5: Update Customer Record

Status: completed

Depends on: Story 3.1, Story 3.2, Story 3.3, Story 3.4

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a sales rep,
I want to update an existing customer's master data,
so that contact details, address, credit limit, and business-number corrections stay accurate over time.

## Acceptance Criteria

1. Given an existing customer record, when I update company name, Taiwan business number, address, contact details, or credit limit, then the system validates the edited fields before save.
2. Given the business number changes, when the save is attempted, then the system re-runs Story 3.2 checksum validation and Story 3.4 duplicate detection before persisting.
3. Given the update succeeds, when the customer is saved, then the customer ID and tenant ownership remain unchanged and the updated record is immediately retrievable through the browse/detail flows.
4. Given invalid data such as malformed Taiwan phone data, malformed email data, negative credit limits, or a duplicate business number is supplied, when I attempt to save, then the system returns clear errors and the existing customer row remains unchanged.

## Tasks / Subtasks

- [ ] Task 1: Add customer update service and API behavior (AC: 1, 2, 3, 4)
  - [ ] Extend `backend/domains/customers/service.py` with an update method that loads the existing customer, enforces optimistic locking via the customer `version` field, applies allowed field changes, and persists the result in one transaction.
  - [ ] Add `PATCH /api/v1/customers/{customer_id}` or an equivalent update endpoint in `backend/domains/customers/routes.py`.
  - [ ] Define update request/response schemas in `backend/domains/customers/schemas.py`, including the concurrency token/version used by the edit form.
  - [ ] Reject attempts to mutate immutable fields such as customer ID or `tenant_id` with a structured `400 Bad Request`; update timestamps explicitly for valid edits only.
  - [ ] Return a structured 404 error when the target customer does not exist.
- [ ] Task 2: Reuse validation and duplicate safeguards during edit (AC: 1, 2, 4)
  - [ ] Compare the stored normalized business number with the incoming normalized business number so business-number-specific checks run only when the value actually changes.
  - [ ] Call the Story 3.2 validator when the business number changes.
  - [ ] Call the Story 3.4 duplicate detector when the business number changes, explicitly excluding the current customer ID from the duplicate lookup.
  - [ ] Validate non-negative credit limits, the `NUMERIC(12,2)` bounds from Story 3.3, and the same contact-field rules used by create.
  - [ ] Keep the old record unchanged if any validation step fails.
- [ ] Task 3: Build the edit-customer UI (AC: 1, 2, 3, 4)
  - [ ] Create or extend `src/components/customers/EditCustomerDialog.tsx` or `src/pages/customers/EditCustomerPage.tsx`.
  - [ ] Pre-fill current customer values from the detail API and allow controlled edits of the supported fields only.
  - [ ] Reuse the customer form primitives from Story 3.3 instead of creating a second unrelated form implementation.
  - [ ] Surface duplicate and checksum validation feedback inline.
- [ ] Task 4: Add update-path tests (AC: 1, 2, 3, 4)
  - [ ] Add backend service tests for valid updates, unchanged business-number updates, changed business-number updates, optimistic-lock conflicts, duplicate failures, immutable field rejection, 404 not found handling, and no-op update behavior across failed validation cases.
  - [ ] Add backend API tests for the update endpoint, version-mismatch 409 responses, immutable-field `400 Bad Request` behavior, and unchanged-row guarantees on failure.
  - [ ] Add frontend tests for edit form initialization, validation, successful save behavior, and stale-version conflict handling.

## Dev Notes

### Story Context

- The PRD explicitly requires customer validation on create and update, but the original Epic 3 breakdown omitted the update story.
- The architecture also defines a `customers.update` capability, so this story closes a real planning gap rather than adding speculative scope.
- Order and invoice workflows depend on customer records remaining accurate over time, especially for contact details and credit limits.

### Dependency Sequencing

- Implement Stories 3.2, 3.3, and 3.4 first.
- Reuse the browse/detail experience from Story 3.1 so users can open a customer into edit mode from the existing customer-management screen.
- Story 8 customer MCP work should map its `customers.update` behavior to the same customer service method implemented here.

### Scope Guardrails

- Do not add delete, disable, merge, or bulk-edit behavior in this story.
- The customer-management wireframe shows a disable action, but that lifecycle behavior is not backed by the current PRD or architecture. Keep it out of this story until product planning explicitly adds it.
- Do not change customer identity fields such as customer ID or `tenant_id`.
- Do not introduce credit-policy enforcement logic on orders here; keep this story focused on maintaining master data.
- Do not build a separate edit-only form stack. Reuse the create-form primitives from Story 3.3.

### Technical Requirements

- Keep update logic inside `backend/domains/customers/` and reuse the same validation helpers and error contracts from Stories 3.2 and 3.4.
- Follow the architecture's request-scoped tenant context pattern, including `SET LOCAL app.tenant_id` or the repo's equivalent helper, before loading or updating the customer row.
- PATCH merge semantics must be explicit: omitted fields retain their stored values, explicit `null` values are only allowed for fields the schema marks nullable, and the implementation should use `exclude_unset=True` or an equivalent partial-update mechanism.
- Reuse the structured customer error contract from Story 3.3; return `409 Conflict` on optimistic-lock and duplicate conflicts, and `404 Not Found` for unknown customer IDs.
- Reject attempts to change immutable identity fields instead of silently ignoring them so clients receive deterministic feedback.
- Make unchanged-on-failure behavior explicit: invalid edits must not leave the row partially mutated.
- If the codebase already has an event or audit hook pattern by the time this story lands, emit a customer-updated event; otherwise leave a clean extension point for later audit logging.

### Testing Requirements

- Mandatory backend coverage:
  - update name/address/contact fields only
  - update credit limit only
  - update business number with valid checksum
  - duplicate business-number rejection
  - optimistic-lock/version conflict rejection
  - invalid checksum rejection
  - immutable field protection
  - 404 customer-not-found handling
  - unchanged row after failed update
- Frontend coverage should verify the edit form's prefilled state, validation, and submit behavior.

### Project Structure Notes

- Extend the same customer schemas, service, and routes introduced in Story 3.3.
- Keep edit UI components under `src/components/customers/` or `src/pages/customers/` and reuse the shared customer types/API helpers.
- Reuse the no-router screen-switch pattern established in Story 3.3 if the app still uses `src/App.tsx` as the direct entry point.

### Risks / Open Questions

- The wireframe hints at status changes such as disable/停用, but the PRD does not require lifecycle-state editing in Epic 3. Leave status toggles out unless later planning adds them explicitly.
- If downstream systems treat business number as a foreign reference, changing it may need broader event propagation later. This story should keep the update service structured so that follow-on work can hook into it.

### References

- `_bmad-output/epics.md` — Story 3.5 acceptance criteria and updated Epic 3 scope.
- `_bmad-output/planning-artifacts/prd.md` — FR17 validation on create/update and Journey 4 customer flow.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — customer domain model and `customers.update` contract.
- `research/ui-ux/01-survey-memo.md` — inline validation and Taiwan-localized form-entry expectations.
- `research/ui-ux/02-wireframes/01-customer-management.md` — edit/view action placement in the customer-management screen.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/6f0af2c8-127f-429b-8f9b-f9f78e0f0e40`

### Completion Notes List

- Story added to close the documented create/update gap between Epic 3, the PRD, and the architecture MCP surface.
- Update behavior was kept intentionally narrow so it extends create/duplicate logic instead of reopening customer-lifecycle scope.
- The story explicitly preserves immutable identity and tenant fields while allowing real master-data maintenance.

### File List

- `backend/domains/customers/service.py`
- `backend/domains/customers/routes.py`
- `backend/domains/customers/schemas.py`
- `backend/tests/domains/customers/test_update_service.py`
- `backend/tests/api/test_update_customer.py`
- `src/lib/api/customers.ts`
- `src/components/customers/CustomerForm.tsx`
- `src/components/customers/EditCustomerDialog.tsx`
- `src/pages/customers/CustomerListPage.tsx`
- `src/tests/customers/EditCustomerDialog.test.tsx`