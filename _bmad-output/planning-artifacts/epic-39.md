# Epic 39: Unified Chart Platform and Time-Series Exploration Architecture

## Epic Goal

Establish a durable chart architecture for UltrERP that separates shared chart contracts, reusable UI primitives, and specialized time-series exploration behavior, so the app can scale its analytics surfaces without forcing every chart into the same interaction model.

## Business Value

- Users get consistent chart controls, loading states, legends, tooltips, and empty states across modules.
- Long-history charts become usable through dense series data, visible-range controls, and overview-plus-detail navigation instead of brittle month-count presets.
- The frontend avoids continued drift between ad hoc `recharts` and `@visx` implementations.
- Teams can add new charts through a documented decision matrix rather than re-deciding libraries and interaction models story by story.

## Current State Summary

UltrERP already has a mixed chart stack:

- `recharts` is used for summary and comparison charts such as `src/domain/dashboard/components/RevenueTrendChart.tsx`, `src/domain/intelligence/components/CategoryTrendRadar.tsx`, and `src/components/customers/CustomerAnalyticsTab.tsx`.
- `@visx` is used for custom operational charts such as `src/domain/inventory/components/StockTrendChart.tsx`, `src/domain/inventory/components/MonthlyDemandChart.tsx`, and `src/domain/dashboard/components/CashFlowCard.tsx`.
- `RevenueTrendChart` already contains a `Brush`, proving the app has an early navigator pattern, but it is not yet generalized.
- `MonthlyDemandChart` and the current monthly-demand backend path expose a key architectural gap: expanding the requested month window does not solve sparse series, because the API still returns only months that have source rows.

This epic standardizes the architecture around chart tiers and shared contracts, not around one universal renderer.

## Architecture Decision

### Core Decision

Adopt a **tiered chart platform**:

1. **Summary tier**
   - Small KPI and trend-summary charts
   - Minimal interaction
   - Recharts remains acceptable by default

2. **Comparison tier**
   - Ranked bars, paired bars, category comparisons, and compact dashboard charts
   - Shared chart shell and formatting, but no explorer navigator by default
   - Recharts or Visx allowed based on need, with a documented decision matrix

3. **Explorer tier**
   - Long-history operational and analytical time series
   - Separate loaded range vs. visible range
   - Dense zero-filled series, presets, pan/zoom, reset, and overview-plus-detail navigator
   - Visx is the default v1 renderer because the repo already uses it for bespoke time-series behavior; a Lightweight Charts adapter remains a future option, not a prerequisite for this epic

### Platform Principles

- Standardize **data contracts and interaction semantics first**, then standardize visuals.
- Keep **domain data hooks domain-owned**, but move reusable chart primitives into a shared chart platform.
- Use a **shared shell** for loading, error, empty, tooltip, legend, and preset controls.
- Do **not** add TradingView-style explorer controls to every chart. Only explorer-tier charts get the navigator/range-controller behavior.
- Backend time-series APIs must support **dense series**, **timezone-aware bucketing**, and explicit **range metadata**.

### Platform Filesystem Target

Frontend shared platform:

- `src/components/charts/types.ts`
- `src/components/charts/registry.ts`
- `src/components/charts/formatters.ts`
- `src/components/charts/ChartShell.tsx`
- `src/components/charts/ChartStateView.tsx`
- `src/components/charts/ChartLegend.tsx`
- `src/components/charts/controls/RangePresetGroup.tsx`
- `src/components/charts/controls/ChartModeToggle.tsx`
- `src/components/charts/explorer/useExplorerRange.ts`
- `src/components/charts/explorer/OverviewNavigator.tsx`
- `src/components/charts/explorer/ExplorerChartFrame.tsx`
- `src/components/charts/explorer/rechartsRangeBridge.ts`
- `src/components/charts/index.ts`

Backend support:

- `backend/common/time_series.py`
- `backend/domains/inventory/routes.py`
- `backend/domains/inventory/services.py`
- `backend/domains/dashboard/routes.py`
- `backend/domains/dashboard/services.py`

### Tech Stack Rules

- Frontend implementation remains `React 19 + Vite + TypeScript`.
- Backend implementation remains `FastAPI + SQLAlchemy async`.
- `recharts` remains acceptable for summary and comparison charts.
- `@visx` is the default v1 drawing layer for explorer-tier charts.
- Shared chart state, presets, formatters, and shells must be renderer-agnostic.
- Frontend validation uses `Vitest` plus Testing Library.
- Backend validation uses `pytest` in `backend/`.

### Compatibility and Rollout Strategy

- Do not break existing chart endpoints in place during v1 of this epic.
- Add parallel explorer endpoints for first-wave migrations and keep the current endpoints unchanged until the migrated consumers land.
- Migrate wave-1 charts one chart PR at a time even if they are planned under one story.
- Remove legacy hooks or compatibility routes only in a dedicated cleanup follow-up after the replacement chart is merged and validated.
- The platform standard applies to all charts, but the explorer interaction model applies only to explorer-tier charts.

### Validation Strategy

- Backend contract changes validate through targeted `pytest` runs in `backend/tests/domains/inventory/` and `backend/tests/domains/dashboard/`.
- Frontend platform changes validate through targeted `vitest` runs in `src/components/charts/`, `src/domain/inventory/`, `src/domain/dashboard/`, and `src/tests/intelligence/`.
- Story 39.6 does not start implementation until Story 39.5 migrations are validated on the first-wave charts.

## Scope

- Introduce a shared chart platform under `src/components/charts/`
- Define shared frontend chart types and backend range-aware time-series contracts
- Build reusable shell and control primitives
- Build an explorer-tier time-series kit with overview-plus-detail navigation
- Migrate the first-wave explorer charts: monthly demand, stock trend, revenue trend
- Standardize the remaining summary/comparison charts on shared shells, formatters, and governance rules without forcing explorer behavior everywhere

## Non-Goals

- Replacing every existing chart renderer in one pass
- Turning all dashboard charts into navigator-driven explorer charts
- Rewriting table-first cards such as `TopProductsCard` into charts when a table is the better surface
- Introducing TradingView Lightweight Charts as a hard dependency for v1 of this architecture

## Dependencies

- Epic 17 for existing dashboard chart surfaces and chart-related frontend groundwork
- Epic 20 for inventory/product analytics context and dense monthly-series semantics
- Epic 22 for shared UI foundations
- Existing inventory and dashboard APIs that currently expose time-series data

---

## Story 39.1: Chart Taxonomy, Platform Contract, and Migration Matrix

As a frontend and architecture team,
I want every chart surface classified into a stable chart tier with a documented platform contract,
so that new work follows one architecture instead of producing more one-off chart implementations.

**Acceptance Criteria:**

1. Given the current chart surfaces in the app, when the architecture inventory is completed, then each surface is assigned to `summary`, `comparison`, or `explorer` tier with a documented rationale.
2. Given a new chart is proposed, when the platform decision matrix is consulted, then the team can choose shell, control model, and renderer without ambiguity.
3. Given the shared chart platform is introduced, when a chart adopts it, then it uses common contracts for states, formatting, and series metadata instead of bespoke prop shapes.

---

## Story 39.2: Dense Time-Series Backend Contracts and Range Semantics

As a chart consumer,
I want time-series APIs to return dense, range-aware, timezone-explicit data,
so that long-range charts remain truthful and navigable even when source activity is sparse.

**Acceptance Criteria:**

1. Given a time-series endpoint returns monthly or daily data, when the requested window contains gaps, then the response includes zero-filled points rather than omitting missing buckets.
2. Given an explorer-tier chart requests data, when the API responds, then it includes range metadata such as requested range, available range, default visible range, bucket, and timezone.
3. Given a partial current period is included, when the response is built, then the payload marks the partial period explicitly instead of blending it silently with closed history.

---

## Story 39.3: Shared Frontend Chart Shell and Control Primitives

As a frontend developer,
I want reusable chart shells and controls,
so that charts across dashboard, intelligence, and inventory share one interaction language for states and simple filtering.

**Acceptance Criteria:**

1. Given a chart needs loading, error, empty, legend, tooltip, and preset controls, when it adopts the shared platform, then it can compose those from shared primitives rather than custom in-component markup.
2. Given chart controls are rendered, when users interact with them, then they follow one accessible pattern for labels, `aria-pressed`, focus, and disabled states.
3. Given summary- or comparison-tier charts migrate, when reviewed, then they share shell and formatting behavior without inheriting explorer-only controls.

---

## Story 39.4: Explorer Time-Series Kit

As a user exploring long-history operational signals,
I want a main chart plus overview navigator with preset windows and reset behavior,
so that I can inspect multi-year history without losing context.

**Acceptance Criteria:**

1. Given an explorer-tier chart loads a long time range, when it renders, then it shows a detail view plus an overview-plus-detail navigator.
2. Given the user changes presets such as `3M`, `6M`, `1Y`, `2Y`, `4Y`, or `All`, when the selection changes, then the visible range updates without requiring a full renderer redesign.
3. Given the user pans, zooms, or resets the view, when the explorer state updates, then visible-range state remains separate from loaded-range state.

---

## Story 39.5: First-Wave Explorer Migration

As an inventory or operations user,
I want the app's most important long-history charts migrated onto the shared explorer architecture,
so that the first-wave operational analytics are consistent and usable.

**Acceptance Criteria:**

1. Given the inventory monthly-demand chart is opened, when history spans sparse or long periods, then the user can inspect the full range through dense series data and explorer controls.
2. Given the stock trend chart is opened, when the user changes visible range, then reorder overlays and projected lines remain intact.
3. Given the dashboard revenue trend chart is opened, when range controls are used, then it follows the shared range-controller model even if its internal renderer remains different in the first migration wave.

---

## Story 39.6: Summary and Comparison Chart Standardization plus Governance

As a product and frontend team,
I want the remaining chart surfaces standardized on shared shells, formatters, and governance rules,
so that simple charts become consistent without overcomplicating them.

**Acceptance Criteria:**

1. Given a summary- or comparison-tier chart such as category trends, customer revenue trend, or cash-flow comparison is reviewed, when migrated, then it adopts the shared shell, formatting, legend, and state model.
2. Given a simple chart does not require long-history exploration, when standardized, then it does not receive navigator or explorer controls by default.
3. Given the epic is complete, when a new chart is proposed, then a documented governance rule exists for tier assignment, renderer choice, and adoption expectations.

## References

- `package.json`
- `src/domain/dashboard/components/RevenueTrendChart.tsx`
- `src/domain/dashboard/components/CashFlowCard.tsx`
- `src/domain/intelligence/components/CategoryTrendRadar.tsx`
- `src/components/customers/CustomerAnalyticsTab.tsx`
- `src/domain/inventory/components/StockTrendChart.tsx`
- `src/domain/inventory/components/MonthlyDemandChart.tsx`
- `backend/domains/inventory/services.py`
- `backend/domains/inventory/routes.py`
- `CLAUDE.md`