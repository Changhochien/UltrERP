# Story 24.3: Goods Receipt and Receiving Exceptions

Status: drafted

## Story

As a receiving user,
I want to receive goods against purchase-order lines with accepted and rejected quantities,
so that UltrERP can record inbound deliveries accurately and keep procurement and inventory state aligned.

## Problem Statement

Story 24.2 creates formal purchase orders, but procurement still needs a receiving document that records what actually arrived. The validated buying research confirms that Purchase Receipt is where PO-line linkage, accepted and rejected quantities, receiving warehouse handling, and downstream `per_received` updates become real. Without a dedicated receipt step, the system cannot distinguish ordered inventory from actually received inventory or capture receiving exceptions cleanly.

## Solution

Add a goods-receipt slice that:

- receives goods against specific purchase-order lines rather than only at the PO header level
- records accepted quantity, rejected quantity, receiving warehouse, and exception notes per line
- updates procurement progress and inventory mutation explicitly from the receipt event
- preserves receiving history as an auditable series of supplier delivery events

This story should create the inbound receiving document and its inventory impact, not supplier-invoice posting, landed cost allocation, quality inspection logic, or serial/batch traceability.

## Acceptance Criteria

1. Given an open purchase order exists, when a receiver creates a goods receipt, then the receipt links to the relevant PO and PO line references instead of relying on header-only matching.
2. Given goods are received, when the receipt is saved or submitted, then each line records accepted quantity, rejected quantity, receiving warehouse context, and exception notes with the invariant that total received context is explainable from accepted plus rejected outcomes.
3. Given a partial delivery arrives, when the receipt is processed, then only the delivered quantities are recorded and the linked PO remains open with updated receipt progress.
4. Given some goods are rejected, when the receipt is processed, then rejected quantity and rejected-warehouse treatment remain explicit rather than being hidden inside the accepted quantity.
5. Given receipt events occur over time, when procurement or warehouse users review a PO, then receipt history and remaining open quantity are visible.
6. Given this story is implemented, when the touched code is reviewed, then no supplier-invoice posting, landed-cost allocation, quality-inspection enforcement, or serial-batch assignment logic is implemented inside goods receipt beyond later extension seams.

## Tasks / Subtasks

- [ ] Task 1: Add the goods-receipt model, schemas, and PO-line linkage. (AC: 1-5)
  - [ ] Create a goods-receipt model with header context, supplier, dates, warehouse data, and line-level references back to PO rows.
  - [ ] Give goods-receipt lines stable UUID identifiers that are independent of display line numbers so supplier-invoice lineage can reference them later.
  - [ ] Add accepted quantity, rejected quantity, explicit rejected-warehouse treatment fields, exception notes, and receiving metadata at the line level.
  - [ ] Preserve enough linkage for later supplier-invoice and procurement-lineage stories without implementing them here.
- [ ] Task 2: Implement receipt services and inventory mutation. (AC: 1-5)
  - [ ] Add create, list, detail, submit, cancel, and return-safe receipt logic.
  - [ ] Update PO `per_received` and line-level received quantities from receipt coverage.
  - [ ] Apply inventory mutation from accepted and rejected quantities explicitly rather than collapsing them into one stock update.
  - [ ] Enforce receiving invariants so the line-level totals remain internally consistent.
- [ ] Task 3: Handle receiving exceptions and partial deliveries. (AC: 2-5)
  - [ ] Support partial delivery across multiple receipt events.
  - [ ] Keep rejected quantities and exception notes visible in the UI and API.
  - [ ] Ensure cancelled or reversed receipts recompute PO progress from the current set of submitted receipt events rather than relying on fragile decrement-only logic.
- [ ] Task 4: Build the receiving UI flows. (AC: 1-5)
  - [ ] Add receipt creation and detail screens from the procurement workspace and PO detail view.
  - [ ] Surface open PO quantities, accepted versus rejected outcomes, and receipt history clearly.
  - [ ] Reuse Epic 22 form, breadcrumb, date, table, and toast primitives.
- [ ] Task 5: Add focused tests and validation. (AC: 1-6)
  - [ ] Add backend tests for PO-line linkage, accepted versus rejected quantity invariants, partial deliveries, receipt cancellation, and PO progress recomputation.
  - [ ] Add frontend tests for receipt entry, partial delivery visibility, rejected-quantity handling, and history display.
  - [ ] Validate that no AP posting, quality gate, or serial-batch logic lands in this story.

## Dev Notes

### Context

- The validated research confirms Purchase Receipt as the inbound execution document linked to Purchase Order lines.
- BuyingController rules make accepted and rejected quantity handling explicit rather than implicit.
- Goods receipt is where ordered quantities begin turning into actual stock movement and PO receipt progress.

### Architecture Compliance

- Keep goods receipt as a separate procurement execution document, not a PO status toggle.
- Preserve explicit PO-line linkage and auditable receipt history.
- Do not mix receipt handling with supplier-invoice or landed-cost behavior.
- Leave quality inspection and serial-batch hooks for Epic 29 rather than implementing them here.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - `backend/domains/procurement/routes.py`
  - inventory mutation integration owned by the current inventory write surface
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/procurement/` receipt components, hooks, and types
  - `src/lib/api/procurement.ts`
  - procurement route and navigation wiring
- If full rejected-warehouse behavior is not already modeled, keep the schema explicit so later inventory and quality stories can extend it safely.
- Rejected-warehouse semantics should be explicit: rejected quantities must remain distinguishable from accepted stock and route into a modeled rejected destination rather than being hidden inside the receiving warehouse.
- Returning or reversing receipts should recompute PO progress from submitted receipt coverage rather than leaving stale `per_received` values.

### Testing Requirements

- Backend tests should cover tenant scoping, receipt-to-PO-line linkage, quantity invariants, inventory mutation calls, and PO progress recomputation.
- Frontend tests should cover receipt creation, accepted versus rejected visibility, and receipt history on the PO detail flow.
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

- 2026-04-21: Drafted Story 24.3 from Epic 24 and the validated buying research, keeping goods receipt as the inbound execution document that updates PO receipt progress and inventory without absorbing AP or traceability scope.

### File List

- `_bmad-output/implementation-artifacts/24-3-goods-receipt-and-receiving-exceptions.md`