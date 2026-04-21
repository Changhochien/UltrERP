# Story 24.1: RFQ and Supplier Quotation Workspace

Status: drafted

## Story

As a procurement user,
I want to issue RFQs to multiple suppliers and compare the quotations they return,
so that I can choose the best supplier before creating a purchase order.

## Problem Statement

UltrERP currently has supplier records and read-only supplier invoices, but no sourcing workflow. The validated ERPnext buying research confirms that Request for Quotation and Supplier Quotation are the upstream records that collect supplier responses, track per-supplier quote status, and support award comparison before a purchase order is created. Without them, procurement decisions stay in email threads or spreadsheets and later PO lineage starts with incomplete context.

## Solution

Add a sourcing workspace that:

- creates RFQs with items, supplier recipients, schedule context, and commercial terms
- tracks per-supplier response state such as pending and received
- captures supplier quotations with validity, pricing, lead time, tax-ready totals, and linkage back to the originating RFQ
- presents supplier responses side by side so buyers can choose the winning source before Story 24.2 PO creation

This story should establish the sourcing phase of procurement, not implement purchase orders, receiving, or AP posting.

## Acceptance Criteria

1. Given a buyer creates an RFQ, when it is saved, then the RFQ stores company, transaction date, optional schedule date, item lines, supplier recipients, terms-ready fields, and sourcing notes in a dedicated procurement record.
2. Given an RFQ is distributed to multiple suppliers, when responses are tracked, then each supplier row shows an explicit quote status such as pending or received.
3. Given a supplier quotation is captured, when it is saved, then it preserves supplier, RFQ linkage, stable RFQ and supplier-quotation item identifiers, item pricing, validity, lead-time or delivery context, header-level tax tables or templates, item-level tax metadata where needed, tax-ready totals, and comparison metadata.
4. Given multiple supplier quotations exist for the same sourcing event, when the buyer opens the workspace, then price, lead-time, validity, and normalized comparison values can be compared without exporting data to spreadsheets.
5. Given a supplier quotation is selected as the preferred offer, when the buyer marks it as the winning source, then Story 24.2 can create a purchase order from that quotation without rekeying supplier and item data.
6. Given this story is implemented, when the touched code is reviewed, then no purchase-order creation, goods receipt, or finance posting logic is implemented here beyond explicit handoff seams for later stories.

## Tasks / Subtasks

- [ ] Task 1: Add RFQ and Supplier Quotation models, schemas, and sourcing linkage. (AC: 1-5)
  - [ ] Create RFQ header, RFQ supplier recipient, RFQ item, supplier quotation header, and supplier quotation item models under the procurement domain.
  - [ ] Give RFQ items and supplier quotation items stable UUID identifiers that are independent of display line numbers so later procurement lineage can reference them safely.
  - [ ] Preserve explicit RFQ-to-supplier-quotation linkage so quote status can be recomputed per supplier.
  - [ ] Add fields for company, dates, items, suppliers, validity, lead time or expected delivery, header-level tax tables or templates, item-level tax metadata where needed, taxes-ready totals, terms, and comparison metadata.
  - [ ] Define an explicit award-tracking model so the winning supplier quotation is visible before Story 24.2 creates a purchase order from it.
- [ ] Task 2: Implement RFQ and supplier-quotation services. (AC: 1-5)
  - [ ] Add create, list, detail, update, and lifecycle logic for RFQs and supplier quotations.
  - [ ] Track supplier-level response state on the RFQ and update it when supplier quotations are captured or submitted through an explicit linkage hook.
  - [ ] Support explicit award selection without creating a PO yet.
  - [ ] Mark expired supplier quotations as non-selectable based on validity rules even if full scheduler automation is deferred.
- [ ] Task 3: Build the sourcing workspace UI. (AC: 1-5)
  - [ ] Add RFQ list, detail, and authoring flows inside the procurement area.
  - [ ] Add supplier-quotation capture and comparison views that surface item, price, lead time, validity, and winner selection clearly.
  - [ ] Reuse Epic 22 shared forms, feedback, breadcrumb, and date primitives.
- [ ] Task 4: Define the PO handoff seam. (AC: 5-6)
  - [ ] Expose a winner-selected supplier quotation contract that Story 24.2 can consume without duplicating sourcing data.
  - [ ] Keep the handoff explicit and additive; do not implement PO write logic inside this story.
  - [ ] Preserve RFQ and supplier quotation lineage for later procurement reporting.
- [ ] Task 5: Add focused tests and validation. (AC: 1-6)
  - [ ] Add backend tests for RFQ creation, supplier quote-status tracking, supplier-quotation capture, and award selection.
  - [ ] Add frontend tests for RFQ authoring, supplier comparison, and winner-selection UX.
  - [ ] Validate that no PO or receipt logic is introduced here.

## Dev Notes

### Context

- The validated research confirms RFQ and Supplier Quotation as the first procurement documents in the buying flow.
- ERPnext tracks quote status per supplier on the RFQ and updates it from linked Supplier Quotations.
- Supplier portal, automated email, and user auto-provisioning exist in ERPnext but are not required to make the first sourcing slice valuable.

### Architecture Compliance

- Keep RFQ and Supplier Quotation separate from Purchase Order ownership.
- Preserve explicit sourcing lineage so Story 24.2 and Story 24.4 can rely on it later.
- Do not embed receiving or supplier-invoice behavior into sourcing records.
- Reuse existing supplier, product, warehouse, and approval surfaces where possible.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - `backend/domains/procurement/routes.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/procurement/` for sourcing components, hooks, and types
  - `src/lib/api/procurement.ts`
  - procurement route and navigation wiring
- The first slice can keep supplier distribution internal or operator-driven; full supplier portal or email automation can remain follow-on work.
- Award selection should preserve the losing quotations for audit and future supplier-performance reporting.
- If Epic 25 multi-currency foundations are present, comparison views should rely on normalized base totals so cross-supplier comparison stays fair.
- If full auto-expiry scheduling is not implemented in the first slice, expiry must still be enforced through service-level or read-time evaluation.
- Comparison rules should be explicit: compare supplier quotations by normalized unit price, normalized total for the requested quantity, lead time, validity, and tax-inclusive or tax-exclusive totals presented with consistent labels.
- If suppliers quote in different UOM or currency contexts, normalize comparison onto the RFQ request quantity and the available base-currency view before ranking offers.

### Testing Requirements

- Backend tests should cover tenant scoping, per-supplier quote-status recomputation, validity handling, and award selection.
- Frontend tests should cover RFQ creation, supplier quotation comparison, and winner-selection feedback.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-24.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-buying-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 24.1 from Epic 24 and the validated buying research, keeping RFQ and supplier quotation as the sourcing workspace that precedes purchase-order creation.

### File List

- `_bmad-output/implementation-artifacts/24-1-rfq-and-supplier-quotation-workspace.md`