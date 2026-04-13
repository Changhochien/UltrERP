# Epic 19: Customer Product Intelligence

**Goal:** Enable AI agents and sales staff to understand what customers are buying, how purchasing behavior is changing, and where market opportunities exist — so agents can prospect intelligently and staff can manage accounts proactively.

**Business value:**
- AI agents can autonomously research accounts and surface cross-sell/upsell opportunities without human intervention
- Sales staff get action-first intelligence surfaces for account health, category context, and prospecting targets instead of relying on manual spreadsheet review
- Data that already exists in orders and order lines becomes actionable commercial intelligence without introducing new operational tables

**AI agents are the primary consumer** of this intelligence via MCP tools. The human UI is a secondary read-only view of the same data for sales staff who prefer not to use the CLI.

**Scope:**
- New `domains/intelligence/` backend module: schemas, services, REST routes, MCP tools
- New `src/domain/intelligence/` frontend module: lean action-first page plus selective embedding into existing customer surfaces
- No new database tables — all intelligence computed from existing `orders`, `order_lines`, `products`, `customers` tables

**Technical approach:**
- All service functions follow the existing pattern: `async def fn(session, ..., tenant_id)` with `async with session.begin(): await set_tenant(session, tid)`
- Financial values use `Decimal`, dates use `date`, IDs use `uuid.UUID`
- Epic 19 metrics are based on confirmed / shipped / fulfilled order activity in v1; they are commercial activity signals, not accounting revenue reports
- `Product.category` is treated as a nullable string dimension in v1; null and explicitly excluded non-merchandise categories must be filtered before ranking or trend calculations
- MCP tools use `FastMCP` with `ToolError` for errors, `model_dump(mode="json")` for responses, and shallow envelopes that expose support counts, score inputs, and applied filters
- Frontend uses existing `SectionCard` / `PageHeader` patterns, but the default human experience should be action-first feeds and drill-throughs rather than a chart-heavy analytics cockpit

**Implementation guardrails:**
- Every response that ranks or classifies entities must include structured evidence first: counts, windows, thresholds, and score components. Narrative fields such as `pitch_hint`, `reason`, `signals`, and `recommended_action` are secondary convenience text.
- Determinism is required for MCP and REST consumers: explicit default limits, stable secondary tie-breakers, and documented period windows.
- Tools that expose customer-level intelligence must not rely on `customers:read` alone when the result is derived from order activity. Use combined scopes aligned to the underlying data.
- `Story 19.3` should extend the existing customer analytics experience instead of creating an isolated duplicate customer intelligence silo.
- `Story 19.5` is a transparency-first whitespace candidate list in v1, not a predictive oracle. Return score components and confidence, and omit contact PII from the default machine-facing payload.
- `Story 19.6` is a late composition layer. Ship only the strongest signals in v1 and avoid turning synthesized banners into the primary source of truth.

**Dependency:** start with `19.7` for access wiring and route scaffolding, then build `19.3` and `19.2` as the shared customer/category foundations. `19.1` can proceed once affinity semantics are fixed. `19.4` depends on the customer snapshot from `19.3`; `19.5` depends on `19.1` plus stable customer/category aggregates; `19.6` comes last as a composition layer. `19.8` should be developed alongside the feature stories, not only at the end.

---

## Story 19.1: Product Affinity Map

As an **AI agent**,
I want to know which products are frequently purchased together
So that I can suggest bundle pitches and cross-sell recommendations to customers.

**Backend deliverables:**
- `domains/intelligence/schemas.py`: `AffinityPair`, `ProductAffinityMap` Pydantic models
- `domains/intelligence/service.py`: `get_product_affinity_map()` — co-occurrence analysis on `OrderLine → Product` across all orders using non-correlated subqueries
- `domains/intelligence/routes.py`: `GET /api/v1/intelligence/affinity` with `min_shared` and `limit` query params
- `domains/intelligence/mcp.py`: `intelligence_product_affinity` tool
- `TOOL_SCOPES` entry: `intelligence_product_affinity` → `orders:read`
- `backend/app/mcp_server.py`: register `domains.intelligence.mcp`

**Frontend deliverables:**
- `src/domain/intelligence/types.ts`: `AffinityPair`, `ProductAffinityMap` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts`: `useProductAffinity(minShared, limit)` hook
- `src/domain/intelligence/components/AffinityMatrix.tsx`: table showing top pairs with sortable columns, inline progress bars for `overlap_pct`
- Route registration and optional embedding in workbench tab

**Acceptance Criteria:**

**Given** multiple orders containing different product combinations from the same customer
**When** the AI agent calls `intelligence_product_affinity(min_shared=3, limit=50)`
**Then** the response includes top 50 product pairs sorted by Jaccard affinity score descending
**And** each pair contains: `product_a_id`, `product_b_id`, `product_a_name`, `product_b_name`, `shared_customer_count`, `customer_count_a`, `customer_count_b`, `overlap_pct`, `affinity_score`, `pitch_hint`
**And** `overlap_pct = shared_customer_count / min(customer_count_a, customer_count_b) * 100`
**And** `affinity_score = shared_customer_count / (customer_count_a + customer_count_b - shared_customer_count)` (customer-level Jaccard)

**Given** a sales staff user viewing the affinity UI
**When** the page loads with default parameters
**Then** the table renders sorted by `affinity_score` descending with `overlap_pct` shown as inline progress bars

---

## Story 19.2: Category Trend Radar

As an **AI agent or sales staff**,
I want to see which product categories are growing or declining
So that I know where to focus sales effort and which categories to pitch.

**Backend deliverables:**
- `domains/intelligence/schemas.py`: `CategoryTrend`, `CategoryTrends` Pydantic models
- `domains/intelligence/service.py`: `get_category_trends()` — period-over-period aggregation by `Product.category` using date-window queries
- `domains/intelligence/routes.py`: `GET /api/v1/intelligence/category-trends` with `period` param (`last_30d | last_90d | last_12m`)
- `domains/intelligence/mcp.py`: `intelligence_category_trends` tool
- `TOOL_SCOPES` entry: `intelligence_category_trends` → `orders:read`, `customers:read`

**Frontend deliverables:**
- `src/domain/intelligence/types.ts`: `CategoryTrend`, `CategoryTrends` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts`: `useCategoryTrends(period)` hook
- `src/domain/intelligence/components/CategoryTrendRadar.tsx`: recharts `BarChart` with two bars per category (current vs. prior period), period selector tabs (30d / 90d / 12m), trend coloring (growing=green, declining=red, stable=gray)

**Acceptance Criteria:**

**Given** orders spanning the current and prior period
**When** the AI agent calls `intelligence_category_trends(period="last_90d")`
**Then** each category in the response includes: `category`, `current_period_revenue`, `prior_period_revenue`, `revenue_delta_pct`, `current_period_orders`, `prior_period_orders`, `order_delta_pct`, `customer_count`, `prior_customer_count`, `new_customer_count`, `churned_customer_count`, `top_products` (top 5 by revenue), `trend`
**And** `trend = "growing"` when `revenue_delta_pct > 10`, `trend = "declining"` when `revenue_delta_pct < -10`, else `trend = "stable"`
**And** zero-baseline cases return support metadata or nullable deltas rather than fabricated `100%` growth
**And** trend labels are only applied when category support floors are met
**And** `new_customer_count` = customers who bought in this category for the first time in the current period
**And** `churned_customer_count` = customers who bought in the prior period but not the current period

**Given** a sales staff user viewing the category trends tab
**When** the page loads with the default 90d period
**Then** the bar chart renders with two bars per category (current=colored, prior=gray), sorted by `revenue_delta_pct` descending, and the period selector allows switching between 30d/90d/12m

---

## Story 19.3: Customer Product Profile

As an **AI agent** preparing for a customer call,
I want to know what this customer buys, how often, and what they've recently started or stopped buying
So that I can have a informed conversation and pitch relevant products.

**Backend deliverables:**
- `domains/intelligence/schemas.py`: `CategoryRevenue`, `ProductPurchase`, `CustomerProductProfile` Pydantic models
- `domains/intelligence/service.py`: `get_customer_product_profile()` — per-customer order aggregation with category + product breakdown
- `domains/intelligence/routes.py`: `GET /api/v1/intelligence/customers/{customer_id}/product-profile`
- `domains/intelligence/mcp.py`: `intelligence_customer_product_profile` tool
- `TOOL_SCOPES` entry: `intelligence_customer_product_profile` → `customers:read`, `orders:read`

**Frontend deliverables:**
- `src/domain/intelligence/types.ts`: `CategoryRevenue`, `ProductPurchase`, `CustomerProductProfile` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts`: `useCustomerProductProfile(customerId)` hook
- `src/domain/intelligence/components/CustomerProductProfile.tsx`: customer-detail intelligence module — metrics row, top categories, top products, `is_dormant` badge, and `new_categories` chips designed to embed into the existing customer experience

**Acceptance Criteria:**

**Given** a customer with orders spanning multiple categories and products over 12 months
**When** the AI agent calls `intelligence_customer_product_profile(customer_id=<uuid>)`
**Then** the response includes: `customer_id`, `company_name`, `total_revenue_12m`, `order_count_12m`, `order_count_3m`, `order_count_6m`, `order_count_prior_12m`, `order_count_prior_3m`, `frequency_trend` (based on trailing 3m vs. the immediately preceding 3m), `avg_order_value`, `avg_order_value_prior`, `aov_trend`, `top_categories` (sorted by revenue desc), `top_products` (sorted by order_count desc), `last_order_date`, `days_since_last_order`, `is_dormant`, `new_categories`, `confidence`, `activity_basis`

**Given** a sales staff user viewing a customer's profile
**When** the customer has been dormant for 60+ days
**Then** a red "Dormant" badge is displayed alongside the last order date
**And** any `new_categories` are shown with a green "New" chip

---

## Story 19.4: Customer Risk Signals

As an **AI agent** monitoring the customer base,
I want a ranked list of accounts that need attention — dormant, at-risk, or growing —
So that I can prioritize outreach and capitalize on expansion.

**Backend deliverables:**
- `domains/intelligence/schemas.py`: `CustomerRiskSignals` Pydantic model
- `domains/intelligence/service.py`: `get_customer_risk_signals()` — all-customer scan with period comparison and status classification
- `domains/intelligence/routes.py`: `GET /api/v1/intelligence/customers/risk-signals` with `status` and `limit` query params
- `domains/intelligence/mcp.py`: `intelligence_customer_risk_signals` tool
- `TOOL_SCOPES` entry: `intelligence_customer_risk_signals` → `customers:read`, `orders:read`

**Frontend deliverables:**
- `src/domain/intelligence/types.ts`: `CustomerRiskSignals` TypeScript interface
- `src/domain/intelligence/hooks/useIntelligence.ts`: `useCustomerRiskSignals(status, limit)` hook
- `src/domain/intelligence/components/RiskSignalFeed.tsx`: scrollable `SectionCard` list with filter bar (All / Growing / At Risk / Dormant / New / Stable), each item shows customer name, status badge (color-coded), revenue delta, signals list

**Acceptance Criteria:**

**Given** all customers with their order history
**When** the AI agent calls `intelligence_customer_risk_signals(status_filter="all", limit=50)`
**Then** each customer is classified as one of: `growing` (revenue +20%+ vs. prior 12m), `at_risk` (revenue -20%- vs. prior 12m), `dormant` (no orders in 60+ days), `new` (first order in last 90d), `stable` (all other cases)
**And** each customer record includes structured evidence fields first: `revenue_current`, `revenue_prior`, `revenue_delta_pct`, `days_since_last_order`, `first_order_date`, `products_expanded_into`, `products_contracted_from`, `reason_codes`, `confidence`
**And** `signals` is a secondary human-readable summary derived from the structured evidence
**And** results are sorted by relevance (dormant first, then at_risk, then growing, then stable, then new) with a configurable limit

**Given** a sales staff user viewing the account signals tab
**When** the page loads
**Then** all 6 status filter buttons are shown and functional
**And** each account card shows the status badge with correct color (growing=green, at_risk=red, dormant=orange, new=blue, stable=gray)

---

## Story 19.5: Prospect Gap Analysis

As an **AI agent or sales staff**,
given a product category, I want to know which customers are NOT buying in that category but would be good fits
So that I can prioritize prospecting efficiently.

**Backend deliverables:**
- `domains/intelligence/schemas.py`: `ProspectFit`, `ProspectGaps` Pydantic models
- `domains/intelligence/service.py`: `get_prospect_gaps()` — transparency-first whitespace candidate list built from category non-buyers and explicit score components
- `domains/intelligence/routes.py`: `GET /api/v1/intelligence/prospect-gaps` with `category` (required) and `limit` query params
- `domains/intelligence/mcp.py`: `intelligence_prospect_gaps` tool
- `TOOL_SCOPES` entry: `intelligence_prospect_gaps` → `customers:read`, `orders:read`

**Frontend deliverables:**
- `src/domain/intelligence/types.ts`: `ProspectFit`, `ProspectGaps` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts`: `useProspectGaps(category, limit)` hook
- `src/domain/intelligence/components/ProspectGapTable.tsx`: table sorted by `affinity_score` desc; columns prioritize Company, Reason, Last Order Date, Category Count, AOV, Affinity Score, and Tags; contact details remain a drill-in concern

**Acceptance Criteria:**

**Given** a target category (e.g., "LED Displays") and the full customer base
**When** the AI agent calls `intelligence_prospect_gaps(category="LED Displays", limit=20)`
**Then** the response includes: `target_category`, `target_category_revenue`, `existing_buyers_count`, `prospects_count`, `prospects` (top 20 by affinity score)
**And** each prospect includes: `customer_id`, `company_name`, `total_revenue`, `category_count`, `avg_order_value`, `last_order_date`, `affinity_score` (0-1, higher = better fit), `score_components`, `reason_codes`, `reason`, `confidence`, `tags`
**And** contact fields are optional, not part of the default MCP payload, and only appear in role-appropriate human drill-ins
**And** `affinity_score` is computed from transparent heuristics such as order-frequency similarity, category breadth proximity, recency, and adjacent-category support

**Given** a sales staff user viewing prospect gaps for "LED Displays"
**When** the page loads
**Then** the category selector shows the selected category
**And** the table shows top 20 prospects with affinity scores as progress bars
**And** the existing buyer count badge is displayed

---

## Story 19.6: Market Opportunities Signal Feed

As an **AI agent or sales staff**,
I want to see high-level market signals — new product adoption, concentration risk, churn risk —
So that I understand macro trends and can act on them.

**Backend deliverables:**
- `domains/intelligence/schemas.py`: `OpportunitySignal`, `MarketOpportunities` Pydantic models
- `domains/intelligence/service.py`: `get_market_opportunities()` — late-stage composition layer that wraps only the strongest stabilized intelligence signals
- `domains/intelligence/routes.py`: `GET /api/v1/intelligence/market-opportunities` with `period` param
- `domains/intelligence/mcp.py`: `intelligence_market_opportunities` tool
- `TOOL_SCOPES` entry: `intelligence_market_opportunities` → `customers:read`, `orders:read`

**Frontend deliverables:**
- `src/domain/intelligence/types.ts`: `OpportunitySignal`, `MarketOpportunities` TypeScript interfaces
- `src/domain/intelligence/hooks/useIntelligence.ts`: `useMarketOpportunities(period)` hook
- `OpportunitySignalBanner` component embedded in Category Trends tab — alert-style banners with severity coloring and recommended action

**Acceptance Criteria:**

**Given** current order and customer data
**When** the AI agent calls `intelligence_market_opportunities(period="last_90d")`
**Then** the response includes a `signals` array composed only from stabilized upstream intelligence in v1
**And** `concentration_risk` is the required v1 signal when any single customer represents >30% of period revenue
**And** `category_growth` may be included when category support floors are met and the upstream category trend contract is stable
**And** each signal includes: `signal_type`, `severity` ("info" | "warning" | "alert"), `headline`, `detail`, `affected_customer_count`, `revenue_impact`, `recommended_action`, `support_counts`, `source_period`
**And** `new_product_adoption` and `churn_risk` are explicitly deferred until upstream signal quality is validated

**Given** a sales staff user viewing the category trends tab
**When** market opportunities exist
**Then** alert banners appear at the top of the tab with severity-appropriate coloring
**And** clicking or reading a banner gives a clear `recommended_action`

---

## Story 19.7: Intelligence Feature Gate

As an **admin**,
I want to control access to the intelligence module
So that only authorized roles can see the data.

**Backend deliverables:**
- `backend/app/mcp_auth.py`: add 6 new `TOOL_SCOPES` entries for intelligence MCP tools
- `backend/app/mcp_server.py`: register `domains.intelligence.mcp` module
- Role-based check in REST routes using existing auth patterns; do not assume a separate backend feature-flag system exists
- `domains/intelligence/routes.py`: apply an intelligence-specific read dependency using the existing `require_role(...)` pattern

**Frontend deliverables:**
- `src/lib/routes.ts`: add `INTELLIGENCE_ROUTE` constant
- `src/hooks/usePermissions.ts`: add `intelligence` to `AppFeature` and grant it intentionally in the role-permission matrix
- `src/App.tsx`: add protected route for `INTELLIGENCE_ROUTE` with `requiredFeature="intelligence"` (or existing `ProtectedAppRoute` pattern)
- `src/pages/IntelligencePage.tsx`: entry page composing the workbench with tabs

**Acceptance Criteria:**

**Given** a user without the `intelligence` feature in the frontend role matrix or without the appropriate backend role / tool scope
**When** they attempt to access `/intelligence` or call an MCP tool
**Then** they are denied access by the existing route or scope enforcement mechanism
**And** the sidebar does not show the Intelligence navigation item

**Given** an AI agent with a valid MCP API key
**When** the agent calls `intelligence_category_trends`
**Then** the request is authenticated via the existing `ApiKeyAuth` middleware
**And** the tool scopes required by the concrete intelligence tool are checked against the key's granted scopes

---

## Story 19.8: Intelligence Backend Test Coverage

As a **developer**,
I want unit tests for the intelligence services
So that I can refactor safely and verify correctness of the aggregation logic.

**Backend deliverables:**
- `backend/tests/domains/intelligence/__init__.py`
- `backend/tests/domains/intelligence/test_service.py`: tests for all 6 service functions

**Test fixtures required (use existing conftest.py patterns):**
- Sample customers, orders, order_lines, products with known categories
- Prefer DB-backed fixtures for aggregation paths, with pure helper tests only where mocking is genuinely cheaper and still trustworthy

**Acceptance Criteria:**

**Given** a mocked database session with known order data
**When** `get_product_affinity_map` is called
**Then** the Jaccard affinity score is computed correctly: `shared_customer_count / (customer_count_a + customer_count_b - shared_customer_count)`
**And** pairs are sorted by `affinity_score` descending

**Given** a mocked session with orders spanning two 90-day periods
**When** `get_category_trends` is called with `period="last_90d"`
**Then** the `revenue_delta_pct` is computed as `(current - prior) / prior * 100`
**And** zero-baseline cases are classified as `newly_active`, `insufficient_history`, or equivalent support metadata rather than fabricated `100%` growth
**And** `new_customer_count` correctly counts customers with first orders in the current period only
**And** `churned_customer_count` correctly counts customers who bought in the prior period but not the current

**Given** a customer with known 12-month order history
**When** `get_customer_product_profile` is called
**Then** `is_dormant` is `true` when the last order is 60+ days ago
**And** `frequency_trend` is computed correctly from trailing 3m vs. the immediately preceding 3m comparison
**And** `new_categories` contains only categories with first orders in the last 90 days

**Given** a customer with known revenue in current and prior 12-month periods
**When** `get_customer_risk_signals` is called
**Then** a customer with `revenue_current > revenue_prior * 1.20` is classified as `growing`
**And** a customer with `revenue_current < revenue_prior * 0.80` is classified as `at_risk`
**And** a customer with no orders in 60 days is classified as `dormant`
**And** tenant isolation, deterministic sorting, and scope rejection paths are covered by the intelligence test suite

**Given** a target category with existing buyers and non-buyers
**When** `get_prospect_gaps` is called
**Then** the result includes explicit `score_components`, `reason_codes`, `confidence`, and no default contact PII in the machine-facing payload

**Given** market opportunities are computed for v1
**When** `get_market_opportunities` is called
**Then** `concentration_risk` is the required signal, `category_growth` is optional when support floors are met, and deferred signals remain omitted until validated upstream
