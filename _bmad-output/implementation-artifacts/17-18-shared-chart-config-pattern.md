# Story 17.18: Shared Chart Config Pattern

**Status:** ready-for-dev

## Story

As a developer,
I want a shared `ChartConfig` type and color token utilities that all chart components consume,
so that chart colors, axis labels, and appearance options are declared consistently rather than hardcoded per-component.

## Business Context

Currently every chart in `src/domain/dashboard/components/` hardcodes its own color strings, axis formatters, and appearance options inline. This makes it impossible to:
- Theme the dashboard (light/dark) without editing every chart
- Understand what colors are in use across the dashboard at a glance
- Add new charts without copying color logic from existing ones
- Change the color scheme globally (e.g., for a dark mode or accessibility override)

ERPNext solves this with `custom_options: "{\"type\": \"bar\", \"colors\": [\"#fc4f51\", \"#78d6ff\", \"#7575ff\"]}"` — a JSON blob stored per chart doctype. Our equivalent is a TypeScript config object + CSS custom property tokens.

## Reference

Epic 22 story 22.5 already added `--chart-1` through `--chart-10` to `src/index.css` (lines 57-65 light, 120-129 dark). These tokens exist but are not consumed by any chart component.

`RevenueTrendChart` has `stroke="#6366f1"` hardcoded — this should use a CSS token as part of this story.

## Acceptance Criteria

**AC1 — `ChartConfig` type defined**
- Create `src/domain/dashboard/chartConfig.ts`
- Define `ChartConfig` interface:
  ```typescript
  interface ChartColor {
    token: string;      // CSS variable name e.g. "--chart-2"
    label: string;      // human-readable label e.g. "Inflows"
  }

  interface ChartConfig {
    /** Unique identifier for this chart */
    id: string;
    /** Chart type */
    type: "line" | "bar" | "area" | "donut" | "sparkline";
    /** Ordered list of color assignments for series/slices */
    colors: ChartColor[];
    /** Currency symbol for value formatting (default: "NT$") */
    currency?: string;
    /** Y-axis formatter function name or pattern */
    yAxisFormatter?: (value: number) => string;
    /** X-axis date format pattern */
    xAxisFormat?: string;  // e.g. "MM/dd" or "yyyy-MM"
    /** Whether to show a legend */
    showLegend?: boolean;
    /** Whether to show a Brush navigator (line/area charts) */
    showBrush?: boolean;
    /** Inner radius for donut charts (0-1 as fraction of outerRadius) */
    donutInnerRadius?: number;
    /** Stack ID for bar charts (bars with same stackId are stacked) */
    stackId?: string;
  }
  ```

**AC2 — Color token utility function**
- Export `getChartColor(token: string): string` — reads CSS custom property from `document.documentElement` via `getComputedStyle`
- Export `CHART_COLORS` constant map for the standard 10 chart colors:
  ```typescript
  export const CHART_COLORS = {
    chart1: { token: "--chart-1", cssVar: "var(--chart-1)", label: "Series 1" },
    chart2: { token: "--chart-2", cssVar: "var(--chart-2)", label: "Series 2" },
    // ... through chart10
    destructive: { token: "--destructive", cssVar: "var(--destructive)", label: "Negative/Outflow" },
    success: { token: "--success", cssVar: "var(--success)", label: "Positive/Inflow" },
  } as const;
  ```

**AC3 — Predefined chart configs for existing charts**
- Export reusable `CHART_PRESETS` object with typed configs for all current charts:
  ```typescript
  export const CHART_PRESETS = {
    revenueTrend: {
      id: "revenue-trend",
      type: "area",
      colors: [
        { token: "--primary", label: "Revenue" },
      ],
      yAxisFormatter: (v) => `NT$ ${(v/1000).toFixed(0)}k`,
      showBrush: true,
    } as ChartConfig,
    cashFlow: {
      id: "cash-flow",
      type: "bar",
      colors: [
        { token: "--chart-2", label: "Inflows" },    // green
        { token: "--destructive", label: "Outflows" }, // red
        { token: "--chart-1", label: "Net" },      // blue
      ],
      yAxisFormatter: (v) => `NT$ ${(v/1000).toFixed(0)}k`,
    } as ChartConfig,
    arAging: {
      id: "ar-aging",
      type: "donut",
      donutInnerRadius: 0.6,
      colors: [
        { token: "--chart-2", label: "0-30 days" },
        { token: "--chart-3", label: "31-60 days" },
        { token: "--chart-9", label: "61-90 days" },
        { token: "--destructive", label: "90+ days" },
      ],
    } as ChartConfig,
    visitorStats: {
      id: "visitor-stats",
      type: "area",
      colors: [
        { token: "--chart-1", label: "Visitors" },
        { token: "--chart-4", label: "Inquiries" },
      ],
      showBrush: false,
    } as ChartConfig,
  };
  ```

**AC4 — All chart components updated to use `CHART_PRESETS`**
- `RevenueTrendChart` — use `CHART_PRESETS.revenueTrend`
  - Replace hardcoded `stroke="#6366f1"` → `getChartColor(CHART_COLORS.chart1.token)`
  - Replace gradient `stopColor="#6366f1"` → `getChartColor(CHART_COLORS.chart1.token)`
- `CashFlowCard` (@visx) — use `CHART_PRESETS.cashFlow` for color assignments (follows story 17-16)
- `ARAgingCard` / `APAgingCard` — use `CHART_PRESETS.arAging` for slice colors
- `VisitorStatsCard` (after story 17-17) — use `CHART_PRESETS.visitorStats`; note this card currently has no chart (only metric tiles), so this AC only applies once story 17-17 adds the AreaChart

**AC5 — `SectionCard` header slot accepts chart config for consistent chart chrome**
- Currently each chart manually wraps recharts in `SectionCard` with custom header actions
- After this story, chart components should use a shared `ChartCard` wrapper component:
  ```typescript
  // src/domain/dashboard/components/ChartCard.tsx
  interface ChartCardProps {
    config: ChartConfig;
    title: string;
    description?: string;
    children: React.ReactNode;
    actions?: React.ReactNode; // period tabs, etc.
    isLoading?: boolean;
    error?: string | null;
    onRetry?: () => void;
  }
  ```
  - Handles loading skeleton (responsive container placeholder)
  - Handles error state with retry button
  - Renders header with title + description + actions slot
  - Passes `children` (the chart) through
  - Standardizes card chrome across all chart cards

**AC6 — Documentation**
- Add JSDoc to `ChartConfig` and all exports
- Add example in the file showing how to create a new chart config

## Tasks

- [ ] Create `src/domain/dashboard/chartConfig.ts`:
  - Define `ChartColor` and `ChartConfig` interfaces
  - Export `getChartColor(token: string): string`
  - Export `CHART_COLORS` constant map
  - Export `CHART_PRESETS` with configs for revenueTrend, cashFlow, arAging, visitorStats
- [ ] Update `RevenueTrendChart` to use `CHART_PRESETS.revenueTrend` + `getChartColor`
  - Replace `stroke="#6366f1"` and gradient color
- [ ] Update `CashFlowCard` (after 17-16) to use `CHART_PRESETS.cashFlow` via `getChartColor`
- [ ] Update `ARAgingCard` / `APAgingCard` (after 17-15) to use `CHART_PRESETS.arAging`
- [ ] Update `VisitorStatsCard` (after 17-17) to use `CHART_PRESETS.visitorStats`
- [ ] Create `src/domain/dashboard/components/ChartCard.tsx` shared wrapper
- [ ] Update all chart components to use `ChartCard` wrapper
- [ ] Run `pnpm build` and `pnpm test`

## File Structure

```
src/domain/dashboard/
  chartConfig.ts          — NEW shared chart configuration
  components/
    ChartCard.tsx         — NEW shared chart card wrapper
    RevenueTrendChart.tsx  — use CHART_PRESETS
    CashFlowCard.tsx       — use CHART_PRESETS (after 17-16)
    ARAgingCard.tsx        — use CHART_PRESETS (after 17-15)
    APAgingCard.tsx        — use CHART_PRESETS (after 17-15)
    VisitorStatsCard.tsx   — use CHART_PRESETS (after 17-17)
```

## Dev Notes

- `getChartColor` must handle SSR (server-side rendering where `document` is undefined) — return the CSS variable name as a string directly when `typeof document === "undefined"` so it works in test environments
- The `ChartConfig` interface is intentionally minimal — don't over-engineer it; add fields only when a real chart needs them
- `ChartCard` wraps `SectionCard` internally and adds chart-specific chrome — `SectionCard` is exported from `src/components/layout/PageLayout.tsx`, don't reimplement it
- The `--chart-*` CSS tokens are the design-system source of truth; `CHART_COLORS` is the TypeScript facade over them
- This story does NOT create a JSON-driven workspace config (like ERPNext) — it creates a typed TS config that is consumed by React components. A full workspace JSON engine is a separate architectural decision.
