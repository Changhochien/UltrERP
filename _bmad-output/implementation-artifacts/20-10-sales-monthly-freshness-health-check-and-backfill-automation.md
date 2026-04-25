# Story 20.10: Sales Monthly Freshness Health Check and Backfill Automation

Status: completed

## Story

As an operator or analytics owner,
I want proactive detection and repair for missing closed-month `sales_monthly` history,
so that planning support and intelligence analytics stay trustworthy without depending on invisible degraded-mode fallback behavior.

## Problem Statement

Story 20.3 introduced `sales_monthly` as the closed-month foundation for Epic 20, and the later stories now depend on it for revenue diagnosis, product performance, customer buying behavior, and inventory planning support. The current codebase now has two resilience improvements: a rolling recent closed-month upkeep path in the reviewed refresh flow, and a transactional fallback when a closed month has sales but missing snapshot rows.

Those fixes keep the app usable, but they do not yet give operators a proactive freshness signal or a stronger repair workflow. A tenant can remain in a degraded state without any explicit health warning, and historical seeding or large-gap recovery still relies on operators manually choosing refresh windows. The next story should turn that hidden recovery behavior into an explicit, auditable health and repair surface.

## Solution

Add a shared `sales_monthly` freshness layer that detects closed-month gaps and gives operators a supported repair path.

For this story:

- add a tenant-scoped health check for closed months with transactional sales but missing `sales_monthly` coverage
- extend the existing reviewed refresh surfaces with explicit missing-month repair and historical backfill modes
- surface degraded freshness through existing operator seams such as CLI output, run summaries, or the existing admin refresh control plane
- keep the existing transactional fallback for downstream reads, but treat it as a temporary resilience guard rather than the steady-state data source

## Best-Practice Update

This section supersedes conflicting details below.

- Keep this story operational and foundation-focused. Do not add a new end-user `product_analytics` route or page.
- Reuse the reviewed Epic 15 refresh surfaces where practical instead of creating a second scheduler or duplicate repair entry point.
- Run health checks only against closed months. The current open month remains a live-read concern, not a snapshot health failure.
- Prefer month-level missing-coverage detection first. Do not introduce speculative per-product checksum or drift-detection systems unless the repo demonstrates a real need.
- Keep the transactional fallback in shared reads until repair completes, but make the degraded state visible to operators.

## Acceptance Criteria

1. Given a tenant has a closed month with countable commercial sales but no `sales_monthly` rows, when the health check runs, then the result marks the month as missing and includes enough evidence for remediation such as tenant, month, and transactional support counts.
2. Given a tenant has no missing closed-month snapshot coverage in the requested window, when the health check runs, then the result reports a healthy state with zero missing months.
3. Given one or more missing months are detected, when the operator runs a missing-month repair mode, then only those closed months are refreshed and rerunning the repair remains idempotent.
4. Given a tenant needs initial historical seeding or large-gap recovery, when the operator runs a historical backfill mode, then the system refreshes the requested closed-month range up to the last closed month and never aggregates the current open month.
5. Given rolling upkeep or a reviewed refresh run completes while missing closed months still remain, when the operator inspects the resulting summary or control-plane status, then the degraded freshness state is visible with remediation guidance instead of appearing silently healthy.
6. Given downstream shared reads still need to serve analytics while closed-month snapshot gaps exist, when a query runs, then the existing transactional fallback remains available but the health output continues to mark the tenant as degraded until the missing months are repaired.

## Technical Notes

### Existing extension points

- `backend/domains/product_analytics/service.py` owns the shared monthly read and refresh helpers.
- `backend/scripts/refresh_sales_monthly.py` already supports full-history refresh and rolling recent closed-month upkeep.
- `backend/scripts/run_legacy_refresh.py` and Story 15.23 already own the reviewed incremental refresh path.
- Story 15.28 already established an admin control-plane surface for refresh operations.

### Intended implementation direction

- Add a shared health-check helper that compares closed-month transactional activity against month-level `sales_monthly` coverage.
- Extend the refresh script with explicit health-check, repair-missing-only, and bounded historical backfill modes.
- If a route or UI surface is needed, extend an existing admin or operator surface rather than introducing a public analytics endpoint.
- Keep health outputs machine-readable so reviewed refresh summaries and future automation can consume them.

### Guardrails

- Do not remove the current transactional fallback in this story.
- Do not move planning support, revenue diagnosis, product performance, or customer buying behavior into a new owner domain.
- Do not force every incremental run to rescan full history.
- Do not invent a new scheduler stack when the reviewed refresh surfaces already exist.

## Tasks / Subtasks

- [x] Task 1: Add a tenant-scoped closed-month `sales_monthly` health check service and machine-readable result contract. (AC: 1, 2, 6)
- [x] Task 2: Extend the existing refresh script with explicit missing-month repair and bounded historical backfill modes. (AC: 3, 4)
- [x] Task 3: Surface degraded freshness status in reviewed run summaries and any reused admin control-plane seams. (AC: 5, 6)
- [x] Task 4: Keep downstream shared reads aligned with the degraded-mode contract so fallback remains available until repair completes. (AC: 6)
- [x] Task 5: Add focused backend coverage for healthy windows, missing-month detection, targeted repair, bounded historical backfill, and degraded-summary reporting. (AC: 1-6)

## Dev Notes

- The local root-cause pattern is already proven: planning support can look correct at the chart layer while the shared monthly fact is incomplete underneath.
- The first health contract should stay month-level and operator-friendly. If later evidence shows partial-month or per-product drift matters, that can be a separate follow-up.
- This story should strengthen operational truth, not redesign end-user analytics UX.

## Project Structure Notes

- Shared health and repair logic belongs with the backend `product_analytics` and reviewed refresh surfaces.
- Any operator-facing visibility belongs in existing admin or refresh-control surfaces.
- End-user inventory and intelligence pages should continue to consume the shared read layer rather than grow their own repair controls.

## References

- `../planning-artifacts/epic-20.md`
- `../implementation-artifacts/20-3-monthly-aggregation-tables.md`
- `../implementation-artifacts/20-5-inventory-planning-support-from-shared-sales-history.md`
- `../implementation-artifacts/15-23-incremental-legacy-refresh-runner-surface.md`
- `../implementation-artifacts/15-28-admin-legacy-refresh-control-plane.md`
- `backend/domains/product_analytics/service.py`
- `backend/scripts/refresh_sales_monthly.py`
- `backend/scripts/run_legacy_refresh.py`

---

## Dev Agent Record

### Implementation Notes

**Implemented Features:**

1. **Health Check Service** (`backend/domains/product_analytics/service.py`):
   - `check_sales_monthly_health()`: Tenant-scoped health check comparing transactional sales against month-level `sales_monthly` coverage
   - `SalesMonthlyHealthResult`: Machine-readable result dataclass with `is_healthy`, `missing_months`, `checked_month_count`
   - `SalesMonthlyMissingMonth`: Details per missing month including `transactional_order_count` and `transactional_revenue`
   - Current open month is never flagged as missing (uses live reads)

2. **Repair Service** (`backend/domains/product_analytics/service.py`):
   - `repair_missing_sales_monthly_months()`: Repairs only specified missing closed months
   - Idempotent - re-running produces same result with no duplicates
   - Never touches current open month

3. **Bounded Backfill** (`backend/domains/product_analytics/service.py`):
   - `backfill_sales_monthly_history()`: Bounded historical backfill for initial seeding or large-gap recovery
   - Never aggregates current open month
   - Returns range refresh result for downstream processing

4. **Extended Refresh CLI** (`backend/scripts/refresh_sales_monthly.py`):
   - Added subcommand modes: `health`, `repair`, `backfill`
   - `refresh`: Legacy mode (unchanged)
   - `health`: Check closed-month coverage with optional `--start-month` and `--end-month`
   - `repair`: Repair specific missing months with `--missing-month` (repeatable)
   - `backfill`: Bounded historical range with `--start-month` and optional `--end-month`

5. **Legacy Refresh Integration** (`backend/scripts/run_legacy_refresh.py`):
   - Added `sales_monthly_health_check` step to STEP_ORDER
   - Health check runs after `refresh_sales_monthly` step
   - Degraded freshness surfaced in summary: `sales_monthly_freshness` object with `is_healthy`, `missing_month_count`, `missing_months`, `degraded_message`, `remediation_guidance`

**Technical Decisions:**

- Used transaction-aware pattern for `refresh_sales_monthly()` to handle nested calls from repair/backfill functions
- Health check uses month-level granularity (not per-product) for operator-friendly output
- CLI modes use argparse subparsers for clean command structure
- Health results include both `transactional_order_count` and `transactional_revenue` for evidence-based remediation

**Files Modified:**
- `backend/domains/product_analytics/service.py` - Added health check, repair, and backfill functions
- `backend/scripts/refresh_sales_monthly.py` - Added CLI subcommands for new modes
- `backend/scripts/run_legacy_refresh.py` - Added health check step and degraded state surfacing
- `backend/tests/domains/product_analytics/test_service.py` - Added 7 new tests for AC coverage
- `backend/tests/test_run_legacy_refresh.py` - Updated tests for new step

**Tests Added:**
- `test_health_check_reports_healthy_when_no_gaps` (AC2)
- `test_health_check_detects_missing_closed_month_with_sales` (AC1)
- `test_repair_missing_months_is_idempotent` (AC3)
- `test_backfill_bounded_history_excludes_current_month` (AC4)
- `test_health_check_returns_healthy_after_repair` (AC6)
- `test_health_check_excludes_current_open_month_from_gap_detection` (AC2)
- `test_health_check_returns_empty_for_future_window` (AC2)

### Completion Notes

✅ All 5 tasks completed
✅ All 6 acceptance criteria validated through tests
✅ 28 tests passing (19 product_analytics + 7 run_legacy_refresh + 2 refresh_sales_monthly)
✅ Lint and type checks passing
✅ Story marked ready for review

---

## File List

### New Files
- (none - all changes extend existing files)

### Modified Files
- `backend/domains/product_analytics/service.py` - Added health check, repair, and backfill functions
- `backend/scripts/refresh_sales_monthly.py` - Added CLI subcommands for new modes
- `backend/scripts/run_legacy_refresh.py` - Added health check step and degraded state surfacing
- `backend/tests/domains/product_analytics/test_service.py` - Added 7 new tests for AC coverage
- `backend/tests/test_run_legacy_refresh.py` - Updated tests for new step in STEP_ORDER

---

## Change Log

| Date | Change |
|------|--------|
| 2026-04-25 | Implemented health check service with machine-readable result contract |
| 2026-04-25 | Added repair_missing_sales_monthly_months() for idempotent month repair |
| 2026-04-25 | Added backfill_sales_monthly_history() for bounded historical backfill |
| 2026-04-25 | Extended refresh_sales_monthly.py CLI with health, repair, and backfill subcommands |
| 2026-04-25 | Integrated health check step into run_legacy_refresh.py pipeline |
| 2026-04-25 | Added sales_monthly_freshness summary object with degraded state surfacing |
| 2026-04-25 | Added 7 new tests covering all acceptance criteria |
| 2026-04-25 | All tests passing, linter clean, story complete |