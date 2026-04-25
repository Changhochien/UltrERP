# Story 20.5: Inventory Planning Support from Shared Sales History

Status: done

## Story

As a warehouse planner or inventory manager,
I want inventory planning to show shared sales-history context alongside current stock and supply signals,
so that reorder decisions are based on actual demand patterns instead of gut feel.

## Problem Statement

UltrERP already has reorder-point preview, lead-time logic, and product-detail analytics in the inventory domain. The current product analytics tab uses stock-adjustment history and a simple monthly-demand hook, while Epic 20 introduces a more trustworthy historical sales foundation. If inventory ignores that foundation, UltrERP ends up with two competing demand stories. If it replaces the current reorder engine too aggressively, it risks breaking warehouse-specific planning because the new shared monthly fact is tenant-by-product-by-month rather than warehouse-by-product-by-month.

## Solution

Extend the existing inventory domain with a planning-support layer that consumes shared product sales history without replacing the current replenishment engine.

Expose an inventory-owned planning-support response that includes:

- a month-ordered sales series
- `avg_monthly_quantity`, `peak_monthly_quantity`, `low_monthly_quantity`
- `seasonality_index` and `above_average_months`
- `history_months_used` and `current_month_live_quantity`
- current inventory context: `reorder_point`, `on_order_qty`, `in_transit_qty`, `reserved_qty`
- provenance fields such as `data_basis` and `advisory_only`

Render that inside the existing inventory product-detail analytics tab.

## Best-Practice Update

This section supersedes conflicting details below.

- Keep ownership in inventory. Reuse `backend/domains/inventory/reorder_point.py`, `backend/domains/inventory/services.py`, `backend/domains/inventory/routes.py`, `src/domain/inventory/components/AnalyticsTab.tsx`, and `src/pages/inventory/ProductDetailPage.tsx`.
- Do not create a second planning engine or standalone product-analytics planning page.
- The shared Epic 20 fact is tenant-by-product-by-month, not warehouse-by-product-by-month. Use it for advisory context and seasonality, not as an unqualified replacement for warehouse-specific usage math.
- Do not silently redefine existing inventory endpoints such as `get_monthly_demand()`, `get_sales_history()`, or `get_top_customer()`.
- Closed months come from Story 20.3. If the planner asks for the open month, current-month quantity must come from live confirmed-or-later orders and be labeled accordingly.
- If a closed month has sales activity but its Story 20.3 snapshot rows are temporarily missing, planning support must use the shared read helper's transactional fallback instead of returning a misleading zero-filled month.
- Steady-state freshness comes from a rolling recent closed-month refresh path after the initial backfill; the transactional fallback is a resilience guard, not the primary source of truth.

## Acceptance Criteria

1. Given Epic 20 shared sales history is available, when `GET /api/v1/inventory/products/{product_id}/planning-support` is called, then the response returns a month-ordered sales series plus structured planning metrics and provenance fields.
2. Given the inventory product-detail analytics tab is open, when planning support loads, then the user sees shared sales history and seasonality in the existing inventory UI rather than on a new standalone page.
3. Given reorder-point preview is run for a product that also has planning-support data, when the preview rows are returned, then the existing reorder-point formula remains authoritative and any shared-history context is clearly marked advisory unless a warehouse-allocation rule is explicitly defined.
4. Given only closed months are queried, when planning support loads, then the monthly series is sourced from the Epic 20 aggregate.
5. Given the current month is included, when planning support loads, then the current-month slice is computed live from confirmed, shipped, or fulfilled orders and the payload marks the window as partial.
6. Given no shared sales history exists, when planning support is requested, then the endpoint returns an empty history plus a data-gap flag rather than guessing a demand pattern.
7. Given a closed month has sales activity but missing Story 20.3 snapshot rows, when planning support is requested, then the shared sales-history reader falls back to transactional aggregation for that month rather than returning a misleading zero-filled history.

## Technical Notes

### Backend

- Extend `backend/domains/inventory/services.py` with a planning-support read function that can consume Story 20.3.
- Extend `backend/domains/inventory/schemas.py` with a planning-support response model.
- Extend `backend/domains/inventory/routes.py` with an inventory-owned planning-support endpoint.
- Extend `backend/domains/inventory/reorder_point.py` only as needed to surface shared-history evidence in preview outputs; do not replace the existing computation pipeline.

### Frontend

- Extend `src/domain/inventory/components/AnalyticsTab.tsx` to render planning support in the existing analytics tab.
- Extend `src/lib/api/inventory.ts` with a planning-support fetch helper.
- Keep `src/domain/inventory/hooks/useProductMonthlyDemand.ts` backward-compatible in the first pass. If a new hook is needed, keep it inside the inventory domain.

## Tasks / Subtasks

- [x] Task 1: Add an inventory-owned planning-support backend contract powered by Story 20.3 shared sales history.
- [x] Task 2: Define planning-support response models with Decimal-safe quantity fields and provenance metadata.
- [x] Task 3: Load closed months from the aggregate and live current-month data only when explicitly requested.
- [x] Task 4: Render planning support inside the existing inventory analytics tab.
- [x] Task 5: Add focused tests for month ordering, advisory-only behavior, empty states, and current-month blending.

## Dev Notes

- This story improves planner context first; it does not redesign replenishment policy.
- The current reorder engine is warehouse-aware; the shared monthly fact is not. Treat that mismatch as a design constraint, not something to paper over.
- Keep the UI responsive. Avoid dense nested multi-column layouts inside constrained product-detail rails.

## Project Structure Notes

- Ownership stays in inventory end to end.
- The product-detail analytics tab is the right UI insertion point.

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/domains/inventory/reorder_point.py`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/components/AnalyticsTab.tsx`
- `src/domain/inventory/hooks/useProductMonthlyDemand.ts`
- `src/pages/inventory/ProductDetailPage.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd backend && uv run pytest tests/domains/inventory/test_planning_support.py -q`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP && pnpm vitest run src/domain/inventory/components/AnalyticsTab.test.tsx`
- VS Code diagnostics over touched backend/frontend files returned no errors.

### Completion Notes List

- Added `GET /api/v1/inventory/products/{product_id}/planning-support` as an inventory-owned advisory endpoint that reuses Story 20.3 monthly history and blends the current month live only when requested.
- Kept reorder preview authoritative by surfacing shared sales history only in the product-detail analytics tab and not by replacing warehouse-aware reorder math.
- Rendered a new planning-support card in the existing inventory analytics tab with provenance badges, shared month history, seasonality metrics, and current supply context.
- Validated focused backend and frontend coverage for month ordering, aggregate-only windows, current-month blending, advisory-only behavior, and empty-state data gaps.

### File List

- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/schemas.py`
- `backend/tests/domains/inventory/test_planning_support.py`
- `src/lib/api/inventory.ts`
- `src/domain/inventory/types.ts`
- `src/domain/inventory/hooks/useProductPlanningSupport.ts`
- `src/domain/inventory/components/AnalyticsTab.tsx`
- `src/domain/inventory/components/PlanningSupportCard.tsx`
- `src/domain/inventory/components/AnalyticsTab.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`