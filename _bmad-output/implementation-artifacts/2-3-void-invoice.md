# Story 2.3: Void Invoice Before Filing Deadline

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a finance clerk,
I want to void an invoice within the allowed filing window,
so that I can correct mistakes while complying with Taiwan tax law.

## Acceptance Criteria

1. Given an invoice remains within the allowed void window for its issue date, when the clerk voids the invoice with a reason, then the invoice status changes to `voided`, the void reason is captured, and the system keeps explicit `replaces_invoice_id` and `replaced_by_invoice_id` linkage fields without auto-creating a replacement invoice in this story.
2. Given a successful void, when the system completes the operation, then all state changes are logged to the immutable audit log with actor, timestamp, reason, before/after state, and replacement-linkage values.
3. Given eGUI submission is enabled for the tenant or the invoice already has downstream submission state, when a void succeeds, then the system records a compensating void event in the outbox that preserves the original invoice number and any prior acknowledgment identifiers needed for downstream FIA notification.
4. Given an invoice is outside the allowed void window, when the clerk attempts to void it, then the system rejects the request with `Void window expired` and does not mutate invoice state.

## Tasks / Subtasks

- [ ] Task 1: Extend the invoice aggregate for void workflow state (AC: 1, 4)
  - [ ] Add void-related fields such as `voided_at`, `void_reason`, `void_window_expires_at`, `replaces_invoice_id`, and `replaced_by_invoice_id` to the invoice model or supporting tables.
  - [ ] Add migration files to persist void metadata without overwriting immutable invoice line snapshots.
  - [ ] Keep replacement linkage explicit so future reconciliation and audit flows can follow the void chain.
- [ ] Task 2: Implement regulatory-window void rules in the invoice service (AC: 1, 4)
  - [ ] Add a domain method such as `void_invoice()` in `backend/domains/invoices/service.py`.
  - [ ] Reject void attempts when the business date exceeds the documented cutoff of the 13th day of the first month of the next filing period.
  - [ ] Return a stable error contract with the message `Void window expired` and the computed deadline metadata.
- [ ] Task 3: Add audit and outbox integration hooks (AC: 2, 3)
  - [ ] Write an append-only `audit_log` entry capturing actor, action, reason, before/after state, prior eGUI submission state, and replacement-linkage values.
  - [ ] Create an `InvoiceVoided` domain event or equivalent hook carrying the original invoice number and any prior acknowledgment identifiers.
  - [ ] If eGUI is feature-flagged on, insert an outbox event in the same transaction as the invoice void; if off, keep the hook but skip outbound submission.
- [ ] Task 4: Expose the void flow through API and finance UI (AC: 1, 2, 4)
  - [ ] Add an endpoint such as `POST /api/v1/invoices/{invoice_id}/void`.
  - [ ] Create a finance-clerk confirmation UI with reason capture, deadline visibility, and clear failure messaging.
  - [ ] Ensure the UI does not present edit-in-place options for immutable invoices.
- [ ] Task 5: Add void-specific tests (AC: 1, 2, 3, 4)
  - [ ] Add backend tests for in-window success, post-deadline rejection, audit logging, outbox behavior behind the eGUI feature flag, and preservation of prior submission identifiers.
  - [ ] Add API tests for response codes and error payloads.

## Dev Notes

### Story Context

- Story 2.3 depends on Story 2.1 establishing the invoice aggregate and invoice identifiers.
- Story 2.7 complements this story by making invoice edits impossible; Story 2.3 is the sanctioned correction path.
- Story 2.5 and later eGUI work depend on this story leaving a reliable `InvoiceVoided` trail for artifact and submission workflows.

### Dependency Sequencing

- Implement Story 2.3 after Story 2.1.
- Prefer Story 2.3 before Story 2.7 so the sanctioned correction path exists before immutability becomes strict.
- Story 2.5 and later eGUI submission work should build on the void trail created here, not define a second correction path.

### Scope Guardrails

- Do not implement editable invoices. The correction path is void plus replacement workflow only.
- Do not implement FIA transport logic directly in this story; create the outbox hook only.
- Do not collapse audit logging into ad hoc application logs. Use the authoritative append-only audit model.

### Technical Requirements

- Void operations must be transactional: invoice status update, audit row insert, and conditional outbox insert all succeed or fail together.
- Keep the business-date comparison logic isolated in a policy/helper so future legal deadline refinements do not require service rewrites.
- Persist the clerk-provided void reason separately from generic metadata so it can be surfaced in audit and support workflows.
- Keep replacement linkage nullable but explicit; this story records the void chain and does not auto-create a replacement invoice.

### Architecture Compliance

- Follow the modular-monolith backend structure in `backend/domains/invoices/` and reuse shared helpers from `backend/common/`.
- Reuse the architecture's outbox pattern and immutable `audit_log` model.
- Preserve the invoice-first build order by keeping this change local to the invoice domain.

### Compliance Notes

- Product requirements now align to the documented filing-window rule rather than a same-month simplification.
- eGUI research states void/reissue must be completed by the 13th day of the first month of the next period and requires a new submission path when live submission is enabled.
- The system should compute the deadline in a policy/helper so the UI can stay simple while the backend preserves the real regulatory rule.

### Testing Requirements

- Mandatory backend coverage:
  - in-window void success
  - post-deadline void rejection
  - append-only audit log write
  - conditional outbox insert when eGUI is enabled
  - preservation of prior submission identifiers when already acknowledged
  - replacement-link persistence
- Frontend coverage should verify reason capture and user-visible failure message behavior.

### Project Structure Notes

- Suggested files:
  - `backend/domains/invoices/service.py`
  - `backend/domains/invoices/routes.py`
  - `backend/domains/invoices/schemas.py`
  - `backend/tests/domains/invoices/test_voiding.py`
  - `backend/tests/api/test_void_invoice.py`
  - `src/components/invoices/VoidInvoiceDialog.tsx`

### Risks / Open Questions

- Replacement invoice creation may be implemented as number reservation, replacement draft creation, or immediate clone flow. Keep the linkage explicit even if the UI path evolves.
- If eGUI is off, the outbox hook still needs to exist so later activation does not require redesign.

### References

- `_bmad-output/epics.md` — Story 2.3 acceptance criteria and invoice immutability context.
- `_bmad-output/planning-artifacts/prd.md` — regulatory void-window rule, audit trail expectations, and Taiwan compliance constraints.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — `InvoiceVoided` event, outbox model, audit log schema, and eGUI state model.
- `research/egui-compliance/01-survey-memo.md` — void/reissue timing notes and compliance context.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story created with transactional audit and outbox requirements explicit.
- Story updated to use the regulatory filing-window rule while keeping the deadline calculation isolated in policy code.

### File List

- `backend/domains/invoices/service.py`
- `backend/domains/invoices/routes.py`
- `backend/domains/invoices/schemas.py`
- `backend/tests/domains/invoices/test_voiding.py`
- `backend/tests/api/test_void_invoice.py`
- `src/components/invoices/VoidInvoiceDialog.tsx`
