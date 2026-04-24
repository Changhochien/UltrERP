/**
 * Chart tier classification based on data density and user interaction needs.
 * summary: Quick KPI snapshots, typically < 20 data points, minimal interaction
 * comparison: Multi-series comparisons, period-over-period analysis, moderate data
 * explorer: Long-history time-series, user-controlled range navigation, high data density
 */
export type ChartTier = "summary" | "comparison" | "explorer";

/**
 * Supported chart renderers.
 * recharts: General-purpose React charting
 * visx: Low-level SVG primitives for custom overlays, projections, and explorer interactions
 */
export type ChartRenderer = "recharts" | "visx";

/**
 * Represents a single data point in a chart series.
 */
export interface ChartSeriesPoint {
  x: string;
  y: number;
  label?: string;
  periodStatus?: "closed" | "partial";
  source?: "aggregate" | "live" | "zero-filled";
}

/**
 * A single series in a chart, with metadata.
 */
export interface ChartSeries<T extends ChartSeriesPoint = ChartSeriesPoint> {
  id: string;
  name: string;
  color: string;
  data: T[];
}

/**
 * Time range metadata for explorer-tier charts.
 * All date strings are ISO 8601 format (YYYY-MM-DD).
 */
export interface ChartRangeMetadata {
  requestedStart: string;
  requestedEnd: string;
  availableStart: string | null;
  availableEnd: string | null;
  defaultVisibleStart: string;
  defaultVisibleEnd: string;
  bucket: "day" | "week" | "month";
  timezone: string;
}

/**
 * A preset time window for quick navigation.
 */
export interface ChartRangePreset {
  label: string;
  id: string;
  months?: number;
  days?: number;
  all?: boolean;
}

/**
 * Standard chart loading states.
 */
export type ChartLoadingState = "idle" | "loading" | "success" | "error";

/**
 * Shared chart state contract for all tiers.
 */
export interface ChartState {
  loadingState: ChartLoadingState;
  errorMessage: string | null;
  isEmpty: boolean;
  series: ChartSeries[];
  range?: ChartRangeMetadata;
}

/**
 * Renderer capability flags.
 */
export interface ChartRendererCapabilities {
  type: ChartRenderer;
  supportedTiers: ChartTier[];
  supportsOverlays: boolean;
  supportsCustomTooltips: boolean;
}

/** recharts renderer capabilities */
export const RECHARTS_CAPABILITIES: ChartRendererCapabilities = {
  type: "recharts",
  supportedTiers: ["summary", "comparison"],
  supportsOverlays: false,
  supportsCustomTooltips: true,
} as const;

/** @visx renderer capabilities */
export const VISX_CAPABILITIES: ChartRendererCapabilities = {
  type: "visx",
  supportedTiers: ["summary", "comparison", "explorer"],
  supportsOverlays: true,
  supportsCustomTooltips: true,
} as const;

/**
 * Owner domain for a chart surface.
 */
export type ChartOwnerDomain = "dashboard" | "inventory" | "intelligence" | "customers";

/**
 * Registration entry for a chart surface.
 */
export interface ChartSurfaceRegistration {
  id: string;
  componentPath: string;
  tier: ChartTier;
  renderer: ChartRenderer;
  owner: ChartOwnerDomain;
  notes: string;
  migrationStatus?: "stable" | "planned" | "in-progress" | "completed";
}

/**
 * Locale-aware formatting options for chart labels.
 */
export interface ChartFormatOptions {
  locale: string;
  currency?: string;
  maximumFractionDigits?: number;
  dateOptions?: Intl.DateTimeFormatOptions;
}

/**
 * Decision outcome for renderer adoption.
 */
export type RendererDecision = "recharts" | "visx" | "defer";

/**
 * Decision criteria for choosing a renderer.
 */
export interface RendererDecisionCriteria {
  needsOverlays: boolean;
  needsCustomGeometry: boolean;
  needsNavigator: boolean;
  estimatedDataPoints: number;
  hasExistingImpl: boolean;
}

/**
 * Apply the decision matrix to determine appropriate renderer.
 */
export function determineRenderer(criteria: RendererDecisionCriteria): RendererDecision {
  if (criteria.needsNavigator || criteria.needsOverlays || criteria.needsCustomGeometry) {
    return "visx";
  }
  return "recharts";
}
