# Story 2.4: Validate Invoice Totals and Rounding

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a finance clerk,
I want the system to validate invoice totals before printing,
so that I don't issue incorrect invoices.

## Acceptance Criteria

1. Given an invoice is being prepared for preview, print, PDF export, or downstream issuance, when persisted line items and tax are evaluated, then the system validates that the recomputed line subtotals and per-line tax amounts reconcile with the persisted summary subtotal, tax total, and invoice total.
2. Given the validation fails, when the clerk attempts to preview, print, or otherwise finalize the invoice, then the system blocks the action.
3. Given validation fails, when the clerk is shown the error, then the UI and API both expose a clear discrepancy message including the mismatch amount.
4. Given an invoice was issued using either tax-exclusive or tax-inclusive pricing, when totals are recomputed, then the validator applies the same persisted pricing mode and uses an explicit `ROUND_HALF_UP` rule.

## Tasks / Subtasks

- [ ] Task 1: Implement a backend totals validation module (AC: 1, 2, 3, 4)
  - [ ] Create `backend/domains/invoices/validators.py` or equivalent.
  - [ ] Recompute subtotal, per-line tax, summary tax total, and grand total from persisted line snapshots using `Decimal` arithmetic.
  - [ ] Apply an explicit `ROUND_HALF_UP` rule at the sanctioned currency boundary before comparing persisted totals.
  - [ ] Respect the persisted invoice pricing mode so tax-inclusive and tax-exclusive invoices validate correctly.
  - [ ] Return structured discrepancy data instead of a boolean-only result.
- [ ] Task 2: Enforce validation at the invoice workflow boundaries (AC: 1, 2)
  - [ ] Invoke totals validation before print preview, print execution, PDF export, and any issuance/finalization transition.
  - [ ] Prevent downstream actions from executing when validation fails.
  - [ ] Keep the validation reusable so later stories do not reimplement the same logic in separate modules.
- [ ] Task 3: Surface validation errors in API and finance UI (AC: 2, 3)
  - [ ] Add a stable API error contract for totals mismatch responses.
  - [ ] Create UI messaging such as `src/components/invoices/InvoiceValidationBanner.tsx` that shows the discrepancy amount and affected totals.
  - [ ] Ensure the frontend never bypasses backend validation with client-only assumptions.
- [ ] Task 4: Add totals-validation tests (AC: 1, 2, 3, 4)
  - [ ] Add backend tests for valid totals, subtotal mismatch, per-line tax mismatch, summary tax mismatch, tax-inclusive and tax-exclusive pricing modes, and rounding edge cases.
  - [ ] Add API tests verifying that blocked actions return the correct error payload.

## Dev Notes

### Story Context

- Story 2.4 depends on Story 2.1 persisting line-level subtotals, tax values, and invoice totals.
- Story 2.2 and Story 2.6 should use this validation as a gate before print/PDF actions.
- Story 2.5 and eGUI issuance flows also depend on validated totals because incorrect totals propagate into MIG 4.1 artifacts.

### Dependency Sequencing

- Implement Story 2.4 immediately after Story 2.1.
- Treat Story 2.4 as the shared prerequisite for Story 2.2, Story 2.5, and Story 2.6 because those workflows should not invent their own totals checks.
- If Story 2.1 does not ship the required persisted pricing-mode and line-snapshot data, fix that gap before starting downstream output or archive stories.

### Scope Guardrails

- Do not duplicate totals logic separately in print, PDF, archival, or eGUI modules.
- Do not trust frontend-only calculations for issuance-critical validation.
- Do not mutate invoice data during validation; this story validates and blocks, it does not auto-correct persisted invoice records.

### Technical Requirements

- Use backend-owned `Decimal` arithmetic only, with explicit `ROUND_HALF_UP` rounding.
- Treat persisted invoice lines as the source of truth for recomputation.
- Validation must respect the persisted pricing mode used at issuance; do not assume tax-exclusive pricing for every invoice.
- Validation output should include enough detail to debug discrepancies without leaking unrelated internal implementation state.
- Block all downstream invoice output operations when validation fails.

### Architecture Compliance

- Keep validation logic under `backend/domains/invoices/`.
- Reuse shared error/response helpers from `backend/common/` if they exist.
- Keep the invoice aggregate as the single source of truth and avoid side-channel calculations.

### Testing Requirements

- Mandatory backend coverage:
  - valid invoice totals
  - subtotal mismatch
  - per-line tax mismatch
  - summary tax mismatch
  - tax-inclusive and tax-exclusive pricing modes
  - rounding/precision edge cases
  - blocked preview/print/export hooks
- UI tests should verify discrepancy messaging, not reproduce the full accounting logic.

### Project Structure Notes

- Suggested files:
  - `backend/domains/invoices/validators.py`
  - `backend/tests/domains/invoices/test_validation.py`
  - `backend/tests/api/test_invoice_validation.py`
  - `src/components/invoices/InvoiceValidationBanner.tsx`

### Risks / Open Questions

- If Story 2.1 stores only aggregate totals and not stable line snapshots or a persisted pricing mode, this story will force schema refinement. Use persisted line data as the validation basis.
- Precision and rounding rules must remain compatible with later MIG 4.1 XML generation and PDF/print presentation.

### References

- `_bmad-output/epics.md` — Story 2.4 acceptance criteria and related print/export stories.
- `_bmad-output/planning-artifacts/prd.md` — invoice immutability and print fidelity constraints.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — invoice line-level tax requirements and MIG 4.1 data-shape expectations.
- `research/egui-compliance/01-survey-memo.md` — tax amount and total amount schema requirements.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story created as a shared invariant story for print, PDF, and archival workflows.
- Validation is intentionally backend-owned, per-line aware, and reusable across downstream invoice lifecycle actions.

### File List

- `backend/domains/invoices/validators.py`
- `backend/tests/domains/invoices/test_validation.py`
- `backend/tests/api/test_invoice_validation.py`
- `src/components/invoices/InvoiceValidationBanner.tsx`
