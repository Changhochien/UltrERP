# Inventory Management

## Overview
UltrERP inventory management covers stock tracking, reorder alerts, and supplier order lifecycle across multi-warehouse configurations with tenant isolation.

## When to Use This Skill
- Understanding reorder point logic and alert thresholds
- Supplier order workflow and states
- Warehouse-scoped inventory queries
- Stock adjustment patterns

## Key Concepts
- **Multi-warehouse:** Each tenant can have multiple warehouses; inventory is tracked per product per warehouse
- **Reorder Point:** Minimum stock threshold that triggers reorder alerts
- **Tenant Isolation:** All inventory queries are scoped by `tenant_id` via RLS (`set_tenant`)

## Reference Files
- [Reorder Logic](reference/reorder.md) — Reorder point calculation and alert conditions
- [Supplier Orders](reference/suppliers.md) — Supplier order lifecycle and states

## Codebase References
- Inventory Service: `backend/domains/inventory/services.py`
- Inventory MCP Tools: `backend/domains/inventory/mcp.py`
- Product Model: `backend/domains/inventory/models.py`
