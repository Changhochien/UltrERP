---
type: bmad-distillate
sources:
  - "_bmad-output/implementation-artifacts/20-10-sales-monthly-freshness-health-check-and-backfill-automation.md"
downstream_consumer: story-context
created: 2026-04-25
token_estimate: 1038
parts: 1
---

# Story 20.10: Sales Monthly Freshness Health Check and Backfill Automation

## Status
- **Status:** completed
- **Epic:** Epic 20 - Product Sales Analytics

## Core Problem Solved
- Operators lacked proactive detection for missing closed-month `sales_monthly` history
- No explicit repair workflow for missing months
- Hidden degraded-mode fallback behavior with no visibility

## Solution Delivered

### Backend Services (`backend/domains/product_analytics/service.py`)
- `check_sales_monthly_health()` - Tenant-scoped health check comparing transactional sales vs month-level snapshot coverage
- `repair_missing_sales_monthly_months()` - Idempotent repair for specified missing closed months
- `backfill_sales_monthly_history()` - Bounded historical backfill (never touches current month)

### CLI Extension (`backend/scripts/refresh_sales_monthly.py`)
- `refresh-sales-monthly health [--start-month YYYY-MM-DD] [--end-month YYYY-MM-DD]`
- `refresh-sales-monthly repair --missing-month YYYY-MM-DD [--missing-month ...]`
- `refresh-sales-monthly backfill --start-month YYYY-MM-DD [--end-month YYYY-MM-DD]`

### Legacy Refresh Integration (`backend/scripts/run_legacy_refresh.py`)
- Added `sales_monthly_health_check` step to pipeline (after `refresh_sales_monthly`)
- Degraded freshness surfaced in summary: `sales_monthly_freshness` object

## Acceptance Criteria Coverage

| AC | Description | Status |
|----|-------------|--------|
| AC1 | Missing month with transactional sales detected | ✅ Tested |
| AC2 | Healthy state reported when no gaps | ✅ Tested |
| AC3 | Missing-month repair is idempotent | ✅ Tested |
| AC4 | Backfill never aggregates current month | ✅ Tested |
| AC5 | Degraded state visible in run summaries | ✅ Implemented |
| AC6 | Transactional fallback available during gaps | ✅ Verified |

## Test Coverage
- 7 new tests in `tests/domains/product_analytics/test_service.py`
- All 28 related tests passing
- Linter clean

## Files Modified
- `backend/domains/product_analytics/service.py`
- `backend/scripts/refresh_sales_monthly.py`
- `backend/scripts/run_legacy_refresh.py`
- `backend/tests/domains/product_analytics/test_service.py`
- `backend/tests/test_run_legacy_refresh.py`

## Key Technical Decisions
- Month-level granularity (not per-product) for operator-friendly output
- Health results include `transactional_order_count` and `transactional_revenue` for evidence
- Transaction-aware pattern for nested calls in repair/backfill
- Current open month never flagged as missing (uses live reads)
