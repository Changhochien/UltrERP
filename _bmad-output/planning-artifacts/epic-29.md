# Epic 29: Quality Control, Traceability, and Warehouse Mobility

## Epic Goal

Close the validated quality and traceability gaps with inspection, serial or batch control, barcode support, scan-first warehouse workflows, AQL sampling, SPC charts, and supplier quality scorecard that fit UltrERP's existing inventory base.

## Business Value

- Regulated or traceable inventory can be handled safely.
- Warehouse teams gain faster, clearer mobile-friendly receiving, transfer, and picking flows.
- Manufacturing and procurement gain quality gates that can stop bad stock from moving silently.
- Inventory reporting becomes suitable for compliance and recall investigations.
- Taiwan-specific AQL sampling improves QC efficiency for manufacturing.
- SPC charts provide statistical visibility into process stability.
- Supplier quality scorecards enable data-driven vendor management.

## Scope

**Backend:**
- Quality Inspection and Quality Inspection Template records.
- Serial, batch, expiry, and bundle-style traceability records.
- Barcode master data and scan-processing utilities.
- Warehouse transfer, pick-list, and traceability reporting enhancements.
- AQL sampling plan definitions and sampling execution.
- SPC chart data collection and statistical calculations.
- Supplier quality scorecard metrics and scoring.

**Frontend:**
- Inspection authoring and execution views.
- Traceability and serial or batch assignment surfaces.
- Scan-first warehouse actions for receiving, transfer, and picking.
- AQL sampling wizard and acceptance/rejection decisions.
- SPC chart visualizations (X-bar, R, C, P charts).
- Supplier quality scorecard dashboard and reports.

**Data Model:**
- Inspection templates, inspection results, acceptance or rejection states.
- Serial numbers, batches, expiry, and per-transaction bundle relationships.
- Item barcode and warehouse-mobility metadata.
- AQL sampling plans with severity levels, sample sizes, and acceptance criteria.
- SPC measurement records with subgroup data and control limits.
- Supplier scorecard metrics: on-time delivery, quality rate, response time, compliance.

## Non-Goals

- Full mobile app rewrite.
- Full WMS slotting parity.
- Advanced manufacturing routing.
- Replacing the current product and warehouse domain foundations.
- Full product variant system with attribute-based configurations (see Epic 32).

## Technical Approach

- Treat quality inspection as a first-class domain, not as free-text notes on stock movements.
- Keep serial and batch assignment explicit at transaction-row level so traceability remains reliable.
- Reuse existing product, warehouse, transfer, and physical-count foundations wherever possible.
- Add barcode support as a shared utility that inventory, procurement, and manufacturing can all consume.
- Implement AQL sampling using standard ISO 2859-1 tables as reference, configurable per product category.
- Use standard SPC calculations (X-bar, R, UCL, LCL, Cp, Cpk) for process control charts.
- Build supplier scorecard from factual metrics: incoming quality data, delivery performance, and audit results.

## Key Constraints

- The validated roadmap explicitly ties BOM quality requirements to later manufacturing flows, so the quality model must integrate cleanly with Epic 27.
- Serial and batch work is high effort; start with the data model and essential transaction hooks rather than every ERPnext variant on day one.
- Warehouse mobility should favor scan-first simplification instead of a second desktop-only workflow.
- AQL and SPC are Taiwan manufacturing-specific enhancements not native to ERPNext.

## Dependency and Phase Order

1. Item barcode and inspection templates should land before the heaviest scan-first flows.
2. AQL sampling lands after inspection templates since it extends inspection criteria.
3. SPC charts land after basic inspection recording for data collection.
4. Supplier quality scorecard lands after receiving inspection since incoming quality data feeds it.
5. Manufacturing integration should consume these controls after Epic 27 stabilizes.
6. Portal or service recall experiences later extend traceability rather than redefining it.

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

## Story 29.6: AQL Sampling Plans and Execution

- Add AQL sampling plan definitions with severity levels (Critical, Major, Minor).
- Configure acceptance and rejection numbers based on sample size tables.
- Support different AQL levels per product category or customer requirement.
- Implement sampling execution wizard: select inspection lot, determine sample size, record defects.
- Calculate acceptance/rejection based on defect count vs. AQL limits.
- Link AQL inspection results to incoming quality metrics and supplier scorecards.
- Support first, double, and normal inspection switching rules per ANSI/ISO standards.

**Acceptance Criteria:**

- Given an incoming inspection is initiated for a product with AQL requirements, the system determines sample size based on lot size and AQL level.
- Given inspectors record defect counts during sampling, the system calculates acceptance or rejection.
- Given an inspection is rejected, the system flags the lot for disposition (return, rework, accept under concession).
- Given AQL inspection history exists, the defect trend by severity and supplier is reportable.
- Given a supplier consistently fails AQL inspections, the quality data feeds the supplier scorecard.
- Given normal inspection switches to reduced or tightened inspection, the system applies the correct sampling plan.

## Story 29.7: SPC Charts and Statistical Process Control

- Add SPC parameter definitions: characteristic, measurement type (variable, attribute), and control chart type (X-bar R, X-bar S, C, P, NP, U).
- Configure control limits (UCL, LCL, USL, LSL) and specification limits.
- Record SPC measurements with subgroup data, measurement timestamp, and operator.
- Calculate and display control chart with center line, control limits, and data points.
- Flag out-of-control conditions: points outside limits, runs, trends, shifts.
- Support Cp and Cpk capability indices for specification compliance.
- Provide SPC dashboard showing process stability status across characteristics.

**Acceptance Criteria:**

- Given an operator records SPC measurements for a characteristic, the system plots points on the control chart.
- Given data points are recorded, the system displays center line and control limits.
- Given a point falls outside control limits, the system flags it as out-of-control.
- Given a process shows special cause variation, the system highlights the affected points for investigation.
- Given capability indices are configured, the system calculates Cp/Cpk from measurement data.
- Given multiple characteristics are monitored, the SPC dashboard shows stability status for all at a glance.
- Given SPC data exists, historical trends are visible for process improvement analysis.

## Story 29.8: Supplier Quality Scorecard

- Add supplier quality scorecard with configurable metrics and weighting.
- Track incoming quality rate: accepted lots vs. total lots inspected.
- Track on-time delivery rate: on-time deliveries vs. scheduled deliveries.
- Track response time: average time to respond to quality issues or RFQs.
- Track compliance rate: regulatory or customer requirement compliance.
- Calculate composite score from weighted metrics.
- Generate supplier ranking and comparison reports.
- Link scorecard to NCR history for defect and corrective action tracking.
- Support scorecard period review (monthly, quarterly) with trend analysis.

**Acceptance Criteria:**

- Given an inspection lot is completed, the system updates supplier incoming quality metrics.
- Given a delivery is received on schedule, the system updates on-time delivery metrics.
- Given a supplier responds to an NCR, response time is recorded for scoring.
- Given all metrics are collected, the system calculates composite score and ranks suppliers.
- Given a supplier scorecard is reviewed, trend shows improvement or degradation over periods.
- Given a supplier score falls below threshold, the system alerts procurement for action.
- Given supplier selection occurs, scorecard data is visible to inform sourcing decisions.
