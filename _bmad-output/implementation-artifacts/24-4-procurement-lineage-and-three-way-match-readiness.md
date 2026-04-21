# Story 24.4: Procurement Lineage and Three-Way-Match Readiness

Status: drafted

## Story

As a finance or procurement user,
I want purchase documents to preserve line-level lineage and mismatch signals,
so that later invoice controls and audit workflows can trace each supplier charge back to the sourcing, ordering, and receiving records that produced it.

## Problem Statement

Stories 24.1 through 24.3 introduce RFQ, supplier quotation, purchase order, and goods receipt flows, but procurement still needs stable lineage across those documents. The validated research is explicit that later supplier invoice and finance work depends on PO and receipt references at the line level, along with tolerance-aware mismatch visibility. UltrERP already has supplier invoice models, but they currently do not preserve procurement lineage fields. Without this story, later three-way match or audit work would have to retrofit references into live transactional rows after the fact.

## Solution

Add a procurement-lineage slice that:

- persists RFQ, supplier quotation, PO, goods receipt, and supplier-invoice references at line level where relevant
- adds mismatch and tolerance-ready fields without implementing final invoice-blocking policy yet
- exposes lineage and mismatch visibility in procurement and finance-facing read views

For v1, procurement lineage should use additive nullable reference fields rather than a separate linkage table. Procurement-owned documents created in Stories 24.1 through 24.3 should expose stable UUID line identifiers that are independent of display line numbers, and the existing supplier-invoice line model should gain nullable foreign-key-compatible fields such as `rfq_item_id`, `supplier_quotation_item_id`, `purchase_order_line_id`, and `goods_receipt_line_id` plus a header-compatible `purchase_order_id` when needed for read navigation.

This story should make three-way-match possible later, not implement supplier-invoice posting or a full blocking workflow.

## Acceptance Criteria

1. Given sourcing, ordering, receiving, and supplier-invoice records exist for the same purchase flow, when finance or procurement inspects a line, then the system can trace that line across RFQ, supplier quotation, PO, receipt, and supplier invoice references.
2. Given a supplier invoice line references a PO line or receipt line, when it is stored or displayed, then the downstream linkage uses stable identifiers rather than fuzzy description matching.
3. Given quantities, unit prices, or totals diverge beyond configured tolerance rules, when a document is reviewed, then mismatch flags and comparison context are visible before later posting automation is added.
4. Given a buyer or finance user opens a procurement detail or audit view, when lineage exists, then upstream and downstream links are visible at header and line level.
5. Given this story is implemented, when the touched code is reviewed, then no supplier-invoice posting engine, no final three-way-match approval workflow, and no AP ledger automation is implemented inside this readiness slice.

## Tasks / Subtasks

- [ ] Task 1: Add procurement-lineage fields and reference contracts. (AC: 1-4)
  - [ ] Lock the stable identifier contract produced by Stories 24.1 through 24.3 for RFQ item, supplier quotation item, purchase-order line, and goods-receipt line references.
  - [ ] Add stable header and line references that connect RFQ, supplier quotation, PO, goods receipt, and supplier invoice records.
  - [ ] Extend the existing supplier invoice line model with additive nullable procurement references such as `rfq_item_id`, `supplier_quotation_item_id`, `purchase_order_line_id`, and `goods_receipt_line_id`, plus header-compatible purchase-order linkage where needed for navigation.
  - [ ] Keep lineage fields additive and nullable so historical rows remain readable during rollout.
- [ ] Task 2: Add mismatch and tolerance-ready structures. (AC: 2-4)
  - [ ] Define quantity, rate, and total comparison fields needed for later three-way-match checks, including stored reference values such as `reference_quantity`, `reference_unit_price`, and `reference_total_amount`, computed variance fields such as `quantity_variance`, `unit_price_variance`, `total_amount_variance`, optional percentage deltas where useful, and a `comparison_basis_snapshot` JSON structure.
  - [ ] Add a deterministic mismatch-status field such as `not_checked`, `within_tolerance`, `outside_tolerance`, or `review_required` plus a nullable tolerance-rule reference or code.
  - [ ] Add configurable tolerance-ready flags or rule references without implementing final finance-blocking behavior.
  - [ ] Surface whether a mismatch is pending review, within tolerance, or outside tolerance.
- [ ] Task 3: Implement lineage read services and audit views. (AC: 1-4)
  - [ ] Add APIs or read models that show document lineage from sourcing through supplier invoice.
  - [ ] Expose line-level references and mismatch summaries in procurement and finance-oriented detail views.
  - [ ] Ensure historical records without full lineage still render safely with an explicit lineage state such as `linked`, `unlinked_historical`, or `missing_reference`.
- [ ] Task 4: Integrate lineage into procurement and supplier-invoice surfaces. (AC: 1-4)
  - [ ] Add procurement detail UI that links RFQ, supplier quotation, PO, and receipt rows.
  - [ ] Add supplier-invoice-facing lineage display using the existing purchases domain as the downstream read seam.
  - [ ] Keep UI language explicit that mismatch indicators are readiness signals, not final posting decisions.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for line-level reference persistence, tolerance-flag evaluation, and lineage read behavior.
  - [ ] Add frontend tests for audit-view navigation and mismatch visibility.
  - [ ] Validate that no AP posting workflow or final three-way-match gate lands in this story.

## Dev Notes

### Context

- Epic 24 explicitly calls for line-level lineage so purchase invoices and receipts can reference the correct PO rows later.
- The buying research confirms PO and receipt linkage patterns as the foundation for later invoice controls.
- UltrERP already has supplier invoice header and line models under the purchases domain, so procurement lineage should extend those compatible seams instead of introducing a parallel invoice record.
- For v1, procurement documents remain owned by the procurement domain, while the existing supplier-invoice line model gains additive nullable procurement reference columns rather than a separate lineage table.

### Architecture Compliance

- Preserve procurement lineage as additive references, not inferred joins.
- Keep mismatch visibility separate from final accounting approval or posting behavior.
- Reuse the existing purchases domain for supplier-invoice read surfaces where possible.
- Do not reinterpret this story as the implementation of full three-way-match policy.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/procurement/models.py`
  - `backend/domains/procurement/schemas.py`
  - `backend/domains/procurement/service.py`
  - `backend/domains/procurement/routes.py`
  - `backend/common/models/supplier_invoice.py`
  - `backend/domains/purchases/schemas.py`
  - `backend/domains/purchases/service.py`
  - migrations under `migrations/versions/`
- Likely frontend files:
  - `src/domain/procurement/` lineage and audit components
  - `src/domain/purchases/` or equivalent supplier-invoice detail surfaces
  - `src/lib/api/procurement.ts`
  - `src/lib/api/purchases.ts`
- Tolerance evaluation should be deterministic and explainable; store the comparison basis used to mark a mismatch.
- Tolerance configuration can start as tenant-scoped settings or a small procurement tolerance rule table, but the story must store a rule reference or rule code with each evaluated mismatch so audit views can explain why a line is inside or outside tolerance.
- Historical supplier invoices that predate procurement lineage should remain readable with null references and clear empty-state messaging.

### Testing Requirements

- Backend tests should cover null-safe rollout, line-reference persistence, mismatch flag calculation, and supplier-invoice compatibility.
- Frontend tests should cover lineage visibility on procurement and supplier-invoice screens.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-24.md`
- `../planning-artifacts/epic-23-31-execution-plan.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/erpnext-buying-detailed.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `backend/common/models/supplier_invoice.py`
- `backend/domains/purchases/schemas.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 24.4 from Epic 24, the buying research, and the existing supplier-invoice model so procurement lineage and mismatch signals have a concrete downstream seam before finance automation lands.

### File List

- `_bmad-output/implementation-artifacts/24-4-procurement-lineage-and-three-way-match-readiness.md`