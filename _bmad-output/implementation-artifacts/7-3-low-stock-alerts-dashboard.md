# Story 7.3: Low-Stock Alerts on Dashboard

Status: done

## Story

As an owner,
I want to view low-stock alerts on the morning dashboard,
So that I can address inventory issues quickly.

## Acceptance Criteria

**AC1:** Alerts displayed on dashboard
**Given** products exist with stock below their reorder point
**When** I view the dashboard
**Then** I see a low-stock alerts card listing products needing reorder
**And** the card shows a badge with the count of active alerts

**AC2:** Alert detail information
**Given** a product triggers a low-stock alert
**When** I view the alert entry
**Then** I see: product name, current stock, reorder point
**And** the alert status is "pending" (not already resolved)

**AC3:** Click-through navigation
**Given** I see a low-stock alert on the dashboard
**When** I click on the alert
**Then** I navigate to the inventory/product detail page for that product

**AC4:** No-alerts graceful handling
**Given** no products have stock below reorder point
**When** I view the dashboard
**Then** I see a success message: "All stock levels OK" with a green indicator

**AC5:** Backend endpoint reuse
**Given** the reorder alerts API already exists at `GET /api/v1/inventory/reorder-alerts`
**When** the dashboard widget loads
**Then** it calls the existing endpoint filtered by `status=pending`
**And** displays up to 10 most recent alerts sorted by creation date descending

**AC6:** Alert data freshness
**Given** reorder alerts are created by inventory operations (stock adjustments, transfers)
**When** the dashboard loads
**Then** the alerts reflect the latest stock state
**And** no separate background job is needed — alerts are created in real-time by existing inventory services

## Tasks / Subtasks

- [ ] **Task 1: Frontend — Low-Stock Alerts Card** (AC1, AC2, AC4)
  - [ ] Create `src/domain/dashboard/components/LowStockAlertsCard.tsx`:
    - Card header: "Low-Stock Alerts" with badge count
    - List of alerts: product name, current stock, reorder point
    - Colored indicator: red when stock is critically low (< 50% of reorder point), orange otherwise
    - Empty state: "All stock levels OK ✓" with green indicator
    - Loading skeleton state
    - Error fallback state
  - [ ] Add to `src/domain/dashboard/hooks/useDashboard.ts`:
    - `useLowStockAlerts()` — fetches pending reorder alerts on mount

- [ ] **Task 2: Frontend API Integration** (AC5)
  - [ ] Add to `src/lib/api/dashboard.ts` (or reuse existing inventory API):
    - `fetchLowStockAlerts(): Promise<ReorderAlertListResponse>`
    - Calls `GET /api/v1/inventory/reorder-alerts?status=pending&limit=10`
    - **IMPORTANT:** Must include `limit=10` query param — the endpoint defaults to `limit=50`. The dashboard card should show at most 10 alerts.
  - [ ] Add types to `src/domain/dashboard/types.ts` (or import from inventory types):
    ```typescript
    export interface LowStockAlert {
      id: string;
      product_id: string;
      product_name: string;
      warehouse_id: string;
      warehouse_name: string;
      current_stock: number;
      reorder_point: number;
      status: string;
      created_at: string;
      acknowledged_at: string | null;
      acknowledged_by: string | null;
    }
    ```

- [ ] **Task 3: Click-Through Navigation** (AC3)
  - [ ] Wire each alert row with `onClick` → navigate to product/inventory detail
  - [ ] Use React Router `useNavigate()`:
    - Navigate to `/inventory/products/{product_id}` or equivalent route
    - **NOTE:** No product detail route exists in `App.tsx` currently. Either: (a) add a basic product detail route as part of this story, or (b) link to the inventory list page with a filter, or (c) make click-through a future enhancement. Recommend option (b) for MVP — link to `/inventory` and document that product detail page is a future story.

- [ ] **Task 4: Integrate into Dashboard Page** (AC1)
  - [ ] Add `LowStockAlertsCard` to `DashboardPage.tsx` grid
  - [ ] Position in the grid layout alongside revenue and top products cards

- [ ] **Task 5: Frontend Tests** (AC1, AC2, AC3, AC4)
  - [ ] Create `src/domain/dashboard/__tests__/LowStockAlertsCard.test.tsx`
  - [ ] Test: renders alert list with product name, stock, reorder point
  - [ ] Test: shows badge count matching alerts length
  - [ ] Test: empty state renders "All stock levels OK"
  - [ ] Test: clicking alert calls navigate
  - [ ] Test: loading skeleton state

## Dev Notes

### Architecture Compliance

- **No new backend code:** This story reuses the existing `GET /api/v1/inventory/reorder-alerts` endpoint. No new backend route, service, or schema is needed.
- **Existing endpoint:** `backend/domains/inventory/routes.py` → `list_reorder_alerts_endpoint()` — already supports `status` filter and pagination
- **Existing schema:** `ReorderAlertItem` and `ReorderAlertListResponse` in `domains/inventory/schemas.py`
- **ReorderAlert model:** `common/models/reorder_alert.py` — has `product_id`, `warehouse_id`, `current_stock`, `reorder_point`, `status` (enum: pending, acknowledged, resolved)

### Backend Endpoint Details

- **Existing endpoint:** `GET /api/v1/inventory/reorder-alerts`
- **Query params:** `status` (filter by alert status), `limit` (default 50, max 200), `offset` (default 0), `warehouse_id` (optional UUID)
- **Response schema (`ReorderAlertItem`):**
  ```python
  class ReorderAlertItem(BaseModel):
      id: uuid.UUID
      product_id: uuid.UUID
      product_name: str
      warehouse_id: uuid.UUID
      warehouse_name: str
      current_stock: int
      reorder_point: int
      status: str
      created_at: datetime
      acknowledged_at: datetime | None
      acknowledged_by: str | None
  ```
- The endpoint already enriches alerts with `product_name` and `warehouse_name` via the service layer.

### Critical Warnings

- **Do NOT create a new backend endpoint.** The existing reorder alerts endpoint already provides all needed data. Creating a duplicate would violate DRY.
- **Product detail route may not exist yet.** Check `src/App.tsx` for existing routes. If no product detail route exists, link to the inventory list page or make the click-through a future enhancement (document this decision).
- **Alert freshness:** Reorder alerts are created reactively when stock drops below reorder point (in `inventory/services.py`). They are NOT computed dynamically on each dashboard load — they persist in the `reorder_alert` table. This means if stock is replenished but the alert isn't resolved, it may show stale data. Document this as a known limitation and suggest an auto-resolve mechanism in a future story.
- **Dependency on Story 7.1:** This story extends the dashboard page scaffold created in 7.1.

### Previous Story Intelligence

- **Inventory schemas:** Defined in `backend/domains/inventory/schemas.py` — `ReorderAlertItem`, `ReorderAlertListResponse`
- **Frontend fetch pattern:** Use the same `useState` + `useEffect` pattern from other dashboard hooks
- **Test mocking pattern:** Mock the fetch call to the inventory API endpoint. Use `vi.fn()` and `global.fetch` mock.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 7, Story 7.3] AC definitions: low-stock alerts on dashboard
- [Source: _bmad-output/planning-artifacts/epics.md#FR27] Owner can view low-stock alerts on dashboard
- [Source: _bmad-output/planning-artifacts/prd.md#Journey 1] Morning Pulse Check — low-stock alerts (if any)
- [Source: common/models/reorder_alert.py] ReorderAlert model with current_stock, reorder_point, status
- [Source: domains/inventory/routes.py] Existing list_reorder_alerts_endpoint
- [Source: domains/inventory/schemas.py] ReorderAlertItem with product_name, warehouse_name enrichment

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story designed to reuse existing reorder alerts endpoint — no new backend work needed
- Existing endpoint already provides product_name and warehouse_name enrichment
- Click-through navigation depends on product detail route existence — flagged as conditional
- **Alert freshness limitation documented: alerts persist in DB, may become stale if stock replenished without resolving**
- **Alert `current_stock` captured at creation time:** The `current_stock` field on `ReorderAlert` is a snapshot from when the alert was created. If stock is replenished without resolving the alert, the dashboard shows stale data. Document this as a known limitation and plan an auto-resolve mechanism in a future story (e.g., background job or trigger that resolves alerts when stock exceeds reorder point).
- 2026-04-04 follow-up: runtime dashboard failures also exposed a PostgreSQL enum mismatch in `backend/common/models/reorder_alert.py`; the model now binds lowercase enum values via `values_callable`, which restored pending low-stock alert queries.
