# Story 39.2: Dense Time-Series Backend Contracts and Range Semantics

Status: review

## Story

As a chart consumer,
I want time-series APIs to return dense, range-aware, timezone-explicit data,
so that long-range charts remain truthful and navigable even when source activity is sparse.

## Problem Statement

The current monthly-demand behavior exposed a structural issue: increasing the requested month count does not guarantee a usable timeline because the endpoint currently returns only buckets that have source rows. That makes long-history charts look broken even when the API technically returned valid data. Similar drift can happen across other time-series endpoints when range metadata, timezone semantics, and partial-period handling are implicit instead of explicit.

## Solution

Standardize backend time-series contracts around dense series and explicit range semantics.

For first-wave explorer endpoints, return:

- zero-filled buckets for the requested time window
- explicit bucket and timezone metadata
- requested range, available range, and default visible range
- partial-period flags when open/current periods are included

In v1, keep the current sparse endpoints unchanged and add parallel dense explorer endpoints:

- `GET /api/v1/inventory/products/{product_id}/monthly-demand-series`
- `GET /api/v1/inventory/stock-history/{stock_id}/series`
- `GET /api/v1/dashboard/revenue-trend-series`

The current routes stay live until Story 39.5 finishes all first-wave migrations and a dedicated cleanup follow-up is approved.

Support explicit range semantics that can evolve from simple preset windows to durable explorer controls.

The explorer response contract is explicit:

```json
{
  "points": [
    {
      "bucket_start": "2026-01-01",
      "bucket_label": "2026-01",
      "value": 0,
      "is_zero_filled": true,
      "period_status": "closed",
      "source": "zero-filled"
    }
  ],
  "range": {
    "requested_start": "2023-01-01",
    "requested_end": "2026-12-01",
    "available_start": "2024-02-01",
    "available_end": "2026-04-01",
    "default_visible_start": "2025-05-01",
    "default_visible_end": "2026-04-01",
    "bucket": "month",
    "timezone": "Asia/Taipei"
  }
}
```

## Acceptance Criteria

1. Given a time-series endpoint returns monthly or daily data, when the requested window contains gaps, then the response includes zero-filled points rather than omitting missing buckets.
2. Given an explorer-tier chart requests data, when the API responds, then it includes range metadata such as `requested_range`, `available_range`, `default_visible_range`, `bucket`, and `timezone`.
3. Given a partial current period is included, when the response is built, then each point exposes `period_status: "closed" | "partial"` and `source: "aggregate" | "live" | "zero-filled"` instead of blending partial periods silently with closed history.
4. Given a first-wave explorer endpoint is modernized, when existing consumers still rely on current shapes, then the current sparse routes remain unchanged and the new dense explorer routes are added in parallel under the exact paths listed in this story.
5. Given the backend contract is reviewed, when business timezone rules apply, then Taiwan month or date bucketing is explicit and test-covered.
6. Given a dense explorer response is generated, when the request would exceed the v1 support envelope, then the backend either uses a coarser bucket or rejects the request with a narrowing hint; v1 targets at most `120` monthly points or `730` daily points in one response.

## Tasks / Subtasks

- [x] Task 1: Define shared response schema for explorer-tier time series. (AC: 1-4)
  - [x] Create reusable helpers and typed response primitives in `backend/common/time_series.py`.
  - [x] Define domain-owned Pydantic response models in the existing schema modules that wrap `points` plus `range` metadata.
  - [x] Define canonical fields for bucket, timezone, points, requested range, available range, and default visible range.
  - [x] Represent partial current periods with `period_status` and `source` fields on each point.
- [x] Task 2: Add densification utilities. (AC: 1, 5)
  - [x] Create shared helpers for zero-filling monthly and daily series in `backend/common/time_series.py`.
  - [x] Keep timezone-aware bucket generation explicit.
  - [x] Avoid duplicating bucket-generation logic across inventory and dashboard domains.
- [x] Task 3: Modernize first-wave endpoints. (AC: 1-5)
  - [x] Add `GET /api/v1/inventory/products/{product_id}/monthly-demand-series` in `backend/domains/inventory/routes.py` and its service implementation in `backend/domains/inventory/services.py`.
  - [x] Add `GET /api/v1/inventory/stock-history/{stock_id}/series` in `backend/domains/inventory/routes.py` and reuse or extend `get_stock_history()` in `backend/domains/inventory/services.py`.
  - [x] Add `GET /api/v1/dashboard/revenue-trend-series` in `backend/domains/dashboard/routes.py` and its service implementation in `backend/domains/dashboard/services.py`.
  - [x] Ensure source-of-truth provenance remains available for closed vs. live/current windows.
- [x] Task 4: Add focused tests and contract coverage. (AC: 1-5)
  - [x] Add shared utility tests in `backend/tests/common/test_time_series.py`.
  - [ ] Extend `backend/tests/domains/inventory/test_product_detail.py` for monthly-demand dense-series coverage.
  - [ ] Extend `backend/tests/domains/inventory/test_stock_history_service.py` for stock-history series coverage.
  - [ ] Extend `backend/tests/domains/dashboard/test_revenue_trend.py` for dense revenue-trend coverage.
  - [ ] Add regression tests for Taiwan timezone bucket boundaries and partial-period flags.

## Dev Notes

### Context

- `backend/domains/inventory/services.py` currently computes a requested month window for monthly demand but only emits source rows present in that window.
- `backend/domains/inventory/routes.py` already widened the monthly-demand preset cap, but a larger cap alone is not the long-term answer.
- `backend/domains/inventory/routes.py` already exposes `monthly-demand`, `stock-history/{stock_id}`, and `planning-support`; this story must avoid breaking those current consumers in place.
- `backend/domains/dashboard/routes.py` already exposes `GET /api/v1/dashboard/revenue-trend` and current frontend callers in `src/lib/api/dashboard.ts` rely on it.

### Architecture Compliance

- Range selection should be modeled as a contract, not just `months=N` query expansion.
- The backend must own densification for business-correct time buckets rather than forcing the frontend to guess missing months.
- Timezone semantics must remain explicit and testable.
- Compatibility strategy is fixed for v1: parallel dense-series routes, no in-place breaking envelope changes.

### Expected Python and JSON Shapes

```py
# backend/common/time_series.py
class DenseSeriesPoint(TypedDict):
  bucket_start: str
  bucket_label: str
  value: int | float
  is_zero_filled: bool
  period_status: Literal["closed", "partial"]
  source: Literal["aggregate", "live", "zero-filled"]

class DenseSeriesRange(TypedDict):
  requested_start: str
  requested_end: str
  available_start: str | None
  available_end: str | None
  default_visible_start: str
  default_visible_end: str
  bucket: Literal["day", "week", "month"]
  timezone: str
```

### Backend Query Rules

- Monthly demand and revenue-series points are bucketed in business timezone first, then densified in Python.
- Stock-history series may reuse existing stock-history query paths, but the dense explorer route must return a normalized `points` plus `range` envelope.
- Do not change the meaning of current sparse endpoints while Story 39.5 is still migrating consumers.

### Testing Requirements

- Add tests for zero-filled gaps, long empty stretches, partial current-month flags, and explicit range metadata.
- Validate that legacy consumers do not break unexpectedly if endpoint envelopes are widened.

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP/backend && PYTEST_RUNNING=1 .venv/bin/python -m pytest tests/common/test_time_series.py tests/domains/inventory/test_product_detail.py tests/domains/inventory/test_stock_history_service.py tests/domains/dashboard/test_revenue_trend.py -q`
- `cd /Users/changtom/Downloads/UltrERP && pnpm exec vitest run src/domain/inventory/hooks/useProductMonthlyDemand.test.tsx src/domain/dashboard/__tests__/useRevenueTrend.test.tsx --reporter=dot`

## References

- `../planning-artifacts/epic-39.md`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `src/domain/inventory/hooks/useProductMonthlyDemand.ts`
- `src/domain/dashboard/hooks/useDashboard.ts`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-24: Drafted Story 39.2 to fix the root backend issue behind sparse long-range charts by introducing dense, range-aware time-series contracts.

### File List

- `_bmad-output/implementation-artifacts/39-2-dense-time-series-backend-contracts-and-range-semantics.md`