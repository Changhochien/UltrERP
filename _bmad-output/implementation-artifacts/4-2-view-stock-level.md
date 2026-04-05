# Story 4.2: View Stock Level and Reorder Point

**Status:** done

**Story ID:** 4.2

---

## Story

As a warehouse staff,
I want to view current stock level and reorder point per product,
So that I can make informed decisions about stock.

---

## Acceptance Criteria

**✓ AC1:** Display stock levels per warehouse
**Given** a product exists with stock in multiple warehouses
**When** I view the product details
**Then** I see: warehouse name, current quantity, reorder point, last adjusted date

**✓ AC2:** Single warehouse display
**Given** only one warehouse exists
**When** I view product details
**Then** I see: current stock quantity, reorder point, last adjusted date, adjustment history

**✓ AC3:** Reorder status indicator
**Given** a product with stock below reorder point
**When** I view status
**Then** I see visual indicator "Below reorder point" (yellow/red warning)

**✓ AC4:** Product history timeline
**Given** a product has recent adjustments
**When** I expand the product details
**Then** I see adjustment history: date, quantity change, reason code, actor

**✓ AC5:** Multi-warehouse product view
**Given** multiple warehouses exist
**When** I view a product from search results
**Then** I can toggle between warehouse views

---

## Tasks / Subtasks

- [ ] **Task 1: Backend Product Detail Endpoint** (AC1-AC4)
  - [ ] Create GET `/api/v1/inventory/products/{product_id}` endpoint
  - [ ] Return: id, code, name, category, reorder_point, warehouses[], adjustment_history[]
  - [ ] Each warehouse: warehouse_id, name, current_stock, last_adjusted_date
  - [ ] Adjustment history: date, quantity_change, reason_code, actor_id, actor_name
  - [ ] Add history pagination parameters (`history_limit`, `history_cursor` or `offset`) so the 100-record cap is explicit in the API contract

- [ ] **Task 2: Stock Calculation & Caching** (AC1-AC3)
  - [ ] Implement stock aggregation across warehouses
  - [ ] Cache warehouse stock levels (Redis, 5-minute TTL)
  - [ ] Implement reorder status calculation (stock < reorder_point)
  - [ ] Invalidate cache on any stock adjustment, supplier receipt, or inter-warehouse transfer

- [ ] **Task 3: Frontend Product Detail Component** (AC1-AC5)
  - [ ] Create ProductDetail component (React)
  - [ ] Display warehouse stock grid
  - [ ] Show warehouse toggle if multiple warehouses
  - [ ] Implement reorder indicator (color-coded warning)
  - [ ] Display adjustment history timeline

- [ ] **Task 4: Accessibility & Performance** (AC1-AC5)
  - [ ] Load product details in < 1 second
  - [ ] Support keyboard navigation in history list
  - [ ] High contrast for reorder indicators (WCAG AA)
  - [ ] Responsive design for warehouse table

- [ ] **Task 5: Testing** (AC1-AC5)
  - [ ] Backend: Unit tests for stock aggregation, reorder logic
  - [ ] Frontend: Component tests for warehouse toggle, indicator display
  - [ ] Integration: E2E test for loading product detail with stock display
  - [ ] Integration: verify cached stock data is invalidated after stock adjustments, supplier receipts, and warehouse transfers

---

## Dev Notes

### Architecture Compliance

- **API Pattern:** GET `/api/v1/inventory/products/{product_id}` with warehouse details
- **Caching:** Redis 7+ with 5-minute TTL for stock levels [Source: arch v2#3.1]
- **Database:** Product linked to multiple Warehouse records via inventory_stock join table
- **Real-time:** Stock updates trigger cache invalidation

### Project Structure

**Backend:**
- Route: `backend/domains/inventory/routes.py` — GET `/products/{id}` handler
- Service: `backend/domains/inventory/services.py` — get_product_with_stock()
- Schema: `backend/domains/inventory/schemas.py` — ProductDetailResponse, WarehouseStock
- Models: `backend/common/models/` — Product, Warehouse, InventoryStock, AdjustmentHistory

**Frontend:**
- Component: `src/domain/inventory/components/ProductDetail.tsx`
- Hook: `src/domain/inventory/hooks/useProductDetail.ts`
- API: `src/lib/api/inventory.ts` — fetchProductDetail()

**Database:**
- `inventory_stock` table: (id, tenant_id, product_id, warehouse_id, quantity, reorder_point, updated_at)
- `stock_adjustment_history` view: derived from `stock_adjustment` joined to users and products for display
- Index: `inventory_stock_idx_product_warehouse` on (product_id, warehouse_id)

### Reorder Logic

```python
# Stock status calculation
warehouse_rows = [
  {
    "warehouse_id": row.warehouse_id,
    "quantity": row.quantity,
    "reorder_point": row.reorder_point,
    "is_below_reorder": row.quantity < row.reorder_point,
  }
  for row in product.warehouses
]
```

### Security & Validation

- Validate tenant_id ownership (user can only see their own products)
- Limit adjustment history to last 100 records (pagination for old records)
- Audit all stock view accesses (for compliance)

---

## Dependencies & Related Stories

- **Depends on:** Story 4.1 (Search Products) — search redirects to this detail view
- **Related to:** Story 4.4 (Stock Adjustment) — adjustment history is populated after adjustment flows go live
- **Related to:** Story 4.6 (Multiple Warehouses) — warehouse toggle implemented here

---

## Technology Stack

| Tech | Version | Purpose |
|------|---------|---------|
| FastAPI | 0.135+ | Async endpoint for product detail |
| PostgreSQL | 18+ | inventory_stock table queries |
| Redis | 7+ | Cache warehouse stock levels |
| React | 19 | Product detail UI |
| Chart library | optional (recharts or simple timeline list) | Adjustment history visualization |

---

## References

- [Story 4.1: Search Products](4-1-search-products.md)
- [Story 4.4: Record Stock Adjustment](4-4-record-stock-adjustment.md)
- [Story 4.6: Multiple Warehouse Support](4-6-multiple-warehouse-support.md)
- [Architecture: Caching Strategy](../../docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#redis)

---

## Dev Agent Record

**Status:** done
**Last Updated:** 2026-04-01

### File List

- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/services.py`
- `src/domain/inventory/components/ProductDetail.tsx`
- `src/domain/inventory/hooks/useProductDetail.ts`
