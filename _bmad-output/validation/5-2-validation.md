# Story 5.2 Validation Report: Check Stock Availability for Order

**Story:** 5.2-check-stock-availability.md
**Iteration:** 4-pass validation complete
**Date:** 2026-04-01

---

## CRITICAL Issues (Will Break Implementation)

### CRITICAL-1: Dependency on Story 5.1 Not Implemented

**Issue:** Story 5.2 depends entirely on the Order and OrderLine models created in Story 5.1. These do NOT exist in the codebase.

**Evidence:**
- `backend/domains/orders/` directory does NOT exist (confirmed via `ls`)
- `backend/common/models/order.py` does NOT exist
- `backend/common/models/order_line.py` does NOT exist
- Migration `migrations/versions/ii999kk99l21_create_orders_tables.py` does NOT exist
- `available_stock_snapshot` and `backorder_note` fields are NOT in any existing model

**Impact:** The stock check integration into `create_order()` (Task 2) cannot be implemented until Story 5.1 creates the Order/OrderLine models.

**Recommendation:** Story 5.1 must be completed before Story 5.2 implementation begins, OR Story 5.2 must be decoupled to work on the stock check API endpoint independently.

---

### CRITICAL-2: Stock Check Endpoint Placed in Orders Domain Routes

**Issue:** The story specifies adding `GET /api/v1/orders/check-stock` to `backend/domains/orders/routes.py`. However, the stock check queries `InventoryStock` and `Warehouse` which are inventory domain models.

**Story says:**
> Add `GET /api/v1/orders/check-stock?product_id={id}` to orders routes

**Analysis:**
- The stock check functionality is logically part of the inventory domain
- The existing inventory domain already has `get_inventory_stocks()` service function
- Creating this endpoint in orders domain creates a cross-domain dependency that violates the modular monolith pattern

**Recommendation:** The stock check endpoint should be added to `backend/domains/inventory/routes.py` as `GET /api/v1/inventory/stock-availability/{product_id}` to maintain domain cohesion. Alternatively, if the intent is to have orders domain call inventory services, the endpoint can stay in orders but should reuse inventory services.

---

### CRITICAL-3: Schema Response Structure Mismatch

**Issue:** The story specifies the return format for stock check:

```json
{
  "product_id": "...",
  "warehouses": [{ "warehouse_id", "warehouse_name", "available": int }],
  "total_available": int
}
```

**But the existing `WarehouseStockInfo` schema (in `domains/inventory/schemas.py` lines 95-101) uses `current_stock` not `available`:**

```python
class WarehouseStockInfo(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int      # <-- NOT "available"
    reorder_point: int
    is_below_reorder: bool
    last_adjusted: datetime | None
```

**Impact:** The story needs either:
1. A new schema `StockCheckWarehouseInfo` with `available` field, OR
2. Document that `current_stock` is the expected field name

**Recommendation:** Add `WarehouseStockInfo` usage with `current_stock` field or create a new schema if semantic difference matters.

---

## WARNINGS (Potential Issues)

### WARNING-1: Frontend Stock Check Hook Does Not Exist

**Issue:** Story references `src/domain/orders/hooks/useStockCheck.ts` as a new file to create, but there is no `src/domain/orders/` directory at all (frontend orders domain not created yet).

**Reference in story:**
> Create `src/domain/orders/hooks/useStockCheck.ts` hook

**Status:** Consistent with CRITICAL-1 - depends on Story 5.1 frontend creation.

---

### WARNING-2: OrderForm.tsx Does Not Exist

**Issue:** Story references `src/domain/orders/components/OrderForm.tsx` as the file to modify for stock display integration. This file does not exist.

**Reference in story:**
> In OrderForm.tsx (from Story 5.1), when a product is selected for a line item

**Status:** Consistent with CRITICAL-1 - depends on Story 5.1 frontend creation.

---

### WARNING-3: Test File Paths Assumed

**Story references:**
- `backend/tests/test_order_stock_check.py`
- `src/domain/orders/__tests__/OrderForm.test.tsx`

**Status:** These paths are consistent with the project structure but the files do not exist yet (depend on Story 5.1).

---

### WARNING-4: Debounce Pattern - useRef Cleanup in useEffect

**Issue:** The `useProductSearch.ts` hook (lines 58-62) has a cleanup function:

```typescript
useEffect(() => {
  return () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();
  };
}, []);
```

**Note:** The dependency array is empty `[]`, which is correct for cleanup-only effects, but the linter/TypeScript may complain about missing `timerRef` and `abortRef` in deps. This pattern is used correctly here and should be replicated in `useStockCheck`.

**Status:** Pattern is valid, but implementors should be aware.

---

### WARNING-5: Route Registration Not Documented

**Issue:** The story says to "register router in `backend/app/main.py`" for Story 5.1, but Story 5.2 does not document where the new `check-stock` endpoint router should be registered.

**For context:** The current `main.py` (lines 23-26) shows:
```python
api_v1.include_router(health_router, prefix="/health", tags=["health"])
api_v1.include_router(customers_router, prefix="/customers", tags=["customers"])
api_v1.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
api_v1.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
```

**If the stock check stays in inventory domain:** No new router registration needed.
**If the stock check goes in orders domain:** Router must be registered.

---

## CONFIRMED VALID (Paths and Patterns That Check Out)

### CONFIRMED-1: InventoryStock Model

**Path:** `backend/common/models/inventory_stock.py`
**Status:** EXISTS with all required fields

```python
class InventoryStock(Base):
    __tablename__ = "inventory_stock"
    # Fields:
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    product_id: Mapped[uuid.UUID]
    warehouse_id: Mapped[uuid.UUID]
    quantity: Mapped[int]           # <-- This is the stock level
    reorder_point: Mapped[int]
    updated_at: Mapped[datetime]
```

**Validated:** The `quantity` field is what represents available stock.

---

### CONFIRMED-2: Warehouse Model

**Path:** `backend/common/models/warehouse.py`
**Status:** EXISTS with all required fields

```python
class Warehouse(Base):
    __tablename__ = "warehouse"
    # Fields:
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    name: Mapped[str]
    code: Mapped[str]
    location: Mapped[str | None]
    address: Mapped[str | None]
    contact_email: Mapped[str | None]
    is_active: Mapped[bool]
    created_at: Mapped[datetime]
```

---

### CONFIRMED-3: get_product_detail() Service Function

**Path:** `backend/domains/inventory/services.py` (lines 529-636)
**Status:** EXISTS and provides the stock query pattern

The function already:
1. Fetches `InventoryStock` records with warehouse joins (lines 563-582)
2. Aggregates `total_stock` across warehouses (lines 586-599)
3. Returns per-warehouse stock info including `quantity` and `warehouse_name`

```python
stock_stmt = (
    select(
        InventoryStock.warehouse_id,
        Warehouse.name.label("warehouse_name"),
        InventoryStock.quantity,
        InventoryStock.reorder_point,
        last_adj_sq.c.last_adjusted,
    )
    .join(Warehouse, InventoryStock.warehouse_id == Warehouse.id)
    # ...
)
```

**This pattern can be directly reused for the stock check query.**

---

### CONFIRMED-4: get_inventory_stocks() Service Function

**Path:** `backend/domains/inventory/services.py` (lines 399-414)
**Status:** EXISTS and is simpler than get_product_detail

```python
async def get_inventory_stocks(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    *,
    warehouse_id: uuid.UUID | None = None,
) -> list[InventoryStock]:
    """Get stock levels for a product, optionally filtered by warehouse."""
    stmt = select(InventoryStock).where(
        InventoryStock.tenant_id == tenant_id,
        InventoryStock.product_id == product_id,
    )
    if warehouse_id is not None:
        stmt = stmt.where(InventoryStock.warehouse_id == warehouse_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

**This is the exact pattern needed for `check_stock_availability()` in orders services.**

---

### CONFIRMED-5: HTTPException Error Pattern

**Path:** `backend/domains/inventory/routes.py`
**Status:** CONFIRMED as the project standard

Examples from the file:

```python
# 404 Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Warehouse not found",
)

# 422 Validation Error
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    detail=f"Invalid reason code: {data.reason_code}...",
)

# 409 Conflict (Insufficient Stock)
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={
        "message": "Insufficient stock",
        "available": exc.available,
        "requested": exc.requested,
    },
)
```

**The story correctly specifies this pattern should be used.**

---

### CONFIRMED-6: useProductSearch.ts Debounce Hook Pattern

**Path:** `src/domain/inventory/hooks/useProductSearch.ts`
**Status:** EXISTS and is well-implemented

Key patterns to replicate in `useStockCheck.ts`:

1. **Debounce with useRef + setTimeout:**
   ```typescript
   const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
   ```

2. **Abort controller for request cancellation:**
   ```typescript
   const abortRef = useRef<AbortController | null>(null);
   ```

3. **Cleanup in useEffect:**
   ```typescript
   useEffect(() => {
     return () => {
       if (timerRef.current) clearTimeout(timerRef.current);
       if (abortRef.current) abortRef.current.abort();
     };
   }, []);
   ```

4. **Default debounce of 300ms:**
   ```typescript
   export function useProductSearch(debounceMs = 300)
   ```

---

### CONFIRMED-7: DEFAULT_TENANT_ID Constant

**Path:** `backend/common/tenant.py`
**Status:** EXISTS and is used project-wide

```python
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
```

**Referenced in:**
- `backend/domains/inventory/routes.py` (line 66)
- `backend/domains/customers/service.py`
- Story correctly specifies using this constant

---

### CONFIRMED-8: FakeAsyncSession Test Pattern

**Path:** `backend/tests/domains/inventory/test_product_search.py`
**Status:** EXISTS inline in test files

```python
class FakeAsyncSession:
    """Minimal fake async session for search tests."""
    def __init__(self) -> None:
        self._results: list[object] = []
    def queue_rows(self, rows: list[tuple]) -> None:
        self._results.append(rows)
    async def execute(self, _stmt: object) -> object:
        data = self._results.pop(0) if self._results else []
        # ... returns FakeResult
```

**Note:** There is no `conftest.py` - each test file defines its own FakeAsyncSession. Story should follow the same pattern.

---

### CONFIRMED-9: Tab Indentation and Future Imports

**Path:** All Python files in `backend/`
**Status:** Project standard confirmed

Every file uses:
```python
from __future__ import annotations
```

And tab indentation (not spaces).

---

### CONFIRMED-10: Inventory API Client Pattern

**Path:** `src/lib/api/inventory.ts`
**Status:** EXISTS and is well-structured

The `searchProducts` function (lines 66-79) is the closest analog to what `checkStock` should be:

```typescript
export async function searchProducts(
  query: string,
  options?: { limit?: number; warehouseId?: string; signal?: AbortSignal },
): Promise<ProductSearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
  const resp = await fetch(
    `/api/v1/inventory/products/search?${params.toString()}`,
    { signal: options?.signal },
  );
  if (!resp.ok) throw new Error("Search failed");
  return resp.json();
}
```

**A `checkStock(productId)` function should follow this same pattern.**

---

### CONFIRMED-11: Read-Only Stock Check Architecture

**Story states:** "Stock check is READ-ONLY - do NOT reduce or reserve inventory"

**Validation:** This is architecturally correct:
- No `inventory_stock` mutations in the story tasks
- `check_stock_availability()` only reads from `InventoryStock`
- Snapshot fields (`available_stock_snapshot`, `backorder_note`) are written only to `OrderLine`, never back to inventory

**This aligns with the "Stock Independence" principle in the architecture.**

---

## Web Search Findings

### Stock Availability API Best Practices

**Key findings from web search:**

1. **RESTful endpoint design**: Stock availability endpoints should return:
   - Available quantity per warehouse/location
   - Total available across all locations
   - Product identification
   - Timestamp or currency indicator (stale data warning)

2. **API Response Pattern** (Salesforce Inventory API, Dynamics 365):
   ```json
   {
     "productId": "...",
     "locations": [
       { "locationId": "...", "available": 42 },
       { "locationId": "...", "available": 10 }
     ],
     "totalAvailable": 52
   }
   ```

3. **Key considerations**:
   - Stock availability should be NEAR REAL-TIME (not cached for more than seconds)
   - Return 0 for products with no inventory, not error
   - Separate "available to fulfill" from "total on hand" (reserved stock not included)

4. **Comparison with story design**:
   - Story's response format matches industry standard
   - `total_available` field is appropriate
   - Per-warehouse breakdown is standard practice

**Reference sources:**
- Salesforce Inventory Availability API documentation
- Microsoft Dynamics 365 Inventory Visibility API
- Shopify inventory management best practices

---

### Debounce Hook Best Practices

**Key findings:**

1. **The useProductSearch.ts pattern is correct**:
   - Uses `useRef` to persist timer across renders
   - Cleans up timer in useEffect return
   - Uses AbortController for fetch cancellation
   - Default 300ms debounce is industry standard

2. **Alternative patterns exist**:
   - `useDebounce` hook (separates debounced value from callback)
   - Lodash `debounce` with `useCallback`
   - `useDeferredValue` (React 18+)

3. **The existing pattern is appropriate** for this codebase (React without external debounce library).

---

## Internal Consistency Analysis

### Story Self-Consistency

**Checks:**

1. **AC1-AC5 traceable to tasks**: Yes
   - AC1 (Real-time stock display) -> Task 3 (Frontend)
   - AC2 (Insufficient stock warning) -> Task 3 (Frontend)
   - AC3 (Backorder allowance) -> Task 2 (Backend integration)
   - AC4 (Stock check endpoint) -> Task 1 (API Endpoint)
   - AC5 (Stock snapshot on order line) -> Task 2 (Integration)

2. **Task completeness**: All acceptance criteria are covered by tasks.

3. **No circular references**: Tasks flow logically from API (Task 1) to integration (Task 2) to frontend (Task 3) to tests (Tasks 4-5).

4. **Naming consistency**:
   - `available_stock_snapshot` - matches Story 5.1
   - `backorder_note` - matches Story 5.1
   - `check_stock_availability()` - consistent naming with existing services

### Cross-Story Consistency

**Story 5.1 dependency is the main issue** (see CRITICAL-1).

**Other dependencies:**
- `InventoryStock`, `Warehouse`, `Product` models from Epic 4: ALL EXIST
- `get_product_detail()` from inventory services: EXISTS
- `useProductSearch.ts` from inventory domain: EXISTS

---

## Summary

| Category | Count |
|----------|-------|
| CRITICAL Issues | 3 |
| WARNINGS | 5 |
| CONFIRMED VALID | 11 |
| Web Search Findings | 2 categories |

**Overall Assessment:** Story 5.2 is well-designed and references correct patterns from the existing codebase. However, it cannot be implemented until Story 5.1 creates the Orders domain and Order/OrderLine models. The stock check endpoint should ideally be placed in the inventory domain (not orders) to maintain domain cohesion.

**Recommendation:**
1. Complete Story 5.1 first, OR
2. Split Story 5.2 into: (a) stock check API in inventory domain, (b) order integration
3. Resolve CRITICAL-2 by deciding whether stock check endpoint belongs in inventory or orders domain
