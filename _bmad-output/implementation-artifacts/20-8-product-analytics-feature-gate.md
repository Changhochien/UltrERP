# Story 20.8: Product Analytics Feature Gate

Status: done

## Story

As an admin or owner,
I want Epic 20 product-sales analytics to follow the existing UltrERP access-control stack,
so that only authorized users and MCP clients can reach the new analytics capabilities while inventory and intelligence extensions keep their owning-domain gates.

## Problem Statement

Epic 20 adds a shared backend analytics foundation plus concrete user-facing surfaces in the intelligence and inventory domains. In this repo, access control is already enforced in four layers: backend settings booleans, REST route-level auth and 403 checks, MCP scope and `ToolError` enforcement, and frontend role-to-feature gating through existing protected routes. If Epic 20 skips any one of those layers, the UI can hide a feature while the API still exposes it, or MCP can call a tool that the route layer would correctly reject.

The story must match repo reality. UltrERP does not have a backend per-user feature table, and the MCP scope vocabulary does not currently include a product-specific scope.

## Solution

Gate concrete Epic 20 capabilities in their owning domains rather than inventing a speculative new public analytics silo.

For v1:

- Story 20.4 revenue diagnosis and Story 20.6 product performance stay in intelligence and use intelligence-style feature toggles, route checks, MCP tool checks, and existing `intelligence` frontend access.
- Story 20.5 planning support stays in inventory and uses inventory route and page protection plus a per-surface backend toggle if a new endpoint ships.
- Story 20.7 customer buying behavior stays in intelligence and follows the same pattern as other intelligence widgets.
- The shared `product_analytics` backend foundation from Story 20.3 remains backend-only and does not require a public route or new frontend AppFeature unless a real standalone page is deliberately added later.

## Best-Practice Update

This section supersedes conflicting details below.

- Follow the live repo gate stack exactly: frontend role-to-feature mapping, REST role auth plus route-level 403 helpers, MCP scope enforcement, and per-capability settings booleans.
- Do not invent a backend `user.features` table, dynamic feature registry, or new per-user feature-management subsystem.
- Do not introduce a new `products:read` MCP scope. Use only the repo's current scope vocabulary.
- Gate only concrete Epic 20 capabilities that actually ship. Do not create dead navigation, dead routes, or placeholder tools.
- If a standalone `/product-analytics` page is added later, it must use the same protected-route and settings patterns, but that is not required for v1.

## Acceptance Criteria

1. Given a request to an Epic 20 intelligence route without authentication, when the request reaches the route, then the existing auth dependency returns a 401 response.
2. Given an authenticated user whose role does not satisfy the owning-domain read dependency, when that user calls an Epic 20 analytics REST endpoint, then a 403 response is returned by the existing role-based auth mechanism.
3. Given `intelligence_revenue_diagnosis_enabled = false`, when the revenue-diagnosis REST route or MCP tool is called, then the REST route returns HTTP 403 via `_require_feature_enabled()` in `backend/domains/intelligence/routes.py`, the MCP tool returns `ToolError` code `FEATURE_DISABLED` via `_require_feature_enabled()` in `backend/domains/intelligence/mcp.py`, and the `IntelligencePage` hides or suppresses that section.
4. Given `intelligence_product_performance_enabled = false`, when the product-performance REST route or MCP tool is called, then the REST route returns HTTP 403 via `_require_feature_enabled()` in `backend/domains/intelligence/routes.py`, the MCP tool returns `ToolError` code `FEATURE_DISABLED` via `_require_feature_enabled()` in `backend/domains/intelligence/mcp.py`, and the `IntelligencePage` hides or suppresses that section.
5. Given Story 20.5 ships a new inventory planning-support endpoint and that capability is disabled, when the endpoint is called, then the inventory route returns HTTP 403 with a feature-specific detail and the inventory UI hides that section behind the existing `usePermissions().canAccess("inventory")` gate while other inventory features remain available.
6. Given `intelligence_customer_buying_behavior_enabled = false`, when the customer-buying-behavior REST route or MCP tool is called, then the REST route returns HTTP 403 via `_require_feature_enabled()` in `backend/domains/intelligence/routes.py`, the MCP tool returns `ToolError` code `FEATURE_DISABLED` via `_require_feature_enabled()` in `backend/domains/intelligence/mcp.py`, and the `IntelligencePage` hides or suppresses that section.
7. Given an MCP caller lacks the scope required by an Epic 20 tool, when that tool is called, then `MCPAuthProvider.authorize()` in `backend/app/mcp_auth.py` fails the call with `INSUFFICIENT_SCOPE`, reusing only the existing `TOOL_SCOPES` atoms already present in the repo: `orders:read`, `customers:read`, and `inventory:read`.
8. Given Story 20.5 remains inventory-owned and Stories 20.4, 20.6, and 20.7 remain intelligence-owned, when those surfaces are rendered or called, then they continue to use their owning-domain frontend features and route wiring rather than a speculative new top-level `product_analytics` route.

## Technical Notes

- Add per-capability booleans in `backend/common/config.py` for the actual owning-domain surfaces that ship first.
- Mirror `_require_feature_enabled()` already used in `backend/domains/intelligence/routes.py` and `backend/domains/intelligence/mcp.py` for intelligence-owned disabled-feature handling.
- Register new MCP tool scopes in `backend/app/mcp_auth.py` only for concrete tools and keep them limited to the existing `TOOL_SCOPES` atoms: `orders:read`, `customers:read`, and `inventory:read`.
- If a new inventory planning-support endpoint ships, guard it in `backend/domains/inventory/routes.py` and keep frontend visibility inside the existing inventory feature.
- Keep frontend visibility inside the existing `usePermissions().canAccess("intelligence")` and `usePermissions().canAccess("inventory")` gates in `src/hooks/usePermissions.ts`. Do not add a new frontend `AppFeature` or top-level route unless a real shared page is deliberately introduced.

## Tasks / Subtasks

- [x] Task 1: Add per-capability settings booleans for the concrete Epic 20 surfaces that ship first.
- [x] Task 2: Add owning-domain REST route gating using existing role dependencies and route-level 403 helpers.
- [x] Task 3: Add MCP scope registration and disabled-feature `ToolError` behavior for concrete Epic 20 tools only.
- [x] Task 4: Hide or suppress disabled Epic 20 sections inside existing intelligence and inventory pages.
- [x] Task 5: Add focused backend and frontend auth tests for unauthorized access, disabled features, insufficient scope, and visibility behavior.

## Dev Notes

- `backend/common/config.py` already uses per-widget booleans for intelligence capabilities instead of one coarse switch.
- `backend/app/mcp_auth.py` already defines `TOOL_SCOPES` and role-derived scopes, but there is no `products:read` scope anywhere in the current repo.
- `backend/domains/intelligence/routes.py` is the closest local example of route-level feature toggles paired with read-role enforcement.
- Keep this story synchronized with the final ownership split of Stories 20.4-20.7.

## Project Structure Notes

- Apply the gate where the public surface lives: intelligence or inventory.
- Keep the backend-only `product_analytics` foundation private unless a real shared page and route are intentionally added later.

## References

- `../planning-artifacts/epic-20.md`
- `../planning-artifacts/research/domain-epic-20-product-sales-analytics-research-2026-04-15.md`
- `../implementation-artifacts/19-7-intelligence-feature-gate.md`
- `backend/common/config.py`
- `backend/app/mcp_auth.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `backend/domains/inventory/routes.py`
- `src/hooks/usePermissions.ts`
- `src/App.tsx`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd /Volumes/2T_SSD_App/Projects/UltrERP/backend && uv run pytest tests/domains/intelligence/test_routes.py tests/test_mcp_intelligence.py tests/test_mcp_auth.py tests/domains/inventory/test_planning_support.py -q`
- `pnpm --dir /Volumes/2T_SSD_App/Projects/UltrERP exec vitest run src/tests/intelligence/RevenueDiagnosisCard.test.tsx src/tests/intelligence/ProductPerformanceCard.test.tsx src/tests/intelligence/CustomerBuyingBehaviorCard.test.tsx src/domain/inventory/components/AnalyticsTab.test.tsx`
- VS Code diagnostics over the touched backend/frontend files returned no errors.

### Completion Notes List

- Story corrected to gate concrete owning-domain capabilities instead of inventing a shared public analytics silo.
- Added the missing `inventory_planning_support_enabled` backend toggle and route-level 403 handling so the Story 20.5 planning-support endpoint now follows the same per-capability gate stack as the intelligence-owned Epic 20 surfaces.
- Reused the existing intelligence route and MCP feature-disabled behavior for Stories 20.4, 20.6, and 20.7, and surfaced those disabled-feature details through the frontend fetch layer instead of inventing a new frontend feature registry.
- Suppressed the Revenue Diagnosis, Product Performance, Customer Buying Behavior, and Planning Support cards when their owning-domain routes report disabled-feature 403s, while preserving the surrounding intelligence and inventory surfaces.
- Added focused backend and frontend regressions for the disabled planning-support route and for disabled-feature suppression across the affected Epic 20 cards.

### File List

- `backend/common/config.py`
- `backend/domains/inventory/routes.py`
- `backend/tests/domains/inventory/test_planning_support.py`
- `src/lib/api/intelligence.ts`
- `src/lib/featureGates.ts`
- `src/domain/intelligence/components/RevenueDiagnosisCard.tsx`
- `src/domain/intelligence/components/ProductPerformanceCard.tsx`
- `src/domain/intelligence/components/CustomerBuyingBehaviorCard.tsx`
- `src/domain/inventory/components/PlanningSupportCard.tsx`
- `src/tests/intelligence/RevenueDiagnosisCard.test.tsx`
- `src/tests/intelligence/ProductPerformanceCard.test.tsx`
- `src/tests/intelligence/CustomerBuyingBehaviorCard.test.tsx`
- `src/domain/inventory/components/AnalyticsTab.test.tsx`