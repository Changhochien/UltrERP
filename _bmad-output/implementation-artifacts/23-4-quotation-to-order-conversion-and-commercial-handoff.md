# Story 23.4: Quotation-to-Order Conversion and Commercial Handoff

Status: drafted

## Story

As a sales user moving from offer to commitment,
I want to convert accepted quotations into the existing order intake flow,
so that UltrERP can preserve quotation lineage without breaking the current order confirmation semantics.

## Problem Statement

Stories 23.1 through 23.3 establish Lead, Opportunity, and Quotation, but without quotation-to-order conversion the pre-sale pipeline still dead-ends in manual re-entry. The validated ERPnext research confirms quotation is expected to map into a sales-order-style document and to reflect partial or full conversion status over time. UltrERP already has a working order intake and confirmation flow under Epic 21, so this story must bridge quotation into that flow without importing CRM semantics into order confirmation or regressing the current `pending -> confirmed -> shipped -> fulfilled/cancelled` lifecycle.

## Solution

Add a quotation-to-order conversion seam that:

- creates a new order through the existing order intake surface and API rather than bypassing it
- carries forward the quotation's party, item, contact, address, notes, taxes, attribution, and commercial defaults into the new pending order
- records explicit quotation-to-order lineage on both sides
- computes quotation conversion state from linked order coverage so partially converted quotations remain visible

This story should stop at pending-order creation and lineage. Confirmation, invoice creation, and stock reservation stay governed by Epic 21.

## Acceptance Criteria

1. Given a quotation is accepted and a customer context is available, when a user converts it, then UltrERP creates a new order in the existing `pending` state through the current order intake flow instead of creating a second order model.
2. Given quotation conversion occurs, when the order is created, then party, item lines, contact fields, billing and shipping address context, notes, UTM and source attribution, territory, customer-group-compatible business context, and compatible commercial defaults are carried forward without manual re-entry.
3. Given a quotation targets a lead or prospect that is not yet resolvable to a valid existing order-facing customer record, when a user attempts conversion, then the UI blocks cleanly and explains that customer conversion or resolution must happen first instead of creating an invalid order.
4. Given one or more orders are created from a quotation, when the quotation is read, then its conversion state reflects `open`, `partially ordered`, or `ordered` based on linked order coverage rather than a manual toggle.
5. Given a quotation-derived order is later confirmed, when Epic 21 confirmation runs, then invoice creation and stock reservation still happen only at order confirmation and not during quotation conversion.
6. Given a quotation has been partially converted, when a user returns to the quotation, then the remaining unconverted commercial scope remains visible and additional conversion can proceed without losing prior lineage.
7. Given this story is implemented, when the touched backend and frontend code are reviewed, then no invoice creation, stock reservation, or finance posting logic is introduced during quotation conversion.

## Tasks / Subtasks

- [ ] Task 1: Add quotation-to-order lineage fields and conversion contract. (AC: 1-6)
  - [ ] Add explicit linkage between quotations and the orders created from them.
  - [ ] Persist enough line-level or quantity-level mapping data to compute `partially ordered` versus `ordered` accurately, including correct recomputation when linked orders are cancelled or materially reduced.
  - [ ] Keep the contract additive to the current orders model rather than introducing a CRM-owned order variant.
- [ ] Task 2: Implement conversion services on top of the existing orders flow. (AC: 1-5, 7)
  - [ ] Add a conversion service that calls or reuses the existing order create path and produces a `pending` order.
  - [ ] Carry forward quotation data needed by orders: party, line items, addresses, notes, UTM and source attribution, territory, customer-group-compatible business context, and payment-term-compatible defaults mapped into the current order model.
  - [ ] Explicitly defer invoice creation and stock reservation until the existing order confirmation step owned by Epic 21.
- [ ] Task 3: Handle customer-resolution prerequisites and invalid conversion attempts. (AC: 3)
  - [ ] Detect when a quotation points at a lead or prospect that lacks an order-ready customer context.
  - [ ] Block conversion with actionable guidance to convert or resolve the party first.
  - [ ] Keep the blocked state visible in the quotation detail UI.
- [ ] Task 4: Compute and surface quotation conversion state. (AC: 4, 6)
  - [ ] Derive quotation status from linked order coverage so `partially ordered` and `ordered` are computed, not manually maintained.
  - [ ] Surface linked orders and remaining scope in quotation detail and list views.
  - [ ] Ensure order cancellation or rollback updates quotation conversion state correctly.
- [ ] Task 5: Build the conversion UX and add focused tests. (AC: 1-7)
  - [ ] Add a clear convert-to-order action from quotation detail that uses the existing orders UX language.
  - [ ] Add backend tests for conversion success, blocked conversion, lineage persistence, and partial-conversion computation.
  - [ ] Add frontend tests for conversion CTA visibility, blocked state messaging, linked-order visibility, and confirmation-boundary preservation.

## Dev Notes

### Context

- Epic 21 explicitly leaves quotation-to-order flow as a follow-on CRM integration point and requires that `pending` remain the editable pre-commit order state.
- ERPnext computes quotation order status from linked downstream sales-order coverage; this story should preserve that behavior conceptually without importing ERPnext's entire selling controller.
- Conversion only makes sense when the target party can resolve into the existing order-facing customer model.
- This story assumes the order domain still requires a valid existing customer record; lead or prospect quotations must be resolved to that customer context before conversion and this story does not auto-create customers implicitly.

### Architecture Compliance

- Use the current order create path; do not introduce a CRM-owned order write model.
- Do not create invoices or reserve stock during quotation conversion.
- Treat confirmation-time invoice creation and stock reservation as a dependency on the preserved Epic 21 order contract, not as behavior redefined here.
- Preserve explicit quotation lineage on orders so later reporting and UX can traverse both directions.
- Reuse Epic 22 UI primitives and Epic 21 order semantics rather than redefining them.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/crm/service.py`
  - `backend/domains/crm/routes.py`
  - `backend/domains/orders/service.py` or the current order create owner
  - `backend/domains/orders/schemas.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/crm/` quotation detail and conversion UI
  - `src/domain/orders/` create-order flow surfaces where prefilled conversion data is consumed
  - `src/lib/api/crm.ts`
  - `src/lib/api/orders.ts`
- Conversion should preserve quotation-to-opportunity lineage transitively if that context already exists.
- Partial conversion must be derived from linked order coverage and should react correctly if a linked order is cancelled or materially changed.
- The quotation-to-order mapping should be explicit enough to track per-line or per-quantity conversion, not just header-level linkage.
- Payment-term carry-forward should map into the current order payment-term shape first, while staying compatible with Epic 25 template-based commercial defaults later.

### Testing Requirements

- Backend tests should cover conversion into pending orders, blocked conversion without customer context, lineage persistence, and computed partial/full conversion state.
- Frontend tests should cover conversion CTA behavior, order-prefill behavior, linked-order visibility, and the confirmation-boundary copy that preserves Epic 21 semantics.
- If translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-23.md`
- `../planning-artifacts/epic-21.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-crm-sales-detailed.md`
- `.omc/research/gap-analysis.md`
- `.omc/research/review-gap-claims.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 23.4 from Epic 23, Epic 21, and the validated quotation-to-order research, keeping conversion additive to the current pending-order flow and preserving quotation lineage without moving invoice or reservation logic forward.

### File List

- `_bmad-output/implementation-artifacts/23-4-quotation-to-order-conversion-and-commercial-handoff.md`