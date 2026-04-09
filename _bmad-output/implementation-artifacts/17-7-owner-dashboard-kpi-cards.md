# Story 17.7: Owner Dashboard KPI Cards (Frontend)

Status: done

## Implementation Status

**Frontend:** DONE — Component, hook, and API fetcher all exist and are wired up

**Completed:**
- `KPISummaryCard` component exists at `src/domain/dashboard/components/KPISummaryCard.tsx`
- `useKPISummary` hook exists at `src/domain/dashboard/hooks/useKPISummary.ts`
- Backend endpoint now available at `/api/v1/dashboard/kpi-summary` (story 17.2 complete)

## Story

As an owner,
I want to see the KPI summary card with today's revenue, open invoice count, pending orders, and low-stock count,
So that I can quickly assess business health from one glance.

## Acceptance Criteria

**AC1:** KPISummaryCard displays all kpi-summary fields
**Given** the owner is on the owner dashboard page at `/owner-dashboard`
**When** the `kpi-summary` endpoint (story 17.2) returns data
**Then** a `KPISummaryCard` component is visible showing all fields from the response
**And** all monetary values are formatted as TWD currency (e.g., `NT$ 123,456.00`)

**AC2:** Loading skeleton state
**Given** the owner dashboard is loading
**When** the `kpi-summary` API call is in flight
**Then** a Skeleton placeholder is shown in place of the card content
**And** the layout does not shift when data loads

**AC3:** Error state with retry
**Given** the owner dashboard has loaded but the `kpi-summary` API call fails
**When** an error occurs (network error, 500, etc.)
**Then** an error message is displayed with a retry button
**And** clicking retry re-fetches the `kpi-summary` data

**AC4:** Uses existing components
**Given** the KPISummaryCard is rendered
**When** the component is built
**Then** it uses existing `MetricCard` or `Card` components from the component library
**And** styling is consistent with the existing dashboard card patterns

## Tasks / Subtasks

- [x] **Task 1: KPISummaryCard Component** (AC1, AC4)
  - [x] Create `src/domain/dashboard/components/KPISummaryCard.tsx`:
    - Props: `data: KPISummary | null`, `isLoading: boolean`, `error: string | null`
    - Display: today's revenue, open invoice count, pending orders count, low-stock count
    - Use existing `MetricCard` or `SectionCard` for layout
    - Format all TWD values with `NT$` prefix and comma separators

- [x] **Task 2: Dashboard Hook for KPI Summary** (AC1-AC3)
  - [x] Create `src/domain/dashboard/hooks/useKPISummary.ts`:
    - `useKPISummary()` — fetches from `/api/v1/dashboard/kpi-summary`
    - Returns `{ data, isLoading, error, refetch }` (refetch for retry)
    - Uses existing `apiFetch` utility

- [x] **Task 3: Loading and Error States** (AC2, AC3)
  - [x] KPISummaryCard renders `Skeleton` (from `components/ui/skeleton`) when `isLoading`
  - [x] KPISummaryCard renders error `SurfaceMessage` with retry button when `error`

- [x] **Task 4: Frontend Tests** (AC1-AC3)
  - [x] Create `src/domain/dashboard/__tests__/KPISummaryCard.test.tsx`
  - [x] Test: renders all KPI fields when data loads
  - [x] Test: shows loading skeleton during fetch
  - [x] Test: shows error with retry button on failure
  - [x] Test: retry button triggers re-fetch

## Dev Notes

### KPI Summary API Contract (Story 17.2)

The `GET /api/v1/dashboard/kpi-summary` endpoint returns:
```typescript
interface KPISummary {
  today_revenue: string;        // Decimal as string, TWD
  open_invoice_count: number;   // count of invoices not paid
  pending_orders_count: number; // count of orders not fulfilled
  low_stock_count: number;      // count of products below reorder point
  report_date: string;          // ISO date string
}
```

### Prerequisites

- **Story 17.2** (KPI Summary Backend Endpoint) must be completed first — this story provides the API endpoint
- Story 17.2 is the backend equivalent; this story builds the frontend consumer

### Component Library References

- `MetricCard` — imported from `components/layout/PageLayout` (used in RevenueCard)
- `SectionCard` — imported from `components/layout/PageLayout` (used in LowStockAlertsCard)
- `SurfaceMessage` — imported from `components/layout/PageLayout` (used in RevenueCard for error)
- `Badge` — imported from `components/ui/badge`
- `Skeleton` — imported from `components/ui/skeleton`
- See `src/domain/dashboard/components/RevenueCard.tsx` for full usage pattern

### TWD Currency Formatting

```typescript
function formatTWD(value: string | number): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
```

### Project Structure Notes

- Component: `src/domain/dashboard/components/KPISummaryCard.tsx`
- Hook: `src/domain/dashboard/hooks/useKPISummary.ts`
- Types: add `KPISummary` to `src/domain/dashboard/types.ts`
- API: add `fetchKPISummary()` to `src/lib/api/dashboard.ts`
- Tests: `src/domain/dashboard/__tests__/KPISummaryCard.test.tsx`

### Loading State Pattern (from RevenueCard)

```typescript
if (isLoading) {
  return (
    <SectionCard ...>
      <div data-testid="kpi-card-loading">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-20 w-full" />
      </div>
    </SectionCard>
  );
}
```

### Error State with Retry Pattern

```typescript
if (error) {
  return (
    <SectionCard ...>
      <SurfaceMessage tone="danger">{error}</SurfaceMessage>
      <Button onClick={refetch}>Retry</Button>
    </SectionCard>
  );
}
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.7] AC definitions
- [Source: src/domain/dashboard/components/RevenueCard.tsx] MetricCard, loading/error pattern
- [Source: src/domain/dashboard/components/LowStockAlertsCard.tsx] Card + Badge pattern
- [Source: src/domain/dashboard/types.ts] Existing dashboard types
- [Source: _bmad-output/implementation-artifacts/17-2-kpi-summary-backend.md] Backend endpoint (co-develop with this story)
