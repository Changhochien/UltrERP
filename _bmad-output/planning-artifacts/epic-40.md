# Epic 40: Intelligence Service Modularization and Architecture Hardening

## Epic Goal

Decompose the intelligence backend monolith into feature-scoped service modules behind a stable compatibility facade so the existing intelligence app can keep shipping without route, MCP, or frontend contract churn.

## Business Value

- Intelligence features become cheaper to change because each use case gets a bounded implementation surface.
- Regression risk drops because transactional analytics and aggregate-backed analytics stop sharing one 2600-line implementation file.
- Future intelligence features can reuse explicit helper seams instead of copying date, Decimal, or category-filter logic.
- The app keeps its current mounted experience while backend architecture catches up with the feature set already delivered.

## Current State Summary

- The backend app mounts the intelligence API through `backend/app/main.py` and `backend/domains/intelligence/routes.py`.
- MCP tools for the same domain are wired through `backend/domains/intelligence/mcp.py`.
- The human UI composes the intelligence workspace in `src/pages/IntelligencePage.tsx`.
- `backend/domains/intelligence/service.py` currently contains eight public use cases, private dataclasses, helper math/date logic, SQL composition, and aggregate-loading logic in one file.
- The test suite is already mostly feature-split, which gives the restructure a natural implementation sequence.

## Architecture Decision

### Core Decision

Adopt a feature-scoped intelligence service package with a compatibility facade:

1. Keep `backend/domains/intelligence/service.py` as the stable public import surface during the epic.
2. Move pure helpers, shared constants, and private dataclasses into a shared support layer that does not import feature modules.
3. Extract feature implementations into dedicated modules under `backend/domains/intelligence/services/`.
4. Separate transactional analytics from aggregate-backed analytics so changes in one slice do not force edits across the whole domain.

### Filesystem Target

- `backend/domains/intelligence/service.py` — compatibility facade only
- `backend/domains/intelligence/services/__init__.py`
- `backend/domains/intelligence/services/shared/` — pure helper and support modules
- `backend/domains/intelligence/services/affinity.py`
- `backend/domains/intelligence/services/customer_profile.py`
- `backend/domains/intelligence/services/risk_signals.py`
- `backend/domains/intelligence/services/prospect_gaps.py`
- `backend/domains/intelligence/services/buying_behavior.py`
- `backend/domains/intelligence/services/category_trends.py`
- `backend/domains/intelligence/services/market_opportunities.py`
- `backend/domains/intelligence/services/revenue_diagnosis.py`
- `backend/domains/intelligence/services/product_performance.py`

### Guardrails

- Preserve all public REST, MCP, and frontend contracts for the duration of the epic.
- Do not add new intelligence endpoints, tool names, feature flags, or frontend routes in this epic.
- Do not mix schema redesign into the first extraction pass unless the monolith split is blocked without it.
- Market opportunities should stop depending on the public `get_category_trends()` entrypoint; share lower-level loaders or pure builders instead.
- The restructure should be mechanical and test-led, not an excuse to change business thresholds or ranking rules.

## Scope

- Introduce the intelligence service package and compatibility facade.
- Consolidate duplicated pure helpers and shared private dataclasses.
- Extract each existing public intelligence use case into a dedicated module.
- Realign focused backend tests to feature ownership where helpful.
- Reduce `backend/domains/intelligence/service.py` to facade-only code by the end of the epic.

## Non-Goals

- New intelligence metrics, endpoints, or UI sections.
- Frontend design changes to `IntelligencePage`.
- A repo-wide rename from `service.py` to `services.py` or similar.
- A speculative repository or CQRS layer for intelligence.
- Breaking changes to `backend/domains/intelligence/schemas.py` or current MCP tool names.

## Validation Strategy

- Use focused backend pytest slices per feature extraction instead of one giant rerun after all moves.
- Keep `routes.py` and `mcp.py` importing through the compatibility facade until the epic is complete.
- Verify the facade behavior with focused route and MCP tests whenever the import graph changes.
- Use a final architectural grep or diff review to confirm `service.py` is facade-only when Epic 40 completes.

## Dependency and Phase Order

1. Story 40.1 establishes the compatibility facade and shared support layer.
2. Story 40.2 extracts the low-coupling affinity and customer-profile slice.
3. Story 40.3 extracts the customer-risk, prospect-gap, and buying-behavior slice.
4. Story 40.4 extracts category trends and market opportunities while removing the current public-service dependency between them.
5. Story 40.5 extracts the aggregate-backed analytics slice and retires the remaining monolith implementation.

---

## Story 40.1: Intelligence Service Facade and Shared Support Layer

As a backend developer,
I want a compatibility facade and shared support layer for intelligence services,
so that feature extraction can proceed without breaking the mounted app surface.

**Acceptance Criteria:**

1. Given callers currently import `domains.intelligence.service`, when Story 40.1 lands, then those imports still resolve without caller changes.
2. Given shared pure helpers exist in the monolith, when they are extracted, then duplicated date/window helpers are consolidated into one authoritative implementation.
3. Given later stories need reusable support logic, when they import from the shared layer, then that layer does not depend on feature modules.

---

## Story 40.2: Affinity and Customer Profile Service Extraction

As a backend developer,
I want the affinity and customer-profile read models extracted into dedicated modules,
so that low-coupling intelligence features stop sharing incidental implementation state with unrelated analytics.

**Acceptance Criteria:**

1. Given Story 40.1 is complete, when Story 40.2 lands, then `get_product_affinity_map()`, `build_empty_customer_product_profile()`, and `get_customer_product_profile()` are implemented outside `service.py` and re-exported through it.
2. Given the focused service, route, and MCP tests run, when the extraction is complete, then ordering, dormant detection, confidence, and empty-state behavior remain unchanged.
3. Given the extracted modules are reviewed, when their imports are inspected, then they depend only on shared support modules and owning collaborators.

---

## Story 40.3: Risk, Prospect, and Buying Behavior Service Extraction

As a backend developer,
I want the customer-risk, prospect-gap, and segment buying-behavior logic extracted into dedicated modules,
so that customer-cohort analytics can evolve without reopening the entire intelligence monolith.

**Acceptance Criteria:**

1. Given Story 40.1 is complete, when Story 40.3 lands, then `get_customer_risk_signals()`, `get_prospect_gaps()`, and `get_customer_buying_behavior()` live in dedicated modules and are re-exported through `service.py`.
2. Given Story 19.9 and Story 20.7 semantics already ship, when the extraction is complete, then `customer_type` handling, excluded-category filtering, cross-sell thresholds, and deterministic ordering remain unchanged.
3. Given the new module layout is reviewed, when module-local helpers are inspected, then customer-cohort internals no longer live in the facade file.

---

## Story 40.4: Category Trends and Market Opportunities Decoupling

As a backend developer,
I want category trends and market opportunities extracted into separate modules with a shared lower-level seam,
so that market-signal composition stops depending on another public service entrypoint.

**Acceptance Criteria:**

1. Given Story 40.1 is complete, when Story 40.4 lands, then `get_category_trends()` and `get_market_opportunities()` are implemented outside `service.py` and re-exported through it.
2. Given market opportunities currently reuse category-trend behavior, when the refactor lands, then they share a lower-level loader or pure builder instead of calling the public `get_category_trends()` entrypoint.
3. Given the focused test suite runs, when the story is complete, then trend ranking, support floors, and signal ordering remain unchanged.

---

## Story 40.5: Revenue Diagnosis and Product Performance Service Extraction

As a backend developer,
I want the aggregate-backed intelligence features extracted into dedicated modules,
so that the heaviest analytics logic can share one explicit support seam and the old monolith can collapse into a facade only.

**Acceptance Criteria:**

1. Given Stories 40.1 through 40.4 are complete, when Story 40.5 lands, then `get_revenue_diagnosis()` and `get_product_performance()` are implemented outside `service.py` and re-exported through it.
2. Given the aggregate-backed slice contains duplicated month or window logic today, when Story 40.5 is complete, then that logic is consolidated into shared support rather than duplicated across feature modules.
3. Given the focused backend suite runs, when the extraction is complete, then partial-current-month handling, snapshot label resolution, lifecycle precedence, and deterministic ordering remain unchanged.
4. Given Epic 40 is complete, when `backend/domains/intelligence/service.py` is inspected, then it contains facade-only imports and no remaining feature implementation bodies.

## References

- `backend/app/main.py`
- `backend/domains/intelligence/service.py`
- `backend/domains/intelligence/routes.py`
- `backend/domains/intelligence/mcp.py`
- `backend/tests/domains/intelligence/test_service.py`
- `backend/tests/domains/intelligence/test_customer_buying_behavior_service.py`
- `backend/tests/domains/intelligence/test_product_performance_service.py`
- `backend/tests/domains/intelligence/test_revenue_diagnosis_service.py`
- `src/pages/IntelligencePage.tsx`