# Supplier Order Lifecycle

## Overview
Supplier orders (purchase orders) track the procurement of inventory from vendors. When goods are received, stock levels are updated and reorder alerts are automatically resolved.

## Order States

```
DRAFT ──► SUBMITTED ──► PARTIALLY_RECEIVED ──► RECEIVED
                │                                  │
                └──────► CANCELLED                 └──► (stock updated, alerts resolved)
```

| State                | Description                                   |
|----------------------|-----------------------------------------------|
| `DRAFT`              | Order created, not yet sent to supplier       |
| `SUBMITTED`          | Sent to supplier, awaiting delivery           |
| `PARTIALLY_RECEIVED` | Some line items received, others pending      |
| `RECEIVED`           | All items received, stock updated             |
| `CANCELLED`          | Order cancelled before full receipt           |

## Stock Update on Receipt
When items are received against a supplier order:
1. `WarehouseStock.quantity` is increased by the received amount
2. `_check_reorder_alert()` is called to auto-resolve alerts if stock is now above reorder point
3. Stock movement records are created for audit trail

## Multi-Warehouse
- Each supplier order line specifies a destination warehouse
- Different lines in the same order can target different warehouses
- Stock updates and alert checks are per warehouse

## Codebase References
- Stock adjustment on receipt: `backend/domains/inventory/services.py`
- Reorder alert auto-resolution: `backend/domains/inventory/services.py` → `_check_reorder_alert()`
- Supplier order domain: `backend/domains/inventory/services.py`
- Supplier order domain is planned for expansion in future epics
