# Story 20.3: Monthly Aggregation Tables

Status: done

## Story

As a backend analytics developer,
I want a single-grain monthly sales aggregate with a current-month live fallback,
so that inventory and intelligence can answer multi-year product questions without repeatedly scanning raw order lines.

## Problem Statement

`backend/domains/intelligence/service.py` already filters countable statuses, but its current historical windows still use `Order.created_at` and live `Product` attributes. `backend/domains/inventory/services.py` exposes monthly demand and sales history, but those are inventory-owned operational views rather than a shared product-sales fact. The repo already has the raw ingredients for a canonical sales analytics timestamp: operational confirmation sets `confirmed_at`, and legacy import writes historical orders with confirmation-aligned dates.

Epic 20 needs one shared monthly product-sales fact before it adds revenue diagnosis, product performance, or stronger planning support.

## Solution

Create a backend-only `product_analytics` foundation centered on `sales_monthly` in v1.

The table grain must be exactly one row per tenant, `month_start`, `product_id`, `product_name_snapshot`, and `product_category_snapshot`. The aggregate must use a shared analytics timestamp rooted in existing countable-status semantics: `confirmed_at` when present, and `created_at` only as a compatibility fallback for rows where `confirmed_at` is absent.

Closed months are refreshed into `sales_monthly` through an admin, CLI, or on-demand service. The current month is always computed live from transactional tables using the same status and timestamp rules. `customer_monthly` stays deferred until `sales_monthly` stabilizes.

## Best-Practice Update

This section supersedes conflicting details below.

- `sales_monthly` has one grain only: tenant, month, product snapshot. No mixed grains and no category-only rows in the same fact.
- Historical truth comes from Story 20.1 snapshot columns. Do not fall back to live `Product.category` or `Product.name` for closed-month history.
- Current month must use a live fallback, not stale aggregate rows.
- After the initial backfill, routine freshness may use a rolling recent closed-month refresh window through the reviewed CLI surfaces rather than reloading the entire historical range every time.
- If a closed month has transactional sales but missing `sales_monthly` rows, the shared read helper may temporarily fall back to transactional aggregation instead of returning a misleading zero-filled result.
- Story 20.2 must not block this story. If no conformed dimension is needed, ship inline snapshot fields only.
- Keep this story backend-only. Do not create a speculative standalone frontend page here.

## Acceptance Criteria

1. Given confirmed, shipped, or fulfilled order lines for a closed month, when `refresh_sales_monthly` runs for that month, then `sales_monthly` stores exactly one row per tenant, month, and product snapshot with correct `quantity_sold`, `order_count`, `revenue`, and `avg_unit_price` values.
2. Given the same month is refreshed multiple times, when `refresh_sales_monthly` reruns, then the upsert is idempotent and the resulting rows remain duplicate-free.
3. Given an order whose `created_at` and `confirmed_at` fall in different months, when monthly aggregation runs, then the row lands in the month derived from the canonical analytics timestamp rather than the raw creation month.
4. Given a query window that includes the current month, when the shared read helper runs, then prior closed months are read from `sales_monthly` and the current month is computed live from `orders` and `order_lines` using the same countable-status and timestamp rules.
5. Given an order line with null snapshot fields, when aggregation runs, then the row is skipped or reported as unsupported in structured refresh metadata and live `Product.category` is not used as a historical fallback.
6. Given Story 20.2 remains deferred, when `sales_monthly` is implemented, then the table still ships with inline snapshot text fields and does not require `product_snapshot_id`.
7. Given a closed month has transactional sales but missing `sales_monthly` rows, when the shared read helper serves downstream consumers, then it falls back to transactional aggregation for that closed month rather than zero-filling the series while upkeep catches up.

## Technical Notes

### Existing extension points

- Timestamp anchors: `backend/common/models/order.py`, `backend/domains/orders/services.py`, `backend/domains/legacy_import/canonical.py`
- Existing countable-status logic: `backend/domains/intelligence/service.py`
- Existing inventory operational views: `backend/domains/inventory/services.py`

### New foundation surface

- Create `backend/domains/product_analytics/models.py` for `sales_monthly`.
- Create `backend/domains/product_analytics/service.py` for refresh and read helpers.
- Add an Alembic migration for the table, uniqueness constraint, and supporting indexes.
- Add an optional CLI or admin maintenance seam only if it is real and immediately useful.

### Guardrails

- Do not add `customer_monthly` in this story.
- Do not mix category-only rollups and product rows in `sales_monthly`.
- Do not change inventory reorder-point math to consume `sales_monthly` in this story.
- Do not expose end-user APIs from this story. Those belong in Stories 20.4-20.7.

## Tasks / Subtasks

- [x] Task 1: Create `sales_monthly`, its migration, uniqueness constraint, and indexes under `backend/domains/product_analytics/`.
- [x] Task 2: Add a canonical analytics timestamp helper that uses `confirmed_at` first and `created_at` only as compatibility fallback.
- [x] Task 3: Implement `refresh_sales_monthly` plus a small range-refresh wrapper for admin or CLI use, with idempotent upsert behavior and structured skip metadata.
- [x] Task 4: Implement a shared read helper that serves closed months from `sales_monthly` and computes the current month live from transactional tables.
- [x] Task 5: Add focused foundation tests for closed-month refresh, idempotent rerun, current-month live fallback, confirmation-month boundary behavior, and missing-snapshot skip reporting.

## Dev Notes

- The most important repo-reality correction in this story is timestamp semantics. Current intelligence code still uses `Order.created_at`; this story should centralize the correct rule instead of letting each consumer restate it.
- Add one regression where an order is created on the last day of one month and confirmed in the next month, then assert the aggregate row lands in the confirmation month.
- Add one regression where a historical line has snapshots, the live product category changes, refresh reruns, and the aggregate still reflects the stored order-line snapshot.

## Project Structure Notes

- New backend-only foundation surface: `backend/domains/product_analytics/*`
- Existing downstream consumers: `backend/domains/intelligence/service.py`, `backend/domains/inventory/services.py`

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/common/models/order.py`
- `backend/common/models/order_line.py`
- `backend/domains/orders/services.py`
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/intelligence/service.py`
- `backend/domains/inventory/services.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd backend && uv run pytest tests/domains/product_analytics/test_service.py -q`
- `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head`
- `cd backend && uv run alembic -c ../migrations/alembic.ini heads`
- Final focused diff review over the Story 20.3 file set returned no findings.

### Completion Notes List

- Added the backend-only `product_analytics` foundation with a `sales_monthly` ORM model, a new Alembic table revision, metadata registration, and a shared service for closed-month refreshes plus current-month live reads.
- Centralized canonical analytics timestamp semantics around `confirmed_at` with `created_at` compatibility fallback so monthly product history lands in the confirmation month when the two timestamps diverge.
- Implemented idempotent upsert behavior, structured skip reporting for null snapshot history, and a current-month live fallback that ignores stale aggregate rows.
- Added focused Story 20.3 coverage for confirmation-month boundary behavior, idempotent reruns, current-month live fallback, missing-snapshot skip reporting, range refresh behavior, and the closed-month inclusive-end read boundary.
- Validation exposed a clean-upgrade gap in the Story 20.1 snapshot migration for dev schemas that already had snapshot columns; the migration was hardened with `ADD COLUMN IF NOT EXISTS`, then `uv run alembic -c ../migrations/alembic.ini upgrade head` completed successfully.
- Validation passed on 2026-04-16 with `cd backend && uv run pytest tests/domains/product_analytics/test_service.py -q` (`6 passed in 0.70s`), followed by `cd backend && uv run alembic -c ../migrations/alembic.ini heads` (`7a3c2d1e9f4b (head)`).
- Final independent review after validation found no Story 20.3 findings.

### File List

- `backend/common/models/__init__.py`
- `backend/domains/product_analytics/__init__.py`
- `backend/domains/product_analytics/models.py`
- `backend/domains/product_analytics/service.py`
- `backend/tests/domains/product_analytics/test_service.py`
- `migrations/versions/2f7c1b4d9e3a_add_order_line_product_snapshots.py`
- `migrations/versions/7a3c2d1e9f4b_add_sales_monthly_table.py`

### Change Log

- 2026-04-16: Implemented Story 20.3 end-to-end across the new monthly aggregate model, service, migration, and focused backend coverage.
- 2026-04-16: Hardened the prior Story 20.1 snapshot migration after Story 20.3 validation exposed duplicate-column drift on clean upgrades for dev schemas with preexisting snapshot columns.
- 2026-04-16: Fixed the closed-month inclusive-end boundary in the shared monthly read helper, reran the focused Story 20.3 suite, and completed a no-findings review pass.