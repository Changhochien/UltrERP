# Story 17.17: Visitor Stats Time-Series Chart

**Status:** ready-for-dev

## Story

As an owner,
I want to see visitor stats as a time-series line chart over 7 and 30 days,
so that I can spot traffic trends, identify drops, and correlate inquiry spikes with marketing activity.

## Business Context

`VisitorStatsCard` currently shows only yesterday's snapshot as three metric tiles (visitors, inquiries, conversion rate). The PostHog backend pipeline already supports historical queries — `get_visitor_stats()` in `backend/domains/dashboard/posthog_client.py` runs HogQL against PostHog's `/api/projects/{project_id}/query/` endpoint. The data is there; the visual is not.

The backend `VisitorStatsResponse` schema needs a new endpoint variant to return a time series, OR we extend the existing `GET /api/v1/dashboard/visitor-stats` to accept a `?period=7d|30d` parameter.

## Reference

ERPNext has no PostHog equivalent, but the pattern of a time-series line chart over a configurable window is well-established:
- `RevenueTrendChart` — 30d/90d/1y line chart with `Brush` navigator and period tabs
- VisitorStats should follow the same period-tab pattern (7d / 30d) but with simpler single-line + no zoom

## Acceptance Criteria

**AC1 — Backend accepts period parameter**
- Extend `GET /api/v1/dashboard/visitor-stats` to accept `?period=7d|30d`
- Return `items: Array<{ date: string; visitor_count: number; inquiry_count: number }>` instead of single-day snapshot when period is specified
- Default (`period` omitted) returns the existing single-day `VisitorStatsResponse` for backward compatibility with the current card
- Response shape for time-series:
  ```typescript
  interface VisitorStatsTimeSeries {
    period: "7d" | "30d";
    items: Array<{
      date: string;         // ISO date string, e.g. "2026-04-20"
      visitor_count: number;
      inquiry_count: number;
    }>;
    totals: {
      visitor_count: number;
      inquiry_count: number;
    };
  }
  ```

**AC2 — `useVisitorStats` hook supports time-series mode**
- Add optional `period?: "7d" | "30d"` parameter to `useVisitorStats`
- When period is set, fetch from `GET /api/v1/dashboard/visitor-stats?period=<value>` and return `VisitorStatsTimeSeries`
- When period is undefined, preserve existing single-day behavior (backward compatible)
- Auto-refresh behavior (5 min interval) applies to both modes

**AC3 — `fetchVisitorStats` API function updated**
- Add `period?: "7d" | "30d"` parameter to `fetchVisitorStats` in `src/lib/api/dashboard.ts`
- When period is provided, append `?period=...` query string

**AC4 — VisitorStatsCard renders time-series chart alongside metrics**
- Add period selector tabs: **7 days | 30 days** above the chart
- Show a `Recharts LineChart` (or AreaChart) with two lines: visitor_count and inquiry_count
- Use `--chart-1` for visitor_count line, `--chart-4` (purple) for inquiry_count line
- X-axis: dates formatted as `MM/dd`
- Y-axis: left axis for visitor_count, right axis for inquiry_count (or two separate charts stacked)
- Tooltip showing both values on hover
- Below the chart, show the same three metric tiles (total visitors, total inquiries, conversion rate) for the selected period
- When no period selected (yesterday-only mode), render only the three metric tiles — no chart — preserving current behavior for the default DashboardPage view

**AC5 — Graceful degradation preserved**
- If `is_configured=false`, show "PostHog not configured" message (existing behavior)
- If `error` is returned, show error state (existing behavior)
- If `totals.visitor_count === 0 && totals.inquiry_count === 0`, show empty state

**AC6 — Loading state**
- Skeleton shows chart placeholder shape while loading

**AC7 — Test coverage**
- Add `useVisitorStats.test.tsx` test for period-switching behavior
- Add `VisitorStatsCard.test.tsx` test for chart rendering with period data

## Tasks

- [ ] Backend: Extend `backend/domains/dashboard/routes.py` — `GET /visitor-stats` to accept `period: Literal["7d", "30d"] | None = None`
  - When period is `None`: return existing `VisitorStatsResponse` (single day, backward compatible)
  - When period is set: run HogQL query for each day in the window, return `VisitorStatsTimeSeries`
  - Map `inquiry_count` and `visitor_count` per-day from HogQL results
- [ ] Backend: Update `backend/domains/dashboard/schemas.py` — add `VisitorStatsTimeSeries` schema
- [ ] Frontend: Update `src/lib/api/dashboard.ts` — `fetchVisitorStats(period?: "7d" | "30d")`
- [ ] Frontend: Update `src/hooks/useDashboard.ts` — `useVisitorStats(period?: "7d" | "30d")`
- [ ] Frontend: Create `VisitorStatsTimeSeries` type in `src/domain/dashboard/types.ts`
- [ ] Frontend: Update `src/domain/dashboard/components/VisitorStatsCard.tsx` (note: `useVisitorStats` lives in `src/hooks/useDashboard.ts`, not `src/domain/dashboard/hooks/`):
  - Add `period: "7d" | "30d" | null` state
  - Add period tabs (7 days / 30 days / None for yesterday)
  - Render `LineChart` or `AreaChart` from recharts when period is set
  - Keep existing metric tiles below chart
- [ ] Add tests
- [ ] Run `pnpm test` and `pnpm build`

## File Structure

```
src/domain/dashboard/
  types.ts                     — add VisitorStatsTimeSeries
  hooks/useDashboard.ts        — useVisitorStats(period?) update
  components/VisitorStatsCard.tsx — add chart + period tabs
src/lib/api/dashboard.ts       — fetchVisitorStats(period?)
backend/domains/dashboard/
  routes.py                    — extend GET /visitor-stats
  schemas.py                   — add VisitorStatsTimeSeries schema
```

## Recharts Components

```typescript
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend, Area, AreaChart
} from "recharts";
```

Use `AreaChart` with a gradient fill for a richer visual — follow the `RevenueTrendChart` gradient pattern for consistency.

## PostHog HogQL Query Pattern

The existing `get_visitor_stats()` in `posthog_client.py` runs:
```sql
SELECT date, count(DISTINCT distinct_id) AS visitor_count
FROM events
WHERE event = '$pageview'
  AND timestamp >= '2026-04-14'  -- 30d ago
GROUP BY date
ORDER BY date
```

The time-series query should return one row per date. Aggregate with `toDate(timestamp)` for daily grouping.

## Dev Notes

- The existing single-day behavior must be preserved for backward compatibility with any other consumers of `VisitorStatsResponse`
- Conversion rate for the time-series period should be computed as `totals.inquiry_count / totals.visitor_count * 100`
- The `Brush` navigator from `RevenueTrendChart` is optional here since the period is capped at 30 days — use it if the 30-day chart is dense
- Period tab UI should match the pattern in `RevenueTrendChart` — `Tabs`, `TabsList`, `TabsTrigger` components from `src/components/ui/tabs`
