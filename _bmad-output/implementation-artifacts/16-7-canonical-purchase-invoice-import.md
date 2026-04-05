# Story 16.7: Canonical Purchase Invoice Import

Status: done

## Story

As a migration operator,
I want staged purchase invoice headers and lines imported into a canonical AP schema,
So that historical supplier invoice data is available in UltrERP without forcing purchase history into sales AR tables or unsupported holding records.

## Acceptance Criteria

**AC1:** Purchase invoice headers land in `supplier_invoices`
**Given** normalized supplier master data and staged tbsslipj headers are available
**When** the canonical import step runs
**Then** each purchase invoice header is upserted into `supplier_invoices`
**And** supplier resolution uses the normalized supplier-party mapping from Story 16.2
**And** the imported record keeps deterministic tenant-scoped identity and lineage

**AC2:** Purchase invoice lines land in `supplier_invoice_lines`
**Given** staged tbsslipdtj rows are available for a purchase invoice
**When** canonical import processes the purchase-history slice
**Then** each purchase invoice line is upserted into `supplier_invoice_lines`
**And** product references reuse the product_code_mapping flow already established in Epic 15
**And** line-level totals reconcile back to the imported supplier invoice header through allocated tax amounts

**AC3:** Replay safety prevents duplicates
**Given** the same batch is imported again
**When** canonical import reruns
**Then** deterministic tenant-scoped IDs and upsert semantics prevent duplicate supplier invoices and supplier invoice lines
**And** payment-adjacent tbsspay/tbsprepay rows remain in unsupported holding until a verified AP payment model exists

## Tasks / Subtasks

- [x] **Task 1: Add canonical AP tables and ORM anchors** (AC1, AC2, AC3)
  - [x] Add `SupplierInvoiceStatus`, `SupplierInvoice`, and `SupplierInvoiceLine` models
  - [x] Add Alembic schema for `supplier_invoices` and `supplier_invoice_lines`
  - [x] Export the new models through `backend/common/models/__init__.py`

- [x] **Task 2: Extend canonical import for purchase invoices** (AC1, AC2)
  - [x] Import normalized suppliers before purchase history runs
  - [x] Upsert tbsslipj rows into `supplier_invoices`
  - [x] Upsert tbsslipdtj rows into `supplier_invoice_lines`
  - [x] Allocate header tax across imported lines so totals reconcile

- [x] **Task 3: Preserve replay safety and CLI observability** (AC3)
  - [x] Extend `CanonicalImportResult` counters for suppliers and supplier invoices
  - [x] Update CLI summary output with supplier-invoice import counts
  - [x] Keep tbsspay/tbsprepay on the holding path until a verified AP payment model exists

- [x] **Task 4: Validate the canonical purchase-invoice path** (AC1, AC2, AC3)
  - [x] Add focused canonical-import coverage for supplier invoices
  - [x] Re-run validation coverage for the legacy-import validation slice

## Dev Notes

### Repo Reality

- Epic 16 originally covered FR67 in the epic requirements, but there was no dedicated story artifact for canonical purchase-invoice import.
- The repo already had supplier master data and purchase-history staging primitives, so the missing implementation surface was the AP landing zone itself.
- The correct target is a dedicated AP schema (`supplier_invoices`, `supplier_invoice_lines`), not the sales-side `invoices` table and not unsupported-history holding.

### Critical Warnings

- Do **not** coerce purchase invoice history into sales/customer AR tables.
- Do **not** import tbsspay or tbsprepay into the AP invoice schema; they remain payment-adjacent deferred scope.
- Do **not** remove deterministic UUID generation or replay-safe upsert behavior; reruns must stay lossless and idempotent.

### Implementation Direction

- Canonical import now creates/imports suppliers before purchase history.
- tbsslipj headers land in `supplier_invoices`; tbsslipdtj lines land in `supplier_invoice_lines`.
- Header tax is allocated back across imported lines so line totals reconcile with supplier invoice headers.

### Validation Follow-up

- `uv run pytest tests/domains/legacy_import/test_canonical.py -q`
- `uv run pytest tests/domains/legacy_import/test_validation.py -q`

## References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.7
- `backend/common/models/supplier_invoice.py` - AP ORM anchors
- `backend/domains/legacy_import/canonical.py` - purchase invoice canonical import path
- `backend/domains/legacy_import/cli.py` - canonical import CLI summary
- `migrations/versions/9f2b6c4d1e77_add_supplier_invoice_tables.py` - supplier invoice schema migration
- `docs/legacy/purchase-invoice-canonical-target.md` - AP target note
- `backend/tests/domains/legacy_import/test_canonical.py` - focused supplier invoice canonical tests

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Completion Notes List

- Added dedicated supplier-invoice ORM models and migration-backed tables for canonical AP history.
- Extended canonical import to load normalized suppliers first, then land tbsslipj/tbsslipdtj into supplier invoice tables.
- Kept tbsspay/tbsprepay on the holding path because no verified AP payment model exists yet.
- Updated canonical import CLI output and legacy docs to surface the new AP target.
- Validated the supplier-invoice canonical path with focused pytest coverage.

### File List

- backend/common/models/supplier_invoice.py
- backend/common/models/__init__.py
- backend/domains/legacy_import/canonical.py
- backend/domains/legacy_import/cli.py
- migrations/versions/9f2b6c4d1e77_add_supplier_invoice_tables.py
- backend/tests/domains/legacy_import/test_canonical.py
- docs/legacy/purchase-invoice-canonical-target.md

### Change Log

- 2026-04-05: Documented the canonical purchase-invoice import path as a dedicated Epic 16 story artifact after implementing the AP landing zone.