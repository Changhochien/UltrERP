# Story 20.7: Customer Buying Behavior Extension

Status: done

## Story

As an AI agent or sales staff user,
I want segment-aware customer buying behavior inside the existing intelligence domain,
so that I can understand what dealers, end users, and unknown accounts typically buy and where cross-sell behavior differs by cohort.

## Problem Statement

Epic 19 already provides customer product profiles, risk signals, prospect gaps, and cohort-aware `customer_type` filtering. What is still missing is a segment-level view of how those cohorts buy across categories and seasons. Without that layer, sales staff can see individual customer behavior but cannot tell whether a pattern is normal for dealers, unusual for end users, or a cross-sell opportunity unique to a segment.

This story must extend the intelligence domain rather than create a second customer analytics silo.

## Solution

Extend the existing intelligence stack with a segment-level buying-behavior contract.

The response should return structured segment evidence first:

- selected `customer_type` or segment filter
- `customer_count`, `avg_revenue_per_customer`, `avg_order_count_per_customer`, `avg_categories_per_customer`
- `top_categories` with revenue, order count, customer count, and revenue share
- `cross_sell_opportunities` with anchor category, recommended category, anchor customer count, shared customer count, outside-segment anchor customer count, outside-segment shared customer count, segment penetration, outside-segment penetration, and lift score
- `buying_patterns` as a month-ordered series
- period metadata, `computed_at`, `data_basis`, and `window_is_partial`

The public surface stays in intelligence: service, route, MCP tool, hook, and UI panel. The implementation may compute on demand if a future `customer_monthly` table is still absent, but it must still follow Epic 20 snapshot and timestamp semantics.

Cross-sell evidence uses a fixed contract:

- `anchor_customer_count`: selected-segment customers with at least one qualifying purchase in the anchor category during the comparison window.
- `shared_customer_count`: selected-segment customers with at least one qualifying purchase in both the anchor and recommended categories during the comparison window.
- `segment_penetration = shared_customer_count / anchor_customer_count`.
- `outside_segment_anchor_customer_count`: qualifying customers outside the selected segment with at least one anchor-category purchase during the same window. When `customer_type = all`, treat this baseline as unavailable.
- `outside_segment_shared_customer_count`: qualifying customers outside the selected segment who purchased both categories during the same window.
- `outside_segment_penetration = outside_segment_shared_customer_count / outside_segment_anchor_customer_count` when the outside-segment anchor count is greater than zero; otherwise `outside_segment_penetration = 0`.
- `lift_score = segment_penetration / outside_segment_penetration`, rounded to 4 decimals, only when `outside_segment_penetration > 0`; otherwise `lift_score = null`.
- Emit a cross-sell row only when `anchor_customer_count >= 5` and `shared_customer_count >= 3`.

## Best-Practice Update

This section supersedes conflicting details below.

- Keep ownership in intelligence. Reuse `backend/domains/intelligence/service.py`, `backend/domains/intelligence/routes.py`, `backend/domains/intelligence/mcp.py`, `src/lib/api/intelligence.ts`, and `src/pages/IntelligencePage.tsx`.
- Reuse Story 19.9 `customer_type` semantics exactly: `dealer`, `end_user`, `unknown`, and `all`.
- For closed-month history, category and category-pair logic must use Story 20.1 snapshot fields and the Story 20.3 canonical analytics timestamp or shared loader. Do not group historical cohorts by live `Product.category` or live `Product.name`.
- Do not block this story on a future `customer_monthly` table. On-demand computation is acceptable if it still uses Epic 20 semantics.
- Narrative insights are secondary. The contract must lead with structured cohort evidence.
- If the selected window includes the open month, current-month results must come from live confirmed-or-later orders and the response must mark the window as partial.

## Acceptance Criteria

1. Given an authenticated intelligence request, when `GET /api/v1/intelligence/customer-buying-behavior` is called with `customer_type`, `period`, and optional `limit`, then the response returns segment summary metrics, top categories, cross-sell opportunities, and a month-ordered buying-pattern series.
2. Given `customer_type` is `dealer`, `end_user`, `unknown`, or `all`, when the service runs, then the same cohort filter is applied consistently across customer counts, category revenue, cross-sell support, and seasonality calculations.
3. Given `customer_monthly` does not exist yet, when the story is implemented, then the backend still returns the full contract by computing from transactional orders and order lines rather than blocking on a new precompute table.
4. Given closed historical months are included, when category or category-pair evidence is computed, then the service uses sale-time snapshot columns and the canonical analytics timestamp rather than live `Product.category` or `Order.created_at` windows.
5. Given `top_categories` are returned, when ties occur, then ordering is deterministic by revenue descending, customer count descending, then category ascending.
6. Given `cross_sell_opportunities` are returned, when lift is computed, then `segment_penetration = shared_customer_count / anchor_customer_count`, `outside_segment_penetration = outside_segment_shared_customer_count / outside_segment_anchor_customer_count`, and `lift_score = segment_penetration / outside_segment_penetration` rounded to 4 decimals whenever the outside-segment denominator is greater than zero.
7. Given a cross-sell candidate has `anchor_customer_count < 5` or `shared_customer_count < 3`, when the response is built, then that candidate is excluded from `cross_sell_opportunities`.
8. Given `outside_segment_anchor_customer_count = 0`, `outside_segment_penetration = 0`, or `customer_type = all`, when the response is built, then `lift_score = null` and those rows sort after numeric lift scores by shared customer count descending, then anchor category ascending, then recommended category ascending.
9. Given the feature is disabled, when the REST route or MCP tool is called, then the REST route fails through `_require_feature_enabled()` in `backend/domains/intelligence/routes.py` with HTTP 403 and the MCP tool fails through `_require_feature_enabled()` in `backend/domains/intelligence/mcp.py` with `ToolError` code `FEATURE_DISABLED`.
10. Given no qualifying customers or orders exist, when the API is called, then it returns zero-valued summary metrics and empty arrays instead of an error.

## Technical Notes

### Backend

- Extend `backend/domains/intelligence/schemas.py` with segment summary, top-category, cross-sell, and buying-pattern response models.
- Extend `backend/domains/intelligence/service.py` with `get_customer_buying_behavior()` that reuses Story 19.9 `customer_type` semantics and Story 20 snapshot/timestamp rules.
- Extend `backend/domains/intelligence/routes.py` with `GET /api/v1/intelligence/customer-buying-behavior`.
- Extend `backend/domains/intelligence/mcp.py` with `intelligence_customer_buying_behavior`.
- Extend `backend/app/mcp_auth.py` with `intelligence_customer_buying_behavior` using the same `TOOL_SCOPES` precedent as `intelligence_customer_product_profile`, `intelligence_customer_risk_signals`, and `intelligence_prospect_gaps`: `frozenset({"customers:read", "orders:read"})`.
- Extend `backend/common/config.py` with `intelligence_customer_buying_behavior_enabled`.
- Implement cross-sell math exactly as documented above, including the minimum support thresholds and `lift_score = null` behavior when the outside-segment baseline is unavailable.

### Frontend

- Extend `src/domain/intelligence/types.ts`, `src/lib/api/intelligence.ts`, and `src/domain/intelligence/hooks/useIntelligence.ts`.
- Mount the UI on `src/pages/IntelligencePage.tsx` as another evidence-first section.
- If customer-detail reuse is needed later, compose through `src/components/customers/CustomerAnalyticsTab.tsx` rather than creating a second domain.

## Tasks / Subtasks

- [x] Task 1: Add customer-buying-behavior schemas, service orchestration, route, feature flag, and MCP tool in the intelligence domain.
- [x] Task 2: Reuse the existing `customer_type` filtering pattern from Story 19.9 and implement deterministic ordering rules.
- [x] Task 3: Implement transactional fallback so the story is not blocked on a future `customer_monthly` aggregate.
- [x] Task 4: Add frontend types, API client, hook, and `IntelligencePage` section.
- [x] Task 5: Add focused tests for cohort filtering, snapshot semantics, deterministic sorting, empty states, and feature-disabled responses.

## Dev Notes

- This story extends intelligence, not customer CRUD and not a separate analytics workbench.
- The transactional fallback is acceptable only if it still uses Epic 20 snapshot and analytics-date semantics.
- Keep the UI actionable and compact; avoid dense nested multi-column analytics blocks in constrained layouts.

## Project Structure Notes

- Public ownership stays in intelligence.
- Customer-detail reuse should happen through the existing customer analytics tab composition path.

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `src/domain/intelligence/hooks/useIntelligence.ts`
- `src/pages/IntelligencePage.tsx`
- `src/components/customers/CustomerAnalyticsTab.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/domains/intelligence/test_customer_buying_behavior_service.py tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py -q`
- `cd /Volumes/2T_SSD_App/Projects/UltrERP && pnpm vitest run src/tests/intelligence/CustomerBuyingBehaviorCard.test.tsx`
- VS Code diagnostics over touched backend/frontend files returned no errors.

### Completion Notes List

- Added transactional customer-buying-behavior schemas and `get_customer_buying_behavior()` in the intelligence domain, reusing Story 19.9 `customer_type` semantics and sale-time line snapshots so closed-month cohort evidence does not drift with live product category edits.
- Exposed the new surface through `GET /api/v1/intelligence/customer-buying-behavior`, the `intelligence_customer_buying_behavior` MCP tool, the `intelligence_customer_buying_behavior_enabled` feature flag, and a matching MCP auth scope of `frozenset({"customers:read", "orders:read"})`.
- Mounted a compact `CustomerBuyingBehaviorCard` on the existing intelligence page with segment filters, period toggles, top-category evidence, cross-sell lift rows, and month-ordered buying-pattern cards.
- Validated focused backend and frontend coverage for cohort filtering, snapshot semantics, deterministic top-category and cross-sell ordering, null lift handling for `customer_type = all`, empty states, and feature-disabled REST/MCP behavior.

### File List

- `backend/common/config.py`
- `backend/app/mcp_auth.py`
- `backend/domains/intelligence/schemas.py`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `backend/tests/domains/intelligence/test_customer_buying_behavior_service.py`
- `backend/tests/domains/intelligence/test_routes.py`
- `backend/tests/test_mcp_intelligence.py`
- `backend/tests/test_mcp_auth.py`
- `src/domain/intelligence/types.ts`
- `src/lib/api/intelligence.ts`
- `src/domain/intelligence/hooks/useIntelligence.ts`
- `src/domain/intelligence/components/CustomerBuyingBehaviorCard.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/tests/intelligence/CustomerBuyingBehaviorCard.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`