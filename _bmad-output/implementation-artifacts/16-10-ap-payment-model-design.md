# Story 16.10: AP Payment Model Design

Status: done

## Story

As a migration operator and ERP architect,
I want a verified canonical model for supplier payments and prepayments,
So that `tbsspay` and `tbsprepay` can be imported later without corrupting AR payment semantics.

## Acceptance Criteria

**AC1:** The design explains why the current AR payment model is insufficient
**Given** the existing `payments` table is reviewed
**When** the AP payment design is documented
**Then** the note explains why the current customer- and invoice-centric model is not a safe target for supplier-side history
**And** it avoids reusing AR reconciliation fields for AP settlement semantics

**AC2:** The design defines a canonical AP payment target
**Given** supplier payments may be unapplied, partially applied, or fully applied
**When** the AP model is described
**Then** it introduces `supplier_payments` as the canonical supplier cash-event table
**And** it introduces `supplier_payment_allocations` as the many-to-many bridge to `supplier_invoices`
**And** prepayments are represented as a supplier payment kind rather than a separate ad hoc operational table

**AC3:** The design preserves replay-safe import boundaries
**Given** legacy payment-column semantics remain partially unverified
**When** the implementation boundary is written down
**Then** `tbsspay` and `tbsprepay` stay in holding until supplier linkage, amount/sign rules, ROC dates, and invoice-link columns are verified
**And** the design includes a verification checklist that must pass before implementation starts

## Tasks / Subtasks

- [x] **Task 1: Review the current payment model and document the mismatch** (AC1)
  - [x] Inspect the current AR `payments` ORM and schema surface
  - [x] Record why single-invoice AR reconciliation is not enough for AP settlement history

- [x] **Task 2: Define the canonical AP payment target** (AC2)
  - [x] Define `supplier_payments`
  - [x] Define `supplier_payment_allocations`
  - [x] Define how prepayments fit the same model without a separate ad hoc table

- [x] **Task 3: Define the import boundary and verification gate** (AC3)
  - [x] Record the staged-to-holding boundary that stays in place until field semantics are verified
  - [x] Record the checklist needed before canonical AP payment import starts
  - [x] Link the new design note from the existing AP migration docs

## Dev Notes

### Repo Reality

- Story 16.5 already stages `tbsspay` and `tbsprepay`, but the repo intentionally kept them in holding because no verified AP settlement model existed.
- The existing `payments` domain is built for customer receipts and one-invoice-centric reconciliation.
- The shipped purchases workspace is currently invoice-centric and read-only, so the next AP step needed to be a model design, not a rushed import.

### Critical Warnings

- Do **not** import supplier-side payment history into the current AR `payments` table.
- Do **not** create allocation rows until invoice-link columns are proven on real legacy samples.
- Do **not** split prepayments into a parallel operational table when the same supplier payment model can represent both unapplied and applied supplier cash events.

### Implementation Direction

- The future canonical target is `supplier_payments` plus `supplier_payment_allocations`.
- Prepayments are modeled as a `supplier_payments.payment_kind`, not as an unrelated side table.
- The existing holding path remains the right boundary until the verification checklist is satisfied.

### Validation Follow-up

- Cross-check the design note against `backend/domains/payments/models.py` before implementation starts.
- Revisit `docs/legacy/canonical-import-target-matrix.md` and `docs/legacy/purchase-invoice-canonical-target.md` whenever AP payment import is actually built.

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.10
- `docs/legacy/ap-payment-model.md` - canonical AP payment design note
- `docs/legacy/purchase-invoice-canonical-target.md` - current AP invoice target and deferrals
- `docs/legacy/canonical-import-target-matrix.md` - holding-path target matrix
- `backend/domains/payments/models.py` - current AR payment model
- `backend/domains/payments/schemas.py` - current AR payment API contract

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- Documented why the current AR payment model cannot safely absorb supplier payment history.
- Defined a future canonical AP target around `supplier_payments` and `supplier_payment_allocations`.
- Kept the current holding-path boundary explicit until the remaining legacy payment semantics are verified.
- Linked the design note from the existing AP migration docs so future implementation starts from an explicit model.

### File List

- docs/legacy/ap-payment-model.md
- docs/legacy/purchase-invoice-canonical-target.md
- docs/legacy/canonical-import-target-matrix.md
- docs/legacy/migration-plan.md

### Change Log

- 2026-04-05: Documented the deferred AP payment and prepayment target as a dedicated Epic 16 story artifact.