# Story 5.2 Re-Validation: Check Stock Availability

**Date:** 2026-04-01
**Story:** 5-2-check-stock-availability.md
**Status:** NOT IN MODIFIED SET (unmodified since prior validation)

---

## Summary of Prior Known Issues

The prior validation identified these issues for Story 5.2:

| Issue | Description |
|-------|-------------|
| CRITICAL-1 | All orders domain code non-existent (blocked on 5.1) |
| CRITICAL-2 | Stock check endpoint in orders domain but queries inventory models — domain cohesion violation |
| CRITICAL-3 | Schema field name mismatch — story expects `available`, existing `WarehouseStockInfo` uses `current_stock` |

---

## Iteration 1: Verify Each Known Issue

### CRITICAL-1: All orders domain code non-existent

**Status: STILL BROKEN**

**Verification:**
- `backend/domains/orders/` — does NOT exist
- `backend/common/models/order.py` — does NOT exist
- `backend/common/models/order_line.py` — does NOT exist
- `src/domain/orders/` — does NOT exist
- `migrations/versions/ii999kk99l21_create_orders_tables.py` — does NOT exist

**Conclusion:** No changes. All Epic 5 stories remain unimplemented.

---

### CRITICAL-2: Stock check endpoint in orders domain queries inventory models

**Status: STILL BROKEN**

**Verification:**
The story still specifies in Task 1:
> Add `GET /api/v1/orders/check-stock?product_id={id}` to orders routes

And the Dev Notes state:
> Reuse existing `InventoryStock` and `Warehouse` models from `backend/common/models/`

**Analysis:**
- The endpoint lives in orders domain (`/orders/check-stock`)
- But queries inventory models (`InventoryStock`, `Warehouse`)
- This is a domain cohesion violation in the modular monolith pattern

The inventory domain already has `get_inventory_stocks()` and `get_product_detail()` which serve the same purpose. The story correctly references reusing these patterns, but placing the endpoint in orders domain is architecturally inconsistent.

**Conclusion:** Still broken. No architectural decision has been made to either:
1. Move the stock check endpoint to the inventory domain, OR
2. Keep it in orders but clearly document it as a cross-domain read operation

---

### CRITICAL-3: Schema field name mismatch — `available` vs `current_stock`

**Status: STILL BROKEN**

**Verification:**
The story specifies the response format:
```json
{
  "warehouses": [{ "warehouse_id", "warehouse_name", "available": int }],
  "total_available": int
}
```

The existing `WarehouseStockInfo` schema in `backend/domains/inventory/schemas.py` (lines 95-101) uses:
```python
class WarehouseStockInfo(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int      # <-- NOT "available"
    reorder_point: int
    is_below_reorder: bool
    last_adjusted: datetime | None
```

**Conclusion:** Still broken. The story expects `available` but the existing schema uses `current_stock`.

---

## Iteration 2: Deep-Dive on Domain Cohesion Issue

### Should Stock Check Be in Inventory or Orders Domain?

**Argument for inventory domain:**
- Stock data lives in inventory domain
- `InventoryStock`, `Warehouse` models are in inventory/warehouse domains
- Existing `get_inventory_stocks()` and `get_product_detail()` already provide this functionality
- Follows Single Responsibility Principle — inventory domain owns inventory data

**Argument for orders domain (story's position):**
- Sales reps need stock availability at order creation time
- The use case is "check stock for order line items"
- Having the endpoint in orders keeps order-related API in one place

**Industry standard:**
- ERP systems typically have stock availability as an inventory operation
- Salesforce Inventory API and Dynamics 365 both provide inventory-centric stock APIs
- Client applications call inventory APIs for stock data regardless of the business context

**Recommendation:**
The stock check endpoint SHOULD be in the inventory domain as `GET /api/v1/inventory/stock-availability/{product_id}`. The story should be updated to reflect this architectural decision.

---

## Iteration 3: Check if Epic 5 Changes Affected Story 5.2

**Question:** Did fixes to Stories 5.1/5.4/5.5 indirectly fix Story 5.2's issues?

**Answer:** NO

**Evidence:**
- Story 5.1: Status = `ready-for-dev` — NOT implemented
- Story 5.4: Status = `ready-for-dev` — NOT implemented
- Story 5.5: Status = `ready-for-dev` — NOT implemented

None of the Epic 5 stories have been implemented. All remain in the specification phase with zero code written. The prior validation findings remain valid — no new information has been introduced that changes the analysis.

---

## Iteration 4: Final Consistency Pass

### Internal Consistency

The story's own components are consistent:
- AC1-AC5 trace to Tasks 1-5 correctly
- Field names (`available_stock_snapshot`, `backorder_note`) are consistent with Story 5.1
- The stock check integration into `create_order()` (Task 2) correctly depends on Story 5.1's OrderLine model

### External Consistency

No changes to:
- `backend/common/models/inventory_stock.py` — still has `quantity` field
- `backend/domains/inventory/schemas.py` — `WarehouseStockInfo` still uses `current_stock`
- `backend/domains/inventory/services.py` — `get_inventory_stocks()` still exists
- `src/domain/inventory/hooks/useProductSearch.ts` — debounce pattern still valid

---

## FINAL ASSESSMENT

### STILL BROKEN (Issues Present Before and After)

| Issue | Prior Status | Current Status | Change |
|-------|-------------|----------------|--------|
| CRITICAL-1: Orders domain non-existent | BROKEN | BROKEN | None |
| CRITICAL-2: Domain cohesion violation | BROKEN | BROKEN | None |
| CRITICAL-3: Schema field name mismatch | BROKEN | BROKEN | None |

### FIXED

None — no fixes have been made to any Epic 5 story.

### NEW ISSUES

None — no new problems introduced because no code was written.

### CONFIRMED VALID

| Item | Details |
|------|---------|
| CONFIRMED-1 | `InventoryStock` model exists at `backend/common/models/inventory_stock.py` with `quantity` field |
| CONFIRMED-2 | `Warehouse` model exists at `backend/common/models/warehouse.py` |
| CONFIRMED-3 | `get_inventory_stocks()` service function exists in `backend/domains/inventory/services.py` |
| CONFIRMED-4 | `get_product_detail()` provides the per-warehouse stock query pattern |
| CONFIRMED-5 | `useProductSearch.ts` debounce hook pattern is reusable for `useStockCheck.ts` |
| CONFIRMED-6 | `DEFAULT_TENANT_ID` constant exists at `backend/common/tenant.py` |
| CONFIRMED-7 | Read-only stock check architecture is correct (does not modify inventory) |
| CONFIRMED-8 | Pydantic schema pattern with `ConfigDict(from_attributes=True)` is correct |
| CONFIRMED-9 | Tab indentation and `from __future__ import annotations` is project standard |
| CONFIRMED-10 | HTTPException error pattern from inventory routes is correct |

---

## Required Actions Before Implementation

### Must Fix (CRITICAL)

1. **CRITICAL-1 Resolution:** Story 5.1 must be implemented first to create the orders domain. Story 5.2 is blocked on the Order and OrderLine models existing.

2. **CRITICAL-2 Resolution:** Decide on stock check endpoint location:
   - **Option A:** Move stock check to inventory domain as `GET /api/v1/inventory/stock-availability/{product_id}` — RECOMMENDED
   - **Option B:** Keep in orders domain but document the cross-domain read pattern clearly

3. **CRITICAL-3 Resolution:** Update the story's response schema to use `current_stock` to match existing `WarehouseStockInfo`, OR create a new `StockCheckWarehouseInfo` schema with `available` and document the semantic difference.

### Implementation Order Recommendation

Based on cross-story dependencies:

1. **First:** Implement Story 5.1 (creates orders domain foundation)
2. **Second:** Resplit Story 5.2 into:
   - 5.2a: Stock check API in inventory domain (unblocks order creation integration)
   - 5.2b: Order integration with stock check (depends on 5.2a)
3. **Third:** Implement Stories 5.3, 5.4, 5.5 in dependency order

---

## Tally

| Category | Count |
|----------|-------|
| STILL BROKEN | 3 |
| FIXED | 0 |
| NEW ISSUES | 0 |
| CONFIRMED VALID | 10 |

**Overall:** Story 5.2 is blocked on Story 5.1 and has unresolved architectural issues. No progress has been made since the prior validation.