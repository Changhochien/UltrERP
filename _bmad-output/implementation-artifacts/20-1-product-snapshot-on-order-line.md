# Story 20.1: Product Snapshot on OrderLine

Status: done

## Story

As a platform developer,
I want each sales order line to store immutable product name and category snapshots at the moment the sale becomes countable,
so that historical analytics remain correct after product master changes.

## Problem Statement

`backend/common/models/order_line.py` currently stores `product_id` and `description`, but not frozen product name or category. `backend/domains/orders/services.py` confirms operational orders, and `backend/domains/legacy_import/canonical.py` imports historical sales lines, yet neither path stamps immutable product context. At the same time, the current intelligence analytics still derive historical category and product views from live `Product` attributes and `Order.created_at`, which makes old analysis drift after product renames or recategorizations.

Epic 20 cannot build a trustworthy monthly product-sales fact until the sale-time product attributes are frozen at the transactional seam.

## Solution

Add nullable `product_name_snapshot` and `product_category_snapshot` columns to `order_lines` and populate them only in the two authoritative write paths that already decide when a sale becomes analytically real:

- operational confirmation in `backend/domains/orders/services.py` via `confirm_order`
- historical import in `backend/domains/legacy_import/canonical.py` via `_import_sales_history`

Do not blanket-backfill old rows from the live `Product` table. Keep pre-story rows nullable until a separate remediation plan is explicitly approved.

## Best-Practice Update

This section supersedes conflicting details below.

- Snapshot columns become the canonical historical truth for Epic 20 and later consumers.
- Once snapshots exist, no historical analytics query may use live `Product.category` or `Product.name` as its primary source for closed-month history.
- Only fill missing snapshots. Never overwrite a non-null snapshot during replay, reconfirmation, or import reruns.
- Snapshot stamping must happen inside the same transaction that confirms the order or imports the historical line.
- The product lookup added to `confirm_order` must be tenant-scoped. Expanding the current `Product` fetch without `Product.tenant_id == tid` would widen an unsafe lookup seam.
- Do not introduce a generic repair script or new canonical-import attempt allocator in this story. Existing batch-run concurrency rules stay unchanged.

## Acceptance Criteria

1. Given a pending order whose lines have null snapshot columns, when `confirm_order` succeeds, then each line receives `product_name_snapshot` and `product_category_snapshot` from the resolved tenant-scoped `Product` row before the transaction commits.
2. Given an order line that already has snapshot values, when confirmation logic is retried or replayed, then the existing snapshot values remain unchanged.
3. Given a legacy sales-history batch with normalized product data, when `_import_sales_history` upserts `order_lines`, then `product_name_snapshot` is stamped from the normalized product name or imported line-name fallback and `product_category_snapshot` is stamped from normalized product category or imported category context.
4. Given a product is later renamed or recategorized, when a historical order line from before the change is queried, then the order line still exposes its original snapshot values and no post-hoc read from the live product row is required.
5. Given an older pre-story line that has null snapshots, when Epic 20 foundation stories run, then the row remains transitional data and is not silently rewritten from the live product table.

## Technical Notes

### Existing extension points

- Extend `backend/common/models/order_line.py` with the two nullable snapshot columns.
- Add an Alembic revision under `migrations/versions/` that appends the two columns to `order_lines`.
- Extend `backend/domains/orders/services.py` in `confirm_order`. The existing product lookup currently fetches only `id` and `code`; expand it to fetch `name` and `category` too, and add a tenant predicate.
- Extend `backend/domains/legacy_import/canonical.py` inside `_import_sales_history`, where imported orders already land with historical confirmation dates and raw `order_lines` upsert SQL.

### Guardrails

- Do not change downstream intelligence or inventory readers in this story beyond adding the persistence fields.
- Preserve existing Decimal behavior and confirmation atomicity.
- For `UNKNOWN` product fallback rows in legacy import, prefer imported line description and category context when available instead of stamping a generic placeholder category.

## Tasks / Subtasks

- [x] Task 1: Add `product_name_snapshot` and `product_category_snapshot` to `OrderLine` and create the Alembic migration.
- [x] Task 2: Update `confirm_order` to fetch tenant-scoped product name and category, then stamp only missing snapshots before invoice creation and stock adjustments.
- [x] Task 3: Update `_import_sales_history` so the `order_lines` insert and conflict-update path persists both snapshot fields from normalized import data.
- [x] Task 4: Add focused confirmation tests in `backend/tests/domains/orders/test_order_confirmation.py` for snapshot stamping, tenant-scoped lookup, and non-overwrite behavior.
- [x] Task 5: Add focused legacy-import tests in `backend/tests/domains/legacy_import/test_canonical.py` for imported snapshot stamping, unknown-product fallback handling, and replay stability.

## Dev Notes

- `backend/domains/orders/services.py` already locks the order row, validates the customer, creates the invoice, and writes stock adjustments inside one transaction. Snapshot stamping belongs in that same transaction.
- `backend/domains/legacy_import/canonical.py` already owns the historical `order_lines` upsert path and confirmation-date import behavior. That is the right historical stamping seam.
- Add one regression that confirms a line, mutates the related `Product.category`, and asserts the stored snapshot remains unchanged.
- Explicitly do not add a blanket remediation job in this story. If older null-snapshot rows need repair later, that should be a separate operator-safe backfill story.

## Project Structure Notes

- Primary implementation surface: `backend/common/models/order_line.py`, `backend/domains/orders/services.py`, `backend/domains/legacy_import/canonical.py`
- Migration surface: `migrations/versions/`
- Downstream consumer surface: `backend/domains/intelligence/service.py`, future `backend/domains/product_analytics/*`

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/common/models/order_line.py`
- `backend/domains/orders/services.py`
- `backend/domains/legacy_import/canonical.py`
- `backend/domains/intelligence/service.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd backend && uv run pytest tests/domains/legacy_import/test_canonical.py -k replay -q`
- `cd backend && uv run pytest tests/domains/inventory/test_reorder_point_integration.py -k product_snapshot -q`
- `cd backend && uv run pytest tests/domains/orders/test_order_confirmation.py tests/domains/legacy_import/test_canonical.py tests/domains/inventory/test_reorder_point_integration.py -q`
- `cd backend && uv run alembic -c ../migrations/alembic.ini heads`
- Final focused review over the Story 20.1 implementation diff returned no findings.

### Completion Notes List

- Added `product_name_snapshot` and `product_category_snapshot` to `OrderLine`, shipped the Story 20.1 Alembic revision, and reconciled the local worktree heads with a branch-local merge revision.
- Updated `confirm_order` to fetch tenant-scoped product name/category, stamp snapshots only when missing, and fail closed with `409` if the product can no longer be resolved for that tenant.
- Updated canonical sales-history import to persist product snapshots on first write and preserve existing non-null snapshots on replay.
- Added focused confirmation, canonical-import, and persisted reorder-point integration coverage, including a shared-schema bootstrap for the integration test and async-session fixes that cache IDs before `expire_all()`.
- Validation passed on 2026-04-16 with `cd backend && uv run pytest tests/domains/orders/test_order_confirmation.py tests/domains/legacy_import/test_canonical.py tests/domains/inventory/test_reorder_point_integration.py -q` (`43 passed in 36.99s`), followed by `cd backend && uv run alembic -c ../migrations/alembic.ini heads` (`6c4d2e1f9a7b (head)`).
- Final independent review after validation found no Story 20.1 findings.

### File List

- `backend/common/models/order_line.py`
- `backend/domains/orders/services.py`
- `backend/domains/legacy_import/canonical.py`
- `backend/tests/domains/inventory/test_reorder_point_integration.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `backend/tests/domains/legacy_import/test_canonical.py`
- `migrations/versions/2f7c1b4d9e3a_add_order_line_product_snapshots.py`
- `migrations/versions/6c4d2e1f9a7b_merge_story20_snapshot_heads.py`

### Change Log

- 2026-04-16: Implemented Story 20.1 end-to-end across order confirmation, canonical import, schema migration, and regression coverage.
- 2026-04-16: Closed the final persisted integration regression, reran the full Story 20.1 validation slice, confirmed a single Alembic head, and completed a no-findings review pass.