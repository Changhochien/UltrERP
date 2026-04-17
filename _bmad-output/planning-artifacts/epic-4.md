## Epic 4: Inventory Operations

### Epic Goal

Warehouse staff can track stock levels, receive reorder alerts, and manage supplier deliveries.

### Stories

### Story 4.1: Search Products

As a warehouse staff,
I want to search products by code or name,
So that I can quickly find items during stock inquiries.

**Acceptance Criteria:**

**Given** products exist in the system
**When** I search by product code (full or partial)
**Then** matching products are returned
**When** I search by product name (full or partial)
**Then** matching products are returned
**And** results support 5,000+ products without visible stutter

### Story 4.2: View Stock Level and Reorder Point

As a warehouse staff,
I want to view current stock level and reorder point per product,
So that I can make informed decisions about stock.

**Acceptance Criteria:**

**Given** a product exists
**When** I view the product details
**Then** I see: current stock quantity, reorder point, last adjusted date
**And** stock is shown per warehouse location if multiple warehouses exist

### Story 4.3: Reorder Alerts

As a system,
I want to generate reorder alerts when stock falls below reorder point,
So that warehouse staff can proactively reorder.

**Acceptance Criteria:**

**Given** a product's stock falls below its reorder point
**When** a stock adjustment is made
**Then** an alert is generated listing products needing reorder
**And** alerts appear on dashboard (Epic 7)
**And** alerts can be viewed in the inventory module

### Story 4.4: Record Stock Adjustment with Reason Codes

As a warehouse staff,
I want to record stock adjustments with reason codes,
So that we maintain accurate inventory records with audit trail.

**Acceptance Criteria:**

**Given** I need to adjust stock for a product
**When** I record an adjustment (+/- quantity)
**Then** I must select a reason code: received, damaged, returned, correction, other
**And** all adjustments are logged to audit_log with actor, timestamp, and reason
**And** stock levels update immediately

### Story 4.5: Track Supplier Orders and Auto-Update Stock

As a system,
I want to track supplier orders and auto-update stock when goods arrive,
So that inventory stays accurate without manual intervention.

**Acceptance Criteria:**

**Given** a supplier order is marked as received
**When** I confirm receipt
**Then** stock levels automatically increase by the ordered quantity
**And** the adjustment is logged with reason "supplier_delivery"
**And** related reorder alerts are cleared

### Story 4.6: Multiple Warehouse Support

As a warehouse staff,
I want to see and manage stock across multiple warehouse locations,
So that I can allocate inventory properly.

**Acceptance Criteria:**

**Given** multiple warehouses exist
**When** I view stock
**Then** I can filter by warehouse location
**And** I can transfer stock between warehouses
**And** each warehouse shows its own stock levels

---

