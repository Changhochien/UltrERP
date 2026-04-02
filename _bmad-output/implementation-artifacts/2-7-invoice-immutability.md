# Story 2.7: Enforce Immutable Invoice Content

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a system,
I want invoices to be immutable after creation,
so that we comply with Taiwan tax requirements.

## Acceptance Criteria

1. Given an invoice has been created, when any user or internal code path attempts to modify invoice number, customer binding, buyer identity, line items, line sequence numbers, quantity, unit price, tax type, tax rate, tax amount, subtotal, tax total, grand total, issue date, filing-period identity, or replacement linkage after it has been set, then the system rejects the change with `Invoices are immutable after creation`.
2. Given an invoice requires correction, when an operator uses a sanctioned correction path, then only void-based workflows are permitted.

## Tasks / Subtasks

- [ ] Task 1: Define which invoice fields are immutable versus operationally mutable (AC: 1, 2)
  - [ ] Mark invoice number, customer identity, buyer identity, invoice lines, line sequence numbers, subtotal, tax totals, grand total, and issue-period identity as immutable financial content.
  - [ ] Allow only sanctioned operational fields such as status transitions, artifact metadata, and eGUI submission state to change through dedicated workflows.
  - [ ] Treat `replaces_invoice_id` and `replaced_by_invoice_id` as workflow-owned fields that become immutable once written.
  - [ ] Document the distinction in the invoice domain module so future stories do not over- or under-enforce immutability.
- [ ] Task 2: Enforce immutability in the invoice service and API layer (AC: 1, 2)
  - [ ] Add guard methods in `backend/domains/invoices/service.py` that reject attempts to edit immutable content after creation.
  - [ ] Ensure any future update endpoints either do not exist or explicitly route to rejection for immutable fields.
  - [ ] Ensure sanctioned workflows can set void/replacement linkage exactly once without enabling later arbitrary relinking.
  - [ ] Return the stable error message `Invoices are immutable after creation`.
- [ ] Task 3: Add persistence-level protection for immutable invoice content (AC: 1)
  - [ ] Add mandatory database constraints, triggers, or equivalent persistence protections to block mutation of immutable invoice fields outside sanctioned flows; service-layer guards alone are insufficient.
  - [ ] Keep the persistence rule compatible with allowed status/void/artifact/eGUI state changes.
- [ ] Task 4: Add immutability tests (AC: 1, 2)
  - [ ] Add service tests attempting to edit customer, buyer identity, lines, linkage fields, and monetary fields after creation.
  - [ ] Add persistence-level tests if triggers or DB guards are introduced.
  - [ ] Add API tests confirming the rejection path is stable and explicit.

## Dev Notes

### Story Context

- Story 2.7 codifies the invariant that makes Story 2.3 the only correction path.
- Story 2.5 and later eGUI workflows require invoice content to remain stable once archival/submission pipelines are introduced.
- This story should reduce future regression risk across UI, API, MCP, and internal service code.

### Dependency Sequencing

- Implement Story 2.7 after Story 2.3 so the sanctioned correction path is already defined.
- Prefer Story 2.7 before Story 2.5 promotion to production use so archived and submitted invoice artifacts are generated from data that is already protected by immutable-content rules.
- If Story 2.1 lacks the fields needed to distinguish immutable financial content from operational state, refine Story 2.1 first rather than weakening this story.

### Scope Guardrails

- Do not make the entire invoice row frozen if that would block valid status, void, archival, or eGUI transitions.
- Do not implement silent auto-cloning or auto-voiding as a substitute for edit rejection.
- Do not rely on UI-only protection; immutability must be enforced server-side and, where practical, at the database level.

### Technical Requirements

- Immutable financial content includes invoice number, customer binding, buyer identity, line items, tax values, subtotal, total, and issue-period identity.
- Operational lifecycle fields may remain mutable only through explicit workflow methods.
- Void and replacement linkage fields may only be written by sanctioned workflows and become immutable once set.
- Error messaging must be stable so UI and API clients can present a consistent explanation.

### Architecture Compliance

- Enforcement belongs in `backend/domains/invoices/` with optional persistence-level support via migrations.
- Keep the invoice aggregate authoritative and avoid scattering immutability rules across unrelated modules.
- This rule must remain compatible with outbox, audit, artifact, and eGUI state transitions.

### Testing Requirements

- Mandatory coverage:
  - attempted customer reassignment after creation
  - attempted buyer-identity mutation after creation
  - attempted line-item mutation after creation
  - attempted totals mutation after creation
  - attempted replacement-link mutation after initial write
  - successful void/status workflow transitions that do not violate the immutability rule

### Project Structure Notes

- Suggested files:
  - `backend/domains/invoices/service.py`
  - `backend/domains/invoices/models.py`
  - `backend/tests/domains/invoices/test_immutability.py`
  - `backend/tests/api/test_invoice_immutability.py`
  - `migrations/versions/*_enforce_invoice_immutability.py`

### Risks / Open Questions

- A naive row-level freeze will break valid workflow transitions. Field-level immutability is required.
- DB-level enforcement is mandatory for this story; UI or service-level guards alone are not sufficient for compliance.
- If future admin tooling needs read-only annotations or reopen flows, those must be modeled explicitly and cannot weaken the invoice immutability invariant.

### References

- `_bmad-output/epics.md` — Story 2.7 acceptance criteria and invoice lifecycle context.
- `_bmad-output/planning-artifacts/prd.md` — immutable invoice requirement and Taiwan tax compliance notes.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — invoice domain model, audit/outbox compatibility, and eGUI state transitions.
- `_bmad-output/implementation-artifacts/2-3-void-invoice.md` — sanctioned correction path dependency.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story updated with an explicit immutable-field inventory and mandatory DB-level enforcement.
- Void remains the only sanctioned correction path.

### File List

- `backend/domains/invoices/service.py`
- `backend/domains/invoices/models.py`
- `backend/tests/domains/invoices/test_immutability.py`
- `backend/tests/api/test_invoice_immutability.py`
- `migrations/versions/*_enforce_invoice_immutability.py`
