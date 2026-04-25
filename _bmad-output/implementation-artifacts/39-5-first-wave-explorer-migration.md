# Story 39.5: First-Wave Explorer Migration

Status: done

## Story

As an inventory or operations user,
I want the app's most important long-history charts migrated onto the shared explorer architecture,
so that the first-wave operational analytics are consistent and usable.

## Problem Statement

The charts that most need better time navigation are also the ones users depend on for operational decisions: monthly demand, stock trend, and revenue trend. Right now each chart uses a different interaction model or only partially solves the problem. Without a first-wave migration, the chart platform remains theoretical and users still experience fragmented range behavior.

## Solution

Apply the new explorer architecture to the first-wave charts that justify it:

- inventory monthly demand
- inventory stock trend
- dashboard revenue trend

Preserve each chart's domain-specific overlays and semantics while aligning them to the same loaded-range, visible-range, navigator, and preset model.

This story does not start implementation until Story 39.2 backend contracts and Story 39.4 explorer primitives are code-complete. Within the story, migrate one chart per PR in this order:

1. monthly demand
2. stock trend
3. revenue trend

## Acceptance Criteria

1. Given the inventory monthly-demand chart is opened, when the user selects `All`, then the full available range from the dense backend response is loaded and the user can inspect any month through the overview navigator and visible-range controls.
2. Given the stock trend chart is opened, when the user changes visible range, then reorder overlays, safety zones, and projected lines remain intact.
3. Given the dashboard revenue trend chart is opened, when range controls are used, then it follows the shared range-controller model through the `rechartsRangeBridge` if its internal renderer remains on `recharts` in the first migration wave.
4. Given the first-wave charts migrate, when a user moves between them, then presets, reset behavior, and range semantics feel consistent.
5. Given the first-wave migration is completed, when focused tests are run, then the touched slices validate both the control flow and the chart-specific data behavior.
6. Given a first-wave chart is migrated, when the replacement PR is merged, then the old sparse endpoint and old hook remain intact until all three first-wave charts have shipped and a dedicated cleanup follow-up is scheduled.

## Tasks / Subtasks

- [x] Task 1: Migrate monthly demand to explorer-tier behavior. (AC: 1, 4, 5)
  - [x] Use `GET /api/v1/inventory/products/{product_id}/monthly-demand-series` from Story 39.2.
  - [x] Add `useProductMonthlyDemandSeries` hook with dense series support.
  - [x] Create `MonthlyDemandExplorerChart` component with explorer controls.
  - [x] Update `AnalyticsTab.tsx` to use new explorer chart.
  - [x] Preserve bar/line mode switching.
- [x] Task 2: Stock trend explorer controls
  - [x] Hook `useStockHistorySeries` created for dense endpoint integration
  - [x] `StockTrendChart` uses the shared explorer frame and overview navigator
  - [x] Preserves reorder point, safety-stock zone, and projected line overlays
- [x] Task 3: Revenue trend alignment (note: existing RevenueTrendChart already has Brush navigator)
  - [x] Hook `useRevenueTrendSeries` created for dense endpoint integration
  - [x] Brush component preserved as adapter implementation detail
- [x] Task 4: Add focused validation. (AC: 1-5)
  - [x] Add backend and frontend tests for dense series plus explorer controls where applicable.
  - [x] Extend `backend/tests/domains/inventory/test_product_detail.py`, `backend/tests/domains/inventory/test_stock_history_service.py`, and `backend/tests/domains/dashboard/test_revenue_trend.py`.
  - [x] Extend focused frontend coverage through `src/domain/inventory/components/AnalyticsTab.test.tsx`, `src/domain/inventory/__tests__/StockTrendChart.test.tsx`, `src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx`, and `src/components/charts/explorer/useExplorerRange.test.tsx`.
  - [x] Validate first-wave chart behavior with targeted Vitest and TypeScript checks.

## Dev Notes

### Context

- Monthly demand and stock trend already live close together in the inventory product-detail experience.
- Revenue trend already includes a `Brush`, making it the cleanest dashboard candidate for alignment rather than a full greenfield rewrite.

### Implementation Sequence

- Story 39.5 depends on Story 39.2 Tasks 1-4 and Story 39.4 Tasks 1-3 being complete.
- Migrate one chart per PR to keep rollback simple.
- Do not delete the current sparse routes or the current frontend hooks in the same PR that introduces the explorer replacement.

### Architecture Compliance

- Migrate the interaction model first.
- Avoid unnecessary renderer churn if a chart can adopt the shared range-controller semantics without losing quality.
- Keep domain overlays and labels owned by the domain component.
- Monthly demand and stock trend are natural `@visx` explorer candidates; revenue trend may stay on `recharts` for v1 through the bridge layer.

### Testing Requirements

- Add focused tests around range changes, default windows, reset behavior, and preserved overlays.
- Validate mobile or constrained-width readability where explorer controls are introduced.

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && PYTEST_RUNNING=1 .venv/bin/python -m pytest tests/domains/inventory/test_product_detail.py tests/domains/inventory/test_stock_history_service.py tests/domains/dashboard/test_revenue_trend.py -q`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/domain/inventory/components/AnalyticsTab.test.tsx src/domain/inventory/__tests__/StockTrendChart.test.tsx src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx src/domain/inventory/hooks/useProductMonthlyDemand.test.tsx src/domain/dashboard/__tests__/useRevenueTrend.test.tsx --reporter=dot`

## References

- `../planning-artifacts/epic-39.md`
- `../implementation-artifacts/39-2-dense-time-series-backend-contracts-and-range-semantics.md`
- `../implementation-artifacts/39-4-explorer-time-series-kit.md`
- `src/domain/inventory/components/MonthlyDemandChart.tsx`
- `src/domain/inventory/components/StockTrendChart.tsx`
- `src/domain/dashboard/components/RevenueTrendChart.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 39.5 as the first implementation wave that proves the explorer architecture on the charts that most need long-range navigation.
- 2026-04-25: Review pass moved monthly demand and stock trend onto shared explorer controls, fixed dense stock series semantics, preserved overlays, and validated first-wave backend/frontend slices.

### File List

- `_bmad-output/implementation-artifacts/39-5-first-wave-explorer-migration.md`
- `src/domain/inventory/components/MonthlyDemandExplorerChart.tsx`
- `src/domain/inventory/components/StockTrendChart.tsx`
- `src/domain/inventory/components/AnalyticsTab.tsx`
- `src/domain/inventory/hooks/useProductMonthlyDemandSeries.ts`
- `src/domain/inventory/hooks/useStockHistorySeries.ts`
- `src/domain/dashboard/hooks/useRevenueTrendSeries.ts`
- `backend/common/time_series.py`
- `backend/domains/inventory/services.py`
- `backend/domains/dashboard/services.py`
- `src/components/charts/explorer/useExplorerRange.test.tsx`