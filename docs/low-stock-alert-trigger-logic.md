# Low Stock Alert Trigger Logic Specification

**Document Version:** 1.0  
**Date:** 2026-04-11  
**Status:** Draft  
**Author:** Architecture Design

---

## 1. Executive Summary

This document specifies the low stock alert trigger logic for the UltrERP inventory management system. It defines trigger conditions, alert generation strategies, deduplication rules, severity calculations, and integration patterns with the reorder point (ROP) system.

**Key Design Goals:**
- Event-driven architecture for immediate response
- Hybrid approach combining real-time and batch processing
- Consistent severity calculation matching business requirements
- Integration with computed ROP system for intelligent replenishment

---

## 2. Trigger Conditions

All trigger conditions are evaluated in response to stock changes. An alert is generated when ANY condition is met.

### 2.1 Reorder Point (ROP) Breach

**Condition:** `current_stock <= reorder_point`

**Implementation Notes:**
- Triggers when stock reaches OR falls below the configured reorder point
- Inclusive comparison (stock = ROP triggers alert)
- Applies to both manual and computed ROP values

**Alert Type Code:** `ROP_BREACH`

### 2.2 Stockout (Critical)

**Condition:** `current_stock == 0`

**Implementation Notes:**
- Special case of ROP breach, marked with CRITICAL severity
- Different notification handling (immediate escalation)
- Often requires emergency reorder action

**Alert Type Code:** `STOCKOUT`

### 2.3 Projected Stockout

**Condition:** `days_until_stockout <= lead_time_days`

Where:
```
days_until_stockout = current_stock / avg_daily_usage
lead_time_days = supplier_lead_time or configured default
```

**Implementation Notes:**
- Uses historical sales velocity (avg_daily_usage from sales_reservation adjustments)
- Threshold: product will run out before replenishment arrives
- Requires minimum demand history (configurable, default: 30 days)

**Alert Type Code:** `PROJECTED_STOCKOUT`

### 2.4 Safety Stock Violation

**Condition:** `current_stock < safety_stock`

Where safety stock is computed as:
```
safety_stock = avg_daily_usage * safety_factor * lead_time_days
```

**Implementation Notes:**
- Requires computed ROP with safety factor > 0
- Explicit violation of minimum buffer threshold
- Higher priority than ROP breach (safety stock < ROP)

**Alert Type Code:** `SAFETY_STOCK_VIOLATION`

### 2.5 ROP Change Detection

**Condition:** `new_reorder_point > old_reorder_point AND current_stock <= new_reorder_point`

**Implementation Notes:**
- Triggers when ROP is increased and current stock falls within new threshold
- Important when switching from manual to computed ROP
- Prevents silent ROP changes that expose stock risk

**Alert Type Code:** `ROP_CHANGE`

---

## 3. Alert Generation Strategy

### 3.1 Primary Strategy: Event-Driven

**Event Source:** `StockChangedEvent`

**Trigger Points:**
- `transfer_stock()` - stock transfer between warehouses
- `create_stock_adjustment()` - manual or automatic stock adjustments
- `receive_supplier_order()` - incoming stock from suppliers

**Flow:**
```
Stock Change → StockChangedEvent → AlertHandler → Create/Update/Dismiss Alert
```

**Benefits:**
- Immediate response (< 5 seconds per NFR)
- Minimal latency between stock change and alert creation
- Synchronous within transaction (atomicity guaranteed)

### 3.2 Secondary Strategy: Batch/Scheduled Scan

**Schedule:** Every 15 minutes (configurable)

**Purpose:**
1. Catch edge cases missed by event-driven system
2. Validate alert consistency with current stock levels
3. Detect projected stockouts based on updated velocity data
4. Handle orphaned or stale alerts

**Scan Logic:**
```python
async def batch_reorder_alert_scan(session):
    # 1. Find all products with pending alerts
    # 2. Verify current stock levels against alert thresholds
    # 3. Auto-resolve alerts where stock is restored
    # 4. Check for newly-breached items without alerts
    # 5. Recalculate projected stockout based on recent velocity
```

**Edge Cases Caught:**
- Stock changes via direct database updates (bypassing application layer)
- Velocity changes that shift projected stockout timeline
- ROP changes from batch computation job

### 3.3 Hybrid Strategy (Default)

**Combined Approach:**
1. **Real-time:** Event-driven alerts for immediate response
2. **Periodic:** Batch scan every 15 minutes for validation and catch-up

**Trade-offs:**
| Aspect | Event-Driven | Batch-Only |
|--------|-------------|-------------|
| Latency | < 5 seconds | 15 minutes |
| Coverage | May miss edge cases | Catches all cases |
| Complexity | Medium | Low |
| Load | Spiky (on changes) | Steady |

**Chosen:** Hybrid for best balance of responsiveness and completeness.

---

## 4. Deduplication Logic

### 4.1 Uniqueness Constraint

**Database Constraint:** `UNIQUE (tenant_id, product_id, warehouse_id)`

Ensures one active alert per product+warehouse combination at any time.

### 4.2 Alert Update Rules

| Scenario | Action |
|----------|--------|
| Alert doesn't exist + condition met | **Create new alert** |
| Alert exists (PENDING) + condition still met | **Update severity/stock** |
| Alert exists (PENDING) + condition cleared | **Auto-resolve** |
| Alert exists (ACKNOWLEDGED) + condition cleared | **Keep acknowledged** (explicit resolution required) |
| Alert exists (ACKNOWLEDGED) + condition still met | **Update severity/stock** |
| Alert exists (RESOLVED) + condition met again | **Transition to PENDING** |
| Alert exists (SNOOZED) + condition still met | **Keep snoozed** |

### 4.3 Update Rules by Alert Status

```python
def _should_update_alert(alert: ReorderAlert, new_severity: str) -> bool:
    """Determine if alert should be updated based on severity change."""
    # Always update for severity escalation
    severity_order = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
    current_order = severity_order.get(alert.severity or "INFO", 1)
    new_order = severity_order.get(new_severity, 1)
    return new_order > current_order

def _should_auto_resolve(alert: ReorderAlert, current_stock: int, reorder_point: int) -> bool:
    """Determine if alert should auto-resolve."""
    # Only PENDING alerts auto-resolve
    if alert.status != AlertStatus.PENDING:
        return False
    # ROP breach condition cleared
    return current_stock > reorder_point
```

### 4.4 ROP Change Handling

When ROP changes via computed ROP batch job:

1. **ROP Increased:** Re-evaluate if `current_stock <= new_ROP`
   - If yes: update alert severity
   - If no: keep existing (will be caught by batch scan)

2. **ROP Decreased:** 
   - Update existing alert if below new ROP
   - Clear alert if stock is now above new ROP

---

## 5. Severity Calculation

### 5.1 Severity Levels (Unified)

| Level | Code | Color | Response SLA | Notification Priority |
|-------|------|-------|--------------|----------------------|
| CRITICAL | `CRITICAL` | Red (#DC2626) | Immediate | All channels |
| WARNING | `WARNING` | Orange (#F97316) | Within 4 hours | Primary + Email |
| INFO | `INFO` | Blue (#3B82F6) | Daily digest | In-app only |

### 5.2 Severity Calculation Algorithm

**FIXED IMPLEMENTATION** (aligns with business requirements):

```python
def compute_severity(
    current_stock: int,
    reorder_point: int,
    safety_stock: float | None = None,
    avg_daily_usage: float | None = None,
    lead_time_days: int | None = None,
) -> str:
    """
    Compute alert severity based on stock level and optional safety stock.
    
    Priority: STOCKOUT > SAFETY_STOCK > ROP_BREACH
    """
    # CRITICAL: Stockout
    if current_stock == 0:
        return "CRITICAL"
    
    # CRITICAL: Stock below 25% of ROP (per BR: stock < 25% of ROP)
    if reorder_point > 0 and current_stock < reorder_point * 0.25:
        return "CRITICAL"
    
    # WARNING: Stock below ROP but >= 25% of ROP
    if current_stock < reorder_point:
        return "WARNING"
    
    # WARNING: Safety stock violation (if safety_stock is defined)
    if safety_stock is not None and current_stock < safety_stock:
        return "WARNING"
    
    # WARNING: Projected stockout within lead time
    if (avg_daily_usage is not None and 
        avg_daily_usage > 0 and 
        lead_time_days is not None):
        days_until_stockout = current_stock / avg_daily_usage
        if days_until_stockout <= lead_time_days:
            return "WARNING"
    
    # INFO: Approaching ROP (stock < 150% of ROP)
    if reorder_point > 0 and current_stock < reorder_point * 1.5:
        return "INFO"
    
    # No alert
    return "NO_ALERT"
```

### 5.3 Severity Calculation Matrix

| Condition | Current Stock | Reorder Point | Safety Stock | Result |
|-----------|---------------|---------------|--------------|--------|
| Stockout | 0 | Any | Any | CRITICAL |
| Below 25% ROP | 5 | 25 | Any | CRITICAL |
| Below ROP, >=25% | 10 | 25 | Any | WARNING |
| Safety violation | 8 | 10 | 10 | WARNING |
| Projected stockout | 15 | 20 | None | WARNING |
| Approaching ROP | 35 | 25 | None | INFO |
| Above all thresholds | 40 | 25 | 10 | NO ALERT |

### 5.4 Resolution of Inconsistencies

**Previous Implementation Issues:**
1. 50% threshold used instead of 25%
2. Safety stock not considered
3. Projected stockout not calculated

**Fix Applied:**
- Changed threshold from `reorder_point * 0.5` to `reorder_point * 0.25`
- Added safety stock evaluation
- Added projected stockout evaluation
- Unified severity calculation in `_compute_severity()`

---

## 6. Integration with ROP System

### 6.1 ROP Computation Flow

```
User triggers batch computation
        ↓
compute_reorder_points_preview() - Dry run for all products
        ↓
Admin reviews and selects rows
        ↓
apply_reorder_points() - Update reorder_point values
        ↓
Alert re-evaluation triggered via StockChangedEvent
```

### 6.2 Alert Integration Points

| ROP Event | Alert Action |
|-----------|-------------|
| Computed ROP applied | Recalculate severity if stock within new ROP |
| Manual ROP changed | Re-evaluate all alerts for affected product+warehouse |
| Safety factor changed | Recalculate safety stock thresholds |
| Lead time updated | Recalculate projected stockout |

### 6.3 Suggested Order Quantity

Calculated when alert is generated:

```python
def calculate_suggested_order_qty(
    current_stock: int,
    reorder_point: int,
    safety_stock: float | None = None,
    lead_time_days: int | None = None,
    avg_daily_usage: float | None = None,
) -> int | None:
    """
    Calculate suggested order quantity based on replenishment parameters.
    
    Returns None if insufficient data for calculation.
    """
    if lead_time_days is None or avg_daily_usage is None:
        # Fallback: order to 2x ROP
        return max(0, 2 * reorder_point - current_stock) if reorder_point > 0 else None
    
    # Standard: order to cover lead time period plus safety buffer
    target_stock = (lead_time_days * avg_daily_usage) + (safety_stock or 0)
    suggested_qty = max(0, round(target_stock - current_stock))
    
    return suggested_qty
```

### 6.4 Suggested Supplier Resolution

```python
async def get_suggested_supplier(
    session: AsyncSession,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> str | None:
    """
    Resolve dominant supplier from historical order data.
    
    Returns supplier name or None if unresolved.
    Uses 60% dominance threshold from reorder_point module.
    """
    from domains.inventory.reorder_point import (
        resolve_replenishment_source,
        SOURCE_UNRESOLVED,
    )
    
    supplier_id = await resolve_replenishment_source(
        session, product_id, warehouse_id
    )
    
    if supplier_id == SOURCE_UNRESOLVED:
        return None
    
    # Fetch supplier name
    stmt = select(Supplier.name).where(Supplier.id == supplier_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

---

## 7. Alert Data Schema

### 7.1 Core Alert Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique alert identifier |
| `tenant_id` | UUID | Yes | Tenant for multi-tenancy |
| `product_id` | UUID | Yes | Reference to product |
| `warehouse_id` | UUID | Yes | Reference to warehouse |
| `current_stock` | Integer | Yes | Stock at time of alert |
| `reorder_point` | Integer | Yes | ROP that triggered alert |
| `severity` | Enum | Yes | CRITICAL/WARNING/INFO |
| `status` | Enum | Yes | PENDING/ACKNOWLEDGED/RESOLVED/DISMISSED/SNOOZED |
| `created_at` | Timestamp | Yes | Alert creation time |
| `acknowledged_at` | Timestamp | No | When acknowledged |
| `acknowledged_by` | String | No | User who acknowledged |

### 7.2 Computed Fields (Added to Response)

| Field | Type | Computed At | Description |
|-------|------|-------------|-------------|
| `product_name` | String | Query time | Product display name |
| `warehouse_name` | String | Query time | Warehouse display name |
| `days_until_stockout` | Float | Query time | Estimated days until depletion |
| `suggested_order_qty` | Integer | Query time | Recommended order quantity |
| `suggested_supplier` | String | Query time | Recommended supplier name |
| `alert_type` | String | Creation | ROP_BREACH, STOCKOUT, etc. |

### 7.3 Alert Response Schema

```typescript
interface ReorderAlertResponse {
  id: string;
  product_id: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  current_stock: number;
  reorder_point: number;
  safety_stock: number | null;
  severity: "CRITICAL" | "WARNING" | "INFO";
  status: "PENDING" | "ACKNOWLEDGED" | "RESOLVED" | "DISMISSED" | "SNOOZED";
  alert_type: "ROP_BREACH" | "STOCKOUT" | "PROJECTED_STOCKOUT" | "SAFETY_STOCK_VIOLATION";
  days_until_stockout: number | null;
  suggested_order_qty: number | null;
  suggested_supplier: string | null;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  snoozed_until: string | null;
}
```

---

## 8. Event Handler Specification

### 8.1 StockChangedEvent Handler

```python
@on(StockChangedEvent)
async def handle_reorder_alert(event: StockChangedEvent, session: AsyncSession) -> None:
    """
    React to stock changes by creating/updating/resolve reorder alerts.
    
    Processing:
    1. Skip if reorder_point <= 0 (ROP not configured)
    2. Evaluate all trigger conditions
    3. Compute severity for worst-case condition
    4. Create/update/resolve alert as appropriate
    5. Emit notification event if new or severity-changed alert
    """
    # [See implementation in handlers.py]
```

### 8.2 Alert State Machine

```
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ACCEPTED/  │  │  SNOOZED  │  │  RESOLVED  │
    │ORDERED    │  └─────┬─────┘  └───────────┘
    └───────────┘        │              ▲
                         │              │
                         └──────────────┘
                              (after snooze period)
```

### 8.3 Transition Rules

| From State | To State | Trigger |
|------------|----------|---------|
| PENDING | ACKNOWLEDGED | User clicks acknowledge |
| PENDING | RESOLVED | Stock restored above ROP (auto or manual) |
| PENDING | SNOOZED | User snoozes for N minutes |
| PENDING | DISMISSED | User dismisses without action |
| ACKNOWLEDGED | RESOLVED | Stock restored OR supplier order placed |
| ACKNOWLEDGED | SNOOZED | User snoozes |
| SNOOZED | PENDING | Snooze period expires |
| SNOOZED | RESOLVED | Stock restored |

---

## 9. Batch Scan Specification

### 9.1 Scheduled Job Configuration

```yaml
# config/scheduler.yaml
jobs:
  - name: reorder_alert_batch_scan
    schedule: "*/15 * * * *"  # Every 15 minutes
    handler: domains.inventory.batch.alert_scan
    enabled: true
```

### 9.2 Batch Scan Logic

```python
async def batch_reorder_alert_scan(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> BatchScanResult:
    """
    Perform periodic scan for edge cases and consistency validation.
    
    Returns:
        BatchScanResult with counts of actions taken.
    """
    results = {
        "auto_resolved": 0,
        "new_alerts_created": 0,
        "severity_updated": 0,
        "projected_stockout_detected": 0,
    }
    
    # 1. Get all products with stock below ROP
    low_stock_products = await _get_low_stock_products(session, tenant_id)
    
    for product_warehouse in low_stock_products:
        # 2. Check if alert exists
        existing_alert = await _get_existing_alert(session, ...)
        
        # 3. Compute current severity
        severity = compute_severity(...)
        
        # 4. Create/update/resolve as appropriate
        if existing_alert is None:
            if severity != "NO_ALERT":
                await _create_alert(...)
                results["new_alerts_created"] += 1
        else:
            if severity == "NO_ALERT" and existing_alert.status == AlertStatus.PENDING:
                await _resolve_alert(...)
                results["auto_resolved"] += 1
            elif severity != "NO_ALERT" and severity != existing_alert.severity:
                await _update_alert_severity(...)
                results["severity_updated"] += 1
    
    # 5. Check for projected stockouts (may not have immediate ROP breach)
    results["projected_stockout_detected"] = await _detect_projected_stockouts(...)
    
    return BatchScanResult(**results)
```

---

## 10. Configuration Parameters

### 10.1 Alert Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ALERT_ENABLED` | true | Enable/disable alert system |
| `BATCH_SCAN_INTERVAL_MINUTES` | 15 | Frequency of batch scans |
| `SNOOZE_DURATION_MINUTES` | 60 | Default snooze duration |
| `MIN_DEMAND_HISTORY_DAYS` | 30 | Minimum history for projected stockout |
| `DEFAULT_LEAD_TIME_DAYS` | 7 | Fallback lead time |
| `SAFETY_FACTOR` | 0.5 | Default safety factor for computed ROP |
| `PROJECTED_STOCKOUT_THRESHOLD` | 1.0 | Days until stockout to trigger warning |

### 10.2 Severity Thresholds

| Threshold | Value | Description |
|-----------|-------|-------------|
| `CRITICAL_STOCKOUT` | 0 | Stock = 0 |
| `CRITICAL_ROP_PCT` | 0.25 | Stock < 25% of ROP |
| `WARNING_ROP_PCT` | 1.0 | Stock < ROP but >= 25% |
| `INFO_APPROACHING_PCT` | 1.5 | Stock < 150% of ROP |

---

## 11. Integration Testing Requirements

### 11.1 Unit Test Cases

| Test Case | Expected Result |
|-----------|----------------|
| Stock drops to exactly ROP | Alert created with WARNING severity |
| Stock drops to zero | Alert created with CRITICAL severity |
| Stock below 25% of ROP | Alert created with CRITICAL severity |
| Stock restored above ROP | PENDING alert auto-resolved |
| ACKNOWLEDGED alert stock restored | Alert stays acknowledged |
| Snooze expires | Alert returns to PENDING |
| ROP increased, stock within new ROP | Alert severity updated |
| Projected stockout in lead time | Alert created with WARNING |

### 11.2 Integration Test Cases

| Test Case | Expected Result |
|-----------|----------------|
| Stock transfer triggers alert on source | Source warehouse alert created |
| Stock transfer triggers alert on destination | Not triggered (stock increases) |
| Supplier delivery resolves alert | Alert resolved, stock restored |
| Batch scan catches missed alert | Alert created during scan |
| Multiple stock changes within seconds | Single alert, latest severity |

---

## 12. Appendix: Current vs Proposed

### 12.1 Inconsistency Fixes

| Item | Current Implementation | Proposed Implementation |
|------|----------------------|------------------------|
| Severity 50% threshold | `current_stock < reorder_point * 0.5` → WARNING | `current_stock < reorder_point * 0.25` → CRITICAL |
| Safety stock check | Not implemented | Added to severity calculation |
| Projected stockout | Not implemented | Added condition with velocity-based calculation |
| Suggested order qty | Not in alert schema | Added to query response |
| Suggested supplier | Not in alert schema | Added to query response |
| Batch scan | Not implemented | Added scheduled job |

### 12.2 Migration Path

1. **Phase 1:** Fix severity calculation logic (backward compatible)
2. **Phase 2:** Add computed fields to query response (non-breaking)
3. **Phase 3:** Implement batch scan job (additive)
4. **Phase 4:** Add safety stock tracking to model (migration required)

---

## 13. References

- Business Requirements: `docs/low-stock-alert-business-requirements.md`
- Reorder Point Module: `backend/domains/inventory/reorder_point.py`
- Alert Service: `backend/domains/inventory/services.py`
- Event Handler: `backend/domains/inventory/handlers.py`
- Event System: `backend/common/events.py`
- Alert Model: `backend/common/models/reorder_alert.py`