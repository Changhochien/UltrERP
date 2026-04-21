# Epic 29: Quality Control, Traceability, and Warehouse Mobility

## Epic Goal

Close the validated quality and traceability gaps with inspection, serial or batch control, barcode support, and scan-first warehouse workflows that fit UltrERP's existing inventory base.

## Business Value

- Regulated or traceable inventory can be handled safely.
- Warehouse teams gain faster, clearer mobile-friendly receiving, transfer, and picking flows.
- Manufacturing and procurement gain quality gates that can stop bad stock from moving silently.
- Inventory reporting becomes suitable for compliance and recall investigations.

## Scope

**Backend:**
- Quality Inspection and Quality Inspection Template records.
- Serial, batch, expiry, and bundle-style traceability records.
- Barcode master data and scan-processing utilities.
- Warehouse transfer, pick-list, and traceability reporting enhancements.

**Frontend:**
- Inspection authoring and execution views.
- Traceability and serial or batch assignment surfaces.
- Scan-first warehouse actions for receiving, transfer, and picking.

**Data Model:**
- Inspection templates, inspection results, acceptance or rejection states.
- Serial numbers, batches, expiry, and per-transaction bundle relationships.
- Item barcode and warehouse-mobility metadata.

## Non-Goals

- Full mobile app rewrite.
- Full WMS slotting parity.
- Advanced manufacturing routing.
- Replacing the current product and warehouse domain foundations.

## Technical Approach

- Treat quality inspection as a first-class domain, not as free-text notes on stock movements.
- Keep serial and batch assignment explicit at transaction-row level so traceability remains reliable.
- Reuse existing product, warehouse, transfer, and physical-count foundations wherever possible.
- Add barcode support as a shared utility that inventory, procurement, and manufacturing can all consume.

## Key Constraints

- The validated roadmap explicitly ties BOM quality requirements to later manufacturing flows, so the quality model must integrate cleanly with Epic 27.
- Serial and batch work is high effort; start with the data model and essential transaction hooks rather than every ERPnext variant on day one.
- Warehouse mobility should favor scan-first simplification instead of a second desktop-only workflow.

## Dependency and Phase Order

1. Item barcode and inspection templates should land before the heaviest scan-first flows.
2. Manufacturing integration should consume these controls after Epic 27 stabilizes.
3. Portal or service recall experiences later extend traceability rather than redefining it.

---

## Story 29.1: Quality Inspection Templates and Execution

- Add template-driven quality parameters and inspection records.
- Support incoming, in-process, and outgoing inspection modes.
- Gate stock movement or acceptance where policy requires it.

**Acceptance Criteria:**

- Given a product requires inspection, the relevant stock movement can trigger or require a quality record.
- Given an inspection fails, the acceptance result is explicit and downstream handling is controlled.
- Given managers review quality performance, pass/fail data is reportable.

## Story 29.2: Serial, Batch, Expiry, and Traceability Bundles

- Add serial numbers, batches, expiry dates, and per-row assignment structures.
- Preserve inbound, transfer, and outbound lineage across inventory events.
- Support recall-ready queries by serial, batch, or customer shipment.

**Acceptance Criteria:**

- Given traceable goods are received, their serial or batch data is captured at receipt time.
- Given goods move between warehouses or to customers, lineage remains queryable.
- Given an expiry-controlled batch exists, warehouse and sales views surface the relevant risk.

## Story 29.3: Barcode Support and Scan Processing

- Add item barcode master data and scanner-friendly parsing utilities.
- Support scan-first item lookup for receiving, picking, and transfer flows.
- Keep the scanning model compatible with mobile or handheld expansion later.

**Acceptance Criteria:**

- Given a barcode is scanned, the correct product or traceable unit resolves reliably.
- Given multiple barcodes exist for one item, selection and precedence remain explicit.
- Given a scan fails, the warehouse user gets immediate actionable feedback.

## Story 29.4: Warehouse Transfers, Pick Lists, and Putaway Guidance

- Add warehouse transfer UI upgrades, pick lists, and putaway-ready guidance.
- Improve existing multi-warehouse workflows with clearer execution states and scan actions.
- Keep transfer and picking views responsive for daily operations.

**Acceptance Criteria:**

- Given stock needs to move between warehouses, users can initiate and track the transfer in the UI.
- Given a picker prepares goods, the pick list shows what, where, and how much to move.
- Given received goods need placement, the system can surface putaway guidance without hiding manual overrides.

## Story 29.5: Traceability, Stock Closing, and Compliance Reporting

- Add reports for inspection outcomes, serial or batch lineage, and stock-closing-style cutoff controls.
- Preserve immutable audit context for compliance-sensitive inventory movements.
- Keep reporting aligned to the underlying traceability model rather than duplicating logic.

**Acceptance Criteria:**

- Given an auditor reviews a serial or batch, the movement history is available end to end.
- Given finance or operations closes a period, stock movement visibility follows the configured cutoff behavior.
- Given a quality incident occurs, reporting can isolate affected lots or serials quickly.