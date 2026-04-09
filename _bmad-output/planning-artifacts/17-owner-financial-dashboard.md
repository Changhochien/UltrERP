---
stepsCompleted:
  - step-01-validate-prerequisites
inputDocuments:
  - path: "_bmad-output/planning-artifacts/prd.md"
    type: "prd"
  - path: "docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md"
    type: "architecture"
  - path: ".omc/handoffs/team-plan.md"
    type: "team-investigation"
workflowType: 'epic'
---

# Owner Dashboard — New Epic Proposal

## Rationale

Epic 7 (Business Dashboard, FR25-FR28) covers the morning pulse check: revenue vs. yesterday, top products, low-stock alerts, and Posthog visitor stats. The Owner Dashboard extends this with **financial visibility layer** for strategic decision-making: gross margin, cash flow, accounts receivable/payable aging, and top customers by revenue.

This requires:
- **Backend**: New API endpoints for aggregated KPIs, AR/AP aging, cash flow
- **Frontend**: New owner-specific KPI strip, filter bar, install recharts, and drill-down visualizations
- **Data model gap**: No COGS/cost tracking → gross profit cannot be computed until unit_cost is added to OrderLine/InvoiceLine

---

## New Functional Requirements

**Owner Dashboard:**

- FR70: Owner can view gross margin % (revenue − COGS) for the current period
- FR71: Owner can view net cash flow for a date range (total incoming payments − total outgoing supplier payments), clearly labeled as cash movement rather than bank balance
- FR72: Owner can view accounts receivable posture with `Current / Not yet due`, `0–30`, `31–60`, `61–90`, and `90+` overdue buckets plus total outstanding amount
- FR73: Owner can view accounts payable posture with `Current / Not yet due`, `0–30`, `31–60`, `61–90`, and `90+` overdue buckets plus total outstanding amount
- FR74: Owner can view revenue trend chart (daily revenue line over 30 days)
- FR75: Owner can view top customers by revenue for a configurable period, including concentration and open receivable exposure
- FR76: Owner can view open order count and total open order revenue
- FR77: Owner can view a KPI summary strip of 4–6 prioritized metrics such as revenue, prior-period delta, open invoice amount, overdue receivables amount, pending order revenue, and low-stock exceptions

**Supporting Backend:**

- FR78: System exposes a `GET /dashboard/kpi-summary` endpoint returning the aggregated metrics from FR77
- FR79: System exposes a `GET /reports/ar-aging` endpoint returning outstanding invoices grouped by current plus aging buckets
- FR80: System exposes a `GET /reports/ap-aging` endpoint returning outstanding supplier invoices grouped by current plus aging buckets
- FR81: System exposes a `GET /dashboard/cash-flow` endpoint returning incoming and outgoing payments by date range, plus net cash flow trend
- FR82: System exposes a `GET /dashboard/top-customers?period=month|quarter|year` endpoint returning top customers by revenue, revenue share, and open receivable exposure

**Data Model Extension (future-gated on COGS):**

- FR83: OrderLine and InvoiceLine store unit_cost enabling gross profit calculation (deferred until after AR/AP endpoints — can ship FR70-FR82 without FR83 by showing "margin data unavailable")

---

## Epic 17: Owner Financial Dashboard

### Epic Goal

Owners and managers can view a financial intelligence layer showing business performance beyond the morning dashboard: gross margin visibility, cash flow trend, AR/AP aging health, revenue trend charts, and top customer performance — all in a single owner dashboard view.

**FRs covered:** FR70–FR83

---

### Story 17.1: Install Recharts for Visualizations

As a frontend developer,
I want a charting library installed in the frontend,
So that the owner dashboard can render revenue trend lines, bar charts, and pie charts.

**Acceptance Criteria:**

- **Given** the frontend project at `src/`
- **When** the developer runs `pnpm add recharts`
- **Then** recharts is listed in `package.json` dependencies and the imports needed for `LineChart`, `BarChart`, `ComposedChart`, `Line`, `Bar`, `XAxis`, `YAxis`, `CartesianGrid`, `Tooltip`, and `ResponsiveContainer` work in TypeScript without errors

---

### Story 17.2: KPI Summary Backend Endpoint

As a backend developer,
I want to expose a `GET /dashboard/kpi-summary` endpoint,
So that the frontend owner dashboard can fetch all primary KPIs in a single request.

**Acceptance Criteria:**

- **Given** a valid authenticated request with Bearer token
- **When** `GET /api/v1/dashboard/kpi-summary` is called with optional `?as_of_date=YYYY-MM-DD` (defaults to today)
- **Then** the response returns:
  - `as_of_date`
  - `today_revenue`: sum of Invoice total_amount where invoice_date = as_of_date and status = 'issued'
  - `yesterday_revenue`: same for the calendar day before `as_of_date`
  - `revenue_change_pct`: (today_revenue − yesterday_revenue) / yesterday_revenue × 100
  - `open_invoice_count`: count of Invoice with status = 'issued' and not fully paid
  - `open_invoice_amount`: sum of outstanding amount on open invoices
  - `pending_order_count`: count of Order with status in ('pending', 'confirmed')
  - `pending_order_revenue`: sum of Order.total_amount for pending orders
  - `low_stock_product_count`: count of products where InventoryStock.quantity < InventoryStock.reorder_point
  - `overdue_receivables_amount`: sum of Invoice total_amount where due_date < as_of_date and status = 'issued'
  - optional secondary fields allowed for KPI drill-down context, but the page presents only 4–6 primary tiles at once
- **And** the response is cached for 5 minutes (Cache-Control: max-age=300)
- **And** response time < 500ms for a tenant with ≤ 10,000 invoices

---

### Story 17.3: AR Aging Report Endpoint

As a backend developer,
I want to expose a `GET /reports/ar-aging` endpoint,
So that the owner can see how much receivables are current, overdue, and by how long.

**Acceptance Criteria:**

- **Given** a valid authenticated request
- **When** `GET /api/v1/reports/ar-aging?as_of_date=YYYY-MM-DD` is called
- **Then** the response returns buckets:
  - `bucket_current`: sum of outstanding invoice amounts where due_date >= as_of_date
  - `bucket_0_30_days`: sum of outstanding invoice amounts where age 0–30 days past due
  - `bucket_31_60_days`: same for 31–60 days
  - `bucket_61_90_days`: same for 61–90 days
  - `bucket_90_plus_days`: same for 90+ days
  - `total_outstanding`: sum of all open invoice amounts
  - `total_overdue`: sum of amounts in any overdue bucket
  - `as_of_date`
- **And** each invoice's outstanding amount = Invoice.total_amount − sum(Payment.amount) for payments matched to that invoice
- **And** age is computed as (as_of_date − Invoice.due_date) in days using `due_date` as the aging basis

---

### Story 17.4: AP Aging Report Endpoint

As a backend developer,
I want to expose a `GET /reports/ap-aging` endpoint,
So that the owner can see outstanding payables and due-date health.

**Acceptance Criteria:**

- **Given** a valid authenticated request
- **When** `GET /api/v1/reports/ap-aging?as_of_date=YYYY-MM-DD` is called
- **Then** the response returns the same current-plus-aging structure as AR aging:
  - `bucket_current`
  - `bucket_0_30_days`, `bucket_31_60_days`, `bucket_61_90_days`, `bucket_90_plus_days`
  - `total_outstanding`, `total_overdue`
  - `as_of_date`
- **And** outstanding amount = SupplierInvoice.total_amount − sum(SupplierPaymentAllocation.applied_amount) for payments applied to that invoice
- **And** age is computed as (as_of_date − SupplierInvoice.due_date) in days using `due_date` as the default aging basis
- **And** the endpoint is documented as due-date-driven so the UI can truthfully label the chart

---

### Story 17.5: Net Cash Flow Endpoint

As a backend developer,
I want to expose a `GET /dashboard/cash-flow` endpoint,
So that the owner can see money in vs. money out over a date range without implying a true bank balance.

**Acceptance Criteria:**

- **Given** a valid authenticated request
- **When** `GET /api/v1/dashboard/cash-flow?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` is called
- **Then** the response returns:
  - `as_of_date`
  - `period_start`, `period_end`
  - `cash_inflows`: sum of Payment.amount where payment_date in range (grouped by date)
  - `cash_outflows`: sum of SupplierPayment.gross_amount where payment_date in range (grouped by date)
  - `net_cash_flow`: cash_inflows − cash_outflows for the period
  - `running_net_by_date[]`: array of {date, cumulative_net_cash_flow} objects in chronological order
- **And** dates without transactions are still represented with the previous cumulative net value
- **And** the API contract and UI label this metric as `net cash flow` or `cash movement`, not `cash position`

---

### Story 17.6: Top Customers Endpoint

As a backend developer,
I want to expose a `GET /dashboard/top-customers` endpoint,
So that the owner can see which customers generate the most revenue and concentration risk.

**Acceptance Criteria:**

- **Given** a valid authenticated request
- **When** `GET /api/v1/dashboard/top-customers?period=month&limit=10&as_of_date=YYYY-MM-DD` is called
- **Then** the response returns an array of:
  - `customer_id`, `company_name`
  - `total_revenue`: sum of Invoice.total_amount for paid + issued invoices in the period
  - `revenue_share_pct`: customer revenue / total revenue for the selected period
  - `open_receivable_amount`: outstanding receivables for that customer as of `as_of_date`
  - `invoice_count`: number of invoices in the period
  - `last_invoice_date`: date of most recent invoice
- **And** results are sorted by total_revenue descending, limited to `limit` (default 10)
- **And** `period` accepts: `month` (current calendar month), `quarter` (current quarter), `year` (current year)

---

### Story 17.7: Owner Dashboard KPI Strip (Frontend)

As an owner,
I want to see a KPI summary strip with the most decision-relevant metrics,
So that I can quickly assess business health from one glance.

**Acceptance Criteria:**

- **Given** the owner is on the owner dashboard page at `/owner-dashboard`
- **When** the page loads
- **Then** a `KPISummaryStrip` renders the `kpi-summary` data as 4-6 compact KPI tiles instead of one overloaded card
- **And** the primary KPI set prioritizes revenue, revenue delta, open invoice amount, overdue receivables amount, pending order revenue, and one operational exception metric
- **And** each tile includes a short subtitle or comparison label clarifying period or basis
- **And** primary tiles support drill-down navigation into the related invoice, order, or inventory view where appropriate
- **And** loading state shows Skeleton placeholders while data fetches
- **And** if the API call fails, an error state is shown with a retry button
- **And** the strip uses existing MetricCard or Card components with consistent styling

---

### Story 17.8: Revenue Trend Chart (Frontend)

As an owner,
I want to see a line chart of daily revenue over the last 30 days,
So that I can spot revenue trends and anomalies at a glance.

**Acceptance Criteria:**

- **Given** the owner dashboard is loaded
- **When** the page renders
- **Then** a `RevenueTrendChart` is displayed using recharts `<LineChart>`
- **And** the X-axis shows dates (last 30 days), Y-axis shows revenue in TWD
- **And** tooltip on hover shows the exact date and revenue amount
- **And** the chart reflects the current page filter context when an `as_of_date` is selected
- **And** the chart is responsive (fills container width, 300px height)
- **And** a loading skeleton is shown while data fetches

---

### Story 17.9: AR Aging Card (Frontend)

As an owner,
I want to see accounts receivable posture in current and overdue bucket columns,
So that I can identify overdue payments and follow up without losing sight of near-term cash.

**Acceptance Criteria:**

- **Given** the owner dashboard is loaded
- **When** the `ar-aging` endpoint returns data
- **Then** an `ARAgingCard` shows five buckets (`Current`, `0–30`, `31–60`, `61–90`, `90+`) as columns with colored indicators:
  - `Current`: neutral
  - `0–30 days overdue`: amber (attention)
  - `31–60 days overdue`: orange (warning)
  - `61–90 days overdue`: red (high risk)
  - `90+ days overdue`: destructive (critical)
- **And** each bucket shows the outstanding amount formatted as TWD currency
- **And** a total row shows total_outstanding and total_overdue amounts
- **And** clicking a bucket opens the matching filtered receivables list when routing support exists
- **And** loading and error states are handled consistently with other cards

---

### Story 17.10: AP Aging Card (Frontend)

As an owner,
I want to see accounts payable posture in current and overdue bucket columns,
So that I can manage cash outflow timing and supplier relationships.

**Acceptance Criteria:**

- **Given** the owner dashboard is loaded
- **When** the `ap-aging` endpoint returns data
- **Then** an `APAgingCard` mirrors the AR Aging Card layout with the same five-bucket structure
- **And** the card labels the basis as `Due date aging`
- **And** bucket colors follow the same risk convention as AR
- **And** the component is visually distinct from AR Aging Card (e.g., "Payables" label)
- **And** clicking a bucket opens the matching filtered supplier invoice view when routing support exists
- **And** loading and error states are handled

---

### Story 17.11: Cash Flow Card (Frontend)

As an owner,
I want to see a chart of weekly cash inflows vs. outflows plus running net cash flow,
So that I can understand if the business is generating or consuming cash.

**Acceptance Criteria:**

- **Given** the owner dashboard is loaded
- **When** the `cash-flow` endpoint returns data
- **Then** a `CashFlowCard` displays a recharts `<ComposedChart>` with:
  - X-axis: weeks (or days if range < 14 days)
  - Two bars per period: inflows (green) and outflows (red)
  - A line showing running net cash flow
- **And** a summary row shows total inflows, total outflows, net for the period
- **And** the card subtitle clearly states that the view represents net cash flow / cash movement, not a bank balance
- **And** the card is positioned in the first analytical row of the page because it is a primary owner decision view
- **And** the chart is responsive

---

### Story 17.12: Top Customers Card (Frontend)

As an owner,
I want to see a ranked list of top customers by revenue and concentration,
So that I can identify and nurture key accounts while monitoring dependency risk.

**Acceptance Criteria:**

- **Given** the owner dashboard is loaded
- **When** the `top-customers` endpoint returns data
- **Then** a `TopCustomersCard` shows:
  - Rank number, company name, total revenue (TWD), revenue share %, open receivable amount, invoice count
  - Period selector: Month / Quarter / Year (tabs or segmented control)
  - Top 10 customers displayed in a table or ranked list
- **And** loading and error states are handled
- **And** results update when the period selector changes
- **And** clicking a customer row opens the related customer or invoice detail flow when routing support exists

---

### Story 17.13: Owner Dashboard Page Route and Filter Bar

As a frontend developer,
I want to add a new `/owner-dashboard` route,
So that the owner-specific KPI views are accessible via the sidebar.

**Acceptance Criteria:**

- **Given** the route file at `src/lib/routes.ts`
- **When** a new route `OWNER_DASHBOARD_ROUTE = '/owner-dashboard'` is added
- **And** the route is added to the navigation sidebar under the "Overview" group
- **Then** the sidebar shows an "Owner Dashboard" menu item with a chart/analytics icon
- **And** the route renders `OwnerDashboardPage` at `src/domain/owner-dashboard/OwnerDashboardPage.tsx`
- **And** the page uses the existing page layout pattern (PageHeader + content grid)
- **And** the page header includes a global filter bar with `As of date`, period selector, refresh timestamp, and export action
- **And** the page layout follows a one-screen-first information hierarchy:
  - KPI strip first
  - cash flow and AR aging second
  - AP aging and revenue trend third
  - top customers and action shortcuts last

---

### Story 17.14: Gross Margin KPI (Frontend, Deferred Until COGS)

As an owner,
I want to see my gross margin %,
So that I know how much profit I'm making on sales after accounting for product costs.

**Acceptance Criteria:**

- **Given** OrderLine and InvoiceLine have unit_cost populated
- **When** the owner dashboard loads
- **Then** a `GrossMarginCard` shows:
  - Gross margin % = (Revenue − COGS) / Revenue × 100
  - COGS = sum(OrderLine.quantity × OrderLine.unit_cost) for the period
  - Revenue = sum(OrderLine.total_amount) for the period
  - Comparison to previous period (same metric, prior month)
- **And** if unit_cost is not populated on OrderLine/InvoiceLine, the card shows "Margin data unavailable — cost tracking not configured" with an info icon instead of a number
- **This story is gated behind Story 17.15 (COGS data model extension)**

---

### Story 17.15: Add unit_cost to OrderLine and InvoiceLine

As a backend developer,
I want to add `unit_cost` to the OrderLine and InvoiceLine models,
So that gross profit can be calculated from revenue minus cost of goods sold.

**Acceptance Criteria:**

- **Given** the existing OrderLine and InvoiceLine SQLAlchemy models
- **When** a migration is created via `alembic revision -m "add unit_cost to OrderLine InvoiceLine"`
- **Then** both models have a `unit_cost: Mapped[Numeric(20, 2) | None]` field
- **And** the field is nullable (backwards-compatible with existing data)
- **And** existing API endpoints for orders/invoices continue to work without modification
- **And** the gross_margin field can be added to the revenue aggregation endpoints

---

## Dependency Graph

```
Story 17.1 (recharts install)
        ↓
Story 17.2 (kpi-summary API) ───────────────┐
Story 17.3 (ar-aging API) ──┐               │
Story 17.4 (ap-aging API) ───┼──┐           │
Story 17.5 (net cash-flow API) ─┼── Story 17.6 (top-customers API)
                                 │           │
                                 ↓           ↓
                Story 17.7 (KPI strip)   Story 17.8 (Revenue chart)
                                 │           │
                                 ├── Story 17.9 (AR aging card)
                                 ├── Story 17.10 (AP aging card)
                                 ├── Story 17.11 (Cash flow card)
                                 └── Story 17.12 (Top customers card)
                                              ↓
                     Story 17.13 (Owner dashboard route + filter bar)
                                              │
                                              ↓
                     Story 17.14 (Gross margin card — deferred)
                                              ↓
                     Story 17.15 (unit_cost on OrderLine/InvoiceLine — enables 17.14)
```

---

## Scope Decision

**In Scope for this Epic:**
- Stories 17.1 through 17.13 (all AR/AP/cash flow/revenue/customer visibility, filter bar, and drill-down ready card behavior)
- Stories 17.14 and 17.15 can be added but are deferred until COGS data is available

**Out of Scope:**
- Budget vs. actual comparisons (Phase 3 per PRD)
- Forecasting or predictive analytics (Phase 3)
- Mobile-specific layout (responsive breakpoints only — defer native mobile app)

---

## Non-Functional Requirements

- NFR37: Owner dashboard page loads in < 2 seconds (p95) — same as Epic 7 dashboard
- NFR38: All new API endpoints respond in < 500ms for tenants with ≤ 10,000 invoices
- NFR39: Caching on `/dashboard/kpi-summary` and `/dashboard/cash-flow` (5-minute TTL)
- NFR40: All dashboard cards show Skeleton loading state; error states include retry action
- NFR41: Dashboard cards sharing financial context use a consistent `as_of_date` and filter state so values do not contradict each other on the same page

---

## Research-Informed Best-Practice Recommendations (2026-04-08)

Based on a focused review of SAP working-capital dashboards, Microsoft Dynamics 365 aging reports, Xero small-business finance guidance, Tableau dashboard guidance, and Power BI report guidance, the highest-value version of Epic 17 should optimize for owner decisions instead of maximizing widget count.

### Highest-Value Owner Questions

- Are we generating or consuming cash?
- Which receivables need action now?
- Which supplier bills are due soon, overdue, or safe to delay?
- Is revenue and margin trending in the right direction?
- Are we over-dependent on a few customers?

### Recommended UX/UI Architecture

1. Filter bar: `As of date`, period selector, refresh timestamp, export.
2. KPI strip: revenue, revenue delta, open AR, overdue AR, net cash flow, and one operational exception KPI.
3. Main working-capital row: cash flow chart plus AR aging.
4. Secondary row: AP aging plus revenue trend / gross margin state.
5. Action row: top customers with concentration context plus operational drill-down shortcuts.

### Best-Practice Corrections to Current Epic Assumptions

- Replace the "single KPI summary card" idea with a KPI strip of atomic cards. One crowded card is slower to scan and lower trust.
- Add a `Current` or `Not yet due` bucket to AR/AP aging. Overdue-only buckets hide near-term workload and working-capital exposure.
- Default AP aging to `due_date`, not `invoice_date`, because payment health is managed against terms and due dates.
- Label FR71 / Story 17.5 output as `net cash flow` or `cash movement` until actual bank balances exist. The current design does not produce a true cash position.
- Show explicit freshness and basis labels such as `As of`, `Cash basis`, or `Margin unavailable`.
- Make every KPI, bucket, and ranked customer row link to a drill-down workflow instead of ending at passive reporting.

### Suggested Next-Wave Metrics After V1

- Days Sales Outstanding (DSO)
- Days Payables Outstanding (DPO)
- Cash conversion cycle
- Quick ratio / liquidity coverage
- Customer concentration percentage
- On-time supplier payment rate and discount capture
