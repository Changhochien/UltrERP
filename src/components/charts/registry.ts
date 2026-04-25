/**
 * Chart Surface Registry
 * 
 * Typed registry of all chart surfaces in UltrERP.
 * Used for migration tracking, architecture review, and identifying charts needing updates.
 */

import type { ChartSurfaceRegistration } from "./types";

/**
 * Complete registry of all chart surfaces.
 * 
 * EXPLORER TIER:
 * - RevenueTrendChart: Long history with Brush navigator and shared formatter contract.
 * - StockTrendChart: Stock movements with projections, shared explorer controls, and overview navigator.
 * 
 * COMPARISON TIER:
 * - CashFlowCard: Weekly inflows/outflows. Fixed 8-12 week window.
 * - CategoryTrendRadar: Prior vs current period. Fixed 30d/90d/12m windows.
 * 
 * SUMMARY TIER:
 * - MonthlyDemandExplorerChart: Single product monthly demand with dense monthly explorer data.
 * - CustomerAnalyticsTab: Single customer revenue over fixed 12-month window.
 */

export const CHART_REGISTRY: ChartSurfaceRegistration[] = [
  // DASHBOARD CHARTS
  {
    id: "dashboard-revenue-trend",
    componentPath: "src/domain/dashboard/components/RevenueTrendChart.tsx",
    tier: "explorer",
    renderer: "recharts",
    owner: "dashboard",
    notes: "Long history revenue visualization with Brush navigator and shared currency formatting. Uses month/quarter/year presets with recharts bridge semantics for v1.",
    migrationStatus: "completed",
  },
  {
    id: "dashboard-cash-flow",
    componentPath: "src/domain/dashboard/components/CashFlowCard.tsx",
    tier: "comparison",
    renderer: "visx",
    owner: "dashboard",
    notes: "Weekly inflows/outflows comparison. Fixed 8-12 week window. Simple @visx bar chart with shared currency formatting and existing Card shell.",
    migrationStatus: "completed",
  },

  // INVENTORY CHARTS
  {
    id: "inventory-stock-trend",
    componentPath: "src/domain/inventory/components/StockTrendChart.tsx",
    tier: "explorer",
    renderer: "visx",
    owner: "inventory",
    notes: "Stock movements with reorder point, safety stock zone, stockout projection, shared explorer presets, and overview navigator.",
    migrationStatus: "completed",
  },
  {
    id: "inventory-monthly-demand",
    componentPath: "src/domain/inventory/components/MonthlyDemandExplorerChart.tsx",
    tier: "explorer",
    renderer: "visx",
    owner: "inventory",
    notes: "Single product monthly demand with dense backend data, bar/line variant toggle, shared explorer presets, and overview navigator.",
    migrationStatus: "completed",
  },

  // INTELLIGENCE CHARTS
  {
    id: "intelligence-category-trend",
    componentPath: "src/domain/intelligence/components/CategoryTrendRadar.tsx",
    tier: "comparison",
    renderer: "recharts",
    owner: "intelligence",
    notes: "Category performance prior vs current period. Fixed 30d/90d/12m windows with shared currency formatting and no explorer controls.",
    migrationStatus: "completed",
  },

  // CUSTOMER CHARTS
  {
    id: "customers-revenue-trend",
    componentPath: "src/components/customers/CustomerAnalyticsTab.tsx",
    tier: "summary",
    renderer: "recharts",
    owner: "customers",
    notes: "Single customer revenue over fixed 12-month window with shared currency formatting. Fixed comparison, not exploratory.",
    migrationStatus: "completed",
  },
];

/**
 * Lookup a chart surface by its ID.
 */
export function getChartById(id: string): ChartSurfaceRegistration | undefined {
  return CHART_REGISTRY.find((chart) => chart.id === id);
}

/**
 * Get all charts for a specific owner domain.
 */
export function getChartsByOwner(owner: ChartSurfaceRegistration["owner"]): readonly ChartSurfaceRegistration[] {
  return CHART_REGISTRY.filter((chart) => chart.owner === owner);
}

/**
 * Get all charts for a specific tier.
 */
export function getChartsByTier(tier: ChartSurfaceRegistration["tier"]): readonly ChartSurfaceRegistration[] {
  return CHART_REGISTRY.filter((chart) => chart.tier === tier);
}

/**
 * Get all charts for a specific renderer.
 */
export function getChartsByRenderer(renderer: ChartSurfaceRegistration["renderer"]): readonly ChartSurfaceRegistration[] {
  return CHART_REGISTRY.filter((chart) => chart.renderer === renderer);
}

/**
 * Get charts that need migration.
 */
export function getChartsNeedingMigration(): readonly ChartSurfaceRegistration[] {
  return CHART_REGISTRY.filter((chart) => 
    chart.migrationStatus === "planned" || chart.migrationStatus === "in-progress"
  );
}

/**
 * Get migration statistics.
 */
export function getMigrationStats(): {
  total: number;
  byTier: Record<string, number>;
  byRenderer: Record<string, number>;
  byStatus: Record<string, number>;
} {
  const countBy = <K extends keyof ChartSurfaceRegistration>(key: K, getValue?: (c: ChartSurfaceRegistration) => string) =>
    CHART_REGISTRY.reduce((acc, chart) => {
      const value = getValue ? getValue(chart) : String(chart[key]);
      acc[value] = (acc[value] ?? 0) + 1;
      return acc;
    }, {} as Record<string, number>);

  return {
    total: CHART_REGISTRY.length,
    byTier: countBy("tier"),
    byRenderer: countBy("renderer"),
    byStatus: countBy("migrationStatus", (c) => c.migrationStatus ?? "stable"),
  };
}
