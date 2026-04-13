## Epic 5: Order to Cash

### Epic Goal

Sales reps can create orders, check stock availability, and have invoices auto-generated.

### Stories

### Story 5.1: Create Order Linked to Customer

As a sales rep,
I want to create an order linked to an existing customer,
So that I can track sales and generate invoices.

**Acceptance Criteria:**

**Given** a customer exists
**When** I create a new order and select the customer
**Then** the order is linked to that customer
**And** the order gets a unique order number
**And** payment terms default to customer's terms

### Story 5.2: Check Stock Availability for Order

As a system,
I want to check and display stock availability for all order line items,
So that sales reps know what's in stock before confirming orders.

**Acceptance Criteria:**

**Given** I'm creating an order with line items
**When** I add products to the order
**Then** the system displays available stock for each item in real-time
**And** if stock is insufficient, shows "Insufficient stock: [available] units"
**And** allows order creation with note about backorder

### Story 5.3: Set Payment Terms on Order

As a sales rep,
I want to set payment terms on an order (e.g., 30 days),
So that customers can pay according to agreed terms.

**Acceptance Criteria:**

**Given** I'm creating an order
**When** I set payment terms (e.g., Net 30, Net 60, COD)
**Then** the terms are recorded on the order
**And** the invoice, when generated, reflects these terms

### Story 5.4: Auto-Generate Invoice from Confirmed Order

As a system,
I want to auto-generate an invoice when an order is confirmed,
So that billing happens automatically without manual intervention.

**Acceptance Criteria:**

**Given** a sales rep confirms an order
**When** the order status changes to "confirmed"
**Then** an invoice is automatically created with correct line items, prices, and tax
**And** the invoice is linked to the order
**And** the sales rep receives confirmation

### Story 5.5: Update Order Status

As a sales rep,
I want to update order status through the lifecycle,
So that we track orders from pending to fulfillment.

**Acceptance Criteria:**

**Given** an order exists
**When** I update the status
**Then** valid transitions are: pending → confirmed → shipped → fulfilled
**And** each transition is logged to audit_log
**And** status change triggers appropriate notifications

---

