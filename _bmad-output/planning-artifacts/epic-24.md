# Epic 24: Supplier Sourcing, Purchase Orders, and Goods Receipt

## Epic Goal
## Epic Goal:

Close the validated purchase-cycle gap by adding RFQ, supplier quotation, purchase order, and goods receipt workflows that create clean procurement lineage from sourcing through receiving. Establish the subcontracting foundation for outsourced manufacturing with material transfer tracking.

## Business Value:

- UltrERP can issue real supplier orders instead of relying on read-only supplier invoices.
- Receiving becomes auditable and inventory-ready instead of implied.
- Finance gains the document lineage needed for later three-way matching and AP posting.
- Supplier comparisons move from ad hoc spreadsheets into the system.
- Subcontracting operations can track materials sent to subcontractors separately from services received.
## Scope
## Scope:

**Backend:**
- New procurement flows for RFQ, Supplier Quotation, Purchase Order, and Goods Receipt.
- Supplier, product, and warehouse linkage using existing UltrERP masters.
- Line-level lineage fields so purchase invoices and receipts can reference the correct PO rows later.
- Subcontracting supplier type and material transfer tracking for outsourced manufacturing.

**Frontend:**
- Procurement workspace for RFQ comparison, PO authoring, and receipt processing.
- Receiving screens for partial, over, and rejected quantities.
- Shared feedback, navigation, and form patterns from Epic 22.
- Subcontracting workspace for material transfers to subcontractors.

**Data Model:**
- RFQ per-supplier quote status.
- PO statuses, scheduled dates, per-received, and per-billed tracking.
- Receipt records with accepted, rejected, and pending quantities.
- Subcontracting order type and material transfer records.
## Non-Goals:

- Full landed-cost valuation distribution.
- Full auto-posted AP accounting in the first procurement slice.
- Manufacturing-driven procurement planning.
- Full subcontracting depth (see Epic 32 for complete subcontracting workflows)
## Technical Approach
## Technical Approach:

- Start with a simple but explicit sourcing chain: RFQ -> Supplier Quotation -> Purchase Order -> Goods Receipt.
- Keep receiving and inventory mutation explicit rather than embedding it inside invoice workflows.
- Preserve enough line-level identifiers to support later three-way matching, landed cost, and finance posting.
- Prefer additive procurement tables over overloading the existing supplier invoice model.
- Add subcontracting as a specialized PO type with separate material transfer tracking; deeper subcontracting (BOM-linked subcontracting, cost sheets, return processing) is detailed in Epic 32.
## Key Constraints
## Key Constraints:

- The validated review is explicit: Purchase Order is high effort and should be scoped accordingly.
- The local ERPnext reference checkout does not fully corroborate PO and Purchase Receipt JSON details; field-level parity must be re-verified against the live ERPnext source during implementation.
- Epic 24 should start with a schema-verification spike against the live ERPnext repository before Story 24.2 and Story 24.3 are implemented.
- Procurement must reuse the existing supplier, product, warehouse, and approval surfaces instead of inventing duplicates.
- Subcontracting support in Epic 24 establishes the foundation; Epic 32 provides the complete subcontracting depth (BOM-linked subcontracting, cost sheets, material return workflows).
## Dependency and Phase Order
## Dependency and Phase Order:

1. RFQ and Supplier Quotation land before PO comparison and award flows.
2. Purchase Order lands before Goods Receipt.
3. Goods Receipt lands before purchase-side finance automation in Epic 26.
4. Later traceability work in Epic 29 extends receiving; it does not redefine procurement lineage.
5. Subcontracting foundation (Story 24.6) lands alongside Goods Receipt; full subcontracting depth follows in Epic 32.
---

## Story 24.1: RFQ and Supplier Quotation Workspace

- Add RFQ authoring, supplier distribution, and per-supplier quote-status tracking.
- Capture supplier quotations with validity dates, quoted items, and award comparison fields.
- Make supplier comparison visible in one workspace before PO creation.

**Acceptance Criteria:**

- Given a buyer issues an RFQ to multiple suppliers, response state is visible per supplier.
- Given supplier quotations arrive, price and schedule differences can be compared without exporting to spreadsheets.
- Given an RFQ closes, the winning supplier can be chosen as the PO source of truth.

## Story 24.2: Purchase Order Authoring, Approval, and Lifecycle

- Add purchase orders with supplier, items, schedule date, warehouse, currency, and status workflow.
- Track per-received and per-billed percentages at header and line levels.
- Integrate with approval rules where spend thresholds require it.
- Support subcontracting PO type with supplier selection from subcontractor list.

**Acceptance Criteria:**

- Given a supplier quotation is accepted, a purchase order can be created without rekeying item data.
- Given a PO is submitted, open, closed, or cancelled, the state remains explicit in list and detail views.
- Given only part of a PO is received or billed, the progress fields remain correct.
- Given a subcontracting supplier is selected, the PO is tagged as subcontracting type for downstream material transfer processing.

## Story 24.3: Goods Receipt and Receiving Exceptions

- Add receipt processing against purchase-order lines.
- Record accepted quantity, rejected quantity, receiving warehouse, and exception notes.
- Preserve supplier delivery audit history for each receiving event.

**Acceptance Criteria:**

- Given a partial delivery arrives, the receipt records only the delivered quantities and keeps the PO open.
- Given goods are rejected, the rejected quantity and warehouse treatment remain explicit.
- Given a receiver reviews a PO, receipt history and remaining open quantities are visible.

## Story 24.4: Procurement Lineage and Three-Way-Match Readiness

- Persist RFQ, quotation, PO, receipt, and supplier invoice references at the line level.
- Add tolerances and mismatch flags needed for later invoice controls.
- Expose procurement lineage to reporting and audit consumers.

**Acceptance Criteria:**

- Given a supplier invoice arrives later, the system can trace it back to the relevant PO and receipt lines.
- Given quantities or prices diverge beyond tolerance, the mismatch is surfaced before posting.
- Given finance inspects a purchase document, the source and downstream links are visible.

## Story 24.5: Supplier Controls and Procurement Extensions

- Add supplier hold controls, supplier scorecard tracking, and contract-ready reference fields.
- Leave clean extension points for blanket orders and landed-cost allocation.
- Ensure procurement reporting can rank supplier responsiveness and quote conversion.
- Establish subcontractor-specific supplier fields (is_subcontractor flag, lead time, quality terms).

**Acceptance Criteria:**

- Given a supplier is blocked or on hold, RFQ and PO authoring respects that control.
- Given supplier performance scores fall below policy thresholds, buyers see warning or blocking behavior before RFQ or PO submission.
- Given procurement performance is reviewed, quote turnaround and award outcomes are reportable.
- Given later blanket-order or landed-cost work lands, procurement documents already expose stable reference hooks.
- Given a supplier is marked as subcontractor, the PO creation workflow surfaces subcontracting-specific fields.
- Given subcontracting BOMs are needed, the supplier selection respects the is_subcontractor flag for subcontracting POs (full BOM linking is in Epic 32).

## Story 24.6: Subcontracting Workflow Foundation

**Context:** Epic 24 establishes the subcontracting foundation for outsourced manufacturing. This enables tracking materials sent to subcontractors separately from services received. Full subcontracting depth (BOM-linked subcontracting, cost sheets, material return workflows) is detailed in Epic 32.

- Add `is_subcontractor` flag to supplier records with subcontractor-specific fields.
- Add subcontracting PO type that references the supplier as subcontractor.
- Add `SubcontractingMaterialTransfer` for tracking materials sent to subcontractor.
- Track subcontracting receipt separately from regular goods receipt.
- Maintain material consumption lineage for later cost absorption.

**Acceptance Criteria:**

- Given a supplier is marked as subcontractor, PO creation surfaces subcontracting-specific fields.
- Given a subcontracting PO is created, a material transfer can be initiated against it.
- Given materials are transferred to a subcontractor, the transfer is tracked with quantity and status (pending, in transit, delivered, returned).
- Given a subcontracting receipt is recorded, material provided versus service received is auditable.
- Given full subcontracting BOMs are needed, Epic 32 extends this foundation with BOM-linked cost sheets and return processing.