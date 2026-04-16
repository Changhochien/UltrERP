# Story 20.6: Product Performance API

Status: done

## Story

As an owner, product manager, or sales lead,
I want a product-performance API that ranks products by contribution and lifecycle stage across historical periods,
so that I can quickly see which products are growing, stable, declining, mature, new, or near end-of-life.

## Problem Statement

UltrERP has product-level operational analytics inside inventory and customer-level commercial analytics inside intelligence, but it does not yet have a tenant-wide portfolio view of product performance. Epic 20 adds the historical product-sales foundation needed to solve this. The missing piece is a stable intelligence contract that turns that history into a ranked, auditable product portfolio view.

## Solution

Add a product-performance API and UI section within the existing intelligence domain.

The response should return structured evidence for each product:

- `product_id`, `product_name`, `product_category_snapshot`
- `lifecycle_stage` and machine-readable `stage_reasons`
- `first_sale_month`, `last_sale_month`, `months_on_sale`
- current and prior period revenue, quantity, order count, and average unit price
- `peak_month_revenue`, `data_basis`, and `window_is_partial`

Default ranking should compare the last 12 complete months to the prior 12 complete months. An optional `include_current_month` flag may blend the open month, but that must be marked as partial and should not be the default.

Lifecycle classification is deterministic and uses this precedence order against the current 12 complete months versus the prior 12 complete months:

- `new`: current-window revenue is greater than zero, prior-window revenue is zero, and `first_sale_month` falls inside the current window.
- `end_of_life`: current-window revenue is zero, prior-window revenue is greater than zero, and `last_sale_month` is at least 6 complete months before the comparison anchor month.
- `declining`: prior-window revenue is greater than zero and either current-window revenue is zero without meeting the `end_of_life` rule, or current-window revenue is less than `0.80 * prior_window_revenue`.
- `growing`: prior-window revenue is greater than zero and current-window revenue is at least `1.20 * prior_window_revenue`.
- `mature`: current-window revenue is greater than zero, prior-window revenue is greater than zero, `months_on_sale >= 24`, and current-window revenue stays within the inclusive band `0.80 * prior_window_revenue` to `1.20 * prior_window_revenue`.
- `stable`: any remaining product with current-window revenue greater than zero.

Portfolio rows are keyed by `product_id`. If a product carries multiple snapshot labels inside the comparison windows, aggregated metrics stay grouped by `product_id`, while the returned `product_name` and `product_category_snapshot` come from the most recent included sale snapshot, preferring current-window months over prior-window months and then the latest analytics timestamp inside that month.

## Best-Practice Update

This section supersedes conflicting details below.

- Keep the public surface in intelligence and reuse the existing intelligence route, tool, hook, and page patterns.
- Do not introduce a new top-level permission feature or standalone route in v1.
- All money and quantity fields remain Decimal in Python and serialize consistently in JSON.
- Narrative fields are secondary. The response must prioritize structured evidence and machine-readable stage reasons.
- Deterministic ordering is required: current-period revenue descending, then revenue delta percent descending, then product name ascending, then product id ascending.
- Historical grouping must use Epic 20 snapshot semantics rather than live product master fields.

## Acceptance Criteria

1. Given an authenticated intelligence request, when `GET /api/v1/intelligence/product-performance` is called with optional `category`, `lifecycle_stage`, `limit`, and `include_current_month`, then the response returns a ranked product list plus comparison-window metadata.
2. Given a returned product row, when it is audited, then it contains structured evidence for revenue, quantity, order count, unit price, stage reasons, months on sale, and data basis.
3. Given the default request path, when product performance is calculated, then the ranking compares the last 12 complete months to the prior 12 complete months and excludes the open month from the default server sort.
4. Given `include_current_month = true`, when the current month is included, then that slice is computed live from confirmed, shipped, or fulfilled orders while closed months still come from Story 20.3 and `window_is_partial = true`.
5. Given historical category or product-name changes, when product performance is run for old periods, then the metrics use Epic 20 snapshot semantics rather than current live product fields.
6. Given a product has multiple sale-time names or categories inside the comparison windows, when the response is built, then metrics remain grouped by `product_id` and the returned `product_name` plus `product_category_snapshot` come from the most recent included sale snapshot, preferring current-window months over prior-window months.
7. Given `lifecycle_stage` is returned, when it is audited, then the backend applies the documented precedence order `new`, `end_of_life`, `declining`, `growing`, `mature`, `stable` with the documented thresholds exactly.
8. Given the feature is disabled, when the REST route or MCP tool is called, then the REST route fails through `_require_feature_enabled()` in `backend/domains/intelligence/routes.py` with HTTP 403 and the MCP tool fails through `_require_feature_enabled()` in `backend/domains/intelligence/mcp.py` with `ToolError` code `FEATURE_DISABLED`.
9. Given no qualifying sales exist, when the API is called, then it returns an empty product list with window metadata instead of an error.

## Technical Notes

### Backend

- Extend `backend/domains/intelligence/schemas.py` with product-performance models and lifecycle-stage enums.
- Extend `backend/domains/intelligence/service.py` with `get_product_performance()` that consumes Story 20.3.
- Extend `backend/domains/intelligence/routes.py` with `GET /api/v1/intelligence/product-performance`.
- Extend `backend/domains/intelligence/mcp.py` with `intelligence_product_performance`.
- Extend `backend/common/config.py` with `intelligence_product_performance_enabled`.
- Extend `backend/app/mcp_auth.py` with `intelligence_product_performance` using the same order-derived `TOOL_SCOPES` precedent as `intelligence_product_affinity`: `frozenset({"orders:read"})`.
- Implement lifecycle-stage precedence exactly as documented above and emit machine-readable `stage_reasons` that name the winning rule and threshold comparison.
- When a product has multiple snapshot labels inside the comparison windows, keep metric aggregation keyed to `product_id` and resolve the display label from the most recent included sale snapshot.

### Frontend

- Extend `src/domain/intelligence/types.ts`, `src/lib/api/intelligence.ts`, and `src/domain/intelligence/hooks/useIntelligence.ts`.
- Mount the UI on `src/pages/IntelligencePage.tsx` as a ranked table or filterable `SectionCard`, not a new route.
- Link rows into the existing inventory detail surface at `src/pages/inventory/ProductDetailPage.tsx`.

## Tasks / Subtasks

- [x] Task 1: Add product-performance schemas, service orchestration, route, feature flag, and MCP tool in the intelligence domain.
- [x] Task 2: Implement the closed-month default comparison window and optional live-current-month blend.
- [x] Task 3: Implement deterministic lifecycle-stage precedence and machine-readable stage reasons.
- [x] Task 4: Add frontend types, fetch helper, hook, and ranked `IntelligencePage` table.
- [x] Task 5: Add focused tests for lifecycle assignment, tie ordering, empty states, and partial-window behavior.

## Dev Notes

- Lifecycle-stage precedence must be explicit and mutually exclusive.
- Keep the first pass auditable. If thresholds change during implementation, update this story before code drifts.
- The drill-through target for a specific product should remain the existing inventory product-detail surface.

## Project Structure Notes

- Public ownership stays in intelligence.
- The existing `IntelligencePage` is the right landing surface for this story.

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `src/pages/IntelligencePage.tsx`
- `src/pages/inventory/ProductDetailPage.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/domains/intelligence/test_product_performance_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP && pnpm vitest run src/tests/intelligence/ProductPerformanceCard.test.tsx`
- VS Code diagnostics over touched backend/frontend files returned no errors.

### Completion Notes List

- Added tenant-scoped product-performance schemas and service orchestration in the intelligence domain, including deterministic lifecycle precedence, most-recent snapshot label resolution, and default closed-month comparison windows with optional live current-month blending.
- Exposed the new surface through `GET /api/v1/intelligence/product-performance`, the `intelligence_product_performance` MCP tool, the `intelligence_product_performance_enabled` feature flag, and the matching MCP auth scope registration.
- Mounted a new filterable `ProductPerformanceCard` on the existing intelligence page with lifecycle/category filters, partial-window provenance badges, ranked portfolio rows, and drill-through links into the inventory analytics detail view.
- Validated focused backend and frontend coverage for lifecycle assignment, deterministic ordering, empty states, feature-disabled REST/MCP behavior, scope registration, and the mounted intelligence UI slice.

### File List

- `backend/common/config.py`
- `backend/app/mcp_auth.py`
- `backend/domains/intelligence/schemas.py`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `backend/tests/domains/intelligence/test_product_performance_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`
- `backend/tests/test_mcp_auth.py`
- `src/domain/intelligence/types.ts`
- `src/lib/api/intelligence.ts`
- `src/domain/intelligence/hooks/useIntelligence.ts`
- `src/domain/intelligence/components/ProductPerformanceCard.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/tests/intelligence/ProductPerformanceCard.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`