# Story 25.4: Customer and Supplier Commercial Profiles

Status: drafted

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

- [ ] Task 1: Extend customer and supplier masters with commercial-default fields. (AC: 1-4)
  - [ ] Add nullable `default_currency_code` and nullable `payment_terms_template_id` references to customer and supplier records, linked to the Epic 25 currency master and payment-terms template models.
  - [ ] Keep existing customer `credit_limit` and `default_discount_percent` visible as part of the customer commercial profile rather than redefining them.
  - [ ] Keep supplier commercial defaults separate from the hold and scorecard controls owned by Story 24.5.
  - [ ] Keep supplier scope bounded to currency and payment-term defaults in this story; supplier bank-account, price-list, and other procurement-master extensions remain out of scope here.
- [ ] Task 2: Apply profile defaults in commercial document flows. (AC: 1-3, 5)
  - [ ] Apply customer profile defaults in quotation, order, and invoice create flows.
  - [ ] Apply supplier profile defaults in purchase-order and supplier-invoice flows.
  - [ ] Persist effective-value source metadata so documents can show whether a value came from the party profile, a source document, a legacy compatibility shim, or a manual override.
  - [ ] Apply defaults within tenant scope and use deterministic fallback order: source document values when present, then party profile template or currency defaults, then legacy compatibility values, then tenant base-currency fallback where applicable.
  - [ ] Exclude Supplier Quotation from this story; supplier commercial defaults apply to PO and supplier-invoice flows only in the first slice.
- [ ] Task 3: Add manual override and audit visibility. (AC: 3-4)
  - [ ] Add explicit document snapshot fields such as `currency_source` and `payment_terms_source` on the relevant commercial documents.
  - [ ] Surface inherited defaults and overridden values clearly in document forms and detail views.
  - [ ] Add audit-friendly metadata or change logging for overridden commercial defaults, including fields such as `currency_source` and `payment_terms_source` or compatible equivalents on the document snapshot.
  - [ ] Keep default application deterministic when both a party profile and legacy compatibility shim are available, with template references taking precedence over legacy enum codes when both are present.
- [ ] Task 4: Build commercial profile UI surfaces. (AC: 1-4)
  - [ ] Add customer and supplier profile sections that group preferred currency, payment terms template, and compatible commercial settings together.
  - [ ] Reuse Epic 22 shared form, layout, feedback, and status-display primitives.
  - [ ] Keep supplier-control messaging from Story 24.5 separate from commercial-default editing.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for default inheritance, manual override persistence, deterministic precedence, and tenant isolation.
  - [ ] Add frontend tests for profile editing, inherited-value display, and override-state visibility.
  - [ ] Validate that supplier-control enforcement remains owned by Story 24.5 and no ledger automation lands in this story.

## Dev Notes

### Context

- Customer records already include `credit_limit` and `default_discount_percent`.
- Supplier records are currently minimal and will also gain procurement controls in Story 24.5, so Epic 25 must avoid mixing control policy with commercial defaults.
- Stories 25.1 through 25.3 provide the currency, rate, and payment-template foundations that these party profiles should reference.

### Architecture Compliance

- Keep commercial defaults on the party master and apply them in owning document services.
- Preserve manual override as an explicit document-level action, not a silent recalculation.
- Keep supplier-control enforcement in Story 24.5.
- Do not reinterpret existing customer credit settings as missing; incorporate them into the profile surface.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/customers/models.py`
  - `backend/domains/customers/schemas.py`
  - `backend/common/models/supplier.py`
  - customer and supplier service layers
  - owning document services for quotations, orders, invoices, procurement, and purchases
  - migrations under `migrations/versions/`
- Likely frontend files:
  - customer maintenance UI
  - supplier maintenance UI
  - document forms that show inherited commercial defaults
- Effective-value source metadata can be lightweight, for example `profile_default` versus `manual_override`, as long as it is visible in API and UI surfaces.
- Effective-value source metadata can be lightweight, for example `profile_default`, `source_document`, `legacy_compatibility`, or `manual_override`, as long as it is visible in API and UI surfaces.
- When a document is created from another document such as invoice-from-order, it should inherit the source document's effective currency and payment-term values before consulting party defaults, preserving audit lineage.
- When legacy enum-based payment terms and profile templates both exist, the document service should use a deterministic precedence order with the template reference winning and expose the winner clearly.
- Historical documents must retain the snapshot of inherited or overridden values even if the customer or supplier profile changes later.
- Lookups for profile defaults should be tenant-scoped and efficient enough for document-create flows; avoid N+1 reads when applying defaults at scale.

### Data Model Contract

- Customer and Supplier should each gain:
  - nullable `default_currency_code` referencing the Epic 25 currency master by code
  - nullable `payment_terms_template_id` referencing the Epic 25 payment-terms template by id
- Document-level snapshot metadata on quotation, order, PO, invoice, and supplier invoice should include:
  - `currency_source`
  - `payment_terms_source`
- Allowed source values should be explicit and shared across domains:
  - `source_document`
  - `profile_default`
  - `legacy_compatibility`
  - `manual_override`
- Party-profile fallback in this story is limited to:
  - customer: `default_currency_code`, `payment_terms_template_id`, existing `credit_limit`, existing `default_discount_percent`
  - supplier: `default_currency_code`, `payment_terms_template_id`
- Source-document inheritance should be supported at minimum for:
  - quotation to order
  - order to invoice
  - supplier quotation to PO
  - PO to supplier invoice
- Historical documents keep their stored effective values and source metadata even if the customer or supplier master changes later.

### Testing Requirements

- Backend tests should cover tenant isolation, inheritance precedence, override persistence, and compatibility with existing customer credit and discount fields.
- Frontend tests should cover editing defaults, viewing inherited values, and separating commercial defaults from supplier-control settings.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-25.md`
- `../implementation-artifacts/25-3-payment-terms-template-builder-and-schedule-handling.md`
- `../implementation-artifacts/24-5-supplier-controls-and-procurement-extensions.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `backend/domains/customers/models.py`
- `backend/domains/customers/schemas.py`
- `backend/common/models/supplier.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 25.4 from Epic 25, the customer and supplier model surfaces, and the validated commercial-default research so party-level defaults can feed document creation without colliding with Story 24.5 supplier controls.

### File List

- `_bmad-output/implementation-artifacts/25-4-customer-and-supplier-commercial-profiles.md`