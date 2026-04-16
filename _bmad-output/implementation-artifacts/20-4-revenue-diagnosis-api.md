# Story 20.4: Revenue Diagnosis API

Status: done

## Story

As an owner or sales lead,
I want a revenue-diagnosis API that decomposes period-over-period revenue change into price, volume, and mix,
so that I can explain growth or decline with evidence instead of intuition.

## Problem Statement

Epic 19 gives UltrERP ranked intelligence views, but it still cannot answer the most basic executive follow-up: why did revenue move. Users can see category momentum or customer risk, but they cannot separate a revenue change into unit-price movement, quantity movement, and product-mix shift. Epic 20 is introducing a shared monthly product-sales foundation; this story should expose that foundation through the existing intelligence domain rather than create a second analytics surface.

## Solution

Add a revenue-diagnosis read model to the existing intelligence stack.

The backend should compare a current period to the immediately preceding equivalent period and return:

- period metadata: period, anchor month, current window, prior window, `computed_at`
- summary totals: `current_revenue`, `prior_revenue`, `revenue_delta`, `revenue_delta_pct`
- component totals: `price_effect_total`, `volume_effect_total`, `mix_effect_total`
- driver rows: product identity, snapshot category/name, current and prior quantity/revenue/order counts, average unit prices, `price_effect`, `volume_effect`, `mix_effect`, `revenue_delta`, `revenue_delta_pct`, `data_basis`, and `window_is_partial`

Closed months should come from Story 20.3. If the requested window includes the open month, compute that slice live and mark the payload as partial.

## Best-Practice Update

This section supersedes conflicting details below.

- Keep the public surface in `backend/domains/intelligence/` and `src/domain/intelligence/`.
- Do not add a new top-level AppFeature or standalone route for v1. Reuse the existing intelligence page and permissions.
- Do not introduce a nonexistent MCP scope such as `products:read`. Stay inside the repo's current scope vocabulary.
- Historical grouping must use sale-time snapshot fields and the Story 20.3 loader, not live product master attributes.
- Lead with structured evidence. Narrative copy is convenience text only.
- Deterministic ordering is required: `abs(revenue_delta)` descending, then `abs(mix_effect)` descending, then `product_name` ascending, then `product_id` ascending.

## Acceptance Criteria

1. Given an authenticated intelligence request, when `GET /api/v1/intelligence/revenue-diagnosis` is called with `period`, `anchor_month`, optional `category`, and optional `limit`, then the response returns summary totals, component totals, comparison metadata, and ranked driver rows.
2. Given any driver row, when the breakdown is audited, then `price_effect + volume_effect + mix_effect = revenue_delta` after the defined Decimal rounding step.
3. Given a comparison window that only includes closed months, when the service loads data, then all periods are sourced from Story 20.3 and the payload marks `data_basis = aggregate_only`.
4. Given a comparison window that includes the current month, when the service loads data, then the current-month slice is computed live from confirmed, shipped, or fulfilled orders while closed months still come from the aggregate and `window_is_partial = true`.
5. Given products or categories were renamed after sale, when revenue diagnosis runs for historical months, then grouping and filtering use `product_name_snapshot` and `product_category_snapshot` rather than live `Product` fields.
6. Given the feature is disabled, when the REST route or MCP tool is called, then the REST route fails through `_require_feature_enabled()` in `backend/domains/intelligence/routes.py` with HTTP 403 and the MCP tool fails through `_require_feature_enabled()` in `backend/domains/intelligence/mcp.py` with `ToolError` code `FEATURE_DISABLED`.
7. Given no qualifying orders exist, when the API is called, then it returns zero totals and an empty drivers list instead of an error.

## Technical Notes

### Backend

- Extend `backend/domains/intelligence/schemas.py` with revenue-diagnosis models.
- Extend `backend/domains/intelligence/service.py` with `get_revenue_diagnosis()`.
- Extend `backend/domains/intelligence/routes.py` with `GET /api/v1/intelligence/revenue-diagnosis`.
- Extend `backend/domains/intelligence/mcp.py` with `intelligence_revenue_diagnosis`.
- Extend `backend/app/mcp_auth.py` with `intelligence_revenue_diagnosis` using the same `TOOL_SCOPES` precedent as `intelligence_product_affinity`: `frozenset({"orders:read"})`.
- Extend `backend/common/config.py` with `intelligence_revenue_diagnosis_enabled`.

### Frontend

- Extend `src/domain/intelligence/types.ts`, `src/lib/api/intelligence.ts`, and `src/domain/intelligence/hooks/useIntelligence.ts`.
- Mount the UI inside `src/pages/IntelligencePage.tsx` as another `SectionCard`, not a new top-level route.
- Add focused frontend tests under the existing intelligence test slice.

## Tasks / Subtasks

- [x] Task 1: Add revenue-diagnosis schemas, service orchestration, route, feature flag, and MCP tool in the intelligence domain.
- [x] Task 2: Implement aggregate-only and live-current-month loading paths using Story 20.3 rather than duplicating historical query logic.
- [x] Task 3: Implement price, volume, and mix decomposition with stable rounding and deterministic ordering.
- [x] Task 4: Add frontend contract, API client, hook, and `IntelligencePage` section.
- [x] Task 5: Add focused tests for arithmetic correctness, empty-state behavior, tie ordering, and feature-disabled responses.

## Dev Notes

- Keep the REST route available to the existing intelligence read roles: admin, owner, and sales.
- Rounding should happen after component calculations, not before, to avoid penny drift.
- If Story 20.3 is not yet implemented in code, stub a shared loader seam rather than re-encoding live history logic in a second place.

## Project Structure Notes

- Public ownership stays in intelligence.
- Shared aggregate access may live in `backend/domains/product_analytics/`, but the user-facing route, tool, hook, and UI belong in intelligence.

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `src/pages/IntelligencePage.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd backend && uv run pytest tests/domains/intelligence/test_revenue_diagnosis_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`
- `cd . && pnpm vitest run src/tests/intelligence/RevenueDiagnosisCard.test.tsx`
- Final focused diff review over the Story 20.4 implementation returned no findings.

### Completion Notes List

- Added revenue-diagnosis schemas and a new `get_revenue_diagnosis()` intelligence service that compares month-based windows, reuses Story 20.3 closed/live loading, and returns structured summary, component, and ranked driver evidence.
- Kept the public backend surface inside intelligence by adding `GET /api/v1/intelligence/revenue-diagnosis`, the `intelligence_revenue_diagnosis` MCP tool, a new intelligence feature flag, and MCP auth scope registration using `orders:read`.
- Implemented deterministic driver ordering by `abs(revenue_delta)`, then `abs(mix_effect)`, then `product_name`, then `product_id`, and preserved historical product/category labels from order-line snapshots rather than live product master fields.
- Added the frontend contract, API client, hook, and `RevenueDiagnosisCard` section inside `IntelligencePage` so the latest comparison window is visible without adding a new route.
- Added focused backend coverage for aggregate-only history, mixed live current-month windows, empty-state behavior, route feature gating, MCP feature gating, and MCP scope registration, plus focused frontend coverage for rendering, period refetch, and empty-state behavior.
- Validation passed on 2026-04-16 with `cd backend && uv run pytest tests/domains/intelligence/test_revenue_diagnosis_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q` (`68 passed in 1.96s`) and `cd . && pnpm vitest run src/tests/intelligence/RevenueDiagnosisCard.test.tsx` (`3 passed`).
- Final independent review after validation found no Story 20.4 findings.

### File List

- `backend/domains/intelligence/schemas.py`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `backend/app/mcp_auth.py`
- `backend/common/config.py`
- `backend/tests/domains/intelligence/test_revenue_diagnosis_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`
- `backend/tests/test_mcp_auth.py`
- `src/domain/intelligence/types.ts`
- `src/lib/api/intelligence.ts`
- `src/domain/intelligence/hooks/useIntelligence.ts`
- `src/domain/intelligence/components/RevenueDiagnosisCard.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/tests/intelligence/RevenueDiagnosisCard.test.tsx`

### Change Log

- 2026-04-16: Implemented Story 20.4 end to end across intelligence schemas, service orchestration, REST/MCP entrypoints, feature gating, frontend types/hooks/UI, and focused backend/frontend coverage.
- 2026-04-16: Locked the backend comparison windows to Story 20.3 aggregate/live loading, snapshot-based historical labels, and deterministic price/volume/mix driver ordering.
- 2026-04-16: Completed the final focused validation and no-findings review pass for the Story 20.4 slice.