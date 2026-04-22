# Story 24.6: Subcontracting Workflow Foundation

Status: drafted

## Story

As a procurement or operations user,
I want a basic subcontracting workflow,
so that materials sent to subcontractors and finished output received back can be tracked separately from normal supplier purchasing.

## Problem Statement

Stories 24.1 through 24.5 create the standard sourcing, PO, receipt, lineage, and supplier-control flow, but subcontracting introduces a different procurement pattern: UltrERP must track materials provided to a subcontractor separately from the finished output or service received back. The validated buying research confirms ERPnext supports deeper subcontracting flows with specialized orders, receipts, and material-transfer tracking, but Epic 24 only claims the foundation. Without a dedicated foundation story, subcontracted work will either be hidden inside normal PO and receipt records or will prematurely pull Epic 24 into full manufacturing-grade BOM and cost workflows.

## Solution

Add a subcontracting-foundation slice that:

- builds on the subcontractor supplier flag introduced in Story 24.5
- extends procurement with a subcontracting PO type and explicit subcontracting metadata
- adds manual, auditable material-transfer and subcontracting-receipt records that stay separate from the standard goods-receipt flow

This story should establish the subcontracting procurement foundation, not implement BOM-driven auto-creation, full material backflush, cost-sheet absorption, or return-processing depth that belongs in Epic 32.

## Acceptance Criteria

1. Given a supplier is marked as a subcontractor, when a buyer creates a subcontracting purchase order, then the workflow surfaces subcontracting-specific fields and rejects suppliers that are not flagged for subcontracting use.
2. Given a subcontracting PO is created, when it is saved, then the PO stores explicit subcontracting metadata such as PO type and finished-goods reference without requiring full BOM-linked subcontracting parity.
3. Given materials are sent to a subcontractor, when a transfer is initiated and updated, then the system tracks source warehouse, item, quantity, transfer status, and the linked subcontracting PO context explicitly.
4. Given subcontracted output is received, when a subcontracting receipt is recorded, then the received output and the related material transfers remain auditable without collapsing into the standard goods-receipt workflow.
5. Given this story is implemented, when the touched code is reviewed, then no BOM explosion, no automatic subcontracting-order creation, no cost-sheet absorption, no material backflush automation, and no subcontract-return workflow is introduced in this slice.

## Tasks / Subtasks

- [ ] Task 1: Define the subcontracting procurement contract. (AC: 1-5)
  - [ ] Reuse the supplier subcontractor flag and related supplier fields introduced in Story 24.5 instead of redefining subcontractor eligibility here.
  - [ ] Add a subcontracting PO type or equivalent explicit marker on the PO contract from Story 24.2.
  - [ ] Add the minimum subcontracting PO metadata needed for this foundation, such as finished-goods item reference and expected subcontracted quantity.
  - [ ] Keep BOM references, reserve-warehouse rules, and auto-created subcontracting orders out of scope for this first slice.
- [ ] Task 2: Add subcontracting material-transfer tracking. (AC: 2-4)
  - [ ] Create a `SubcontractingMaterialTransfer` record or equivalent model linked to the subcontracting PO.
  - [ ] Track source warehouse, subcontractor supplier, item, quantity, status, timestamps, and notes for each transfer.
  - [ ] Support a simple lifecycle such as `draft`, `pending`, `in_transit`, `delivered`, and `cancelled` without introducing manufacturing planning logic; subcontract-return processing remains deferred to Epic 32.
- [ ] Task 3: Add subcontracting receipt tracking. (AC: 2-4)
  - [ ] Create a separate subcontracting receipt record or clearly separated receipt subtype for output received from the subcontractor.
  - [ ] Link the receipt to the subcontracting PO and relevant material transfers.
  - [ ] Record the finished output received, receiving warehouse, receipt status, and a snapshot of material-provided context needed for audit.
  - [ ] Keep standard goods receipt behavior from Story 24.3 separate from this specialized subcontracting receipt flow.
- [ ] Task 4: Build subcontracting UI and review surfaces. (AC: 1-4)
  - [ ] Surface subcontracting-specific fields during PO authoring when a subcontractor supplier is selected.
  - [ ] Add list and detail views for subcontracting material transfers and subcontracting receipts.
  - [ ] Reuse Epic 22 shared forms, tables, statuses, and feedback patterns.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for subcontractor-only PO enforcement, subcontracting metadata persistence, material-transfer status changes, and receipt lineage.
  - [ ] Add frontend tests for subcontracting field visibility, transfer tracking, and subcontracting receipt review.
  - [ ] Validate that Epic 32-only capabilities such as BOM-linked generation, cost sheets, backflush, and returns do not land in this story.

## Dev Notes

### Context

- Story 24.2 explicitly left subcontracting out of the first PO slice beyond later seams.
- Story 24.5 already claims the subcontractor supplier flag and related supplier extensions.
- The validated buying research confirms ERPnext has both old and new subcontracting flows, but Epic 24 only needs a narrow foundation rather than full manufacturing parity.

### Architecture Compliance

- Build subcontracting as an additive procurement specialization, not as a full manufacturing workflow.
- Keep supplier eligibility on the supplier master, PO type on the procurement document, and transfers or receipts on dedicated subcontracting records.
- Keep normal goods receipt and subcontracting receipt distinct so audits can differentiate standard purchasing from supplied-material work.
- Defer BOM-linked automation, backflush, reserve-warehouse rules, and cost absorption to Epic 32.

### Implementation Guidance

- Likely backend files:
  - `backend/common/models/supplier.py`
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - inventory or stock-transfer seams only where transfer tracking must reference warehouse movement context
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/procurement/` subcontracting PO, transfer, and receipt views
  - supplier-maintenance UI for subcontractor eligibility already touched by Story 24.5
  - `src/lib/api/procurement.ts`
- Do not mirror both ERPnext subcontracting flows. For Epic 24, choose one explicit foundation: manual subcontracting PO metadata plus explicit material transfers and receipt tracking.
- If warehouse movement integration is needed, keep the first slice at auditable transfer tracking and explicit status updates rather than full inventory automation.

### Data Model Contract

- Subcontracting procurement should add at minimum:
  - a subcontracting PO marker such as `po_type = subcontracting` or `is_subcontracted`
  - nullable finished-goods reference and expected subcontracted quantity on the subcontracting PO
- `SubcontractingMaterialTransfer` should include at minimum:
  - `id`
  - `purchase_order_id`
  - `supplier_id`
  - `source_warehouse_id`
  - `item_id`
  - `quantity`
  - `status`
  - transfer timestamps and notes
- `SubcontractingReceipt` should include at minimum:
  - `id`
  - `purchase_order_id`
  - finished-goods reference
  - received quantity
  - receiving warehouse
  - receipt status
  - linked material-transfer references or a material snapshot for audit visibility

### Testing Requirements

- Backend tests should cover supplier eligibility checks, subcontracting PO metadata, transfer state transitions, and receipt-to-transfer lineage.
- Frontend tests should cover subcontracting field gating, transfer status display, and subcontracting receipt visibility.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-24.md`
- `../implementation-artifacts/24-2-purchase-order-authoring-approval-and-lifecycle.md`
- `../implementation-artifacts/24-3-goods-receipt-and-receiving-exceptions.md`
- `../implementation-artifacts/24-5-supplier-controls-and-procurement-extensions.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-buying-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `backend/common/models/supplier.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 24.6 from Epic 24, the validated buying research, and the existing supplier and procurement seams so subcontracted purchasing can track supplied materials and received output without pulling Epic 24 into full manufacturing subcontracting depth.

### File List

- `_bmad-output/implementation-artifacts/24-6-subcontracting-workflow-foundation.md`