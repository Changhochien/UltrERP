## Epic 8: AI Agent Interface

### Epic Goal

AI agents (Claude Code, etc.) can query ERP data via MCP with Taiwan tax domain knowledge.

### Stories

### Story 8.1: MCP Tool - Inventory Check

As an AI agent,
I want to check inventory levels via MCP tools,
So that I can answer questions about stock.

**Acceptance Criteria:**

**Given** I'm an AI agent with MCP access
**When** I call `inventory.check` with a product identifier
**Then** I receive: product name, current stock, location, reorder point, last adjusted, status
**And** response time is < 1 second (p95)

### Story 8.2: MCP Tool - Customer Query

As an AI agent,
I want to query customer data via MCP tools,
So that I can retrieve customer information.

**Acceptance Criteria:**

**Given** I'm an AI agent with MCP access
**When** I call `customers.list` or `customers.get`
**Then** I receive customer data based on my scopes
**And** current Taiwan business-number checksum validation is applied if searching by 統一編號

### Story 8.3: MCP Tool - Invoice Query

As an AI agent,
I want to query invoice data via MCP tools,
So that I can retrieve invoice information.

**Acceptance Criteria:**

**Given** I'm an AI agent with MCP access
**When** I call `invoices.list` or `invoices.get`
**Then** I receive invoice data based on my scopes
**And** invoice totals and tax are included

### Story 8.4: MCP Tool - Role-Scoped Authentication

As a system,
I want MCP tools to support role-scoped authentication,
So that agents only access what they're permitted to.

**Acceptance Criteria:**

**Given** an MCP tool is called
**When** the request includes bearer token or API key
**Then** the system validates scopes: customers:read, invoices:write, etc.
**And** requests without valid scopes are rejected with 403

### Story 8.5: Taiwan Tax Domain Knowledge (Skills)

As an AI agent,
I want Claude Code to use Taiwan tax domain knowledge from Skills files,
So that I can answer tax-related questions correctly.

**Acceptance Criteria:**

**Given** Claude Code is configured with ERP skills
**When** I ask about tax rates, void rules, or eGUI workflows
**Then** the Skills files provide accurate Taiwan tax knowledge
**And** Skills include: MIG-permitted tax policy mapping, Taiwan business-number checksum rules, and regulatory void-window policy

### Story 8.6: MCP Server - Session Mode HTTP

As a system,
I want FastMCP 2.14.6 to use session-mode HTTP transport,
So that agents can maintain persistent connections.

**Acceptance Criteria:**

**Given** FastMCP is configured
**When** agents connect to `/mcp` endpoint
**Then** transport is streamable-http (NOT stateless_http)
**And** concurrent agent connections are supported

---

