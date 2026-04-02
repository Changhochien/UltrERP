# Multi-Agent Patterns Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

MCP tool design principles (from MCP best practices):
- Single responsibility: one tool per business operation
- Descriptive names: domain.action.entity (e.g., customers.list, invoices.create)
- Comprehensive docstrings: explain when to use, not just what
- Typed parameters with JSON Schema
- Limit returns: max ~25 items, paginate with cursor
- Fail gracefully: structured errors with retry guidance

Auth patterns for agents:
- API key with scopes: customers:read, customers:write, invoices:read, invoices:write, admin
- MCP OAuth 2.1 for agent authorization
- Per-tool authorization checking

RBAC roles:
- admin: full CRUD all domains
- finance: invoices CRUD+void, payments CRUD
- warehouse: inventory CRUD
- sales: customers CRUD, orders CRUD, inventory read
- agent: read all, create invoices

Error response format:
- ValidationError: field-level details
- NotFoundError: entity type + ID
- PermissionError: required scope
- All include retry guidance

Key reference: modelcontextprotocol/servers (official MCP server implementations)
