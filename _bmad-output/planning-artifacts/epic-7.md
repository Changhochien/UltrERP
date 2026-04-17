## Epic 7: Business Dashboard

### Epic Goal

Owners can view morning KPIs: revenue, top products, stock alerts, and Posthog visitor data.

### Stories

### Story 7.1: Morning Dashboard - Revenue Comparison

As an owner,
I want to see today's revenue vs. yesterday's,
So that I can quickly assess business performance.

**Acceptance Criteria:**

**Given** I'm on the dashboard
**When** the page loads
**Then** I see today's total revenue
**And** I see yesterday's total revenue
**And** I see the percentage change
**And** dashboard loads in < 2 seconds (p95)

### Story 7.2: Top Selling Products

As an owner,
I want to view top selling products by day/week,
So that I can identify trends.

**Acceptance Criteria:**

**Given** I'm on the dashboard
**When** I view the top products section
**Then** I see the top 3 selling products for today
**And** I can toggle to view by week
**And** products show: name, quantity sold, revenue

### Story 7.3: Low-Stock Alerts

As an owner,
I want to view low-stock alerts on the dashboard,
So that I can address inventory issues quickly.

**Acceptance Criteria:**

**Given** products exist with stock below reorder point
**When** I view the dashboard
**Then** I see alerts listing products needing reorder
**And** alerts show: product name, current stock, reorder point
**And** clicking an alert takes me to the product detail

### Story 7.4: Posthog Visitor Count

As an owner,
I want to see Posthog visitor count from the previous day,
So that I can track website traffic.

**Acceptance Criteria:**

**Given** Posthog is integrated
**When** I view the dashboard
**Then** I see yesterday's visitor count
**And** I see the conversion rate (visitor → inquiry)
**And** data is visible within 10 minutes of session end
**And** data refreshes automatically

### Story 7.5: Posthog Integration - Visitor Tracking

As a system,
I want to track website visitor sessions via Posthog,
So that we understand user behavior.

**Acceptance Criteria:**

**Given** Posthog is configured
**When** visitors browse the website
**Then** sessions are tracked in Posthog
**And** page views, events, and sessions are captured
**And** data flows to dashboard within 10 minutes

### Story 7.6: Posthog Integration - Goal Conversions

As a system,
I want to track goal conversions (visitor → inquiry),
So that we measure marketing effectiveness.

**Acceptance Criteria:**

**Given** Posthog is integrated
**When** a visitor completes an inquiry action
**Then** the conversion is tracked as a goal
**And** conversion rate is calculated and displayed on dashboard
**And** trend data is available for comparison

---

