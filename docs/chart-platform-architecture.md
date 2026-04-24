# Chart Platform Architecture

**Status:** Active  
**Last Updated:** 2026-04-24  
**Epic:** 39 - Chart Platform Foundation

## Overview

This document defines the shared architecture contract for all chart surfaces in UltrERP. The goal is consistent chart behavior across dashboard, inventory, intelligence, and customer surfaces while respecting domain ownership.

## Architecture Principles

1. **Standardize the architecture, not a single universal component**  
   Different chart tiers have different needs. An explorer chart needs a navigator; a summary chart needs clarity, not complexity.

2. **Keep domain data ownership local**  
   Domain hooks and API helpers own data fetching. The chart platform provides presentation primitives only.

3. **Shared primitives, not shared super-components**  
   Reusable chart shells, controls, and formatters belong in `src/components/charts/`. Domain-specific chart logic stays in domain folders.

## Chart Tier System

### Tier Definitions

| Tier | Use Case | Data Density | Navigation |
|------|----------|--------------|------------|
| **summary** | KPI snapshots, single-metric trends | < 20 points | Period presets only |
| **comparison** | Period-over-period, multi-series | 5-50 points | Period presets, legend toggles |
| **explorer** | Long-history time-series, operational signals | 50-1000+ points | Brush/navigator, visible range |

### Tier Assignment

See [chart-taxonomy.md](./chart-taxonomy.md) for the complete inventory and classification rationale.

## Renderer Decision Matrix

### When to Use recharts

- ✅ Summary and comparison tier charts
- ✅ Standard line, bar, area charts
- ✅ When no custom overlays are needed
- ✅ Quick prototyping for new chart surfaces

### When to Use @visx

- ✅ Explorer tier charts requiring brush/navigator
- ✅ Custom reference lines (ROP, safety zones)
- ✅ Stockout projections and overlays
- ✅ Custom SVG geometry beyond standard chart types
- ✅ Precise control over rendering behavior

### When to Defer

- ❌ Complex custom visualizations (defer until real need emerges)
- ❌ Heavy 3D or geographic charts (out of scope for v1)
- ❌ Replacing a working chart just for consistency

### Decision Flowchart

```
Start
  │
  ▼
Needs navigator or brush? ──Yes──▶ Use @visx
  │
  No
  │
  ▼
Needs custom SVG overlays or reference lines? ──Yes──▶ Use @visx
  │
  No
  │
  ▼
Data density > 100 points with exploration intent? ──Yes──▶ Use @visx
  │
  No
  │
  ▼
Standard line/bar/area chart? ──Yes──▶ Use recharts
  │
  No
  │
  ▼
Consult architecture team before proceeding
```

## Backend Contract for Explorer Charts

Explorer-tier charts require dense, range-aware time-series data from the backend.

### Required Response Shape

```json
{
  "points": [
    {
      "bucket_start": "2026-01-01",
      "bucket_label": "2026-01",
      "value": 0,
      "is_zero_filled": true,
      "period_status": "closed",
      "source": "zero-filled"
    }
  ],
  "range": {
    "requested_start": "2023-01-01",
    "requested_end": "2026-12-01",
    "available_start": "2024-02-01",
    "available_end": "2026-04-01",
    "default_visible_start": "2025-05-01",
    "default_visible_end": "2026-04-01",
    "bucket": "month",
    "timezone": "Asia/Taipei"
  }
}
```

### Key Metadata Fields

| Field | Description |
|-------|-------------|
| `requested_start/end` | User-requested time window |
| `available_start/end` | Actual data bounds (null if no data) |
| `default_visible_start/end` | Initial viewport |
| `bucket` | Granularity: "day" \| "week" \| "month" |
| `timezone` | IANA timezone (e.g., "Asia/Taipei") |
| `period_status` | "closed" (historical) \| "partial" (current) |
| `source` | "aggregate" \| "live" \| "zero-filled" |

### v1 Support Envelope

- Maximum 120 monthly points per response
- Maximum 730 daily points per response
- Coarser bucketing for requests exceeding limits

## Frontend State Model

### Loaded Range vs Visible Range

For explorer charts, maintain two separate range states:

```typescript
interface ExplorerRange {
  start: string; // ISO date
  end: string;   // ISO date
}

interface UseExplorerRangeReturn {
  // Full data window from backend
  loadedRange: ExplorerRange;
  // User's current viewport
  visibleRange: ExplorerRange;
  // Navigation actions
  applyPreset: (preset: PresetId) => void;
  updateVisibleRange: (range: ExplorerRange) => void;
  reset: () => void;
}
```

### Preset Windows

| Preset | Months | Notes |
|--------|--------|-------|
| 3M | 3 | Short-term view |
| 6M | 6 | Medium-term view |
| 1Y | 12 | Standard year view |
| 2Y | 24 | Extended view |
| 4Y | 48 | Long-term view |
| All | - | Full available range |

## Shared Control Primitives

All chart controls should use shared primitives from `src/components/charts/controls/`:

- `RangePresetGroup`: Period preset button group
- `ChartModeToggle`: Bar/line view toggle

### Control Accessibility

All controls must implement:
- Proper `aria-label` attributes
- `aria-pressed` for toggle states
- Keyboard navigation support
- Focus indicators

## File Organization

```
src/components/charts/
├── types.ts              # Platform type contracts
├── registry.ts           # Chart surface registry
├── formatters.ts         # Locale-aware formatting helpers
├── ChartShell.tsx        # Section/card wrapper with states
├── ChartStateView.tsx    # Loading/error/empty state handler
├── ChartLegend.tsx       # Shared legend component
├── controls/
│   ├── RangePresetGroup.tsx
│   └── ChartModeToggle.tsx
├── explorer/
│   ├── useExplorerRange.ts    # Range state hook
│   ├── OverviewNavigator.tsx   # Brush/strip navigator
│   └── ExplorerChartFrame.tsx # Explorer wrapper
└── index.ts             # Public exports
```

## Migration Waves

### First Wave (Stories 39-2, 39-4, 39-5)
- Backend dense time-series contracts
- Frontend explorer kit
- RevenueTrendChart, StockTrendChart, MonthlyDemandChart

### Second Wave (Story 39-6)
- CashFlowCard shell standardization
- CategoryTrendRadar shell standardization
- CustomerAnalyticsTab shell standardization

### Non-Migration Holdouts
- KPI cards and sparklines (not charts)
- Intelligence tables (data tables, not charts)

## PR Review Checklist

When adding or modifying a chart:

- [ ] Updated `src/components/charts/registry.ts` with new/modified chart entry
- [ ] Documented tier classification rationale
- [ ] If explorer tier: using `useExplorerRange` hook
- [ ] If comparison tier: using shared shell and formatters
- [ ] If summary tier: keeping complexity minimal
- [ ] Controls use shared primitives (no one-off button groups)
- [ ] Loading/error/empty states handled consistently
- [ ] i18n locale passed to formatters (not hardcoded)
- [ ] Accessibility: keyboard nav, screen reader labels

## References

- [Chart Taxonomy](./chart-taxonomy.md)
- [Story 39-1: Chart Taxonomy and Platform Contract](../_bmad-output/implementation-artifacts/39-1-chart-taxonomy-platform-contract-and-migration-matrix.md)
- [Story 39-2: Dense Time-Series Backend](../_bmad-output/implementation-artifacts/39-2-dense-time-series-backend-contracts-and-range-semantics.md)
- [Story 39-3: Shared Frontend Chart Shell](../_bmad-output/implementation-artifacts/39-3-shared-frontend-chart-shell-and-control-primitives.md)
- [Story 39-4: Explorer Time-Series Kit](../_bmad-output/implementation-artifacts/39-4-explorer-time-series-kit.md)
- [Story 39-5: First-Wave Migration](../_bmad-output/implementation-artifacts/39-5-first-wave-explorer-migration.md)
- [Story 39-6: Summary/Comparison Standardization](../_bmad-output/implementation-artifacts/39-6-summary-and-comparison-chart-standardization-and-governance.md)
