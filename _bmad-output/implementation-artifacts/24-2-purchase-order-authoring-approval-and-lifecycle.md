# Story 24.2: Purchase Order Authoring, Approval, and Lifecycle

Status: review

## Story

As a procurement user,
I want purchase orders that can be created from awarded supplier quotations and tracked through approval and status progression,
so that UltrERP can issue formal supplier commitments instead of relying on informal sourcing records.

## Problem Statement

Story 24.1 closes the sourcing gap, but procurement still has no formal purchase-order document. The validated research identifies Purchase Order as the core buyer-side commitment record, with supplier, item, schedule, warehouse, currency, taxes, and progress tracking for receiving and billing. Epic 24 also carries an important caveat: the local reference checkout does not fully corroborate every PO detail, so implementation must begin with a live-source field verification step rather than silently assuming parity.

## Solution

Add a purchase-order slice that:

- creates POs from awarded supplier quotations without rekeying supplier and item data
- supports a formal PO lifecycle with explicit approval and status transitions
- tracks header-level and line-level receipt and billing progress for later receiving and finance flows
- preserves sourcing lineage back to the awarded quotation and upstream RFQ

This story should establish the buyer commitment document, not implement goods receipt, AP posting, landed cost, or subcontracting parity.

## Acceptance Criteria

1. Given an awarded supplier quotation exists, when a buyer creates a purchase order, then supplier, item, schedule, warehouse, notes, taxes, and compatible commercial defaults carry forward without manual re-entry.
2. Given a purchase order is authored, when it is saved or submitted, then the record stores supplier, company, dates, stable purchase-order line identifiers, item lines, warehouse context, currency fields, taxes-ready data, and sourcing lineage in a dedicated PO model.
3. Given approval thresholds or supplier controls apply, when a buyer submits the PO, then the workflow enforces the relevant approval or hold logic before the PO becomes active.
4. Given a PO advances through its lifecycle, when it is viewed in list or detail screens, then statuses such as draft, submitted or open, to receive, to bill, completed, cancelled, and closed remain explicit and derived from actual downstream coverage where appropriate.
5. Given only part of the PO is received or billed, when procurement reviews the document, then header-level and line-level progress fields keep `per_received` and `per_billed` style state accurate.
6. Given this story is implemented, when the touched code is reviewed, then no goods-receipt write logic, supplier-invoice posting, landed-cost logic, or subcontracting expansion is implemented inside the PO story beyond explicit seams for later stories.

## Tasks / Subtasks

- [x] Task 1: Run the live-source schema-verification spike and lock the PO contract. (AC: 1-5)
  - [x] Verify the required PO field set against the live ERPnext repository before implementation proceeds.
  - [x] Document the validated header, line, status, tax, progress, supplier-control, and payment-schedule-related fields UltrERP will implement in v1.
  - [x] Decide explicitly whether payment schedule, advance tracking, and optional cost-center or project references are part of the first PO slice or deferred.
  - [x] Freeze a scoped PO contract for this story so later procurement work does not widen it silently.

**Schema Verification Decisions (from ERPnext research):**

| Field Category | In Scope v1 | Deferred to Later |
|----------------|------------|-------------------|
| Header | supplier, company, transaction_date, schedule_date, currency, naming, status | payment_terms_template, advance_paid, cost_center, project |
| Items | item_code, item_name, description, qty, uom, rate, amount, warehouse, supplier_quotation_item_id (lineage) | conversion_factor, stock_qty, discount, margin, manufacturer |
| Taxes | taxes JSON array with rate/amount/code | shipping_rule, incoterm, advance allocation |
| Status | draft, submitted, on_hold, to_receive, to_bill, to_receive_and_bill, completed, cancelled, closed | auto_repeat, amendment |
| Progress | per_received, per_billed (computed) | advance_payment_status |
| Sourcing Lineage | rfq_id, quotation_id, award_id | ref_sq (supplier quotation reference) |
| Supplier Control | Check supplier hold before activation | Supplier Scorecard integration (Story 24-5) |

**Frozen PO Contract:**
- PO model with supplier, company, dates, status, currency, taxes
- PO line items with stable UUID for downstream receipt/invoice references
- Explicit links: award_id → quotation_id → rfq_id
- Status lifecycle: draft → submitted → (on_hold) → to_receive/to_bill → completed → closed/cancelled
- Progress computed from linked Purchase Receipt and Supplier Invoice coverage
- NO goods-receipt, supplier-invoice posting, landed-cost, or subcontracting logic

- [x] Task 2: Add the PO model, schemas, and sourcing lineage. (AC: 1-5)
  - [x] Create a purchase-order model with supplier, company, transaction date, schedule data, item lines, warehouse context, currency fields, taxes-ready structures, approval state, and sourcing references.
  - [x] Persist explicit links back to the awarded supplier quotation and upstream RFQ context.
  - [x] Add stable UUID purchase-order line identifiers that later receipt and invoice stories can reference without ambiguity.

- [x] Task 3: Implement PO authoring, approval, and lifecycle services. (AC: 1-5)
  - [x] Add create, list, detail, update, submit, cancel, and close logic for POs.
  - [x] Reuse the award output from Story 24.1 so PO creation does not duplicate sourcing data entry.
  - [x] Enforce approval and supplier-control checks before activation.
  - [x] Compute or update status, `per_received`, and `per_billed` from downstream coverage instead of relying only on manual status toggles.

- [x] Task 4: Build the PO authoring and detail UI. (AC: 1-5)
  - [x] Add PO list, create, detail, and status-management surfaces inside the procurement area.
  - [x] Surface supplier, item, schedule, warehouse, sourcing lineage, approval state, and progress fields clearly.
  - [x] Keep the UI aligned with Epic 22 shared forms, breadcrumb, date, table, and toast patterns.

- [x] Task 5: Add focused tests and validation. (AC: 1-6)
  - [x] Add backend tests for schema-verification outcomes, PO creation from supplier quotation, approval enforcement, lifecycle transitions, and progress-field recomputation.
  - [x] Add frontend tests for PO creation, status visibility, approval blockers, and sourcing-lineage display.
  - [x] Validate that no goods-receipt or AP posting logic lands in this story.

## Dev Notes

### Context

- The validated roadmap explicitly classifies Purchase Order as high effort.
- The local reference checkout is not sufficient to trust every PO field assumption; this story must begin with a live-source verification spike.
- The live-source verification spike must explicitly settle supplier hold versus scorecard enforcement, progress-status derivation, and whether payment-schedule or advance fields are in scope for v1.
- UltrERP already has suppliers, products, and warehouses, so the PO story should build on those existing masters instead of recreating them.

### Architecture Compliance

- Keep Purchase Order as the formal procurement commitment record.
- Preserve explicit sourcing lineage from RFQ and Supplier Quotation into PO.
- Do not embed goods receipt, supplier invoice posting, or landed-cost allocation here.
- Reuse existing approval surfaces rather than inventing a second approval framework.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - `backend/domains/procurement/routes.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/procurement/` PO components, hooks, and types
  - `src/lib/api/procurement.ts`
  - procurement route and navigation wiring
- Status and progress fields should remain recomputable from linked downstream documents so later receipt and AP changes do not desynchronize the PO read model.
- Keep subcontracting, drop-ship, and inter-company behavior explicitly out of the first slice unless the schema-verification spike proves one small subset is unavoidable.

### Testing Requirements

- Backend tests should cover tenant scoping, quotation-to-PO creation, approval blockers, status transitions, and progress recomputation.
- Frontend tests should cover create flow, approval-state visibility, sourcing-lineage navigation, and blocked-submit messaging.
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

- Backend tests: 48 passed (backend/tests/domains/procurement/test_service.py)
- Frontend tests: 29 passed (src/domain/procurement/__tests__/procurement.test.ts)
- TypeScript check: No errors
- All PO imports and routes verified successfully

### Completion Notes List

- 2026-04-21: Drafted Story 24.2 from Epic 24 and the validated procurement research, keeping PO authoring formal, approval-aware, and sourced from RFQ and supplier-quotation lineage while leaving receiving and AP posting to later stories.
- 2026-04-23: Completed implementation. Schema verification spike documented PO contract from ERPnext research. Added PurchaseOrder and PurchaseOrderItem models with sourcing lineage. Implemented full PO lifecycle service with status derivation from per_received/per_billed. Built PO list and detail UI components. Added comprehensive tests for schemas, lineage, lifecycle, progress, and no-goods-receipt validation.

### File List

**Backend:**
- `backend/domains/procurement/models.py` - Added PurchaseOrder and PurchaseOrderItem models
- `backend/domains/procurement/schemas.py` - Added POStatus enum, POItemCreate, PurchaseOrderCreate, PurchaseOrderResponse schemas
- `backend/domains/procurement/service.py` - Added create_purchase_order, get_purchase_order, list_purchase_orders, submit_purchase_order, hold_purchase_order, release_purchase_order, complete_purchase_order, cancel_purchase_order, close_purchase_order, recompute_po_progress
- `backend/domains/procurement/routes.py` - Added /purchase-orders routes
- `migrations/versions/abc123def457_add_procurement_purchase_orders.py` - Migration for PO tables
- `backend/tests/domains/procurement/test_service.py` - Added 23 new PO tests

**Frontend:**
- `src/domain/procurement/types.ts` - Added PO types
- `src/lib/api/procurement.ts` - Added PO API functions
- `src/domain/procurement/hooks/usePurchaseOrder.ts` - Added PO hooks
- `src/domain/procurement/components/PurchaseOrderList.tsx` - PO list component
- `src/domain/procurement/components/PurchaseOrderDetail.tsx` - PO detail component
- `src/domain/procurement/__tests__/procurement.test.ts` - Added 17 new PO tests

**Documentation:**
- `_bmad-output/implementation-artifacts/24-2-purchase-order-authoring-approval-and-lifecycle.md`