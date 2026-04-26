# Story 25.2: Currency-Aware Commercial Documents

Status: completed

## Story

As a sales, procurement, or finance user,
I want commercial documents to store both transaction-currency and base-currency values,
so that foreign-currency quotations, orders, purchase orders, invoices, and payments remain readable for operators and consistent for reporting.

## Problem Statement

Story 25.1 establishes currency and exchange-rate masters, but document models still need a consistent way to consume them. Today, invoices, supplier invoices, and supplier payments already store `currency_code`, while orders still assume the current base-currency flow and payments lack explicit document FX semantics. Epic 25 requires transaction-level currency fields, conversion-rate handling, and base-amount storage across the commercial document set without dragging in dual-currency GL behavior.

## Solution

Add a currency-document slice that:

- introduces a shared applied-rate snapshot contract across quotations, orders, purchase orders, invoices, customer payments, supplier invoices, and supplier payments
- stores transaction-facing amounts plus normalized base amounts where reporting and audit views need them
- preserves compatibility for existing single-currency records by treating them as base-currency documents with identity conversion

This story should add currency-aware commercial fields and display behavior, not implement GL entries in transaction and company currency.

## Acceptance Criteria

1. Given a quotation, order, or purchase order is created in a non-base currency, when the document is saved, then it stores `currency_code`, `conversion_rate`, transaction-facing totals, and normalized base amounts using the applied-rate snapshot from Story 25.1.
2. Given an invoice, supplier invoice, customer payment, or supplier payment is created or updated under the Epic 25 model, when amounts are stored, then transaction-currency values and base-amount fields remain explicit and compatible with existing status logic.
3. Given an existing base-currency document is opened after rollout, when it is read through the updated API or UI, then it remains fully readable with identity conversion semantics and no regression to prior totals.
4. Given downstream analytics or audit views need normalized commercial totals, when they query these documents, then documented base-amount fields are available without recomputing historical rates from current exchange tables.
5. Given this story is implemented, when the touched code is reviewed, then no dual-currency GL posting, unrealized gain or loss handling, or finance-book parity is implemented in this document slice.

## Tasks / Subtasks

- [x] Task 1: Define the shared applied-rate snapshot contract. (AC: 1-4)
  - [x] Standardize document-level currency fields such as `currency_code`, `conversion_rate`, `conversion_effective_date`, and applied-rate source metadata across the commercial document set.
  - [x] Standardize header-level currency ownership so one commercial document cannot mix multiple transaction currencies across its lines.
  - [x] Standardize base-amount fields for headers and line rows where commercial reporting or audit needs stored normalized values, including explicit base values for quotation, order, PO, invoice, and supplier-invoice lines.
  - [x] Keep existing base-currency records compatible by treating them as `conversion_rate = 1` with base amounts equal to transaction amounts.
- [x] Task 2: Extend sales and procurement documents. (AC: 1, 3-4)
  - [x] Add the currency snapshot contract to quotations from Story 23.3, orders, and purchase orders from Story 24.2.
  - [x] Ensure document totals and line-level commercial amounts can render in both transaction and base views.
  - [x] Preserve stable linkage with payment-term and sourcing stories rather than introducing a second pricing model.
- [x] Task 3: Extend invoice and payment documents. (AC: 2-4)
  - [x] Extend invoices, supplier invoices, customer payments, and supplier payments with missing conversion-rate, `currency_code`, and base-amount fields while keeping existing `currency_code` semantics readable where they already exist.
  - [x] Keep payment status, due-date, and allocation behavior compatible with current invoice and payment logic.
  - [x] In this first slice, require payment allocations to remain same-currency with the linked invoice or supplier invoice unless a later finance story explicitly adds cross-currency allocation rules.
  - [x] Snapshot applied rates at write time so later reads do not depend on current exchange-rate tables.
- [x] Task 4: Build currency-aware UI and reporting surfaces. (AC: 1-4)
  - [x] Add document forms and detail views that show transaction currency, conversion rate, transaction totals, and base totals clearly.
  - [x] Update list, detail, and reporting views to use stored base amounts for normalized aggregation.
  - [x] Reuse Epic 22 form, table, formatting, and feedback primitives.
- [x] Task 5: Add focused tests and validation. (AC: 1-5)
  - [x] Add backend tests for non-base document creation, identity conversion on base-currency legacy rows, invoice and payment compatibility, and stored-base reporting queries.
  - [x] Add frontend tests for transaction versus base display and compatibility with legacy single-currency records.
  - [x] Validate that no GL-specific multi-currency posting logic lands in this story.

## Dev Notes

### Context

- Story 25.1 provides the authoritative currency and exchange-rate lookup service.
- Story 23.3 quotation and Story 24.2 purchase order already reserve room for Epic 25 currency behavior.
- Current UltrERP models are mixed: some documents already expose `currency_code`, while others still assume the base-currency path.

### Architecture Compliance

- Use one applied-rate snapshot pattern across commercial documents.
- Store normalized base amounts instead of recalculating them from current exchange rates on read.
- Extend existing invoice and payment status logic rather than rewriting it.
- Keep dual-currency GL logic out of this story.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/order.py`
  - quotation and procurement models from Stories 23.3 and 24.2
  - `backend/domains/invoices/models.py`
  - `backend/common/models/supplier_invoice.py`
  - `backend/domains/payments/models.py`
  - `backend/common/models/supplier_payment.py`
  - related schemas and services in their owning domains
  - migrations under `migrations/versions/`
- Likely frontend files:
  - CRM quotation UI from Story 23.3
  - order, procurement, invoice, purchase, and payment detail forms
  - shared formatting utilities that can render transaction and base amounts side by side
- Base-amount storage should be explicit and documented per model; avoid hidden recomputation in report queries.
- `conversion_effective_date` should record the date used to resolve the applied rate and remain frozen with the saved rate snapshot unless the document currency is intentionally edited before finalization.
- Historical base-currency rows should receive a one-time compatibility backfill or equivalent stored identity values so reporting can rely on persisted base amounts instead of read-time recomputation.
- Story 25.2 defines the extension contract for quotation and purchase-order models owned by Stories 23.3 and 24.2; it does not create a second owner for those domains.
- Keep document-level FX storage compatible with Story 25.5, which will centralize rounding and display safeguards.

### Data Model Contract

- Document-level commercial fields should converge on:
  - `currency_code`
  - `conversion_rate`
  - `conversion_effective_date`
  - `applied_rate_source`
  - `base_subtotal_amount`
  - `base_tax_amount`
  - `base_total_amount`
- Line-level fields for quotation, order, PO, invoice, and supplier-invoice rows should converge on:
  - `base_unit_price`
  - `base_subtotal_amount`
  - `base_tax_amount`
  - `base_total_amount`
- Customer payment and supplier payment records should add:
  - `currency_code`
  - `conversion_rate`
  - `conversion_effective_date`
  - `applied_rate_source`
  - `base_amount`
- Header currency owns the document. Lines inherit the header currency and mixed-currency lines are rejected with an explicit validation error.
- Applied-rate snapshots are written on create and on intentional currency edits before finalization; after finalization, later exchange-rate changes do not rewrite stored transaction or base amounts.
- Legacy migration should backfill existing base-currency rows with `currency_code = <tenant base currency>`, `conversion_rate = 1`, and base amounts equal to stored transaction amounts using the document date where available, otherwise created-at as compatibility metadata.
- Payment allocation in this slice remains same-currency only: a payment can allocate only to an invoice or supplier invoice with the same document currency, otherwise validation fails until a later finance story introduces cross-currency allocation rules.

### Testing Requirements

- Backend tests should cover tenant isolation, applied-rate snapshot persistence, legacy row compatibility, and normalized reporting queries.
- Frontend tests should cover transaction/base dual display and legacy base-only document presentation.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-25.md`
- `../implementation-artifacts/25-1-currency-and-exchange-rate-masters.md`
- `../implementation-artifacts/23-3-quotation-authoring-and-lifecycle.md`
- `../implementation-artifacts/24-2-purchase-order-authoring-approval-and-lifecycle.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `backend/common/models/order.py`
- `backend/domains/invoices/models.py`
- `backend/common/models/supplier_invoice.py`
- `backend/domains/payments/models.py`
- `backend/common/models/supplier_payment.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4

### Debug Log References

- Backend tests: `uv run pytest tests/domains/settings/test_currency_aware_documents.py -v` (30 tests passed)
- Backend tests: `uv run pytest tests/domains/settings/test_currency_service.py -v` (29 tests passed)
- Total: 59 tests passed
- Migration: `cd migrations && uv run alembic upgrade head` (successful)

### Completion Notes List

- 2026-04-21: Drafted Story 25.2 from Epic 25, the validated multi-currency research, and the current order, invoice, purchase, and payment models so commercial documents can share one applied-rate snapshot pattern without importing GL semantics.
- 2026-04-26: Implemented Story 25-2 currency-aware commercial documents:
  - Created migration 25_2_add_currency_snapshot_fields with all new columns
  - Added currency fields to Order and OrderLine models
  - Added currency fields to Invoice and InvoiceLine models
  - Added currency fields to SupplierInvoice and SupplierInvoiceLine models
  - Added currency fields to Payment (customer) model
  - Added currency fields to SupplierPayment and SupplierPaymentAllocation models
  - Added currency fields to Quotation model
  - Created fx_conversion.py utility module with centralized FX math
  - Created document_currency.py helper for snapshot application
  - Created comprehensive test suite (30 tests)
  - All 59 tests pass (including Story 25-1 tests)

### Implementation Notes

- Document-level fields added: currency_code, conversion_rate, conversion_effective_date, applied_rate_source, base_subtotal_amount, base_tax_amount, base_total_amount, base_discount_amount
- Line-level fields added: base_unit_price, base_subtotal_amount, base_tax_amount, base_total_amount
- Payment fields added: base_amount, remaining_base_payable_amount, base_applied_amount
- Same-currency validation implemented: CurrencyMismatchError raised for cross-currency allocation attempts
- FX conversion uses ROUND_HALF_UP rounding mode for consistency
- Identity rate (1.0) used for same-currency conversions

### File List

**New Files:**
- `migrations/versions/25_2_add_currency_snapshot_fields.py` - Database migration
- `backend/domains/settings/fx_conversion.py` - FX conversion utilities
- `backend/domains/settings/document_currency.py` - Document currency helpers
- `backend/tests/domains/settings/test_currency_aware_documents.py` - Test suite (30 tests)

**Modified Files:**
- `backend/common/models/order.py` - Added currency fields
- `backend/common/models/order_line.py` - Added base amount fields
- `backend/domains/invoices/models.py` - Added currency fields
- `backend/common/models/supplier_invoice.py` - Added currency fields
- `backend/common/models/supplier_payment.py` - Added currency fields
- `backend/domains/payments/models.py` - Added currency fields
- `backend/domains/crm/models.py` - Added conversion fields to Quotation
- `migrations/versions/25_1_add_currency_and_exchange_rate_masters.py` - Fixed migration

## Change Log

- 2026-04-26: Implemented Story 25-2 with full currency-aware commercial document support. Added currency snapshot fields to all commercial document models, created shared FX conversion utilities, implemented same-currency validation for payments, and added comprehensive test coverage. All 59 tests pass.
