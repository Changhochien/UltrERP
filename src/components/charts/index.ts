/**
 * Chart Platform - Public Exports
 */

// Types
export type {
  ChartTier,
  ChartRenderer,
  ChartSeriesPoint,
  ChartSeries,
  ChartRangeMetadata,
  ChartRangePreset,
  ChartLoadingState,
  ChartState,
  ChartFormatOptions,
  ChartOwnerDomain,
  ChartSurfaceRegistration,
  RendererDecision,
  RendererDecisionCriteria,
  ChartRendererCapabilities,
} from "./types";

// Registry utilities
export {
  CHART_REGISTRY,
  getChartById,
  getChartsByOwner,
  getChartsByTier,
  getChartsByRenderer,
  getChartsNeedingMigration,
  getMigrationStats,
} from "./registry";

export { RECHARTS_CAPABILITIES, VISX_CAPABILITIES } from "./types";
export { determineRenderer } from "./types";
