# Chart Taxonomy and Migration Matrix

**Status:** Active  
**Last Updated:** 2026-04-24  
**Epic:** 39 - Chart Platform Foundation

## Chart Surface Inventory

This document catalogs all chart surfaces in UltrERP and classifies them into tiers for migration planning.

## Classification Summary

| Tier | Count | Charts |
|------|-------|--------|
| **explorer** | 2 | RevenueTrendChart, StockTrendChart |
| **comparison** | 2 | CashFlowCard, CategoryTrendRadar |
| **summary** | 2 | MonthlyDemandChart, CustomerAnalyticsTab |
| **non-chart** | 8+ | KPI cards, sparklines, data tables |

## Detailed Inventory

### EXPLORER TIER

#### 1. RevenueTrendChart
| Attribute | Value |
|-----------|-------|
| **Path** | `src/domain/dashboard/components/RevenueTrendChart.tsx` |
| **Renderer** | recharts |
| **Data Density** | 30-365 points (varies by granularity) |
| **Owner** | dashboard |
| **Migration Wave** | First (Story 39-5) |

**Rationale for explorer tier:**  
Long history (up to 1 year daily data), has Brush navigator component, multiple granularity levels (day/week/month). Users explore revenue patterns and trends over extended time periods.

**Current interaction model:**
- Period presets: month (30d), quarter (90d), year (1y)
- Brush navigator for zoom/pan
- Load more for extended ranges

**Migration notes:**  
Will adopt explorer kit in Story 39.5, possibly bridging to visx renderer if justified by navigator improvements.

---

#### 2. StockTrendChart
| Attribute | Value |
|-----------|-------|
| **Path** | `src/domain/inventory/components/StockTrendChart.tsx` |
| **Renderer** | @visx |
| **Data Density** | Variable (stock movements, typically 50-200 points) |
| **Owner** | inventory |
| **Migration Wave** | First (Story 39-5) |

**Rationale for explorer tier:**  
Stock movements over time with reorder point reference line, safety stock zone, and stockout projection. Uses 30d/90d/180d/1yr/all presets for time navigation. Users explore inventory levels and stockout risk over extended periods.

**Current interaction model:**
- Time range presets: 30d, 90d, 180d, 1yr, all
- Reference line for reorder point
- Projected future line (dashed) for stockout forecast
- Color-coded dots by reason code

**Migration notes:**  
Already uses @visx, will adopt explorer kit in Story 39.5 for consistent range controls.

---

### COMPARISON TIER

#### 3. CashFlowCard
| Attribute | Value |
|-----------|-------|
| **Path** | `src/domain/dashboard/components/CashFlowCard.tsx` |
| **Renderer** | @visx |
| **Data Density** | 8-12 points (weekly periods) |
| **Owner** | dashboard |
| **Migration Wave** | Second (Story 39-6) |

**Rationale for comparison tier:**  
Weekly inflows vs outflows comparison. Fixed 8-12 week window. Not exploratory - users compare periods side by side.

**Current interaction model:**
- Static chart with tooltip on hover
- No range navigation
- Grouped bars for inflow/outflow

**Migration notes:**  
Will standardize shell and formatting in Story 39.6. No renderer change needed.

---

#### 4. CategoryTrendRadar
| Attribute | Value |
|-----------|-------|
| **Path** | `src/domain/intelligence/components/CategoryTrendRadar.tsx` |
| **Renderer** | recharts |
| **Data Density** | 5-15 points (categories) |
| **Owner** | intelligence |
| **Migration Wave** | Second (Story 39-6) |

**Rationale for comparison tier:**  
Prior vs current period comparison for category performance. Fixed 30d/90d/12m windows. Not exploratory - users compare category performance across fixed periods.

**Current interaction model:**
- Period presets: 30d, 90d, 12m
- Color-coded bars (growing=green, declining=red)
- Tooltip for details

**Migration notes:**  
Will standardize shell and formatting in Story 39.6. No renderer change needed.

---

### SUMMARY TIER

#### 5. MonthlyDemandChart
| Attribute | Value |
|-----------|-------|
| **Path** | `src/domain/inventory/components/MonthlyDemandChart.tsx` |
| **Renderer** | @visx |
| **Data Density** | 12-24 points (monthly) |
| **Owner** | inventory |
| **Migration Wave** | First (Story 39-5) |

**Rationale for summary tier (candidate for explorer upgrade):**  
Currently summary tier with 12-24 month window and bar/line toggle. However, users need to see longer demand history for operational planning. Story 39.5 will upgrade to explorer tier with dense backend.

**Current interaction model:**
- Bar/line variant toggle
- Simple tooltip
- No range navigation

**Migration notes:**  
Story 39.5 will upgrade to explorer tier with dense time-series backend. Will gain navigator and visible range controls.

---

#### 6. CustomerAnalyticsTab (Revenue Trend)
| Attribute | Value |
|-----------|-------|
| **Path** | `src/components/customers/CustomerAnalyticsTab.tsx` |
| **Renderer** | recharts |
| **Data Density** | 12 points (12 months) |
| **Owner** | customers |
| **Migration Wave** | Second (Story 39-6) |

**Rationale for summary tier:**  
Single customer revenue over fixed 12-month window. Fixed comparison, not exploratory. Users view a customer's revenue history, not explore patterns.

**Current interaction model:**
- Static 12-month view
- Tooltip for details
- Gradient area fill

**Migration notes:**  
Will standardize shell and formatting in Story 39.6. Keep as summary tier.

---

## Non-Chart Surfaces (DO NOT MIGRATE)

These surfaces are **not charts** and should not be force-migrated into the chart architecture:

### KPI Cards and Sparklines

| Component | Path | Reason |
|-----------|------|--------|
| RevenueCard | `src/domain/dashboard/components/RevenueCard.tsx` | Metric card with sparkline |
| KPISummaryCard | `src/domain/dashboard/components/KPISummaryCard.tsx` | Key-value pairs only |
| MetricCards | `src/domain/inventory/components/MetricCards.tsx` | SKU counts, alerts |

*Note: `MetricSparkline` in PageLayout.tsx is a lightweight polyline, not a chart.*

### Data Tables

These are **data tables** with optional progress bars, not chart visualizations:

| Component | Path |
|-----------|------|
| RevenueDiagnosisCard | `src/domain/intelligence/components/RevenueDiagnosisCard.tsx` |
| ProductPerformanceCard | `src/domain/intelligence/components/ProductPerformanceCard.tsx` |
| CustomerBuyingBehaviorCard | `src/domain/intelligence/components/CustomerBuyingBehaviorCard.tsx` |
| AffinityMatrix | `src/domain/intelligence/components/AffinityMatrix.tsx` |

---

## Migration Matrix

### First Wave (Stories 39-2, 39-4, 39-5)

| Chart | Current State | Target State | Dependencies |
|-------|---------------|--------------|--------------|
| MonthlyDemandChart | summary, visx | explorer, visx | 39-2 backend, 39-4 kit |
| StockTrendChart | explorer, visx | explorer, visx (consolidated kit) | 39-2 backend, 39-4 kit |
| RevenueTrendChart | explorer, recharts | explorer, visx (or bridged) | 39-2 backend, 39-4 kit |

### Second Wave (Story 39-6)

| Chart | Current State | Target State | Dependencies |
|-------|---------------|--------------|--------------|
| CashFlowCard | comparison, visx | comparison, visx (shared shell) | 39-3 shell |
| CategoryTrendRadar | comparison, recharts | comparison, recharts (shared shell) | 39-3 shell |
| CustomerAnalyticsTab | summary, recharts | summary, recharts (shared shell) | 39-3 shell |

### Non-Chart Holdouts

| Surface | Decision | Rationale |
|---------|----------|-----------|
| RevenueCard | Keep as-is | KPI card, not a chart |
| MetricSparkline | Keep as-is | Lightweight visualization |
| Intelligence tables | Keep as-is | Data tables, not charts |

---

## Future Considerations

### Optional: Lightweight Charts Adapter
A future adapter for TradingView's Lightweight Charts may be added for high-performance financial charts, but this is **not a prerequisite** for Epic 39 completion.

### Optional: Comparison Tier Enhancements
Period-over-period comparison charts may benefit from:
- Automatic prior period calculation
- Growth/delta indicators
- Period comparison legend

These enhancements are **out of scope** for v1.

---

## References

- [Chart Platform Architecture](./chart-platform-architecture.md)
- [Story 39-1 Implementation](../_bmad-output/implementation-artifacts/39-1-chart-taxonomy-platform-contract-and-migration-matrix.md)
