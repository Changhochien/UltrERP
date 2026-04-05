# Story 16.11: Canonical AP Payment Architecture

Status: done

## Story

As an ERP engineer,
I want the canonical AP payment tables and relationships implemented,
So that the deferred supplier-payment import has a stable backend target before legacy allocation logic is turned on.

## Acceptance Criteria

**AC1:** The backend ships first-class AP payment tables
**Given** AP settlement history needs its own schema foundation
**When** the backend migration runs
**Then** `supplier_payments` and `supplier_payment_allocations` exist as first-class tables
**And** they use AP-specific enums for payment kind, payment status, and allocation kind
**And** the schema keeps supplier payments separate from the AR `payments` table

**AC2:** The ORM layer models supplier cash events and invoice allocations
**Given** future supplier payments may be unapplied, partially applied, or fully applied
**When** the ORM layer is loaded
**Then** `SupplierPayment` supports prepayment, special-payment, and adjustment kinds
**And** `SupplierPaymentAllocation` bridges supplier payments to `supplier_invoices`
**And** the supplier-invoice model exposes the reverse allocation relationship

**AC3:** The architecture stays ahead of guessed import logic
**Given** the legacy payment columns are still only partially verified
**When** this backend foundation ships
**Then** no guessed canonical import path is added for `tbsspay` or `tbsprepay`
**And** the repo keeps those rows in holding until the AP payment verification checklist is satisfied

**AC4:** The new foundation has focused validation
**Given** the new AP payment architecture files are added
**When** focused backend validation runs
**Then** the supplier payment model tests pass
**And** Ruff passes on the touched models, migration, and test file

## Tasks / Subtasks

- [x] **Task 1: Add AP payment ORM models** (AC1, AC2)
  - [x] Add `SupplierPaymentKind`, `SupplierPaymentStatus`, and `SupplierPaymentAllocationKind`
  - [x] Add `SupplierPayment`
  - [x] Add `SupplierPaymentAllocation`

- [x] **Task 2: Wire the new model into the common schema surface** (AC2)
  - [x] Export supplier payment models through `backend/common/models/__init__.py`
  - [x] Add reverse allocation relationship on `SupplierInvoice`

- [x] **Task 3: Add the database migration** (AC1)
  - [x] Add Alembic revision for `supplier_payments`
  - [x] Add Alembic revision for `supplier_payment_allocations`
  - [x] Create indexes for tenant/date/status and allocation lookups

- [x] **Task 4: Prove the architecture with focused validation** (AC4)
  - [x] Add focused object-level model tests for enums and relationships
  - [x] Run focused pytest coverage for the new test file
  - [x] Run Ruff on the touched models, migration, and test file

## Dev Notes

### Repo Reality

- The design work in Story 16.10 established that AP payment history could not safely reuse the AR `payments` table.
- The repo still does not have verified enough legacy-column semantics to import `tbsspay` or `tbsprepay` into canonical AP tables.
- That made a schema-first architecture step the safe next move: ship the backend target now, keep the import boundary intact.

### Critical Warnings

- Do **not** treat this story as approval to import legacy AP payment rows yet.
- Do **not** add guessed supplier-payment API or UI behavior that implies the legacy allocation mapping is already known.
- Do **not** collapse AP payment history back into the AR `payments` model after this foundation exists.

### Implementation Direction

- `supplier_payments` models supplier-side cash events.
- `supplier_payment_allocations` models many-to-many settlement links from supplier payments to supplier invoices.
- The current canonical-import behavior stays unchanged: payment-adjacent legacy rows remain in holding until field verification finishes.

### Validation Follow-up

- `uv run pytest tests/common/test_supplier_payment_models.py -q`
- `uv run ruff check common/models/supplier_payment.py common/models/supplier_invoice.py common/models/__init__.py tests/common/test_supplier_payment_models.py ../migrations/versions/84a7c8f1d2ab_add_supplier_payment_tables.py`

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.11
- `backend/common/models/supplier_payment.py` - AP payment ORM foundation
- `backend/common/models/supplier_invoice.py` - reverse allocation relationship
- `backend/common/models/__init__.py` - common model export surface
- `migrations/versions/84a7c8f1d2ab_add_supplier_payment_tables.py` - AP payment schema migration
- `backend/tests/common/test_supplier_payment_models.py` - focused model tests
- `docs/legacy/ap-payment-model.md` - AP payment design note

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- Added first-class AP payment ORM models and allocation relationships.
- Added a dedicated migration for `supplier_payments` and `supplier_payment_allocations`.
- Kept canonical import behavior unchanged so legacy payment rows still remain in holding until verified.
- Added focused backend model tests and passed focused Ruff validation for the new architecture slice.

### File List

- backend/common/models/supplier_payment.py
- backend/common/models/supplier_invoice.py
- backend/common/models/__init__.py
- migrations/versions/84a7c8f1d2ab_add_supplier_payment_tables.py
- backend/tests/common/test_supplier_payment_models.py
- docs/legacy/ap-payment-model.md

### Change Log

- 2026-04-06: Documented the validated AP payment schema foundation as a dedicated Epic 16 story artifact.