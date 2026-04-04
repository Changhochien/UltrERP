# Reorder Logic

## Reorder Point System
Each product-warehouse combination has a configurable `reorder_point` — the minimum stock threshold that triggers an alert.

### Alert Trigger Condition
```
current_quantity <= reorder_point  →  alert created/updated (PENDING)
current_quantity > reorder_point   →  alert resolved (RESOLVED)
```

**Note:** Alerts trigger at `<=` (proactive), while the UI display flag `is_below_reorder` uses strict `<` ("at reorder point" is not "below").

### Alert States
| State          | Description                                    |
|----------------|------------------------------------------------|
| `PENDING`      | Stock is at or below reorder point             |
| `ACKNOWLEDGED` | User has seen the alert                        |
| `RESOLVED`     | Stock has been replenished above reorder point |

### Auto-Resolution
- When stock rises above `reorder_point` (e.g., after receiving a supplier order), existing non-resolved alerts are automatically set to `RESOLVED`
- If stock drops again, a resolved alert is reactivated back to `PENDING`

### Zero Reorder Point
- Products with `reorder_point <= 0` skip alert checking entirely
- This effectively disables reorder alerts for that product-warehouse pair

## Alert Query
`list_reorder_alerts()` returns alerts joined with product and warehouse names, supporting:
- **Status filter:** Show only PENDING, ACKNOWLEDGED, or RESOLVED
- **Warehouse filter:** Scope to a specific warehouse
- **Pagination:** `limit` + `offset`

## MCP Tool
The `inventory_reorder_alerts` tool exposes this via MCP with optional `status_filter`, `warehouse_id`, `limit`, and `offset` parameters.

## Codebase References
- Alert logic: `backend/domains/inventory/services.py` → `_check_reorder_alert()`
- Alert query: `backend/domains/inventory/services.py` → `list_reorder_alerts()`
- Alert model: `backend/common/models/reorder_alert.py` → `ReorderAlert`, `AlertStatus`
