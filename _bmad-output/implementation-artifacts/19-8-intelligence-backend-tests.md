# Story 19.8: Intelligence Backend Test Coverage

Status: revised-ready-for-dev

## Story

As a **developer**,
I want unit tests for the intelligence services
So that I can refactor safely and verify correctness of the aggregation logic.

## Problem Statement

The intelligence aggregation logic is non-trivial — Jaccard affinity scores, period-over-period deltas, dormant classification, risk signal classification — and will be called by AI agents making business decisions. Without test coverage, refactoring the aggregation SQL or service logic risks introducing subtle correctness bugs (e.g., off-by-one period boundaries, incorrect churn/new-customer counting, wrong Decimal precision).

## Solution

Add `pytest` async unit tests for all 6 intelligence service functions using SQLAlchemy's async `AsyncSession` with a mocked in-memory or SQLite backend. Use the existing test fixture patterns from `conftest.py` and create intelligence-specific fixtures for customers, orders, order_lines, and products with known categories and dates.

## Best-Practice Update

This section supersedes conflicting details below.

- Do not limit this story to happy-path math checks. Cover tenant isolation, scope rejection, deterministic sorting, sparse-data handling, and category exclusion rules.
- Prefer DB-backed fixtures plus pure helper tests over heavily mocked `AsyncSession` behavior for the critical aggregation paths.
- Zero-baseline cases are first-class tests. The suite should verify that the implementation does not emit fake `100%` growth where the contract says `newly_active`, `insufficient_history`, nullable deltas, or equivalent support metadata.
- Prospecting and market-opportunity tests should assert transparency: score components, support counts, and deferred / omitted weak signals.
- This story should also validate MCP response-shape stability and the fact that narrative fields remain secondary to structured evidence.

## Acceptance Criteria

**AC1: `get_product_affinity_map` Jaccard score is correct**
**Given** customer A ordered products P1, P2; customer B ordered P1, P2, P3; customer C ordered P1
**When** `get_product_affinity_map(session, tenant_id, min_shared=1, limit=50)` is called
**Then** the pair (P1, P2) has `shared_customer_count = 2` (A and B)
**And** `affinity_score = 2 / (2 + 2 - 2) = 1.0` (P1 and P2 co-ordered by every customer who bought either)
**And** the pair (P1, P3) has `shared_customer_count = 1` (only B)
**And** results are sorted by `affinity_score` descending

**AC2: `get_product_affinity_map` Jaccard formula**
**Given** customer A ordered P1 in 3 orders, P2 in 2 orders; customer B ordered P1 in 1 order, P2 in 2 orders (no shared customer in this setup, different scenario)
**When** affinity is computed
**Then** `affinity_score = shared_customers / (unique_customers_product_a + unique_customers_product_b - shared_customers)` (standard Jaccard)
**And** `overlap_pct = shared_customers / min(unique_customers_product_a, unique_customers_product_b) * 100`

**AC3: `get_category_trends` revenue_delta_pct formula**
**Given** a category with `current_period_revenue = 150000` and `prior_period_revenue = 100000`
**When** `get_category_trends(period="last_90d")` is called
**Then** `revenue_delta_pct = (150000 - 100000) / 100000 * 100 = 50.0`

**AC4: `get_category_trends` new_customer_count**
**Given** 5 customers in a category: C1 (first order 100 days ago, still buying), C2 (first order 60 days ago), C3 (first order 30 days ago), C4 (first order 20 days ago), C5 (first order 10 days ago)
**When** `get_category_trends(period="last_90d")` is called
**Then** `new_customer_count = 3` (C3, C4, C5 — first order within current 90d period)

**AC5: `get_category_trends` churned_customer_count**
**Given** 5 customers in a category: C1 (ordered in prior period, not in current), C2 (ordered in prior period, not in current), C3 (ordered in both periods), C4 (first order in current period), C5 (ordered in both periods)
**When** `get_category_trends(period="last_90d")` is called
**Then** `churned_customer_count = 2` (C1, C2 — bought in prior period but not in current)

**AC6: `get_customer_product_profile` is_dormant = true**
**Given** a customer whose last order was 65 days ago
**When** `get_customer_product_profile(session, tenant_id, customer_id)` is called
**Then** `is_dormant = True`

**AC7: `get_customer_product_profile` is_dormant = false**
**Given** a customer whose last order was 30 days ago
**When** `get_customer_product_profile(session, tenant_id, customer_id)` is called
**Then** `is_dormant = False`

**AC8: `get_customer_product_profile` frequency_trend = increasing**
**Given** a customer with 8 orders in the last 3 months and 4 orders in the prior 3 months
**When** `get_customer_product_profile(...)` is called
**Then** `frequency_trend = "increasing"` (8 > 4 * 1.20 = 4.8)

**AC9: `get_customer_product_profile` frequency_trend = declining**
**Given** a customer with 3 orders in the last 3 months and 8 orders in the prior 3 months
**When** `get_customer_product_profile(...)` is called
**Then** `frequency_trend = "declining"` (3 < 8 * 0.80 = 6.4)

**AC10: `get_customer_product_profile` frequency_trend = stable**
**Given** a customer with 5 orders in the last 3 months and 5 orders in the prior 3 months
**When** `get_customer_product_profile(...)` is called
**Then** `frequency_trend = "stable"` (5 is not > 6.0 and not < 4.0)

**AC11: `get_customer_product_profile` new_categories**
**Given** a customer who bought category "LED Displays" for the first time 45 days ago, and has bought "Power Supplies" for 200 days
**When** `get_customer_product_profile(...)` is called
**Then** `"LED Displays"` is in the `new_categories` list
**And** `"Power Supplies"` is NOT in the `new_categories` list

**AC12: `get_customer_risk_signals` growing classification**
**Given** a customer with `revenue_current = 132000` and `revenue_prior = 100000`
**When** `get_customer_risk_signals(...)` is called
**Then** the customer's status is `growing` (132000 > 100000 * 1.20 = 120000)

**AC13: `get_customer_risk_signals` at_risk classification**
**Given** a customer with `revenue_current = 75000` and `revenue_prior = 100000`
**When** `get_customer_risk_signals(...)` is called
**Then** the customer's status is `at_risk` (75000 < 100000 * 0.80 = 80000)

**AC14: `get_customer_risk_signals` dormant classification**
**Given** a customer with no orders in the last 65 days
**When** `get_customer_risk_signals(...)` is called
**Then** the customer's status is `dormant`

**AC15: `get_customer_risk_signals` new classification**
**Given** a customer whose first order was 45 days ago
**When** `get_customer_risk_signals(...)` is called
**Then** the customer's status is `new`

**AC16: `get_customer_risk_signals` stable classification**
**Given** a customer with `revenue_current = 95000` and `revenue_prior = 100000`
**When** `get_customer_risk_signals(...)` is called
**Then** the customer's status is `stable` (not growing, not at_risk, not dormant, not new)

**AC17: `get_prospect_gaps` returns transparent score evidence**
**Given** a target category with existing buyers and qualified non-buyers
**When** `get_prospect_gaps(...)` is called
**Then** each returned prospect includes `score_components`, `reason_codes`, and `confidence`
**And** the default machine-facing payload omits contact phone and email

**AC18: `get_market_opportunities` emits only stabilized v1 signals**
**Given** market opportunities are computed for a tenant
**When** `get_market_opportunities(...)` is called
**Then** `concentration_risk` is emitted when thresholds are met
**And** `category_growth` is emitted only when Story 19.2 support floors are met
**And** deferred signals remain omitted until validated upstream

## Technical Notes

### File Locations (create these)

- `backend/tests/domains/intelligence/__init__.py` — package init (empty file)
- `backend/tests/domains/intelligence/test_service.py` — all 6 test functions
- `backend/tests/domains/intelligence/conftest.py` — optional shared fixtures (customers, orders, products)

### Key Implementation Details

**Package init** (`backend/tests/domains/intelligence/__init__.py`):
```python
"""Intelligence domain tests."""
```

**Test class structure** — use a single `TestIntelligenceServices` class with individual test methods, or separate classes per service function. Follow the pattern used in `backend/tests/domains/inventory/`.

**Async test setup** — use `@pytest.mark.asyncio` decorator and `pytest-asyncio` for all async tests. Example from `backend/tests/domains/inventory/`:
```python
import pytest
from pytest_asyncio import fixture

@pytest.mark.asyncio
async def test_get_product_affinity_map(db_session, tenant_fixture):
    # test body
```

**Service function signatures** (to be tested):
```python
# backend/domains/intelligence/service.py

async def get_product_affinity_map(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    min_shared: int = 3,
    limit: int = 50,
) -> ProductAffinityMap:
    ...

async def get_category_trends(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> CategoryTrends:
    ...

async def get_customer_product_profile(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> CustomerProductProfile:
    ...

async def get_customer_risk_signals(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status: Literal["all", "growing", "at_risk", "dormant", "new", "stable"] = "all",
    limit: int = 50,
) -> list[CustomerRiskSignals]:
    ...

async def get_prospect_gaps(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category: str,
    *,
    limit: int = 20,
) -> ProspectGaps:
    ...

async def get_market_opportunities(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period: Literal["last_30d", "last_90d", "last_12m"] = "last_90d",
) -> MarketOpportunities:
    ...
```

**Period boundary calculation** — use `date.today()` as the reference. For `last_90d`, the current period is `[today - 90 days, today]`, the prior period is `[today - 180 days, today - 90 days]`. Use the same logic in tests and implementation.

**Jaccard affinity formula**:
```
affinity_score = shared_customer_count / (customers_who_bought_A + customers_who_bought_B - shared_customer_count)
overlap_pct = shared_customer_count / min(customers_who_bought_A, customers_who_bought_B) * 100
```

**Churned customer formula**: customers who appear in the prior period's orders but NOT in the current period's orders for a given category.

**New customer formula**: customers whose FIRST order ever (across all time) falls within the current period for a given category.

**Dormant formula**: `last_order_date < today - 60 days`.

**Risk classification thresholds**:
- `growing`: `revenue_current > revenue_prior * 1.20`
- `at_risk`: `revenue_current < revenue_prior * 0.80`
- `dormant`: `last_order_date < today - 60 days`
- `new`: `first_order_date >= today - 90 days`
- `stable`: all others

**Frequency trend thresholds**:
- `increasing`: `order_count_3m > order_count_prior_3m * 1.20`
- `declining`: `order_count_3m < order_count_prior_3m * 0.80`
- `stable`: everything else

**Test data setup pattern** — create fixture customers/orders in a helper or at the top of the test file. Use `uuid.uuid4()` for IDs and `date.today() - timedelta(days=N)` for dates.

### Test Data Fixtures (inline, no external DB needed)

Build test data inline in each test using raw SQL or SQLAlchemy model insertions. Keep tests self-contained so they run in isolation.

Example test data for affinity:
```python
today = date.today()
p1, p2, p3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
c1, c2, c3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
# C1: ordered P1 (order 1) and P2 (order 1)
# C2: ordered P1, P2, P3 (single order with all 3)
# C3: ordered P1 only
```

Example for risk signals:
```python
# Growing customer: current revenue 130k, prior 100k
# At-risk customer: current 75k, prior 100k
# Dormant customer: last order 70 days ago
# New customer: first order 45 days ago
# Stable customer: current 95k, prior 100k
```

### Critical Warnings

- Do **not** use real database dates in assertions — always use controlled relative dates (e.g., `date.today() - timedelta(days=65)` for dormant)
- Do **not** hard-code the period boundary as a fixed date — compute it relative to `date.today()` so tests don't fail next year
- Do **not** test `get_prospect_gaps` or `get_market_opportunities` with opaque or unstable heuristics — assert deterministic score components, deferred-signal omission, and response-shape stability instead
- Do **not** forget to call `async with session.begin()` before running service functions (the service will do this internally, but if testing at the service layer directly, manage the transaction)
- The `Decimal` type must be used for financial values — do not mix `float` and `Decimal` in assertions
- Add explicit tests for tenant isolation, scope rejection, and deterministic secondary sort order because AI agents will consume these endpoints directly

## Tasks / Subtasks

- [ ] **Task 1: Create test package and conftest** (all ACs)
  - [ ] Create `backend/tests/domains/intelligence/__init__.py`
  - [ ] Create `backend/tests/domains/intelligence/conftest.py` with shared fixtures:
    - `tenant_fixture` — tenant UUID for all tests
    - `product_fixtures` — 5 products across 3 categories with known IDs
    - `customer_fixtures` — 8 customers with known order history patterns
    - `order_fixture` helper to create orders with order_lines

- [ ] **Task 2: Test `get_product_affinity_map`** (AC1, AC2)
  - [ ] Test Jaccard formula with 2-product shared customer
  - [ ] Test Jaccard with no shared customers (score = 0)
  - [ ] Test sorting is descending by affinity_score
  - [ ] Test `min_shared` filter excludes pairs below threshold
  - [ ] Test `limit` caps results

- [ ] **Task 3: Test `get_category_trends`** (AC3, AC4, AC5)
  - [ ] Test `revenue_delta_pct` formula for growing category (+50%)
  - [ ] Test `revenue_delta_pct` formula for declining category (-30%)
    - [ ] Test zero-baseline categories return support metadata rather than fabricated `100%` growth
  - [ ] Test `new_customer_count` correctly identifies first-time category buyers in current period
  - [ ] Test `churned_customer_count` correctly identifies prior-period buyers not in current period
  - [ ] Test `trend` classification: growing (>10%), declining (<-10%), stable

- [ ] **Task 4: Test `get_customer_product_profile`** (AC6–AC11)
  - [ ] Test `is_dormant = True` when last order 65+ days ago
  - [ ] Test `is_dormant = False` when last order 30 days ago
  - [ ] Test `frequency_trend = "increasing"` when 3m orders > prior 3m * 1.20
  - [ ] Test `frequency_trend = "declining"` when 3m orders < prior 3m * 0.80
  - [ ] Test `frequency_trend = "stable"` in between
  - [ ] Test `new_categories` contains only categories first purchased in last 90 days

- [ ] **Task 5: Test `get_customer_risk_signals`** (AC12–AC16)
  - [ ] Test `growing` classification when revenue_current > revenue_prior * 1.20
  - [ ] Test `at_risk` classification when revenue_current < revenue_prior * 0.80
  - [ ] Test `dormant` classification when no orders in 60+ days
  - [ ] Test `new` classification when first order in last 90 days
  - [ ] Test `stable` classification for everything else
  - [ ] Test `status` filter parameter returns only matching accounts
  - [ ] Test `limit` parameter caps result count

- [ ] **Task 6: Test `get_prospect_gaps` and `get_market_opportunities` transparency rules** (AC17, AC18)
  - [ ] Test `get_prospect_gaps` returns `score_components`, `reason_codes`, and `confidence`
  - [ ] Test default `get_prospect_gaps` payload omits contact PII
  - [ ] Test `get_market_opportunities` emits `concentration_risk` when thresholds are met
  - [ ] Test `get_market_opportunities` omits deferred signals in v1
  - [ ] Test optional `category_growth` only appears when support floors are satisfied

- [ ] **Task 7: Run and verify all tests pass**
  - [ ] Run `pytest backend/tests/domains/intelligence/ -v`
  - [ ] Fix any failures due to API mismatches with actual service implementations
  - [ ] Verify no warnings about missing fixtures

## Dev Notes

### Repo Reality

- `backend/tests/conftest.py` sets `JWT_SECRET` and `PYTEST_RUNNING` env vars before imports
- `pytest-asyncio` is used for async tests — look for `@pytest.mark.asyncio` in existing test files
- `AsyncSession` is the SQLAlchemy session type used — mock it with `AsyncMock` or use a real async session against SQLite
- No `backend/domains/intelligence/` module exists yet — tests should import from `domains.intelligence.service` which will be created in stories 19.1–19.6
- Existing domain test patterns at `backend/tests/domains/inventory/test_reorder_point_calculation.py` for reference
- Decimal values in assertions should use `pytest.approx` for float comparisons or compare as strings

### References

- `backend/tests/conftest.py` — test environment setup (lines 1–10)
- `backend/tests/domains/inventory/test_reorder_point_calculation.py` — async test pattern with `@pytest.mark.asyncio`
- `backend/domains/intelligence/service.py` — service function signatures (to be created in 19.1–19.6)
- `backend/domains/intelligence/schemas.py` — Pydantic model definitions (to be created in 19.1–19.6)
- `Epic 19` (in `_bmad-output/planning-artifacts/epic-19.md`) — full spec for all 6 service functions including formulas and classification thresholds

## Story Dependencies

- Prerequisite: Story 19.7 for shared access wiring and the intelligence module skeleton
- Depends on: the concrete service contracts for 19.1–19.6 as they land; this story should be developed alongside those stories, not postponed to the end
- Enables: ongoing refactoring safety net and contract validation before production use of the intelligence module
