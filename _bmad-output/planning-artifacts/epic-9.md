## Epic 9: LINE Integration

### Epic Goal

Staff receive LINE notifications for new orders; customers can submit orders via LINE BOT.

### Stories

### Story 9.1: LINE Notification on New Order

As a staff member,
I want to receive LINE notifications when new orders are created,
So that I can respond quickly to customer orders.

**Acceptance Criteria:**

**Given** a new order is created
**When** the order is saved
**Then** a LINE notification is sent to configured staff channel
**And** notification includes: order number, customer name, order total
**And** notification is sent via LINE Notify or Messaging API

### Story 9.2: LINE BOT - Order Submission

As a customer,
I want to submit orders via LINE BOT,
So that I can place orders easily through our existing communication channel.

**Acceptance Criteria:**

**Given** a customer messages the LINE BOT
**When** the customer sends order details in text format
**Then** the BOT parses the message
**And** creates a draft order in the system
**And** sends confirmation to the customer

### Story 9.3: LINE Order Confirmation

As a system,
I want to confirm order receipt via LINE to customers,
So that they know their order was received.

**Acceptance Criteria:**

**Given** a customer submits an order via LINE
**When** the order is parsed and created
**Then** a confirmation message is sent to the customer via LINE
**And** the message includes: order number, items, estimated processing time

---

