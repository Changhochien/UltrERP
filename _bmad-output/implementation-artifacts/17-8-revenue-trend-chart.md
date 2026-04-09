# Story 17.8: Revenue Trend Chart (Frontend)

Status: done

## Implementation Status

**Frontend:** DONE — Component exists with recharts; dependency now installed

**Completed:**
- `RevenueTrendChart` component exists at `src/domain/dashboard/components/RevenueTrendChart.tsx`
- `recharts` dependency installed in `package.json` (story 17.1 complete)
- `useRevenueTrend` hook exists in `useDashboard.ts`

## Story

As an owner,
I want to see a line chart of daily revenue over the last 30 days,
So that I can spot revenue trends and anomalies at a glance.

## Acceptance Criteria

**AC1:** Revenue trend line chart renders
**Given** the owner dashboard is loaded
**When** the page renders
**Then** a `RevenueTrendChart` is displayed using recharts `<LineChart>`
**And** the X-axis shows dates for the last 30 days (daily granularity)
**And** the Y-axis shows revenue in TWD

**AC2:** Interactive tooltip
**Given** the user hovers over a data point on the chart
**When** the tooltip is triggered
**Then** it shows the exact date and revenue amount for that day

**AC3:** Responsive layout
**Given** the chart is placed in a container
**When** the container width changes
**Then** the chart fills the container width
**And** the chart height is fixed at 300px

**AC4:** Loading skeleton
**Given** the owner dashboard is loading
**When** the revenue trend data is being fetched
**Then** a Skeleton placeholder is shown instead of the chart
**And** the skeleton is approximately the same size as the chart (300px height)

**AC5:** Error handling
**Given** the revenue trend API call fails
**When** an error occurs
**Then** an error state is displayed with a retry button
**And** clicking retry re-fetches the data

## Tasks / Subtasks

- [x] **Task 1: Revenue Trend Chart Component** (AC1, AC3)
  - [x] Create `src/domain/dashboard/components/RevenueTrendChart.tsx`:
    - Uses `recharts` `<LineChart>`, `<Line>`, `<XAxis>`, `<YAxis>`, `<Tooltip>`, `<ResponsiveContainer>`
    - Props: `data: RevenueTrendItem[]`, `isLoading: boolean`, `error: string | null`, `onRetry: () => void`
    - X-axis: date labels (last 30 days, format: "MM/DD")
    - Y-axis: revenue in TWD with `NT$` prefix and comma formatting
    - Chart height: 300px, full container width

- [x] **Task 2: Revenue Trend Data Type** (AC1)
  - [x] Add to `src/domain/dashboard/types.ts`:
    ```typescript
    export interface RevenueTrendItem {
      date: string;   // ISO date string "YYYY-MM-DD"
      revenue: string; // Decimal as string, TWD
    }
    ```

- [x] **Task 3: Dashboard Hook for Revenue Trend** (AC4, AC5)
  - [x] Add `useRevenueTrend()` to `src/domain/dashboard/hooks/useDashboard.ts`:
    - Fetches from `/api/v1/dashboard/revenue-trend` (story 17.8 backend equivalent)
    - Returns `{ data, isLoading, error, refetch }`

- [x] **Task 4: Loading and Error States** (AC4, AC5)
  - [x] When `isLoading`: show `Skeleton` with 300px height
  - [x] When `error`: show `SurfaceMessage` with retry button

- [x] **Task 5: Frontend Tests** (AC1-AC5)
  - [x] Create `src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx`
  - [x] Test: chart renders with data points for 30 days
  - [x] Test: tooltip shows date and revenue on hover
  - [x] Test: loading skeleton shown during fetch
  - [x] Test: error state with retry button

## Dev Notes

### Prerequisite

- **Story 17.1** (Install Recharts for Visualizations) must be completed first — recharts must be installed before this component can be built
- A backend equivalent story (17.8 backend) should provide `/api/v1/dashboard/revenue-trend` endpoint returning 30-day daily revenue array

### recharts Usage Pattern

```typescript
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// Y-axis formatter for TWD
const yAxisFormatter = (value: number) => `NT$ ${value.toLocaleString()}`;
```

### recharts Installation

```bash
pnpm add recharts
```

Ensure the recharts package is added to `package.json`. Story 17.1 handles this.

### Responsive Container Pattern

```typescript
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <XAxis dataKey="date" tickFormatter={(d) => dayjs(d).format("MM/DD")} />
    <YAxis tickFormatter={yAxisFormatter} />
    <Tooltip labelFormatter={(d) => dayjs(d).format("YYYY-MM-DD")} />
    <Line type="monotone" dataKey="revenue" stroke="#8884d8" />
  </LineChart>
</ResponsiveContainer>
```

### Loading Skeleton Pattern

```typescript
{isLoading ? (
  <Skeleton className="h-[300px] w-full" />
) : (
  <RevenueTrendChart data={data ?? []} />
)}
```

### Data Type

The chart expects:
```typescript
interface RevenueTrendItem {
  date: string;    // "2026-04-01"
  revenue: string; // "12345.67"
}
```

### TWD Currency Formatting

Format revenue values as `NT$ XXX,XXX.00` using:
```typescript
const formatTWD = (value: number) =>
  `NT$ ${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
```

### Project Structure Notes

- Component: `src/domain/dashboard/components/RevenueTrendChart.tsx`
- Hook: extend `src/domain/dashboard/hooks/useDashboard.ts`
- Types: extend `src/domain/dashboard/types.ts`
- Tests: `src/domain/dashboard/__tests__/RevenueTrendChart.test.tsx`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.8] AC definitions
- [Source: src/domain/dashboard/components/RevenueCard.tsx] Loading/error pattern reference
- [Source: src/domain/dashboard/types.ts] Existing dashboard types
- [Source: _bmad-output/implementation-artifacts/17-1-install-recharts.md] recharts installation
