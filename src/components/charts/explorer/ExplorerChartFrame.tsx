/**
 * ExplorerChartFrame - Explorer-tier chart wrapper component.
 * 
 * Composes:
 * - Range preset controls
 * - Detail chart
 * - Overview navigator (optional)
 * - Chart state handling
 */

import type { ReactNode } from "react";

import { ChartStateView } from "../ChartStateView";
import { RangePresetGroup } from "../controls/RangePresetGroup";
import { useExplorerRange } from "./useExplorerRange";
import { OverviewNavigator } from "./OverviewNavigator";

export interface ExplorerChartFrameProps {
  /** Chart title */
  title?: string;
  /** Chart description */
  description?: string;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
  /** Whether data is empty */
  empty?: boolean;
  /** Empty message */
  emptyMessage?: string;
  /** Retry handler */
  onRetry?: () => void;
  /** Available data range from backend */
  availableRange: { start: string; end: string };
  /** Default visible range from backend */
  defaultVisibleRange: { start: string; end: string };
  /** Current visible range (controlled) */
  visibleRange?: { start: string; end: string };
  /** Visible range change handler (controlled) */
  onVisibleRangeChange?: (range: { start: string; end: string }) => void;
  /** Selected preset */
  selectedPreset?: string | null;
  /** Preset change handler */
  onPresetChange?: (preset: string) => void;
  /** Show overview navigator */
  showNavigator?: boolean;
  /** Chart content to render */
  children: ReactNode;
  /** Chart controls (mode toggle, etc.) */
  controls?: ReactNode;
  /** Additional className */
  className?: string;
}

/**
 * ExplorerChartFrame provides a complete explorer chart wrapper with:
 * - Range preset navigation
 * - Overview navigator
 * - State handling
 */
export function ExplorerChartFrame({
  title,
  description,
  loading,
  error,
  empty,
  emptyMessage,
  onRetry,
  availableRange,
  defaultVisibleRange,
  visibleRange: controlledVisibleRange,
  onVisibleRangeChange,
  selectedPreset: controlledPreset,
  onPresetChange,
  showNavigator = true,
  children,
  controls,
  className = "",
}: ExplorerChartFrameProps) {
  // Use controlled or internal state
  const {
    visibleRange: internalVisibleRange,
    selectedPreset: internalPreset,
    applyPreset,
    updateVisibleRange,
  } = useExplorerRange({
    availableRange,
    defaultVisibleRange,
  });

  const visibleRange = controlledVisibleRange ?? internalVisibleRange;
  const selectedPreset = controlledPreset ?? internalPreset;

  const handlePresetChange = (preset: "3M" | "6M" | "1Y" | "2Y" | "4Y" | "All") => {
    applyPreset(preset);
    onPresetChange?.(preset);
  };

  const handleRangeChange = (range: { start: string; end: string }) => {
    updateVisibleRange(range);
    onVisibleRangeChange?.(range);
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header with title and controls */}
      {(title || controls) && (
        <div className="flex items-center justify-between gap-4">
          <div>
            {title && <h3 className="text-sm font-medium">{title}</h3>}
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {controls}
          </div>
        </div>
      )}

      {/* Preset controls */}
      <div className="flex items-center justify-between">
        <RangePresetGroup
          value={selectedPreset as "3M" | "6M" | "1Y" | "2Y" | "4Y" | "All"}
          onChange={handlePresetChange}
          aria-label="Chart time range"
        />
        {controls}
      </div>

      {/* Chart state view */}
      <ChartStateView
        loading={loading}
        error={error}
        empty={empty}
        emptyMessage={emptyMessage}
        onRetry={onRetry}
      >
        {children}
      </ChartStateView>

      {/* Overview navigator */}
      {showNavigator && !loading && !error && !empty && (
        <div className="mt-2">
          <OverviewNavigator
            loadedRange={availableRange}
            visibleRange={visibleRange}
            onRangeChange={handleRangeChange}
            height={48}
            className="rounded-lg border bg-muted/30"
          >
            {/* Miniature chart - placeholder for now */}
            <div className="h-full" />
          </OverviewNavigator>
        </div>
      )}
    </div>
  );
}
