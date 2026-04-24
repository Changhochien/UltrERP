/**
 * Chart Platform - Public Exports
 * 
 * This module exports the public API for the UltrERP chart platform.
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

// Formatters
export {
  formatChartCurrency,
  formatChartQuantity,
  formatChartQuantityCompact,
  formatChartDate,
  formatChartDateCompact,
  formatChartMonth,
  formatChartPercent,
  formatCurrencyAxis,
} from "./formatters";

// Shell and state components
export { ChartShell } from "./ChartShell";
export type { ChartShellProps } from "./ChartShell";

export { ChartStateView } from "./ChartStateView";
export type { ChartStateViewProps } from "./ChartStateView";

export { ChartLegend } from "./ChartLegend";
export type { ChartLegendProps, ChartLegendItem } from "./ChartLegend";

// Control components
export { RangePresetGroup } from "./controls/RangePresetGroup";
export type { RangePreset, RangePresetGroupProps, PresetId } from "./controls/RangePresetGroup";
export { presetToMonths } from "./controls/RangePresetGroup";

export { ChartModeToggle } from "./controls/ChartModeToggle";
export type { ChartMode, ChartModeOption, ChartModeToggleProps } from "./controls/ChartModeToggle";
