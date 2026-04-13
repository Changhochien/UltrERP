## Epic 6: Payment Handling

### Epic Goal

Finance can record payments against invoices with automatic reconciliation.

### Stories

### Story 6.1: Record Payment Against Invoice

As a finance clerk,
I want to record payments against invoices,
So that we track what's been paid.

**Acceptance Criteria:**

**Given** an invoice exists with outstanding balance
**When** I record a payment (amount, method, date)
**Then** the payment is saved and linked to the invoice
**And** the invoice's outstanding balance is reduced
**And** the payment is logged to audit_log

### Story 6.2: Auto-Match Payments to Open Invoices

As a system,
I want to auto-match payments to open invoices during reconciliation,
So that finance doesn't have to manually match.

**Acceptance Criteria:**

**Given** a payment is recorded
**When** reconciliation runs
**Then** the system matches payments to open invoices by: customer → amount → date range
**And** if exact match found, invoices are marked as paid
**And** unmatched payments are flagged for manual review

### Story 6.3: Display Outstanding Payment Status

As a finance clerk,
I want to see outstanding payment status per invoice,
So that I know what customers owe.

**Acceptance Criteria:**

**Given** invoices exist
**When** I view the invoices list
**Then** each invoice shows: total amount, amount paid, outstanding balance
**And** invoices are sortable by outstanding balance
**And** overdue invoices are highlighted

---

