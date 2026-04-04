# UltrERP Domain Knowledge

## Overview
Domain knowledge skills for UltrERP — a Taiwan-focused ERP system handling invoicing, inventory, customers, orders, and payments.

## Available Skills

### Taiwan eGUI & Tax
- **Path:** `taiwan-egui/SKILL.md`
- **Use when:** Questions about Taiwan tax rates, VAT, business number (統一編號) validation, invoice void rules, eGUI submission, MIG 4.1 format

### Inventory Management
- **Path:** `inventory/SKILL.md`
- **Use when:** Questions about reorder logic, stock adjustment workflow, supplier orders

## Deferred Skills
- `sales-workflow/` — Deferred to a future epic covering orders and pricing domains

## Codebase References
- Backend business logic: `backend/domains/`
- MCP tools: `backend/domains/*/mcp.py`
- MCP server: `backend/app/mcp_server.py`
- MCP auth: `backend/app/mcp_auth.py`
