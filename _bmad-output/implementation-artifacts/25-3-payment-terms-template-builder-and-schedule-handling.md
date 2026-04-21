# Story 25.3: Payment Terms Template Builder and Schedule Handling

Status: drafted

## Story

As a finance or commercial operations user,
I want reusable payment-term templates and generated payment schedules,
so that sales and procurement documents can use real installment logic instead of only hard-coded day-count enums.

## Problem Statement

UltrERP currently has `payment_terms_code` and `payment_terms_days` on orders, and invoice due-date logic still derives a single due date from those day counts. The validated research confirms ERPnext supports Payment Terms Template plus schedule rows with invoice portions, due dates, and early-payment discounts. Epic 25 needs that template-backed model, but it must arrive without breaking current `NET_30`, `NET_60`, and `COD` behavior or the existing payment-status logic.

## Solution

Add a payment-terms slice that:

- introduces reusable payment-term templates and schedule detail rows
- maps legacy enum-coded terms onto documented template-compatible behavior
- generates explicit payment schedules for new documents while preserving a compatibility path for existing due-date and payment-status logic

This story should add payment-term templates and schedule handling, not implement full cross-currency allocation logic or AP/AR ledger automation.

## Acceptance Criteria

1. Given finance defines a payment-term template, when it is saved, then the template stores reusable schedule rules such as invoice portion, due-date offsets, and optional early-payment discounts.
2. Given sales or procurement users create new documents, when they choose a template-backed payment term, then the document stores the template reference plus an explicit generated payment schedule.
3. Given a legacy `NET_30`, `NET_60`, or `COD` term is used, when existing records are viewed or new compatible records are created, then a documented compatibility shim preserves current readability and behavior.
4. Given invoice or payment summary logic needs a primary due-date anchor, when a schedule exists, then the compatibility path uses a deterministic rule while still keeping the full schedule explicit.
5. Given this story is implemented, when the touched code is reviewed, then no full payment-allocation engine rewrite, no finance-ledger automation, and no incompatible removal of existing payment-term code lands in this story.

## Tasks / Subtasks

- [ ] Task 1: Add payment-term template and schedule models. (AC: 1-4)
  - [ ] Create a payment-term template model with template name, allocation mode, and schedule detail rows.
  - [ ] Create schedule detail fields for invoice portion, credit days or months, due date, optional mode of payment, discount validity, and discount amount or percent semantics.
  - [ ] Add generated payment-schedule child rows on order, quotation, PO, invoice, and supplier-invoice documents, with one document header template reference plus schedule rows containing installment number, invoice portion, due date, payment amount, outstanding amount, paid amount, and discount metadata.
- [ ] Task 2: Implement legacy compatibility mapping. (AC: 2-4)
  - [ ] Map `NET_30`, `NET_60`, and `COD` to documented single-term template behavior without breaking existing order and invoice logic: 100 percent due at document date plus 30 days, 60 days, or 0 days respectively.
  - [ ] Keep `payment_terms_code` and `payment_terms_days` readable during migration even when a template reference is present.
  - [ ] Document and implement the deterministic primary due-date rule as the earliest unpaid installment due date for schedule-backed payment summary and the single generated installment for legacy rows.
- [ ] Task 3: Generate schedules in commercial document flows. (AC: 2-4)
  - [ ] Extend order, quotation, and purchase-order create flows to reference a payment-term template or compatibility shim.
  - [ ] Extend invoice and supplier-invoice flows to copy or persist the generated schedule used for due-date and outstanding behavior, inheriting from the source commercial document unless explicitly overridden before finalization.
  - [ ] Keep payment-status and due-date logic compatible with both schedule-backed and legacy single-term documents.
- [ ] Task 4: Build template and schedule UI flows. (AC: 1-4)
  - [ ] Add finance-facing template CRUD and schedule-builder UI.
  - [ ] Add document forms that let users select a template and inspect generated installments clearly.
  - [ ] Reuse Epic 22 shared form, table, date, and feedback patterns.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for template creation, schedule generation, legacy term mapping, due-date compatibility, and invoice payment-summary behavior.
  - [ ] Add frontend tests for template builder UX, template selection, and generated-schedule display.
  - [ ] Validate that no incompatible removal of `payment_terms_code` behavior or finance-posting automation lands in this story.

## Dev Notes

### Context

- ERPnext supports Payment Terms Template, Payment Term detail rows, and Payment Schedule rows with portions, due dates, and discount metadata.
- Current UltrERP order and invoice logic still depends on `payment_terms_days` for due-date computation.
- The validated review is explicit that payment terms already exist in UltrERP as enums; the missing piece is the template builder and schedule model, not basic term support.

### Architecture Compliance

- Extend existing payment-term behavior rather than replacing it abruptly.
- Keep legacy `payment_terms_code` and `payment_terms_days` compatible while templates roll out.
- Make schedule rows explicit and inspectable.
- Do not combine this story with payment allocation or ledger posting redesign.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/orders/schemas.py`
  - `backend/domains/orders/services.py`
  - `backend/domains/invoices/service.py`
  - payment-term template models and schemas in a commercial-foundations or settings-aligned domain
  - quotation and procurement services for template references
  - migrations under `migrations/versions/`
- Likely frontend files:
  - finance or settings-facing payment-term template builder UI
  - order, quotation, procurement, and invoice forms that surface template selection and generated schedules
- The compatibility shim should remain explicit: single-term legacy rows keep their current behavior, while schedule-backed rows expose installment detail plus a documented primary due-date rule for current payment-summary consumers.
- Early-payment discounts in this story are metadata and schedule-generation concerns only; automatic discount application in payment-entry or ledger logic is deferred.
- Template-backed defaults should remain compatible with Story 25.4 commercial profiles.

### Data Model Contract

- `PaymentTermsTemplate` should include at minimum:
  - `id`
  - `tenant_id`
  - `template_name`
  - `allocate_payment_based_on_payment_terms`
  - `is_active`
- `PaymentTermsTemplateDetail` should include at minimum:
  - `id`
  - `template_id`
  - `row_number`
  - `invoice_portion`
  - `credit_days`
  - `credit_months`
  - `discount_validity_days`
  - `discount_percent` or `discount_amount`
  - `mode_of_payment`
- Generated `PaymentSchedule` rows on commercial documents should include at minimum:
  - `id`
  - owning document reference
  - `row_number`
  - `invoice_portion`
  - `due_date`
  - `payment_amount`
  - `outstanding_amount`
  - `paid_amount`
  - discount metadata copied from the template detail
- Invoice payment summary compatibility should derive the displayed `due_date` from the earliest unpaid schedule row when schedules exist; otherwise it continues to use legacy `payment_terms_days` behavior.

### Testing Requirements

- Backend tests should cover tenant isolation, installment percent totals, discount metadata persistence, legacy term mapping, and due-date computation for schedule-backed invoices.
- Frontend tests should cover template creation, validation of installment totals, and schedule preview display.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-25.md`
- `../implementation-artifacts/25-2-currency-aware-commercial-documents.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-accounting-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `backend/domains/orders/schemas.py`
- `backend/domains/orders/services.py`
- `backend/domains/invoices/service.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 25.3 from Epic 25, the validated accounting research, and the current order and invoice due-date logic so payment-term templates can land without breaking legacy enum-driven behavior.

### File List

- `_bmad-output/implementation-artifacts/25-3-payment-terms-template-builder-and-schedule-handling.md`