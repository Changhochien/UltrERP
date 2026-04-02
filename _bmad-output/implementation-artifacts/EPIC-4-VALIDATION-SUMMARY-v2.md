# Epic 4 — Multi-Agent Validation Summary (Round 2)

**Date:** 2026-04-01
**Validators:** 6 parallel agents, 4 iterations each (internal consistency → architecture cross-ref → web best practices → gap analysis)
**Status:** ⚠️ PARTIALLY REMEDIATED — This report captured a pre-fix snapshot; remaining claims need re-triage against the current story docs

> **Post-review note (repo-grounded follow-up):** This Round 2 report reflected the Epic 4 story docs before the latest correction pass. The following findings have already been fixed in the story files: stale backend paths under `backend/app/...`, invalid async transaction examples using `db.transaction()`, missing references to the shared `AsyncSession` and `common.database` patterns, malformed supplier receiving and warehouse transfer pseudocode, explicit row-locking requirements, and several implementation-task omissions such as pagination/schema notes. Treat the original critical-issue count as a historical snapshot until the remaining claims are re-validated against the current docs.

---

## Cross-Cutting Critical Issues (Affect All Stories)

These issues appear in **every** Epic 4 story and must be fixed project-wide before any story can move to implementation.

### 1. 🚨 WRONG FILE PATHS — All Backend Stories
**Severity:** CRITICAL

All Epic 4 stories use paths like `backend/app/domains/inventory/` and `backend/app/common/models/`. The actual project structure is:
- Backend domains: `backend/domains/` (NOT `backend/app/domains/`)
- Common models: `backend/common/models/` (NOT `backend/app/common/models/`)

| Story Path (WRONG) | Actual Project Path (CORRECT) |
|---|---|
| `backend/app/domains/inventory/routes.py` | `backend/domains/inventory/routes.py` |
| `backend/app/domains/inventory/services.py` | `backend/domains/inventory/services.py` |
| `backend/app/domains/inventory/schemas.py` | `backend/domains/inventory/schemas.py` |
| `backend/app/common/models/` | `backend/common/models/` |

**Frontend paths** (`src/domain/inventory/`) are structurally correct (directory needs to be created) but the `src/lib/api/` and `src/domain/inventory/` subdirectories don't exist yet.

### 2. 🚨 Race Conditions — All Stock-Mutating Stories
**Severity:** CRITICAL — Data integrity risk

Stories 4.3, 4.4, 4.5, and 4.6 all perform `SELECT` then `UPDATE` without row-level locks. Concurrent requests can overdraw stock.

**Required fix:** Use `SELECT ... FOR UPDATE` on all stock-reading queries within transactions:
```python
# WRONG (all stories):
inventory = await get_inventory_stock(product_id, warehouse_id)

# CORRECT:
inventory = await db.fetch_one(
    "SELECT * FROM inventory_stock WHERE product_id = :pid AND warehouse_id = :wid FOR NO KEY UPDATE",
    {"pid": product_id, "wid": warehouse_id}
)
```

### 3. 🚨 Wrong SQLAlchemy Async Transaction API
**Severity:** CRITICAL — Runtime error

Stories 4.3, 4.4, and 4.5 all use `async with db.transaction():` which is NOT valid SQLAlchemy 2.0 async API.

**Required fix:**
```python
# WRONG:
async with db.transaction():

# CORRECT (SQLAlchemy 2.0 async):
async with session.begin():
```

The `AsyncSession.transaction()` method does not support the async context manager protocol.

### 4. 🚨 Missing Tenant Isolation in Code Examples
**Severity:** CRITICAL — Security

All code examples across all stories show queries without `tenant_id` filtering:
- Story 4.3: `get_supplier_order(order_id)` — no tenant filter
- Story 4.4: `get_inventory_stock()` — no tenant filter
- Story 4.5: `receive_supplier_order()` — no tenant filter
- Story 4.6: `transfer_stock()` — no tenant filter

**Required:** Every query must show `WHERE tenant_id = :tenant_id` filtering.

### 5. 🚨 asyncpg `statement_cache_size=0` Only in Dev Notes
**Severity:** HIGH — PgBouncer compatibility

The architecture mandates `connect_args={"statement_cache_size": 0}` for all asyncpg connections, but this appears only as a citation in Dev Notes — not as an implementation task in any story. A developer could miss this and break PgBouncer in team mode.

**Required:** Add `statement_cache_size=0` as an explicit implementation step in Task 1 or Task 2 of each backend story.

---

## Per-Story Critical Issues

---

### Story 4.1 — Search Products

**Critical Issues:**

| # | Issue | Fix Required |
|---|-------|-------------|
| C1 | `current_stock` in `ProductSearchResult` requires JOIN to `inventory_stock` table — no Task specifies this JOIN or the aggregation strategy when `warehouse_id` is omitted | Add explicit SQL JOIN + aggregation (SUM for all-warehouse, direct lookup for single-warehouse) to Task 2 |
| C2 | Backend rate limiting completely absent — frontend debounce is bypassable | Add Redis-based rate limit middleware or per-endpoint rate limiting to Task 2 |
| C3 | "No results" shown after 300ms timer, not after API confirms empty — race condition | Remove timer-based display; show "no results" only after debounced API call returns empty |
| C4 | Whitespace-only queries (e.g., `"   "`) pass length validation but are semantically empty | Add `query.strip() != ""` validation before DB call |

**Warnings:**
- `sku` field appears in table definition but is never indexed or searched — orphan field
- `sale_price` and `avg_cost` in architecture Product entity are missing from story
- `category` column type not confirmed (column vs. FK vs. enum)
- react-window 2.x API breaking changes not documented (`rowComponent` vs `children`, `rowCount` vs `itemCount`, etc.)
- `SET LOCAL app.tenant_id` approach vs. `WHERE tenant_id = ?` not clarified
- Hybrid ranking query (exact code → prefix → trigram/ts_rank) not specified as a single SQL expression

---

### Story 4.2 — View Stock Level

**Critical Issues:**

| # | Issue | Fix Required |
|---|-------|-------------|
| C1 | File paths are wrong — `backend/app/domains/inventory/` doesn't exist; correct is `backend/domains/inventory/` | Fix all file paths in Dev Notes |
| C2 | Redis 5-minute TTL cited from `[Source: arch v2#3.1]` — that section does not contain a 5-min TTL value; this is a bad citation | Either remove the citation or align with actual architecture TTLs (60s MCP cache, 30s job locks, etc.) |
| C3 | `cache.py` referenced in Dev Notes but does not exist in `backend/common/` | Create `backend/common/cache.py` or clarify the caching strategy uses an external Redis client |
| C4 | `inventory_stock` table schema described in Dev Notes but no Alembic migration task exists | Add migration task to Task 1 |
| C5 | Pagination for adjustment history not specified (Story 4.2 Dev Notes says "100 records limit" but no API param defined) | Add pagination params (cursor or offset) to Task 1/Task 4 |

**Warnings:**
- Read audit logging mentioned in Dev Notes but no task implements it
- Cache invalidation mechanism (event-driven vs. direct delete) not specified
- ProductDetailResponse, WarehouseStock schemas not defined anywhere
- React 19 data fetching patterns (useActionState/Suspense) not specified vs. traditional hooks

---

### Story 4.3 — Reorder Alerts

**Critical Issues:**

| # | Issue | Fix Required |
|---|-------|-------------|
| C1 | **UPSERT overwrites `acknowledged` status** — if user acknowledged an alert and stock drops further, the UPSERT resets status to `pending`, violating AC4/AC5 | Add conditional in ON CONFLICT: `status=CASE WHEN status IN ('pending','resolved') THEN 'pending' ELSE status END` |
| C2 | Wrong SQLAlchemy API: `async with db.transaction():` → use `async with session.begin():` | Fix transaction context manager |
| C3 | Tenant isolation missing on acknowledge endpoint — any tenant could acknowledge any tenant's alert by guessing UUID | Add `WHERE tenant_id = :tenant_id` check before updating |
| C4 | `acknowledged_by`/`actor_id` field missing from `reorder_alert` table schema — only `acknowledged_at` exists | Add `acknowledged_by UUID` column to schema |
| C5 | 30-day cleanup job referenced in status flow diagram but no task implements it | Add cleanup job task/subtask |

**Warnings:**
- PUT vs PATCH for acknowledge endpoint — PATCH is semantically more correct for partial update
- Bulk reorder interface to Story 4.5 (payload/contract) not specified
- `warehouse_name` in GET response requires join not detailed
- GET endpoint 404 vs 200 contradiction: error codes list includes 404 but empty array returns 200
- Cache invalidation strategy (which mutations invalidate) not specified
- Redis cache key pattern not specified

---

### Story 4.4 — Stock Adjustment

**Critical Issues:**

| # | Issue | Fix Required |
|---|-------|-------------|
| C1 | Race condition: `get_inventory_stock()` without `FOR UPDATE` allows concurrent overdraws | Use `SELECT ... FOR UPDATE` before checking/adjusting stock |
| C2 | Alert resolution missing from transaction pattern — only creates alert, never resolves it (violates Story 4.3 AC7 atomicity requirement) | Add `resolve_reorder_alert()` branch in the else clause of the stock check |
| C3 | AC2 error message mismatch: AC says "Insufficient stock: 50 units available" but code produces shortfall message | Fix error message format in code to match AC2 expectation |
| C4 | No RBAC enforcement — any authenticated user can adjust stock | Add `inventory:write` scope check in route handler dependency |

**Warnings:**
- `actor_type` missing from audit log entry (architecture requires 'human' vs 'agent')
- Append-only audit log trigger not specified in migration task
- Frontend form library not specified (react-hook-form vs React 19 native)
- Adjustment history pagination not implemented (conflicts with Story 4.2 Dev Notes "100 records limit")
- Confirmation dialog UI details not specified
- No idempotency key on POST endpoint

---

### Story 4.5 — Supplier Orders

**Critical Issues:**

| # | Issue | Fix Required |
|---|-------|-------------|
| C1 | `determine_receive_quantity()` is called but never defined | Define function — clarify whether it auto-calculates full remaining qty or reads from request body |
| C2 | `ReasonCode.SUPPLIER_DELIVERY` enum referenced but never defined | Define full `ReasonCode` enum with all values |
| C3 | Race condition in idempotency check: TOCTOU between `status == "received"` check and update | Use `SELECT ... FOR UPDATE` within transaction to lock the row before checking status |
| C4 | `tenant_id` missing in receiving code example (`get_supplier_order()` has no tenant filter) | Add tenant filtering to all queries |
| C5 | Request/response schemas entirely missing for `PUT /supplier-orders/{id}/status` and `PUT /supplier-orders/{id}/receive` | Define Pydantic schemas for both request bodies |
| C6 | File path mismatch: `backend/app/common/models/supplier_order.py` → correct is `backend/common/models/supplier_order.py` | Fix all paths |
| C7 | Line-level idempotency gap: if client retries partial receipt, stock gets double-added | Add idempotency key or change logic to prevent double-receipt on retry |

**Warnings:**
- `get_reorder_point()` function undefined
- `resolve_reorder_alert()` signature unclear — does it take alert_id or clear all alerts for product/warehouse?
- RBAC scopes not specified for endpoints
- Indexes incomplete: missing `(tenant_id, status)` and `(tenant_id, supplier_id)`
- `updated_at` not set in receiving code
- `received_date` handling inconsistent (nullable? cleared on cancel?)
- Bulk creation from alerts — no `source_alert_ids` field in supplier_order model
- PUT vs POST for `/receive` action endpoint — POST is more correct for actions

---

### Story 4.6 — Multiple Warehouses

**Critical Issues:**

| # | Issue | Fix Required |
|---|-------|-------------|
| C1 | No `FOR UPDATE` lock on source stock in transfer — concurrent transfers can both pass validation | Add `SELECT ... FOR NO KEY UPDATE` on source warehouse stock row |
| C2 | Null source stock record not handled — if product never stocked in source warehouse, `source.quantity` throws AttributeError | Handle `None` case with proper error: "Product not in source warehouse" |
| C3 | No check that `from_warehouse_id != to_warehouse_id` — self-transfer is a no-op but wastes a transaction | Add validation: `if from == to: raise BadRequest("Cannot transfer to same warehouse")` |
| C4 | No idempotency key on transfer endpoint — retries cause double transfers | Add idempotency key parameter |
| C5 | `stock_transfer_history.status` column missing — cannot model in-transit states | Add `status` column (PENDING/IN_TRANSIT/RECEIVED/CANCELLED) |
| C6 | No outbox event for `StockTransferred` — architecture §4.4 requires outbox for side effects | Emit domain event to outbox table after transfer commit |
| C7 | Multi-tenancy not enforced in `transfer_stock()` — function takes no tenant_id | Derive tenant_id from session context, validate warehouse belongs to tenant |

**Warnings:**
- `inventory_stock_idx_warehouse_product` index missing `tenant_id` — queries will be slower without it
- `stock_transfer_history.notes` column missing despite `notes` being in input
- React WarehouseContext persistence strategy not specified (sessionStorage? localStorage? server-backed?)
- Active warehouse check (`is_active = true`) not validated during transfer
- Zero/negative transfer quantity not validated
- RBAC mapping from warehouse operations to roles not specified

---

## Summary: Critical Issues Per Story

| Story | Critical Issues | Status |
|-------|---------------|--------|
| 4.1 Search Products | 4 (stock JOIN, rate limiting, timer race, whitespace validation) | Not ready |
| 4.2 View Stock Level | 5 (wrong paths, bad TTL citation, no cache.py, no migration task, no pagination) | Not ready |
| 4.3 Reorder Alerts | 5 (UPSERT overwrites ack, wrong async API, no tenant isolation, missing actor field, no cleanup job) | Not ready |
| 4.4 Stock Adjustment | 4 (race condition, no alert resolution, error message mismatch, no RBAC) | Not ready |
| 4.5 Supplier Orders | 7 (undefined function, undefined enum, race condition, no tenant, no schemas, wrong paths, no idempotency) | Not ready |
| 4.6 Multiple Warehouses | 7 (no row lock, null handling, self-transfer, no idempotency, no status col, no outbox, no tenant enforcement) | Not ready |

**Total critical issues across Epic 4: 32**

---

## What Was Correctly Specified (No Changes Needed)

| Story | What's Correct |
|-------|---------------|
| 4.1 | Hybrid pg_trgm + tsvector search strategy; case-insensitivity; debounce timing; react-window 2.x version; FastAPI error code distinction (400 vs 422); performance target (< 500ms) |
| 4.2 | All 5 acceptance criteria are clear and testable; warehouse toggle requirement; reorder indicator color-coding |
| 4.3 | Application-side UPSERT (not triggers) pattern; transactional atomicity; UNIQUE constraint on (tenant_id, product_id, warehouse_id); status enum flow |
| 4.4 | Reason code enum separation (user vs system); immediate stock update requirement; audit log fields; system reason codes not user-selectable |
| 4.5 | Partial receipt per-line tracking; `partially_received` status; idempotent status-check pattern; status flow state machine |
| 4.6 | ReasonCode.TRANSFER_OUT/TRANSFER_IN reuse from Story 4.4; atomic transfer pattern structure; warehouse context persistence requirement |

---

## Recommended Fix Order

Since stories depend on each other, fixes should be applied in this order:

1. **Story 4.6** (foundational) — Fix paths, add row locks, add tenant enforcement, fix idempotency, add status column, add outbox event
2. **Story 4.1** — Fix stock JOIN, add rate limiting, fix whitespace validation, document react-window 2.x API
3. **Story 4.2** — Fix paths, remove bad TTL citation, create cache.py spec or document caching approach, add pagination
4. **Story 4.4** — Add row locks, add alert resolution, fix error message, add RBAC check
5. **Story 4.3** — Fix UPSERT conditional, fix async API, add tenant isolation, add actor field, add cleanup job
6. **Story 4.5** — Define all undefined functions/enums, fix race condition, add schemas, fix paths, add idempotency

---

## Files to Update

For each story file (`_bmad-output/implementation-artifacts/4-X-*.md`):
1. Fix all file paths (`backend/app/domains/` → `backend/domains/`, `backend/app/common/` → `backend/common/`)
2. Add `async with session.begin():` (not `db.transaction()`) in all code examples
3. Add `tenant_id` filtering to all queries in code examples
4. Add `SELECT ... FOR UPDATE` to all stock-reading queries in transactions
5. Add missing fields/operations identified above
6. Add missing tasks/fields to the task list

Additionally:
- **`EPIC-4-VALIDATION-SUMMARY.md`** → superseded by this document
- **`docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md`** — add 5-min stock cache TTL to §8.2, clarify `SET LOCAL` vs `WHERE` tenant filtering approach
- **`package.json`** — add `react-window` (not yet present)

---

**Overall Epic 4 Status: 🚨 NOT READY FOR DEV — 32 critical issues must be resolved**
