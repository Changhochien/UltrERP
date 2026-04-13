## Epic 11: User & Access Management

### Epic Goal

Admins can manage users with role-based access control across all surfaces (UI, API, MCP, CLI).

### Stories

### Story 11.1: Create Users with Roles

As an admin,
I want to create users with specific roles,
So that I can control who has access to what.

**Acceptance Criteria:**

**Given** I'm an admin
**When** I create a new user
**Then** I can assign one of these roles: Owner, Finance, Warehouse, Sales
**And** the user receives an invitation to set up their account
**And** RBAC is enforced immediately upon activation

### Story 11.2: RBAC in UI

As a system,
I want to enforce RBAC in the UI,
So that users only see features appropriate to their role.

**Acceptance Criteria:**

**Given** a user is logged in
**When** they access the UI
**Then** menu items are filtered by role
**And** Finance users see: Invoices, Payments, Customers (read-only)
**And** Warehouse users see: Inventory, Orders (read-only)
**And** Sales users see: Customers, Orders, Inventory (read-only)

### Story 11.3: RBAC in API

As a system,
I want to enforce RBAC consistently in the API layer,
So that unauthorized access is blocked at all endpoints.

**Acceptance Criteria:**

**Given** an API request is made
**When** the request includes authentication
**Then** the system validates role permissions
**And** returns 403 for unauthorized endpoints
**And** audit_log records the access attempt

### Story 11.4: RBAC for MCP/CLI

As a system,
I want to enforce RBAC and auth scopes consistently across MCP and CLI surfaces,
So that all access methods are equally secure.

**Acceptance Criteria:**

**Given** an MCP or CLI request is made
**When** the request includes bearer token or API key
**Then** the system validates scopes: customers:read, invoices:write, etc.
**And** returns 403 for unauthorized tool calls
**And** audit_log records the access attempt

### Story 11.5: Human-in-the-Loop for Sensitive Writes

As a system,
I want to require explicit human confirmation for sensitive write actions via AI or automation,
So that we prevent unauthorized changes.

**Acceptance Criteria:**

**Given** a sensitive write action is triggered through AI or automation
**When** the action is: invoices.void, invoices.submit, or inventory.adjust above threshold
**Then** an approval record is created
**And** a human must explicitly confirm before execution
**And** the action is logged with approval status

### Story 11.6: Audit Log

As a system,
I want to record all invoice state changes, inventory adjustments, and user actions,
So that we have a complete audit trail.

**Acceptance Criteria:**

**Given** any of these events occur: invoice create/void, inventory adjustment, login/logout, RBAC change
**When** the event completes
**Then** audit_log records: actor_type, actor_id, action, target_entity, before_state, after_state, timestamp
**And** audit_log entries cannot be modified or deleted

---

