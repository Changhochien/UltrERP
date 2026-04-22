# Epic 32: Advanced Product Management, EDI Integration, and Budget Controls

## Epic Goal

Close the remaining validated operational gaps by adding product variant management with configurable attributes, Electronic Data Interchange (EDI) for trading partner integration, budget controls for financial oversight, and subcontracting workflows for outsourced manufacturing — completing the feature surface beyond what ERPNext provides while maintaining Taiwan-specific focus.

## Business Value

- Businesses can model complex products with size/color/style variants without duplicating product records.
- Trading partners can exchange purchase orders, invoices, and shipping notices electronically via EDI.
- Finance gains budget visibility and spending controls against departmental or project budgets.
- Manufacturing operations can manage subcontracted work with material transfers and subcontractor invoicing.
- UltrERP achieves feature parity with ERPNext in these four remaining operational domains.

## Scope

### Backend (Product Variants)

- Product attribute definitions with predefined value sets.
- Variant generation rules combining attributes into valid SKU combinations.
- Variant-level pricing, stock tracking, and barcode support.
- Parent product (template) vs. variant relationship model.

### Backend (EDI Integration)

- EDI document types: Purchase Order (850), Invoice (810), Shipping Notice (856), Acknowledgment (855).
- Trading partner profiles with AS2 or SFTP transport configuration.
- Inbound document parsing, validation, and conversion to internal orders/invoices.
- Outbound document generation from internal records.
- EDI transmission status tracking and retry logic.

### Backend (Budget Controls)

- Budget period definitions (monthly, quarterly, annual).
- Budget allocation by department, project, or cost center.
- Commitment tracking against purchase orders and expenses.
- Alert thresholds and blocking controls when budget limits are approached or exceeded.
- Budget vs. actual reporting.

### Backend (Subcontracting)

**Note:** Epic 24 provides the subcontracting foundation (is_subcontractor flag, subcontracting PO type, basic material transfer tracking). Epic 32 extends this with:

- Subcontracting BOM with subcontracting operations linked to BOM.
- Subcontractor service receipts linked to material transfers.
- Subcontracting cost sheets for service cost calculation.
- Material return processing and cost absorption.
- Three-way matching for subcontracting (PO → Material Transfer → Receipt → Invoice).

### Frontend

- Product variant configuration UI with attribute selection.
- Variant matrix view for bulk editing prices and status.
- EDI workspace: partner setup, document queue, transmission logs.
- Budget management workspace: budget creation, monitoring, alerts.
- Subcontracting workspace extensions: BOM-linked material transfer, service receipt, cost sheet review (basic workspace is in Epic 24).

### Data Model

**Product Variants:**
- `ProductAttribute` — name, values, type (color/size/style/custom).
- `ProductAttributeValue` — individual attribute values.
- `ProductVariant` — generated from attribute combinations, links to parent template.
- `ProductVariantPrice` — variant-specific pricing.
- `ProductVariantBarcode` — variant-specific barcodes.

**EDI:**
- `TradingPartner` — partner ID, name, EDI version, transport config.
- `EDIDocumentType` — document type definition, field mapping.
- `EDIInboundQueue` — received documents awaiting processing.
- `EDIOutboundQueue` — documents pending transmission.
- `EDITransmissionLog` — transmission history with status.

**Budgets:**
- `Budget` — period, department/project, allocated amount.
- `BudgetLine` — breakdown by category or account.
- `BudgetCommitment` — linked commitments from POs/expenses.
- `BudgetAlert` — threshold configuration and alert records.

**Subcontracting:**
- `SubcontractingOrder` — subcontractor, items, operations.
- `SubcontractingMaterialTransfer` — materials sent to subcontractor.
- `SubcontractingReceipt` — finished goods received from subcontractor.
- `SubcontractingCostSheet` — cost calculation per subcontracted item.

## Non-Goals
## Non-Goals:

- Full EDI compliance certification (X12, EDIFACT level testing).
- Multi-level BOM with nested subcontracting (basic subcontracting foundation is in Epic 24).
- Manufacturing scheduling and capacity planning for subcontracted work.
- Real-time EDI gateway hosting (relies on customer-managed EDI VAN or AS2 endpoint).
- Budget forecasting or scenario modeling.
## Technical Approach

### Product Variants

- Treat variants as first-class products with a parent reference.
- Generate variants combinatorially from attribute selections.
- Variant inherits defaults from parent but can override pricing, stock, barcodes.
- Use SCD Type 2 for variant attributes to preserve historical accuracy.
- Keep variant count reasonable with validation on maximum combinations.

### EDI Integration

- Support AS2 (HTTPS-based) and SFTP for transport.
- Parse standard X12 850/810/855/856 formats with field mapping tables.
- Convert inbound EDI to internal orders/invoices for processing.
- Generate outbound EDI from confirmed orders/deliveries.
- Provide manual requeue and retry for failed transmissions.
- Keep EDI mapping configurable per trading partner.

### Budget Controls

- Budgets are period-scoped with allocation amounts.
- Track commitments from POs and actual expenses separately.
- Compute available = allocated - committed - actual.
- Support soft alerts (warning) and hard blocks (prevent PO submission).
- Derive budget lines from chart of accounts or Epic 26 cost centers.

### Subcontracting

**Note:** Epic 24 provides the subcontracting foundation (is_subcontractor flag, subcontracting PO type, basic material transfer tracking). Epic 32 extends this with:

- Subcontracting BOM with subcontracting operations linked to work orders.
- Subcontracting cost sheets for service cost calculation from BOM operation rates.
- Material return processing when subcontractor returns unused materials.
- Three-way matching for subcontracting invoices (PO → Material Transfer → Receipt → Invoice).

**Key Constraints:**

- Product variant generation must not create unbounded SKU explosions.
- EDI support starts with a narrow set of document types; expand via configuration.
- Budget blocking must be configurable per organization; not all tenants need it.
- Subcontracting assumes the subcontractor handles the work off-site; in-house operations use Epic 27.
- Epic 32 builds upon Epic 24 subcontracting foundation; do not duplicate basic material transfer logic.
- Epic 32 is low priority relative to earlier epics and should not delay their completion.

## Dependency and Phase Order

1. Budget Controls (Stories 32.6-32.7) land after Epic 26 (GL/Accounting) since it depends on the account and cost center structure.
2. Product Variants (Stories 32.1-32.2) land after Epic 22 (UI Foundation) for form primitives and Epic 29 (Quality) for inspection template integration.
3. EDI Integration (Stories 32.3-32.5) lands after Epic 24 (Purchase Orders) since EDI primarily targets purchase orders and invoices.
4. **Subcontracting (Stories 32.8-32.9) depends on Epic 24 (Purchase Orders + Subcontracting Foundation)** for:
   - Story 32.8: BOM linking to subcontracting POs (Epic 24 Story 24.6 establishes PO type and basic material transfer)
   - Story 32.9: Receipt integration (Epic 24 Story 24.6 establishes basic receipt tracking)
5. Epic 32 stories can be split across teams if earlier dependencies are met.

---

## Story 32.1: Product Attribute Definitions and Variant Configuration

**Context:** UltrERP currently supports simple products without variant support. Businesses with size/color/style product lines must create separate products manually. This story adds attribute-based variant configuration.

**R1 - Attribute master records**
- Add `ProductAttribute` records with name, description, and attribute type (color, size, style, custom).
- Add `ProductAttributeValue` records with value name, hex code (for colors), and display order.
- Support active/inactive attribute and value states.

**R2 - Parent product as template**
- Add `is_template` flag to product records.
- Template products hold the base product info but are not sellable directly.
- Link variants to template via `parent_product_id`.

**R3 - Variant generation**
- Generate all valid attribute combinations as candidate variants.
- Support "invalid combination" rules to prevent impossible variants.
- Batch-create variants from the generator UI.
- Preserve existing simple products (no variant) during migration.

**R4 - Variant-specific data**
- Allow variant-level: code, name, description, standard cost, barcodes.
- Default inherited values from parent when variant-specific value is empty.
- Track variant stock independently in warehouse stock records.

**Acceptance Criteria:**

**Given** an admin creates a "Size" attribute with values "S", "M", "L", "XL"
**When** the attribute is saved
**Then** it is available for assignment to template products

**Given** a template product has "Size" and "Color" attributes assigned
**When** the variant generator runs
**Then** it creates 4 × N variants (4 sizes × N colors)

**Given** a variant is created with no custom code
**When** it is saved
**Then** the system generates a code from parent code + attribute values

**Given** a user searches for a specific variant SKU
**When** the search returns the variant
**Then** stock levels, price, and barcode are variant-specific

---

## Story 32.2: Variant Matrix View and Bulk Operations

**Context:** Managing variants individually is tedious when a product has many combinations. A matrix view enables bulk editing.

**R1 - Variant matrix UI**
- Display product variants in a grid: rows = attribute A, columns = attribute B.
- Show current stock, price, and status per cell.
- Support inline editing directly in matrix cells.

**R2 - Bulk status changes**
- Allow selecting multiple variants and setting status (active/inactive) together.
- Preserve existing bulk operations where they exist.

**R3 - Variant barcode assignment**
- Support assigning or generating barcodes per variant via matrix.
- Print barcode labels for selected variants.

**Acceptance Criteria:**

**Given** a template product has 20 variants across size and color
**When** the matrix view loads
**Then** the grid shows 4 rows (sizes) × 5 columns (colors) with current values

**Given** a user changes the price in one matrix cell
**When** the change is saved
**Then** only that variant's price is updated

**Given** a user selects 5 variants and marks them inactive
**When** the bulk action is applied
**Then** all 5 variants show inactive status

---

## Story 32.3: EDI Trading Partner Setup and Document Configuration

**Context:** UltrERP needs to exchange documents electronically with trading partners who require EDI. This story establishes the EDI infrastructure.

**R1 - Trading partner profiles**
- Add `TradingPartner` records with: partner ID, name, EDI version (X12 4010/5010), document types supported.
- Store transport configuration: AS2 ID/certificates or SFTP credentials.
- Mark partners as active/inactive.

**R2 - EDI document type mapping**
- Define document type configurations for 850, 810, 855, 856.
- Map EDI fields to internal order, invoice, and delivery fields.
- Support field transformation rules (date formats, code mappings).

**R3 - Connection testing**
- Provide test transmission capability for AS2 and SFTP.
- Store connection test results with timestamps.

**Acceptance Criteria:**

**Given** an admin creates a trading partner with AS2 configuration
**When** the test connection is triggered
**Then** the system reports success or failure with error details

**Given** a trading partner supports X12 850 (Purchase Order) and 856 (ASN)
**When** the partner record is saved
**Then** both document types are available for inbound/outbound processing

---

## Story 32.4: Inbound EDI Processing — Purchase Orders

**Context:** Trading partners send purchase orders via EDI. UltrERP must receive, parse, validate, and convert them to internal orders.

**R1 - Inbound document receipt**
- Receive EDI documents via AS2 (pull) or SFTP (polling).
- Store raw document in `EDIInboundQueue` with status: received, processing, completed, failed.
- Log receipt timestamp and source partner.

**R2 - Parsing and validation**
- Parse X12 850 into internal order structure.
- Validate required fields and data format.
- Map EDI codes to internal product/supplier references via mapping table.
- Flag unresolvable items for manual review.

**R3 - Order conversion**
- Convert validated 850 to internal purchase order.
- Link original EDI reference on PO header.
- Notify appropriate users of new PO from EDI.

**R4 - Acknowledgment generation**
- Generate and send EDI 855 (Purchase Order Acknowledgment) for each received 850.
- Include acceptance, changes, or rejection status per line.

**Acceptance Criteria:**

**Given** an EDI 850 is received from a trading partner
**When** it is processed
**Then** a purchase order is created with correct supplier, items, quantities, and dates

**Given** an EDI 850 contains an unrecognized product code
**When** the parser runs
**Then** the line is flagged for manual mapping and processing continues

**Given** an EDI 850 is successfully processed
**When** the acknowledgment is sent
**Then** the 855 reflects acceptance of all recognized lines

---

## Story 32.5: Outbound EDI Processing — Invoices and Shipping Notices

**Context:** UltrERP must send invoices and shipping notices to trading partners via EDI.

**R1 - Outbound document generation**
- Generate EDI 810 from confirmed invoices when partner requires it.
- Generate EDI 856 from delivery notes when partner requires ASN.
- Apply field mapping and transformation rules per partner configuration.

**R2 - Outbound queue management**
- Queue generated documents in `EDIOutboundQueue`.
- Support manual hold, release, and requeue actions.
- Track document status: pending, transmitted, acknowledged, failed.

**R3 - Transmission and retry**
- Transmit documents via configured transport (AS2/SFTP).
- Retry failed transmissions with exponential backoff.
- Log all transmission attempts with response codes.

**Acceptance Criteria:**

**Given** an invoice is confirmed for a trading partner configured for EDI
**When** the invoice is saved
**Then** an EDI 810 is generated and queued for transmission

**Given** a delivery note is completed for an EDI partner
**When** the delivery is confirmed
**Then** an EDI 856 ASN is generated with correct ship-from, ship-to, and item details

**Given** an outbound transmission fails
**When** the retry job runs
**Then** the document is retransmitted up to the configured retry limit

---

## Story 32.6: Budget Definition and Allocation

**Context:** UltrERP needs budget controls to track spending against allocated amounts per department, project, or cost center.

**R1 - Budget master records**
- Add `Budget` records with: name, period (monthly/quarterly/annual), start date, end date, allocation amount.
- Link budget to cost center, department, or project (or organization-wide).
- Support multiple budget types: expense, revenue, purchase.

**R2 - Budget line breakdown**
- Add `BudgetLine` for detailed allocation by category or account.
- Sum of line amounts must equal or be less than budget allocation.
- Track committed and actual amounts per line.

**R3 - Budget versioning**
- Support budget revisions (v2, v3) with change history.
- Track revision reason and approval status.

**Acceptance Criteria:**

**Given** a finance user creates an annual expense budget for Q1 2027
**When** the budget is saved
**Then** it is active for the specified period with zero committed and actual amounts

**Given** a budget has 5 lines totaling $50,000
**When** the budget is submitted
**Then** it is locked for editing except by admins

---

## Story 32.7: Budget Commitment Tracking and Alert Controls

**Context:** Purchase orders and expenses should be tracked against budgets to prevent overspending.

**R1 - Commitment tracking**
- When a PO is created, calculate the commitment impact on relevant budgets.
- Update committed amount on budget lines when PO is submitted.
- Release commitment when PO is cancelled or completed.

**R2 - Alert thresholds**
- Add configurable alert thresholds: e.g., 80% warning, 100% blocking.
- Fire alerts when threshold is crossed: in-app notification + optional email.
- Allow soft alerts (warning only) vs. hard blocks (prevent submission).

**R3 - Budget vs. actual reporting**
- Show allocated, committed, actual, and available amounts per budget and line.
- Include variance (available - 0 if negative indicates overspend).

**Acceptance Criteria:**

**Given** a PO for $5,000 is submitted against a budget with $10,000 available
**When** the PO is saved
**Then** the budget committed amount increases by $5,000 and available decreases to $5,000

**Given** a budget reaches 90% committed with an 80% warning threshold configured
**When** the next PO is created
**Then** a warning notification is sent to the budget owner

**Given** a budget reaches 100% committed with blocking enabled
**When** a new PO is submitted
**Then** the submission is blocked with a clear budget exhaustion message

---

## Story 32.8: Subcontracting BOM and Cost Sheet

**Context:** Epic 24 provides the subcontracting foundation (is_subcontractor flag, subcontracting PO type, basic material transfer). This story extends that foundation with BOM-linked subcontracting, cost sheet calculation, and material return processing.

**Note:** This story builds on Epic 24's foundation. Do not implement the is_subcontractor flag or basic SubcontractingMaterialTransfer here — those are in Epic 24.

**R1 - Subcontracting BOM**
- Add `BOMType` with subcontracting option.
- Subcontracting BOM specifies the operation, subcontractor, and cost per unit.
- Support material items that will be transferred to subcontractor.

**R2 - Material transfer to subcontractor (extends Epic 24)**
- Link material transfer to subcontracting BOM for cost calculation.
- Track transfer status: pending, in transit, delivered, returned.
- Update subcontractor-held stock in inventory.

**R3 - Material return processing**
- Handle return of unused materials from subcontractor.
- Calculate material consumption (transferred - returned).
- Update cost absorption for finished goods.

**Acceptance Criteria:**

**Given** a product has a subcontracting BOM with operations and material items
**When** a subcontracting PO is created
**Then** the BOM is linked and material transfer can be initiated

**Given** materials are transferred to a subcontractor
**When** unused materials are returned
**Then** the material consumption is calculated and cost absorption is updated

**Given** a subcontracting receipt is recorded
**When** the cost sheet is generated
**Then** service cost from BOM operation rates is calculated

---

## Story 32.9: Subcontracting Receipt and Invoice Matching

**Context:** This story extends Epic 24's subcontracting receipt with cost sheet integration and three-way matching for subcontracting invoices.

**R1 - Receipt recording (extends Epic 24)**
- Record received quantities against the material transfer and BOM.
- Track accepted vs. rejected quantities.
- Update subcontractor-held stock: decrease received materials, increase finished goods.

**R2 - Service cost calculation**
- Calculate subcontracting cost from BOM operation rates × received quantity.
- Add material consumption cost (from Story 32.8 material return).
- Generate subcontracting cost sheet for review and approval.

**R3 - Subcontracting invoice matching**
- Link received subcontracting costs to purchase invoices.
- Support three-way matching: PO → Material Transfer + Receipt → Invoice.
- Flag discrepancies between PO price, BOM cost, and invoice amount.

**Acceptance Criteria:**

**Given** a material transfer for 100 units is in "delivered" status
**When** the subcontractor reports 95 units completed
**Then** a receipt is created with 95 accepted, 5 rejected, and finished goods inventory increases by 95

**Given** 95 units are received at $2/unit subcontracting cost + $10 material cost
**When** the cost sheet is generated
**Then** the total subcontracting cost is $200 service + $10 material = $210, ready for invoice matching

**Given** a subcontracting invoice arrives
**When** it is matched against PO and receipt
**Then** the system flags any price or quantity discrepancies

---

## Story 32.10: EDI and Budget Audit Trails

**Context:** EDI transactions and budget changes require proper audit logging for compliance.

**R1 - EDI audit logging**
- Log all EDI transmissions with: timestamp, direction (inbound/outbound), document type, partner, status, raw document reference.
- Keep raw EDI document content for dispute resolution.
- Retain logs per configured retention policy.

**R2 - Budget change audit**
- Log all budget modifications: who changed what, when, previous and new values.
- Log all commitment and actual postings against budgets.
- Include PO reference and invoice reference where applicable.

**R3 - Subcontracting audit**
- Log material transfers and receipts with quantities and timestamps.
- Track cost sheet approvals and changes.

**Acceptance Criteria:**

**Given** an EDI 850 is processed
**When** the processing completes
**Then** the transmission log shows: received at, parsed at, converted to PO#, any failures

**Given** a budget line amount is revised from $10,000 to $12,000
**When** the revision is saved
**Then** the audit log shows: user, timestamp, old value, new value, reason

**Given** an auditor requests EDI document content from 6 months ago
**When** the system retrieves the log entry
**Then** the raw EDI content is available for download
