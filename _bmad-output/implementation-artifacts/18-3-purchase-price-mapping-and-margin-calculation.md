# Story 18.3: Purchase Price Mapping and Margin Calculation

Status: review

## Story

As an owner,
I want product purchase costs to flow automatically into sales margin calculations,
So that the gross margin in the owners tab is accurate and available.

## Problem Statement

The owner dashboard already had a gross-margin card, but the cost chain feeding it was broken in three places:

1. Supplier orders could not persist purchase prices on their lines.
2. Invoice creation did not consistently stamp `InvoiceLine.unit_cost` from purchase history.
3. The gross-margin backend/frontend contract diverged, so the card expected `available`, `gross_margin_percent`, and `previous_period` fields the API did not return.

The result was predictable: COGS stayed zero or incomplete, and the owners tab either showed "Margin data unavailable" forever or risked reporting misleading numbers.

## Implemented Solution

This story now ships the full purchase-price-to-margin path for new and future data:

- Added nullable `unit_price` to `SupplierOrderLine` and created Alembic revision `1c2d3e4f5a6b_add_unit_price_to_supplier_order_line`.
- Updated supplier-order creation and serialization so line prices can be stored and returned through the API.
- Updated the supplier-order form request mapping to send `unit_price` instead of the stale `unit_cost` field name, including explicit `0.00` prices.
- Extended `_resolve_latest_unit_cost()` in `backend/domains/invoices/service.py` so invoice creation resolves the newest priced source across both `SupplierOrderLine.unit_price` and `SupplierInvoiceLine.unit_price`, applies an `invoice_date` cutoff, and deterministically prefers supplier invoices on same-day ties.
- Updated `_create_invoice_core()` so both manual invoices and auto-generated invoices persist resolved `InvoiceLine.unit_cost`.
- Updated `get_product_supplier()` so product supplier info returns the latest supplier relationship while still surfacing price when available, instead of querying a non-existent field.
- Expanded `GrossMarginResponse` with `available`, `gross_margin_percent`, `margin_percent`, and `previous_period`.
- Updated `GrossMarginCard` and frontend types to match backend nullability and suppress the trend gracefully when the previous period has no complete cost data.
- Kept gross margin conservative: the KPI is only `available = true` when every current-period invoice line has a cost, so the dashboard does not report partial COGS as a trustworthy margin.

## Acceptance Criteria

1. [x] Supplier order lines can persist purchase `unit_price` through the backend model, schema, API, and local migration.
2. [x] Invoice creation resolves `unit_cost` from the newest priced supplier order or supplier invoice source when invoice lines do not already carry a cost.
3. [x] The gross-margin API returns the fields the owner dashboard actually consumes: `available`, `gross_margin_percent`, `margin_percent`, `revenue`, `cogs`, and `previous_period`.
4. [x] The owner dashboard shows the unavailable state when current-period cost coverage is incomplete, and shows the KPI when cost coverage is complete.

## Tasks / Subtasks

- [x] Task 1: Persist supplier-order line purchase prices
  - [x] Subtask 1.1: Add `SupplierOrderLine.unit_price` to the SQLAlchemy model.
  - [x] Subtask 1.2: Add Alembic revision `1c2d3e4f5a6b_add_unit_price_to_supplier_order_line` and apply it locally.
  - [x] Subtask 1.3: Thread `unit_price` through supplier-order request/response serialization.

- [x] Task 2: Propagate purchase cost into invoice lines
  - [x] Subtask 2.1: Extend `_resolve_latest_unit_cost()` to use both supplier orders and supplier invoices with deterministic same-day precedence.
  - [x] Subtask 2.2: Persist resolved `unit_cost` inside `_create_invoice_core()`.
  - [x] Subtask 2.3: Preserve explicit `unit_cost` from order confirmation when already present, while keeping invoice-side resolution as the primary source of truth.

- [x] Task 3: Align gross-margin backend and frontend contract
  - [x] Subtask 3.1: Expand `GrossMarginResponse` with `available`, `gross_margin_percent`, and `previous_period`.
  - [x] Subtask 3.2: Update `GrossMarginCard` and frontend types to consume the new payload.
  - [x] Subtask 3.3: Add focused backend and frontend regression tests.

- [x] Follow-up: Backfill historical `InvoiceLine.unit_cost`
  - [x] Existing invoice lines created before this change still retain `unit_cost = NULL`.
  - [x] Separate backfill story/command shipped in Story 18.4 via `cd backend && uv run python -m scripts.backfill_invoice_unit_cost`.
  - [x] Follow-up story completed: `18-4-historical-invoice-unit-cost-backfill.md`.

## Dev Notes

### Key Files

| File | Purpose |
|------|---------|
| `backend/common/models/supplier_order.py` | Added `SupplierOrderLine.unit_price` |
| `backend/domains/inventory/services.py` | Supplier-order write path and `get_product_supplier()` lookup |
| `backend/domains/invoices/service.py` | `_resolve_latest_unit_cost()` and `_create_invoice_core()` cost persistence |
| `backend/domains/dashboard/services.py` | Gross-margin availability and previous-period response assembly |
| `backend/domains/dashboard/schemas.py` | `GrossMarginResponse` contract |
| `src/domain/dashboard/components/GrossMarginCard.tsx` | Frontend unavailable/previous-period handling |
| `src/domain/inventory/components/SupplierOrderForm.tsx` | Corrected supplier-order request field mapping |
- `src/domain/inventory/components/SupplierOrderForm.test.tsx` | Explicit zero-price regression coverage |
| `migrations/versions/1c2d3e4f5a6b_add_unit_price_to_supplier_order_line.py` | Supplier-order line price migration |

## Validation

Validated on 2026-04-12 with:

- `cd backend && uv run pytest tests/domains/dashboard/test_gross_margin.py tests/domains/invoices/test_service.py tests/domains/orders/test_order_confirmation.py tests/domains/inventory/test_supplier_orders.py -k 'gross_margin or test_persists_snapshot_and_allocates_invoice_number or test_normalizes_b2c_identifier_in_persisted_invoice or test_archives_invoice_artifact_when_store_is_provided or test_confirm_order_success or test_confirm_order_resolves_invoice_line_unit_costs or test_create_supplier_order_success' -q`
- `cd backend && uv run pytest tests/domains/invoices/test_service.py -k 'test_resolve_latest_unit_cost_uses_invoice_date_cutoff_and_priority' -q`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP && pnpm vitest run src/domain/dashboard/components/GrossMarginCard.test.tsx src/domain/inventory/components/SupplierOrderForm.test.tsx`
- `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head`
- `cd backend && uv run alembic -c ../migrations/alembic.ini current` → `1c2d3e4f5a6b (head)`

## Completion Notes

- The new margin contract is intentionally conservative: any current-period invoice line missing cost keeps `available = false` so the dashboard never mixes priced and unpriced revenue into a misleading margin percentage.
- Historical invoices are backfilled by the Story 18.4 follow-up command. The conservative owner-dashboard availability rule remains unchanged; older periods only become available when the missing invoice-line costs are actually filled.
- Story 18.5 now aligns the forward invoice resolver with the same ambiguity rule used by Story 18.4, so future invoices also avoid guessing a `unit_cost` when the top-ranked purchase tier disagrees on price.

## File List

- `backend/common/models/supplier_order.py`
- `backend/domains/inventory/schemas.py`
- `backend/domains/inventory/services.py`
- `backend/domains/invoices/schemas.py`
- `backend/domains/invoices/service.py`
- `backend/domains/orders/services.py`
- `backend/domains/dashboard/schemas.py`
- `backend/domains/dashboard/services.py`
- `backend/tests/domains/dashboard/test_gross_margin.py`
- `backend/tests/domains/invoices/test_service.py`
- `backend/tests/domains/orders/test_order_confirmation.py`
- `backend/tests/domains/inventory/test_supplier_orders.py`
- `migrations/versions/1c2d3e4f5a6b_add_unit_price_to_supplier_order_line.py`
- `src/domain/dashboard/types.ts`
- `src/domain/dashboard/components/GrossMarginCard.tsx`
- `src/domain/dashboard/components/GrossMarginCard.test.tsx`
- `src/domain/inventory/types.ts`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/domain/inventory/components/SupplierOrderForm.test.tsx`
