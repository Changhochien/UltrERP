## Epic 2: Invoice Lifecycle

### Epic Goal

Finance clerks can create, print, and void invoices with automatic tax calculation and MIG 4.1 compliance.

### Stories

### Story 2.1: Create MIG-Ready Invoice Snapshot

As a finance clerk,
I want to create an invoice with multiple line items, customer reference, and automatic tax calculation,
So that I can quickly issue compliant invoices without manual math.

**Acceptance Criteria:**

**Given** a customer exists in the system
**When** I create a new invoice and add line items (product, quantity, unit price)
**Then** the system auto-calculates line-level TaxType, TaxRate, and tax amount from the approved backend-owned Taiwan tax policy
**And** displays the invoice total with tax breakdown
**And** allocates the next invoice number from the configured government-issued range in format `[A-Z]{2}\d{8}` (MIG 4.1)
**And** links the invoice to the customer

### Story 2.2: Preview and Print on Approved Stationery

As a finance clerk,
I want to preview and print invoices to pre-printed stationery,
So that the printed invoice matches our established A4/A5 format exactly.

**Acceptance Criteria:**

**Given** an invoice has been created
**When** I preview the invoice
**Then** the layout matches pre-printed stationery exactly
**And** the preview surface renders in < 1 second on target hardware
**When** I click print
**Then** the invoice prints correctly on pre-printed stationery

### Story 2.3: Void Invoice Before Filing Deadline

As a finance clerk,
I want to void an invoice within the allowed regulatory window,
So that I can correct mistakes while complying with Taiwan tax law.

**Acceptance Criteria:**

**Given** an invoice remains within the allowed void window
**When** I void the invoice
**Then** the invoice status changes to "voided"
**And** replacement linkage is recorded for the follow-up invoice workflow
**And** all state changes are logged to audit_log with actor, timestamp, and reason
**And** the void is recorded in the outbox for FIA notification if eGUI enabled

**Given** an invoice is outside the allowed void window
**When** I attempt to void it
**Then** the system rejects the void with an explicit void-window-expired error

### Story 2.4: Validate Invoice Totals and Rounding

As a finance clerk,
I want the system to validate invoice totals before printing,
So that I don't issue incorrect invoices.

**Acceptance Criteria:**

**Given** I'm creating an invoice
**When** I add line items and tax
**Then** the system validates each line tax calculation and verifies sum of line totals + tax = invoice total using the approved rounding rule
**And** prevents print if validation fails
**And** shows clear error message with discrepancy amount

### Story 2.5: Archive MIG 4.1 XML in MinIO

As a system,
I want to store issuer-side invoice artifacts in MinIO,
So that we have durable archives independent of MOF platform retention.

**Acceptance Criteria:**

**Given** an invoice is issued
**When** the invoice is created
**Then** MIG 4.1 XML is generated and stored in MinIO at `{tenant_id}/mig41/{invoice_id}.xml`
**And** the storage path is recorded in the invoice record
**And** artifacts are accessible for 10+ years per retention policy

### Story 2.6: Export PDF from Shared Invoice Renderer

As a finance clerk,
I want to export an invoice to PDF,
So that I can email it to customers or save for records.

**Acceptance Criteria:**

**Given** an invoice exists
**When** I click "Export to PDF"
**Then** a PDF is generated from the shared print renderer, matching the approved pre-printed stationery layout
**And** downloaded to the user's device

### Story 2.7: Enforce Immutable Invoice Content

As a system,
I want invoices to be immutable after creation,
So that we comply with Taiwan tax requirements.

**Acceptance Criteria:**

**Given** an invoice has been created
**When** any user attempts to modify line items, amounts, or customer
**Then** the system rejects the change with error "Invoices are immutable after creation"
**And** only void operations are permitted

---

