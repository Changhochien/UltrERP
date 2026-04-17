# Story 20.9: Product Analytics Backend Test Coverage

Status: done

## Story

As a developer,
I want focused backend coverage for the shared product analytics foundation and its inventory and intelligence reuse seams,
so that I can refactor aggregate queries, feature gates, and MCP contracts safely without breaking commercial analytics or downstream planning behavior.

## Problem Statement

Epic 20 is not a single isolated module. It spans a shared monthly sales foundation, intelligence-owned analytics, inventory-owned planning support, settings and auth layers, and MCP scope enforcement. That creates multiple regression seams: monthly aggregation math, snapshot correctness, tenant isolation, current-month fallback behavior, lifecycle classification boundaries, feature-disabled handling, MCP scope enforcement, and downstream reuse in inventory and intelligence.

The repo already uses different pytest styles for different seams: DB-backed async service tests for aggregation logic, fake-session route tests for HTTP behavior, direct MCP tool tests with patched headers for `ToolError` contracts, and centralized MCP auth middleware tests. Story 20.9 should add coverage at those real seams instead of collapsing everything into one mocked test file.

## Solution

Create a dedicated shared product analytics foundation test slice, then extend the existing intelligence and inventory suites where those domains consume the shared history.

For v1 coverage:

- foundation tests under `backend/tests/domains/product_analytics/`
- intelligence service, route, and MCP tests for Stories 20.4, 20.6, and 20.7
- inventory tests for Story 20.5 planning support
- centralized `TOOL_SCOPES` and auth-middleware assertions in `backend/tests/test_mcp_auth.py`

If Story 20.2 remains deferred, do not spend this story on unshipped SCD2 behavior.

## Best-Practice Update

This section supersedes conflicting details below.

- Prefer DB-backed async tests for monthly aggregate refresh, current-month fallback, revenue diagnosis math, lifecycle classification, tenant isolation, and empty-history behavior.
- Reuse the existing split between service tests, route tests, MCP tool tests, and centralized MCP auth tests rather than over-mocking `AsyncSession` end to end.
- Add explicit disabled-feature tests for REST and MCP, mirroring the existing intelligence suite.
- Cover zero-baseline cases, deterministic sorting, sparse data, and current-month versus historical-month path selection. Do not stop at happy-path arithmetic.
- Keep downstream reuse tests in the owning domain suites. Inventory behavior belongs in inventory tests, and intelligence behavior belongs in intelligence tests.
- Do not require SCD2-specific tests unless Story 20.2 actually ships.

## Acceptance Criteria

1. Given confirmed, shipped, fulfilled, draft, and cancelled orders in the same tenant and month, when the monthly refresh service runs, then only countable commercial orders are aggregated, exactly one historical row exists per tenant-month-product-snapshot grain, and rerunning the refresh is idempotent.
2. Given two tenants with overlapping product names and categories, and a live product record renamed after sale, when the monthly fact is refreshed and queried, then only the caller tenant's data is included and historical assertions are based on immutable sale-time snapshots.
3. Given stale current-month aggregate rows exist, when a shared analytics query requests a window that includes the current month, then the current month is derived from live transactional data while prior months continue to use the historical aggregate.
4. Given two consecutive historical periods with known quantity and price changes, when the revenue-diagnosis service runs, then price effect, volume effect, and mix effect sum exactly to the total revenue delta and the breakdown sort is deterministic.
5. Given products at the boundary between new, growing, stable, declining, mature, and end-of-life behavior, when the product-performance service runs, then lifecycle classification follows the contract exactly and the result ordering is deterministic.
6. Given shared monthly sales history is wired into inventory planning support, when the inventory planning endpoint runs, then sales velocity and seasonality come from the shared history while reorder recommendations still respect current stock, inbound supply, and existing inventory policy inputs.
7. Given shared historical sales inputs are wired into customer buying behavior, when the intelligence extension runs, then segment filtering, top-category ordering, cross-sell evidence, and snapshot semantics remain correct without regressing existing intelligence contracts.
8. Given an Epic 20 owner-domain route is enabled for an authorized role, when the route is called, then the response shape matches the schema contract; and given the corresponding feature setting is false, when the route is called, then a 403 response with a stable disabled-feature detail message is returned.
9. Given an Epic 20 MCP tool is enabled and receives valid tenant context, when the tool is called, then it returns a stable machine-facing payload; and given the tool is disabled, missing tenant context, or missing required scope, when the tool is called, then it raises structured errors consistent with current MCP conventions.
10. Given new Epic 20 tools are registered in the auth layer, when the MCP auth test suite runs, then exact `TOOL_SCOPES` entries and insufficient-scope behavior are asserted in the centralized auth tests.

## Technical Notes

- Mirror the DB-backed service-test pattern already used in `backend/tests/domains/intelligence/test_service.py`.
- Mirror the fake-session route-test pattern already used in `backend/tests/domains/intelligence/test_routes.py`.
- Mirror the direct MCP tool test pattern already used in `backend/tests/test_mcp_intelligence.py`.
- Extend the centralized auth suite in `backend/tests/test_mcp_auth.py` for Epic 20 tool scopes and tenant-binding behavior.
- Keep inventory planning assertions in inventory-owned suites such as `backend/tests/domains/inventory/test_reorder_point_integration.py` or adjacent inventory service tests.
- Keep intelligence extension assertions in intelligence-owned suites beside the existing intelligence tests.

## Tasks / Subtasks

- [x] Task 1: Add DB-backed shared product analytics service tests covering monthly refresh grain, snapshot correctness, tenant isolation, current-month fallback, empty history, and deterministic sorting.
- [x] Task 2: Add owner-domain route tests for authorized access, unauthorized access, disabled-feature behavior, and query validation.
- [x] Task 3: Add MCP tool tests for success payloads, validation errors, disabled-feature `ToolError`s, and tenant-context failures.
- [x] Task 4: Extend `backend/tests/test_mcp_auth.py` with exact `TOOL_SCOPES` assertions and insufficient-scope cases for Epic 20 tools.
- [x] Task 5: Extend the inventory planning test seam so Story 20.5 proves shared monthly sales history informs planning without bypassing existing stock and supplier logic.
- [x] Task 6: Extend the intelligence test seam so Story 20.7 proves segment-level customer analytics reuse the shared history without regressing existing intelligence contracts.

## Dev Notes

- The strongest local template for aggregate logic is `backend/tests/domains/intelligence/test_service.py`, which already builds real customers, products, orders, and order lines with DB-backed async fixtures.
- The strongest local template for route-level disabled-feature assertions is `backend/tests/domains/intelligence/test_routes.py`.
- The strongest local template for MCP disabled-feature and tenant-context assertions is `backend/tests/test_mcp_intelligence.py`.
- If Story 20.2 remains deferred, do not spend this story on unshipped product-dimension tests.

## Project Structure Notes

- Add the new shared foundation test split parallel to the existing intelligence split.
- Keep shared MCP tool contract tests parallel to the existing intelligence MCP suite.
- Keep auth-middleware scope tests centralized in `backend/tests/test_mcp_auth.py`.

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `../implementation-artifacts/19-8-intelligence-backend-tests.md`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`
- `backend/tests/test_mcp_auth.py`
- `backend/tests/domains/inventory/test_reorder_point_integration.py`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/domains/intelligence/test_routes.py -q` -> `36 passed in 1.21s`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/domains/product_analytics/test_service.py -q` -> `8 passed in 0.88s`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/test_mcp_auth.py -q` -> `27 passed in 0.36s`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/domains/product_analytics/test_service.py tests/domains/intelligence/test_revenue_diagnosis_service.py tests/domains/intelligence/test_product_performance_service.py tests/domains/intelligence/test_customer_buying_behavior_service.py tests/domains/intelligence/test_routes.py tests/domains/inventory/test_planning_support.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q` -> `109 passed in 2.78s`

### Completion Notes List

- Added shared product analytics foundation regressions for countable commercial statuses, per-snapshot monthly grain aggregation, cross-tenant isolation, and immutable sale-time snapshots after live product renames.
- Added Epic 20 intelligence route boundary coverage for unauthenticated requests, finance-role rejection, and query validation, including a local no-auth HTTP helper because the shared route helper injects an owner token by default.
- Added explicit centralized MCP auth insufficient-scope coverage for `intelligence_revenue_diagnosis`, `intelligence_product_performance`, and `intelligence_customer_buying_behavior` while reusing the existing Story 20.4, 20.5, 20.6, and 20.7 owner-domain suites in the broader validation batch.
- Story 20.9 keeps the public and planning seams in their owning domains instead of introducing a speculative shared analytics route or duplicate cross-domain test layer.

### File List

- `backend/tests/domains/product_analytics/test_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_auth.py`
- `_bmad-output/implementation-artifacts/20-9-product-analytics-backend-test-coverage.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`