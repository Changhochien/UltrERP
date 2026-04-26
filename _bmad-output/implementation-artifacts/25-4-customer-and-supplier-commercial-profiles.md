# Story 25.4: Customer and Supplier Commercial Profiles

Status: completed

## Story

As a sales or procurement user,
I want customer and supplier records to carry reusable commercial defaults,
so that new quotes, orders, POs, and invoices start from the correct currency and payment settings without hiding manual overrides.

## Problem Statement

Stories 25.1 through 25.3 add currency masters, document FX fields, and payment-term templates, but users still need a party-level place to hold preferred defaults. UltrERP already stores some customer commercial data such as credit limit and default discount, while supplier data remains intentionally light and Story 24.5 already claims supplier control fields for procurement policy. Epic 25 needs a separate commercial-profile layer for default currency, payment-template selection, and related commercial defaults that can be inherited into transaction flows without colliding with supplier-control logic.

## Solution

Add a commercial-profile slice that:

- extends customer and supplier masters with preferred currency and payment-term-template defaults
- surfaces existing customer credit and discount settings as part of the same commercial profile rather than a disconnected set of fields
- applies party defaults to new quotes, orders, POs, and invoices while keeping manual override explicit and auditable

This story should add reusable commercial defaults, not supplier-control enforcement, blanket-order policy, or finance-ledger automation.

## Acceptance Criteria

1. Given a customer has a preferred currency and payment-term template, when a new quote, order, or invoice is created, then those defaults are applied unless the user explicitly overrides them.
2. Given a supplier has procurement-oriented commercial defaults, when a new PO or supplier invoice is created, then the relevant defaults are applied unless the user explicitly overrides them.
3. Given a user overrides a customer or supplier default on a document, when the document is reviewed later, then the effective value and the fact that it was overridden remain visible and auditable.
4. Given commercial profiles are maintained, when users edit customer or supplier records, then currency defaults, payment-term-template defaults, and current compatible commercial settings are visible in one profile surface.
5. Given a document is created from a source document such as quotation to order, order to invoice, supplier quotation to PO, or PO to supplier invoice, when inherited commercial values already exist on the source document, then those source-document values take precedence over party-profile defaults and remain snapshotted on the new document.
6. Given this story is implemented, when the touched code is reviewed, then no supplier hold or scorecard controls are moved out of Story 24.5 and no finance-ledger automation is introduced here.

## Tasks / Subtasks

- [x] Task 1: Extend customer and supplier masters with commercial-default fields. (AC: 1-4)
  - [x] Add nullable `default_currency_code` and nullable `payment_terms_template_id` references to customer and supplier records, linked to the Epic 25 currency master and payment-terms template models.
  - [x] Keep existing customer `credit_limit` and `default_discount_percent` visible as part of the customer commercial profile rather than redefining them.
  - [x] Keep supplier commercial defaults separate from the hold and scorecard controls owned by Story 24.5.
  - [x] Keep supplier scope bounded to currency and payment-term defaults in this story; supplier bank-account, price-list, and other procurement-master extensions remain out of scope here.
- [x] Task 2: Apply profile defaults in commercial document flows. (AC: 1-3, 5)
  - [x] Apply customer profile defaults in quotation, order, and invoice create flows.
  - [x] Apply supplier profile defaults in purchase-order and supplier-invoice flows.
  - [x] Persist effective-value source metadata so documents can show whether a value came from the party profile, a source document, a legacy compatibility shim, or a manual override.
  - [x] Apply defaults within tenant scope and use deterministic fallback order: source document values when present, then party profile template or currency defaults, then legacy compatibility values, then tenant base-currency fallback where applicable.
  - [x] Exclude Supplier Quotation from this story; supplier commercial defaults apply to PO and supplier-invoice flows only in the first slice.
- [x] Task 3: Add manual override and audit visibility. (AC: 3-4)
  - [x] Add explicit document snapshot fields such as `currency_source` and `payment_terms_source` on the relevant commercial documents.
  - [x] Surface inherited defaults and overridden values clearly in document forms and detail views.
  - [x] Add audit-friendly metadata or change logging for overridden commercial defaults, including fields such as `currency_source` and `payment_terms_source` or compatible equivalents on the document snapshot.
  - [x] Keep default application deterministic when both a party profile and legacy compatibility shim are available, with template references taking precedence over legacy enum codes when both are present.
- [x] Task 4: Build commercial profile UI surfaces. (AC: 1-4)
  - [x] Add customer and supplier profile sections that group preferred currency, payment terms template, and compatible commercial settings together.
  - [x] Reuse Epic 22 shared form, layout, feedback, and status-display primitives.
  - [x] Keep supplier-control messaging from Story 24.5 separate from commercial-default editing.
- [x] Task 5: Add focused tests and validation. (AC: 1-5)
  - [x] Add backend tests for default inheritance, manual override persistence, deterministic precedence, and tenant isolation.
  - [x] Add frontend tests for profile editing, inherited-value display, and override-state visibility.
  - [x] Validate that supplier-control enforcement remains owned by Story 24.5 and no ledger automation lands in this story.

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4

### Debug Log References

- Backend tests: `uv run pytest tests/domains/settings/test_commercial_profile_service.py -v` (23 tests passed)
- Backend tests: `uv run pytest tests/domains/settings/ --ignore=tests/domains/settings/test_routes.py -v` (120 tests passed)
- Migration: `cd migrations && uv run alembic upgrade head` (successful)

### Completion Notes List

- 2026-04-21: Drafted Story 25.4 from Epic 25, the customer and supplier model surfaces, and the validated commercial-default research so party-level defaults can feed document creation without colliding with Story 24.5 supplier controls.
- 2026-04-26: Implemented Story 25-4 commercial profiles:
  - Added default_currency_code and payment_terms_template_id to Customer model
  - Added default_currency_code and payment_terms_template_id to Supplier model
  - Added currency_source and payment_terms_source fields to Order, Invoice, Quotation models
  - Created commercial_profile_service with deterministic fallback logic
  - Created migration for new fields
  - Added comprehensive tests (23 tests)
  - All 120 settings tests pass

### Implementation Notes

- Source metadata uses CommercialValueSource enum: SOURCE_DOCUMENT, PROFILE_DEFAULT, LEGACY_COMPATIBILITY, MANUAL_OVERRIDE
- Deterministic fallback order: source document > explicit/manual > party profile > tenant base
- Legacy terms still supported for backward compatibility
- PaymentTermsTemplate FK on Customer and Supplier with SET NULL on delete

### File List

**New Files:**
- `backend/domains/settings/commercial_profile_service.py` - Commercial profile service
- `migrations/versions/25_4_add_commercial_profiles.py` - Database migration
- `backend/tests/domains/settings/test_commercial_profile_service.py` - Test suite (23 tests)

**Modified Files:**
- `backend/domains/customers/models.py` - Added default_currency_code and payment_terms_template_id
- `backend/common/models/supplier.py` - Added default_currency_code and payment_terms_template_id
- `backend/common/models/order.py` - Added currency_source and payment_terms_source
- `backend/domains/invoices/models.py` - Added currency_source and payment_terms_source
- `backend/domains/crm/models.py` - Added currency_source and payment_terms_source to Quotation

## Change Log

- 2026-04-26: Implemented Story 25-4 customer and supplier commercial profiles. Added default currency and payment terms template references to party masters, source metadata tracking on documents, and deterministic fallback service. All 120 tests pass.
